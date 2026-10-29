########################################################################
#                      evals/kds/evals/metrics.py                      #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Small metrics plain enough to check by hand:     #
#                     matches, field accuracy, abstention,             #
#                     percentiles.                                     #
########################################################################
"""Dependency-free metrics; each one can be checked by hand."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Sequence
from typing import Any

# Module constants
log = logging.getLogger(__name__)
# log.debug("Lists the values that count as no answer")
EMPTY: tuple[Any, ...] = (None, "", [])
# log.debug("Sets the highest percentile")
HUNDRED = 100
# log.debug("Names the keys both precision-recall results share")
TP, PRECISION, RECALL = "tp", "precision", "recall"


# log.debug("Defines the normal form two values are compared in")
def _norm(value: Any) -> Any:
    """Fold case and spacing in strings; sort lists; keep the rest."""
    # log.debug("Folds a string's case and collapses its spaces")
    if isinstance(value, str):
        # log.debug("Returns the folded string")
        return " ".join(value.split()).casefold()
    # log.debug("Sorts a list's normalised items, so order is ignored")
    if isinstance(value, list):
        # log.debug("Returns the sorted items")
        return sorted(_norm(item) for item in value)
    # log.debug("Returns anything else as it is")
    return value


# log.debug("Defines the hashable normal form, for sets")
def _norm_key(value: Any) -> Any:
    """Return the normal form, with a list turned into a tuple."""
    # log.debug("Normalises the value")
    normal = _norm(value)
    # log.debug("Returns a tuple for a list, else the value")
    return tuple(normal) if isinstance(normal, list) else normal


# log.debug("Defines exact match after normalising")
def exact_match(predicted: Any, expected: Any) -> bool:
    """Equal ignoring case and spacing; lists compare as sets."""
    # log.debug("Compares the two normal forms")
    return bool(_norm(predicted) == _norm(expected))


# log.debug("Defines per-field and overall accuracy")
def field_accuracy(
    predicted: dict[str, Any], expected: dict[str, Any], fields: Iterable[str]
) -> dict[str, Any]:
    """Return each field's exact match and the share that matched."""
    # log.debug("Scores each field")
    per_field = {f: exact_match(predicted.get(f), expected.get(f)) for f in fields}
    # log.debug("Counts the matching fields")
    correct = sum(per_field.values())
    # log.debug("Returns the details, counts and accuracy")
    return {
        "per_field": per_field,
        "correct": correct,
        "total": len(per_field),
        "accuracy": correct / len(per_field) if per_field else 0.0,
    }


# log.debug("Defines how well a system says it does not know")
def null_metrics(
    predicted: dict[str, Any], expected: dict[str, Any], fields: Iterable[str]
) -> dict[str, Any]:
    """Return precision and recall of empty answers on empty truths.

    A false abstention is an empty answer where one existed; a guess
    is an answer where the truth was empty.
    """
    # log.debug("Starts the three counts")
    both = abstained = guessed = 0
    # log.debug("Classifies each field")
    for f in fields:
        # log.debug("Notes whether the prediction is empty")
        said_none = predicted.get(f) in EMPTY
        # log.debug("Notes whether the truth is empty")
        truly_none = expected.get(f) in EMPTY
        # log.debug("Counts an empty answer where the truth is empty")
        both += said_none and truly_none
        # log.debug("Counts an empty answer where an answer existed")
        abstained += said_none and not truly_none
        # log.debug("Counts an answer where the truth was empty")
        guessed += truly_none and not said_none
    # log.debug("Returns the counts with precision and recall")
    return {
        TP: both,
        "false_abstentions": abstained,
        "guesses": guessed,
        PRECISION: both / (both + abstained) if both + abstained else 1.0,
        RECALL: both / (both + guessed) if both + guessed else 1.0,
    }


# log.debug("Defines set precision, recall and F1")
def precision_recall(predicted: Iterable[Any], expected: Iterable[Any]) -> dict[str, float]:
    """Return set-based precision, recall and F1 on normalised items."""
    # log.debug("Normalises the predicted items into a set")
    got = {_norm_key(item) for item in predicted}
    # log.debug("Normalises the expected items into a set")
    want = {_norm_key(item) for item in expected}
    # log.debug("Counts the items in both")
    hits = len(got & want)
    # log.debug("Computes precision; predicting nothing for nothing is perfect")
    precision = hits / len(got) if got else float(not want)
    # log.debug("Computes recall; nothing to find is perfect")
    recall = hits / len(want) if want else 1.0
    # log.debug("Computes their harmonic mean")
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    # log.debug("Returns the scores and counts")
    return {
        PRECISION: precision,
        RECALL: recall,
        "f1": f1,
        TP: hits,
        "predicted": len(got),
        "expected": len(want),
    }


# log.debug("Defines the nearest-rank percentile")
def percentile(values: Sequence[float], pct: float) -> float:
    """Return the nearest-rank percentile (pct 0-100); 0 if empty."""
    # log.debug("Returns zero for no values")
    if not values:
        # log.debug("Returns zero")
        return 0.0
    # log.debug("Sorts the values")
    ordered = sorted(values)
    # log.debug("Finds the rank: the smallest covering pct of the values")
    rank = max(1, math.ceil(pct / HUNDRED * len(ordered)))
    # log.debug("Returns the value at that rank")
    return float(ordered[rank - 1])


# log.debug("Defines the arithmetic mean")
def mean(values: Sequence[float]) -> float:
    """Return the mean, or 0 for no values."""
    # log.debug("Returns the sum over the count")
    return float(sum(values) / len(values)) if values else 0.0
