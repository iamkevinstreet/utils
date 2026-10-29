########################################################################
#                        llm/kds/llm/adapter.py                        #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The one object every project calls a model       #
#                     through: retries, JSON, cost, budget, logs.      #
########################################################################
"""The model adapter.

- uses the provider the settings name, or one passed in (tests pass
  the offline fake)
- retries failures that can succeed later, with capped, jittered
  backoff, and never retries ones that cannot
- validates structured output against a pydantic model, with one
  repair attempt
- prices every call and stops a run at its budget
- logs every call with its request id, tokens, latency and cost
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Final

from pydantic import BaseModel

from kds.llm import structured
from kds.llm.base import Provider
from kds.llm.errors import BudgetExceededError, StructuredOutputError, is_transient
from kds.llm.pricing import estimate_cost
from kds.llm.providers import build_provider
from kds.llm.types import Completion, Message, ToolSpec
from kds.logs import current_request_id, log_event
from kds.settings import Settings, get_settings

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the first retry's longest wait, in seconds")
BACKOFF_BASE_S = 0.5
# log.debug("Sets the longest wait between retries, in seconds")
BACKOFF_CAP_S = 8.0
# log.debug("Sets the decimal places spend is logged with")
SPEND_PLACES = 6
# log.debug("Names the speaker of a prompt")
USER: Final = "user"
# log.debug("Names the request key that holds the model")
MODEL: Final = "model"
# log.debug("Sets the request the repair turn sends after a bad answer")
REPAIR = "That did not validate: {error}. Return the corrected JSON object only."


# log.debug("Defines the wait before a given retry")
def backoff(attempt: int) -> float:
    """Return a random wait up to 0.5s, 1s, 2s ... capped at 8s.

    "Full jitter": spreading retries at random stops many clients
    that failed together from retrying together.
    """
    # log.debug("Doubles the ceiling each attempt, up to the cap")
    ceiling = min(BACKOFF_CAP_S, BACKOFF_BASE_S * 2**attempt)
    # log.debug("Returns a random wait under the ceiling")
    return random.uniform(0, ceiling)  # noqa: S311 - timing jitter, not security


# log.debug("Defines how a prompt becomes a conversation")
def as_turns(messages: list[Message] | str) -> list[Message]:
    """Return the conversation; a plain string becomes one user turn."""
    # log.debug("Wraps a string as a single user turn")
    return [Message(role=USER, content=messages)] if isinstance(messages, str) else messages


# log.debug("Defines the adapter")
class ModelAdapter:
    """Calls a model, and keeps the run's calls, spend and budget."""

    # log.debug("Defines the constructor")
    def __init__(
        self,
        provider: Provider | None = None,
        *,
        model: str | None = None,
        settings: Settings | None = None,
        budget_usd: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Build an adapter from settings, overriding what is passed.

        Args:
            provider: The provider to call; built from settings if None.
            model: The model to use; `llm_model` if None.
            settings: The settings; the shared ones if None.
            budget_usd: The spending limit; `eval_budget_usd` if None.
            sleep: How to wait between retries; tests pass a no-op.
        """
        # log.debug("Keeps the settings, shared ones unless given")
        self.settings = settings or get_settings()
        # log.debug("Keeps the provider, built from settings unless given")
        self.provider = provider or build_provider(self.settings)
        # log.debug("Keeps the model, from settings unless given")
        self.model = model or self.settings.llm_model
        # log.debug("Keeps the budget, from settings unless given")
        self.budget_usd = self.settings.eval_budget_usd if budget_usd is None else budget_usd
        # log.debug("Keeps the wait function")
        self.sleep = sleep
        # log.debug("Starts the run's spend at zero")
        self.spent_usd = 0.0
        # log.debug("Starts the run's record of calls")
        self.calls: list[Completion] = []

    # log.debug("Defines one call to the model")
    def complete(
        self,
        messages: list[Message] | str,
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        model: str | None = None,
    ) -> Completion:
        """Call the model once, with retries; price and log the call.

        Raises:
            BudgetExceededError: The run has already spent its budget.
        """
        # log.debug("Stops before calling when the budget is spent")
        if self.spent_usd > self.budget_usd:
            # log.debug("Raises with the spend and the limit")
            msg = f"spent ${self.spent_usd:.4f} of the ${self.budget_usd:.2f} budget"
            # log.debug("Raises it")
            raise BudgetExceededError(msg)
        # log.debug("Turns a plain string into a one-message conversation")
        turns = as_turns(messages)
        # log.debug("Calls the provider, retrying what can succeed later")
        completion = self._call_with_retries(
            {
                MODEL: model or self.model,
                "messages": turns,
                "system": system,
                "tools": tools,
                "max_tokens": max_tokens or self.settings.llm_max_tokens,
                "temperature": self.settings.llm_temperature,
                "json_mode": json_mode,
            }
        )
        # log.debug("Prices, records and logs the call, then returns it")
        return self._record(completion)

    # log.debug("Defines the retry loop around one provider call")
    def _call_with_retries(self, request: dict[str, Any]) -> Completion:
        """Call the provider; retry transient failures with backoff."""
        # log.debug("Counts attempts from one")
        attempt = 1
        # log.debug("Tries until a call succeeds or retrying cannot help")
        while True:
            # log.debug("Tries the call")
            try:
                # log.debug("Returns the completion when the call succeeds")
                return self.provider.complete(**request)
            except Exception as error:
                # log.debug("Gives up on a failure retrying cannot fix, or the last try")
                if attempt > self.settings.llm_max_retries or not is_transient(error):
                    # log.debug("Logs the failure before passing it on")
                    log_event(
                        log,
                        "llm.error",
                        logging.WARNING,
                        model=request[MODEL],
                        attempt=attempt,
                        error=type(error).__name__,
                    )
                    # log.debug("Re-raises the original error")
                    raise
                # log.debug("Picks a jittered wait for this attempt")
                delay = backoff(attempt)
                # log.debug("Logs the retry and the wait")
                log_event(
                    log,
                    "llm.retry",
                    model=request[MODEL],
                    attempt=attempt,
                    delay_s=round(delay, 2),
                    error=type(error).__name__,
                )
                # log.debug("Waits before trying again")
                self.sleep(delay)
                # log.debug("Counts the next attempt")
                attempt += 1

    # log.debug("Defines the bookkeeping after a successful call")
    def _record(self, completion: Completion) -> Completion:
        """Price the call, add it to the spend, log it, return it."""
        # log.debug("Prices the call at list price")
        completion.cost_usd = estimate_cost(completion.model, completion.usage)
        # log.debug("Stamps the call with the current request id")
        completion.request_id = current_request_id()
        # log.debug("Adds the cost to the spend, or logs a missing price")
        if completion.cost_usd is None:
            # log.debug("Logs that the model has no price in the table")
            log_event(log, "llm.unpriced_model", logging.WARNING, model=completion.model)
        else:
            # log.debug("Adds the call's cost to the run's spend")
            self.spent_usd += completion.cost_usd
        # log.debug("Keeps the call in the run's record")
        self.calls.append(completion)
        # log.debug("Logs the call's provider, tokens, time and cost")
        log_event(
            log,
            "llm.call",
            provider=completion.provider,
            model=completion.model,
            input_tokens=completion.usage.input_tokens,
            output_tokens=completion.usage.output_tokens,
            latency_ms=completion.latency_ms,
            cost_usd=completion.cost_usd,
            stop_reason=completion.stop_reason,
            tool_calls=[call.name for call in completion.tool_calls],
            spent_usd=round(self.spent_usd, SPEND_PLACES),
        )
        # log.debug("Returns the priced completion")
        return completion

    # log.debug("Defines a call whose answer must match a schema")
    def complete_json[T: BaseModel](
        self,
        messages: list[Message] | str,
        schema: type[T],
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> tuple[T, Completion]:
        """Ask for JSON matching `schema`; on a mismatch, repair once.

        Raises:
            StructuredOutputError: The repaired answer still fails.
        """
        # log.debug("Turns a plain string into a one-message conversation")
        turns = as_turns(messages)
        # log.debug("Adds the schema to the system prompt")
        prompt = structured.schema_prompt(system, schema)
        # log.debug("Asks for the JSON answer")
        first = self.complete(
            turns, system=prompt, max_tokens=max_tokens, json_mode=True, model=model
        )
        # log.debug("Tries to parse the first answer")
        try:
            # log.debug("Returns the parsed answer and its completion")
            return structured.parse(schema, first.text), first
        except ValueError as error:  # ValidationError and JSON errors are ValueErrors
            # log.debug("Shows the model its answer and the error, once")
            repair = [
                *turns,
                Message(role="assistant", content=first.text),
                Message(role=USER, content=REPAIR.format(error=error)),
            ]
        # log.debug("Asks for the corrected answer")
        second = self.complete(
            repair, system=prompt, max_tokens=max_tokens, json_mode=True, model=model
        )
        # log.debug("Tries to parse the corrected answer")
        try:
            # log.debug("Returns the parsed answer and its completion")
            return structured.parse(schema, second.text), second
        except ValueError as error:
            # log.debug("Gives up, keeping the validation error as the cause")
            raise StructuredOutputError(str(error)) from error

    # log.debug("Defines embeddings through the configured provider")
    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        """Return one vector per text from the embedding model."""
        # log.debug("Returns the provider's vectors")
        return self.provider.embed(model=model or self.settings.llm_embedding_model, texts=texts)


# log.debug("Defines the process-wide adapter")
@lru_cache(maxsize=1)
def get_adapter() -> ModelAdapter:
    """Return one adapter built from settings, shared by the process.

    Tests build their own `ModelAdapter(FakeProvider(...))` instead.
    """
    # log.debug("Builds the adapter once")
    return ModelAdapter()
