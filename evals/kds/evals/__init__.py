########################################################################
#                     evals/kds/evals/__init__.py                      #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Evaluation cases, metrics, a runner that writes  #
#                     results tables, a model judge, run comparison.   #
########################################################################
"""kds.evals: run a system over known answers and report the numbers.

Usage:
    run = run_eval(name="extraction-v0.1", cases=load_cases(path),
                   adapter=adapter, system_fn=..., scorer_fn=...,
                   out_dir="results")
"""

from __future__ import annotations

import logging

from kds.evals.case import EvalCase, load_cases
from kds.evals.metrics import (
    exact_match,
    field_accuracy,
    null_metrics,
    percentile,
    precision_recall,
)
from kds.evals.runner import CaseResult, RunResult, run_eval

# Module constants
log = logging.getLogger(__name__)
# log.debug("Lists what the package exports")
__all__ = [
    "CaseResult",
    "EvalCase",
    "RunResult",
    "exact_match",
    "field_accuracy",
    "load_cases",
    "null_metrics",
    "percentile",
    "precision_recall",
    "run_eval",
]
