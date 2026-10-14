"""An evaluation case: an input, the expected output, and tags for slicing results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    id: str
    input: dict[str, Any]
    expected: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


def load_cases(path: Path | str) -> list[EvalCase]:
    """Load cases from a .jsonl file (one case per line) or a .json file (a list)."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip() and not line.startswith("#")]
    else:
        rows = json.loads(text)
    cases = [EvalCase.model_validate(r) for r in rows]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"duplicate case ids: {dupes}")
    return cases
