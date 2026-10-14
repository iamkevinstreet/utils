"""The one object every prototype talks to.

- picks the provider from settings (or takes one explicitly, which is how tests inject the fake)
- retries transient failures with backoff
- validates structured output against a pydantic model, with one repair attempt
- accounts for cost and enforces the run budget
- logs every call with a request id, token counts, latency and cost (prompts are redacted)
"""

from __future__ import annotations

import json
import re
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from kds.llm.base import Provider
from kds.llm.pricing import estimate_cost
from kds.llm.types import Completion, Message, ToolSpec
from kds.logs import current_request_id, get_logger, log_event
from kds.settings import Settings, get_settings

T = TypeVar("T", bound=BaseModel)

_log = get_logger("kds.llm")
_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class BudgetExceededError(RuntimeError):
    pass


class StructuredOutputError(ValueError):
    pass


def _build_provider(settings: Settings) -> Provider:
    if settings.llm_provider == "anthropic":
        from kds.llm.anthropic_provider import AnthropicProvider

        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        return AnthropicProvider(settings.anthropic_api_key.get_secret_value())
    if settings.llm_provider == "openai":
        from kds.llm.openai_provider import OpenAIProvider

        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return OpenAIProvider(settings.openai_api_key.get_secret_value())
    if settings.llm_provider == "azure":
        from kds.llm.openai_provider import OpenAIProvider

        if not (settings.azure_openai_api_key and settings.azure_openai_endpoint):
            raise RuntimeError("AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT are not set")
        return OpenAIProvider(
            settings.azure_openai_api_key.get_secret_value(),
            azure_endpoint=settings.azure_openai_endpoint,
            azure_api_version=settings.azure_openai_api_version,
        )
    from kds.llm.fake import FakeProvider

    return FakeProvider()


class ModelAdapter:
    def __init__(
        self,
        provider: Provider | None = None,
        *,
        model: str | None = None,
        settings: Settings | None = None,
        budget_usd: float | None = None,
        max_retries: int = 3,
    ):
        self.settings = settings or get_settings()
        self.provider = provider or _build_provider(self.settings)
        self.model = model or self.settings.llm_model
        self.budget_usd = self.settings.eval_budget_usd if budget_usd is None else budget_usd
        self.max_retries = max_retries
        self.spent_usd = 0.0
        self.calls: list[Completion] = []

    # ----- core call -------------------------------------------------------------------------------------

    def complete(
        self,
        messages: list[Message] | str,
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        json_mode: bool = False,
        model: str | None = None,
    ) -> Completion:
        if isinstance(messages, str):
            messages = [Message(role="user", content=messages)]
        chosen_model = model or self.model
        if self.spent_usd > self.budget_usd:
            raise BudgetExceededError(f"spent ${self.spent_usd:.4f} of ${self.budget_usd:.2f} budget")
        attempt = 0
        while True:
            attempt += 1
            try:
                completion = self.provider.complete(
                    model=chosen_model,
                    messages=messages,
                    system=system,
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                )
                break
            except Exception as exc:  # noqa: BLE001 - provider SDKs raise many types; retry a bounded number
                if attempt > self.max_retries or not _is_transient(exc):
                    log_event(_log, "llm.error", model=chosen_model, attempt=attempt, error=repr(exc))
                    raise
                delay = min(8.0, 0.5 * 2**attempt)
                log_event(
                    _log, "llm.retry", model=chosen_model, attempt=attempt, delay_s=delay, error=repr(exc)
                )
                time.sleep(delay)
        completion.cost_usd = estimate_cost(completion.model, completion.usage)
        completion.request_id = current_request_id()
        if completion.cost_usd is None:
            log_event(_log, "llm.unpriced_model", model=completion.model)
        else:
            self.spent_usd += completion.cost_usd
        self.calls.append(completion)
        log_event(
            _log,
            "llm.call",
            provider=completion.provider,
            model=completion.model,
            input_tokens=completion.usage.input_tokens,
            output_tokens=completion.usage.output_tokens,
            latency_ms=completion.latency_ms,
            cost_usd=completion.cost_usd,
            stop_reason=completion.stop_reason,
            tool_calls=[tc.name for tc in completion.tool_calls],
            spent_usd=round(self.spent_usd, 6),
        )
        return completion

    # ----- structured output -----------------------------------------------------------------------------

    def complete_json(
        self,
        messages: list[Message] | str,
        schema: type[T],
        *,
        system: str | None = None,
        max_tokens: int = 2048,
        model: str | None = None,
    ) -> tuple[T, Completion]:
        """Ask for JSON matching `schema`. On a validation failure, send the error back once and retry."""
        if isinstance(messages, str):
            messages = [Message(role="user", content=messages)]
        schema_text = json.dumps(schema.model_json_schema(), indent=0)
        sys_prompt = (
            (system or "")
            + "\n\nReturn only a JSON object that validates against this schema:\n"
            + schema_text
        )
        completion = self.complete(
            messages, system=sys_prompt.strip(), max_tokens=max_tokens, json_mode=True, model=model
        )
        try:
            return _parse(schema, completion.text), completion
        except (ValidationError, json.JSONDecodeError, StructuredOutputError) as first_error:
            repair = messages + [
                Message(role="assistant", content=completion.text),
                Message(
                    role="user",
                    content=f"That did not validate: {first_error}. Return the corrected JSON object only.",
                ),
            ]
            completion = self.complete(
                repair, system=sys_prompt.strip(), max_tokens=max_tokens, json_mode=True, model=model
            )
            try:
                return _parse(schema, completion.text), completion
            except (ValidationError, json.JSONDecodeError) as second_error:
                raise StructuredOutputError(str(second_error)) from second_error

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        return self.provider.embed(model=model or self.settings.llm_embedding_model, texts=texts)


def _parse[S: BaseModel](schema: type[S], text: str) -> S:
    raw = text.strip()
    fenced = _JSON_FENCE.search(raw)
    if fenced:
        raw = fenced.group(1).strip()
    if not raw.startswith("{"):
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise StructuredOutputError("no JSON object in response")
        raw = raw[start : end + 1]
    return schema.model_validate_json(raw)


def _is_transient(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    return any(
        k in name or k in text
        for k in ("ratelimit", "rate limit", "timeout", "overloaded", "503", "529", "connection")
    )


_default: ModelAdapter | None = None


def get_adapter() -> ModelAdapter:
    """Process-wide adapter built from settings. Tests construct their own with a FakeProvider."""
    global _default
    if _default is None:
        _default = ModelAdapter()
    return _default
