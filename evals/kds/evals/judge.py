########################################################################
#                       evals/kds/evals/judge.py                       #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           A model judge for answers exact match cannot     #
#                     score, and its agreement with human grades.      #
########################################################################
"""A model-as-judge with a calibration check.

A judge is only as good as its agreement with a person. `calibrate`
runs the judge over cases a person already graded and reports how
often they agree; that rate belongs beside any judged metric.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from kds.llm.adapter import ModelAdapter

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the judge's standing instructions")
JUDGE_SYSTEM = (
    "You grade an answer against a rubric. Be strict and literal. A claim that is not "
    "supported by the reference material is wrong even if it sounds plausible. "
    "Output JSON only."
)
# log.debug("Sets the prompt each grading request fills in")
JUDGE_PROMPT = (
    "Question:\n{question}\n\nReference material (the only source of truth):\n{reference}\n\n"
    "Rubric:\n{rubric}\n\nAnswer to grade:\n{answer}\n\n"
    'Return {{"score": 0|1|2, "reason": "..."}}.'
)


# log.debug("Defines the judge's verdict")
class Verdict(BaseModel):
    """A score from 0 to 2 and the reason for it."""

    # log.debug("Holds the score")
    score: int = Field(ge=0, le=2, description="0 wrong or unsupported, 1 partly, 2 right")
    # log.debug("Holds the judge's reason")
    reason: str


# log.debug("Defines one grading")
def judge(adapter: ModelAdapter, case: dict[str, str], rubric: str) -> Verdict:
    """Grade one answer.

    Args:
        adapter: The adapter; the judge model comes from its settings.
        case: The question, the answer and the reference material.
        rubric: What a full-score answer must do.

    Returns:
        The judge's verdict.
    """
    # log.debug("Fills the grading prompt")
    prompt = JUDGE_PROMPT.format(rubric=rubric, **case)
    # log.debug("Asks the judge model for a verdict")
    verdict, _ = adapter.complete_json(
        prompt, Verdict, system=JUDGE_SYSTEM, model=adapter.settings.llm_judge_model
    )
    # log.debug("Returns the verdict")
    return verdict


# log.debug("Defines the judge's agreement with human grades")
def calibrate(
    adapter: ModelAdapter, graded: list[dict[str, Any]], rubric: str
) -> dict[str, float]:
    """Return how often the judge matches a person's grade.

    Args:
        adapter: The adapter the judge runs on.
        graded: Rows of question, answer, reference and human_score.
        rubric: The rubric both the person and the judge used.

    Returns:
        The count, exact agreement and agreement within one point.
    """
    # log.debug("Starts both agreement counts")
    exact = within_one = 0
    # log.debug("Grades each row the person graded")
    for row in graded:
        # log.debug("Picks out the three texts the judge reads")
        case = {key: row[key] for key in ("question", "answer", "reference")}
        # log.debug("Measures how far the judge is from the person")
        gap = abs(judge(adapter, case, rubric).score - int(row["human_score"]))
        # log.debug("Counts an exact agreement")
        exact += gap == 0
        # log.debug("Counts an agreement within one point")
        within_one += gap <= 1
    # log.debug("Guards the division for an empty set")
    n = max(1, len(graded))
    # log.debug("Returns the rates")
    return {"n": float(len(graded)), "exact_agreement": exact / n, "within_one": within_one / n}
