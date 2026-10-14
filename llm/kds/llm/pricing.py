"""Cost accounting from a small editable price table."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from kds.llm.types import Usage

_TABLE = Path(__file__).with_name("pricing.json")


@lru_cache(maxsize=1)
def load_table() -> dict:
    return json.loads(_TABLE.read_text())


def prices_as_of() -> str:
    return str(load_table().get("as_of", "unknown"))


def estimate_cost(model: str, usage: Usage) -> float | None:
    """Return the cost in USD, or None when the model is not in the table (the caller logs that)."""
    models = load_table()["models"]
    entry = models.get(model)
    if entry is None:
        # Allow dated variants such as "claude-sonnet-4-5-20250929" to match their base name.
        for name, prices in models.items():
            if model.startswith(name):
                entry = prices
                break
    if entry is None:
        return None
    return round(usage.input_tokens * entry["input"] / 1e6 + usage.output_tokens * entry["output"] / 1e6, 6)
