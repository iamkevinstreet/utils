########################################################################
#                      llm/tests/test_adapter.py                       #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests the adapter offline: calls, JSON repair,   #
#                     budget stop, retries and the price table.        #
########################################################################
"""Tests for kds.llm, all against the offline fake provider."""

from __future__ import annotations

import logging

import pytest
from pydantic import BaseModel

from kds.llm.adapter import ModelAdapter
from kds.llm.anthropic_provider import AnthropicProvider
from kds.llm.errors import BudgetExceededError, StructuredOutputError, TransientError
from kds.llm.fake import FakeProvider
from kds.llm.pricing import estimate_cost
from kds.llm.types import Message, ToolCall, Usage

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the model name the offline price table lists at zero")
FAKE_MODEL = "fake-model"
# log.debug("Sets a prompt the tests send")
PROMPT = "extract"


# log.debug("Defines the schema the JSON tests ask for")
class Record(BaseModel):
    """A record with one required and one optional field."""

    # log.debug("Holds the required field")
    charge_number: str
    # log.debug("Holds the optional field")
    respondent: str | None = None


# log.debug("Defines a provider that fails a set number of times first")
class Flaky(FakeProvider):
    """Raises `error` for the first `failures` calls, then answers."""

    # log.debug("Defines the constructor with the failures to script")
    def __init__(self, failures: int, error: Exception) -> None:
        """Script `failures` failures, then the answer "ok"."""
        # log.debug("Queues the eventual answer")
        super().__init__(["ok"])
        # log.debug("Keeps how many failures are left")
        self.failures = failures
        # log.debug("Keeps the error to raise")
        self.error = error

    # log.debug("Defines a call that fails until the failures run out")
    def complete(self, **request: object) -> object:  # type: ignore[override]
        """Raise while failures remain, then answer normally."""
        # log.debug("Raises while there are failures left")
        if self.failures:
            # log.debug("Uses one failure up")
            self.failures -= 1
            # log.debug("Raises the scripted error")
            raise self.error
        # log.debug("Answers like the plain fake")
        return super().complete(**request)  # type: ignore[arg-type]


# log.debug("Defines an adapter that never really sleeps")
def _adapter(provider: FakeProvider, budget_usd: float | None = None) -> ModelAdapter:
    """Return an adapter on `provider` whose retries do not wait."""
    # log.debug("Builds the adapter with a no-op sleep")
    return ModelAdapter(provider, model=FAKE_MODEL, budget_usd=budget_usd, sleep=lambda _: None)


# log.debug("Defines the test that a call is recorded and priced")
def test_complete_records_usage_and_cost() -> None:
    """A call returns text, counts tokens, costs zero, is recorded."""
    # log.debug("Builds an adapter with one scripted answer")
    adapter = _adapter(FakeProvider(["hello"]))
    # log.debug("Makes the call")
    completion = adapter.complete("hi")
    # log.debug("Checks the answer and that tokens were counted")
    assert completion.text == "hello" and completion.usage.total > 0
    # log.debug("Checks the fake model costs nothing")
    assert completion.cost_usd == 0.0 and adapter.spent_usd == 0.0
    # log.debug("Checks the call was recorded")
    assert len(adapter.calls) == 1


# log.debug("Defines the test that a fenced JSON answer parses")
def test_complete_json_strips_fences() -> None:
    """JSON inside a code fence parses into the schema."""
    # log.debug("Scripts an answer wrapped in a json fence")
    adapter = _adapter(FakeProvider(['```json\n{"charge_number": "510-2026-00001"}\n```']))
    # log.debug("Asks for the record")
    record, _ = adapter.complete_json(PROMPT, Record)
    # log.debug("Checks both fields")
    assert record.charge_number == "510-2026-00001" and record.respondent is None


# log.debug("Defines the test that a bad answer is repaired once")
def test_complete_json_repairs_once() -> None:
    """An answer missing a field is sent back once, with the error."""
    # log.debug("Scripts a bad answer, then a good one")
    provider = FakeProvider(['{"respondent": "Acme"}', '{"charge_number": "x"}'])
    # log.debug("Asks for the record")
    record, _ = _adapter(provider).complete_json(PROMPT, Record)
    # log.debug("Checks the repaired answer was used")
    assert record.charge_number == "x"
    # log.debug("Checks the repair turn told the model what failed")
    assert "did not validate" in provider.calls[1]["messages"][-1]["content"]


# log.debug("Defines the test that a second bad answer gives up")
def test_complete_json_gives_up_after_repair() -> None:
    """Two answers that are not JSON raise StructuredOutputError."""
    # log.debug("Scripts two answers that are not JSON")
    adapter = _adapter(FakeProvider(["not json", "still not json"]))
    # log.debug("Expects the structured-output error")
    with pytest.raises(StructuredOutputError):
        # log.debug("Asks for the record")
        adapter.complete_json(PROMPT, Record)


# log.debug("Defines the test that the budget stops a run")
def test_budget_is_enforced() -> None:
    """Once spend passes the budget, the next call is refused."""
    # log.debug("Builds an adapter with a zero budget")
    adapter = _adapter(FakeProvider(["a", "b"]), budget_usd=0.0)
    # log.debug("Makes a first call, which is free")
    adapter.complete("one")
    # log.debug("Pretends a priced call happened")
    adapter.spent_usd = 0.01
    # log.debug("Expects the budget error")
    with pytest.raises(BudgetExceededError):
        # log.debug("Makes the call that should be refused")
        adapter.complete("two")


# log.debug("Defines the test that transient failures are retried")
def test_transient_failures_are_retried() -> None:
    """Two transient failures are retried; the third try answers."""
    # log.debug("Scripts two transient failures before the answer")
    provider = Flaky(2, TransientError("overloaded"))
    # log.debug("Checks the call still succeeds")
    assert _adapter(provider).complete("hi").text == "ok"


# log.debug("Defines the test that other failures are not retried")
def test_other_failures_are_not_retried() -> None:
    """A failure retrying cannot fix is raised at once."""
    # log.debug("Scripts one failure that is not transient")
    provider = Flaky(1, ValueError("bad request"))
    # log.debug("Expects the original error")
    with pytest.raises(ValueError, match="bad request"):
        # log.debug("Makes the call")
        _adapter(provider).complete("hi")
    # log.debug("Checks the answer was never reached")
    assert provider.calls == []


# log.debug("Defines the test of the price table")
def test_pricing_table_and_prefix_match() -> None:
    """Exact names, dated names, the longest base name, and unknowns."""
    # log.debug("Checks an exact name at its list price")
    assert estimate_cost("claude-sonnet-4-5", Usage(input_tokens=1_000_000)) == 3.0
    # log.debug("Checks a dated name is priced as its base name")
    assert estimate_cost("claude-sonnet-4-5-20250929", Usage(output_tokens=1_000_000)) == 15.0
    # log.debug("Checks the longest base name wins")
    assert estimate_cost("gpt-4.1-mini-2025", Usage(input_tokens=1_000_000)) == 0.4
    # log.debug("Checks an unknown model has no price")
    assert estimate_cost("unknown-model", Usage(input_tokens=10)) is None


# log.debug("Defines the test that one turn's tool results travel together")
def test_anthropic_joins_a_turns_tool_results() -> None:
    """Two calls in one turn come back as one turn of two results."""
    # log.debug("Builds a turn with two tool calls and both results")
    turns = [
        Message(role="user", content="intake"),
        Message(
            role="assistant",
            content="",
            tool_calls=[
                ToolCall(id="a", name="search", arguments={"name": "x"}),
                ToolCall(id="b", name="search", arguments={"name": "y"}),
            ],
        ),
        Message(role="tool", content="[]", tool_call_id="a"),
        Message(role="tool", content="[]", tool_call_id="b"),
        Message(role="user", content="next"),
    ]
    # log.debug("Converts them to Anthropic's shape")
    converted = AnthropicProvider._convert(turns)
    # log.debug("Checks the roles: user, assistant, one results turn, user")
    assert [turn["role"] for turn in converted] == ["user", "assistant", "user", "user"]
    # log.debug("Checks the results turn holds both results, in order")
    assert [block["tool_use_id"] for block in converted[2]["content"]] == ["a", "b"]
