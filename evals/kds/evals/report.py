"""Compare two runs and produce the one-line changelog entry a case study needs."""

from __future__ import annotations

import json
from pathlib import Path

from kds.evals.runner import RunResult


def load_run(path: Path | str) -> RunResult:
    return RunResult.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def compare(before: RunResult, after: RunResult, keys: list[str] | None = None) -> str:
    """A markdown table of `before -> after` for every summary key (or the given ones)."""
    keys = keys or sorted(set(before.summary) | set(after.summary))
    lines = [
        f"| Measure | {before.name} ({before.model}) | {after.name} ({after.model}) | Change |",
        "| --- | --- | --- | --- |",
    ]
    for k in keys:
        b = before.summary.get(k)
        a = after.summary.get(k)
        change = ""
        if isinstance(a, int | float) and isinstance(b, int | float):
            change = f"{a - b:+.4f}".rstrip("0").rstrip(".")
        lines.append(f"| {k} | {_f(b)} | {_f(a)} | {change} |")
    return "\n".join(lines) + "\n"


def changelog_line(version: str, date: str, note: str, before: RunResult, after: RunResult, key: str) -> str:
    """Example: `- **v0.2, Oct 20, 2026.** Added span verification: unsupported_rate 0.09 -> 0.01.`"""
    b = before.summary.get(key)
    a = after.summary.get(key)
    return f"- **{version}, {date}.** {note}: {key} {_f(b)} -> {_f(a)}."


def _f(v) -> str:
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return "" if v is None else str(v)
