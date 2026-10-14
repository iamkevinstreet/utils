import pytest
from pydantic import BaseModel

from kds.llm.adapter import BudgetExceededError, ModelAdapter, StructuredOutputError
from kds.llm.fake import FakeProvider
from kds.llm.pricing import estimate_cost
from kds.llm.types import Usage


class Record(BaseModel):
    charge_number: str
    respondent: str | None = None


def test_complete_logs_usage_and_cost():
    adapter = ModelAdapter(FakeProvider(["hello"]), model="fake-model")
    c = adapter.complete("hi")
    assert c.text == "hello" and c.usage.total > 0
    assert c.cost_usd == 0.0 and adapter.spent_usd == 0.0
    assert len(adapter.calls) == 1


def test_complete_json_parses_and_strips_fences():
    adapter = ModelAdapter(
        FakeProvider(['```json\n{"charge_number": "510-2026-00001"}\n```']), model="fake-model"
    )
    rec, _ = adapter.complete_json("extract", Record)
    assert rec.charge_number == "510-2026-00001" and rec.respondent is None


def test_complete_json_repairs_once():
    adapter = ModelAdapter(
        FakeProvider(['{"respondent": "Acme"}', '{"charge_number": "x", "respondent": "Acme"}']),
        model="fake-model",
    )
    rec, _ = adapter.complete_json("extract", Record)
    assert rec.charge_number == "x"
    assert len(adapter.calls) == 2
    assert "did not validate" in adapter.provider.calls[1]["messages"][-1]["content"]


def test_complete_json_gives_up_after_repair():
    adapter = ModelAdapter(FakeProvider(["not json", "still not json"]), model="fake-model")
    with pytest.raises(StructuredOutputError):
        adapter.complete_json("extract", Record)


def test_budget_is_enforced():
    adapter = ModelAdapter(FakeProvider(["a", "b"]), model="fake-model", budget_usd=0.0)
    adapter.complete("one")
    adapter.spent_usd = 0.01  # simulate a priced call
    with pytest.raises(BudgetExceededError):
        adapter.complete("two")


def test_pricing_table_and_prefix_match():
    assert estimate_cost("claude-sonnet-4-5", Usage(input_tokens=1_000_000, output_tokens=0)) == 3.0
    assert estimate_cost("claude-sonnet-4-5-20250929", Usage(input_tokens=0, output_tokens=1_000_000)) == 15.0
    assert estimate_cost("unknown-model", Usage(input_tokens=10, output_tokens=10)) is None
