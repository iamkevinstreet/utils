########################################################################
#                     evals/kds/evals/__init__.py                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Runs a system over cases with known answers and reports the numbers.
This file exports the cases, the metrics and the runner, which writes
the results tables; the model judge and run comparison are imported
from kds.evals.judge and kds.evals.report.

Usage:
    run = run_eval(name="extraction-v0.1", cases=load_cases(path),
                   adapter=adapter, system_fn=..., scorer_fn=...,
                   out_dir="results")
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Local
from kds.evals.case import EvalCase, load_cases
from kds.evals.metrics import (
    exact_match,
    field_accuracy,
    null_metrics,
    percentile,
    precision_recall,
)
from kds.evals.runner import CaseResult, RunResult, run_eval

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
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
