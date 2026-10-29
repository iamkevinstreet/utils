########################################################################
#                     evals/tests/test_metrics.py                      #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests each metric against values worked out by   #
#                     hand.                                            #
########################################################################
"""Tests for kds.evals.metrics."""

from __future__ import annotations

import logging

from kds.evals.metrics import (
    exact_match,
    field_accuracy,
    null_metrics,
    percentile,
    precision_recall,
)

# Module constants
log = logging.getLogger(__name__)


# log.debug("Defines the test that matching ignores case and spacing")
def test_exact_match_normalises() -> None:
    """Case, spacing and list order do not matter; values do."""
    # log.debug("Checks case and spacing are ignored")
    assert exact_match("  Acme   Logistics LLC ", "acme logistics llc")
    # log.debug("Checks list order is ignored")
    assert exact_match(["race", "sex"], ["Sex", "Race"])
    # log.debug("Checks different values do not match")
    assert not exact_match("2026-01-02", "2026-01-03")


# log.debug("Defines the test of field accuracy")
def test_field_accuracy() -> None:
    """Two of three fields right is 2/3, with each field reported."""
    # log.debug("Scores a prediction with one wrong field")
    result = field_accuracy(
        {"a": "x", "b": "wrong", "c": None}, {"a": "X", "b": "right", "c": None}, ["a", "b", "c"]
    )
    # log.debug("Checks the counts")
    assert (result["correct"], result["total"]) == (2, 3)
    # log.debug("Checks the per-field results")
    assert result["per_field"] == {"a": True, "b": False, "c": True}


# log.debug("Defines the test of abstention counts")
def test_null_metrics_counts_guesses_and_false_abstentions() -> None:
    """One right abstention, one guess, one false abstention."""
    # log.debug("Scores four fields, one of each kind and one answered")
    result = null_metrics(
        {"a": None, "b": "guess", "c": None, "d": "v"},
        {"a": None, "b": None, "c": "truth", "d": "v"},
        ["a", "b", "c", "d"],
    )
    # log.debug("Checks each count")
    assert (result["tp"], result["guesses"], result["false_abstentions"]) == (1, 1, 1)
    # log.debug("Checks precision and recall are both one half")
    assert (result["precision"], result["recall"]) == (0.5, 0.5)


# log.debug("Defines the test of set precision and recall")
def test_precision_recall() -> None:
    """One of two predicted is right, one of two expected is found."""
    # log.debug("Scores two predictions against two expected names")
    result = precision_recall(["Acme LLC", "beta inc"], ["acme llc", "Gamma Co"])
    # log.debug("Checks the hit, precision and recall")
    assert (result["tp"], result["precision"], result["recall"]) == (1, 0.5, 0.5)


# log.debug("Defines the test of the nearest-rank percentile")
def test_percentile_nearest_rank() -> None:
    """Median, tail and the empty case."""
    # log.debug("Builds ten evenly spaced values")
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    # log.debug("Checks the median")
    assert percentile(values, 50) == 50
    # log.debug("Checks the 95th percentile")
    assert percentile(values, 95) == 100
    # log.debug("Checks no values give zero")
    assert percentile([], 50) == 0.0
