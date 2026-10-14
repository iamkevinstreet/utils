"""Small, dependency-free metrics. Every function is plain enough to check by hand."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any


def _norm(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.split()).strip().casefold()
    if isinstance(value, list):
        return sorted(_norm(v) for v in value)
    return value


def exact_match(predicted: Any, expected: Any) -> bool:
    """Case- and whitespace-insensitive equality; lists compare as sets."""
    return _norm(predicted) == _norm(expected)


def field_accuracy(
    predicted: dict[str, Any], expected: dict[str, Any], fields: Iterable[str]
) -> dict[str, Any]:
    """Per-field exact match plus the overall share of correct fields."""
    per_field: dict[str, bool] = {}
    for f in fields:
        per_field[f] = exact_match(predicted.get(f), expected.get(f))
    correct = sum(per_field.values())
    total = len(per_field)
    return {
        "per_field": per_field,
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else 0.0,
    }


def null_metrics(
    predicted: dict[str, Any], expected: dict[str, Any], fields: Iterable[str]
) -> dict[str, Any]:
    """How well the system says "I don't know": precision and recall of empty predictions where the truth is empty."""
    tp = fp = fn = 0
    for f in fields:
        pred_null = predicted.get(f) in (None, "", [])
        gold_null = expected.get(f) in (None, "", [])
        if pred_null and gold_null:
            tp += 1
        elif pred_null and not gold_null:
            fp += 1  # said "unknown" when an answer existed (a false abstention)
        elif not pred_null and gold_null:
            fn += 1  # filled in something that should have been empty (a guess)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return {"tp": tp, "false_abstentions": fp, "guesses": fn, "precision": precision, "recall": recall}


def precision_recall(predicted: Iterable[Any], expected: Iterable[Any]) -> dict[str, float]:
    """Set-based precision, recall and F1, with normalisation applied to each element."""
    p = {_norm_key(x) for x in predicted}
    e = {_norm_key(x) for x in expected}
    tp = len(p & e)
    precision = tp / len(p) if p else (1.0 if not e else 0.0)
    recall = tp / len(e) if e else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "predicted": len(p),
        "expected": len(e),
    }


def _norm_key(value: Any) -> Any:
    n = _norm(value)
    return tuple(n) if isinstance(n, list) else n


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile. pct in [0, 100]. Returns 0.0 for an empty sequence."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return float(ordered[rank - 1])


def mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0
