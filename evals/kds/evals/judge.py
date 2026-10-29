########################################################################
#                       evals/kds/evals/judge.py                       #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Grades answers that exact match cannot score, with a model as judge,
and checks the judge against human grades.

A judge is only as good as its agreement with a person: `calibrate`
runs the judge over cases a person already graded and reports how
often they agree. That rate belongs beside any judged metric.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from typing import Any

# Third-party
from pydantic import BaseModel, Field

# Local
from kds.args import required
from kds.llm.adapter import ModelAdapter

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
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


########################################################################
#                             Model judge                              #
########################################################################
# log.debug("Defines the judge's verdict")
class Verdict(BaseModel):
    """A score from 0 to 2 and the reason for it."""

    # log.debug("Holds the score")
    score: int = Field(ge=0, le=2, description="0 wrong or unsupported, 1 partly, 2 right")
    # log.debug("Holds the judge's reason")
    reason: str


# log.debug("Defines one grading")
def judge(
    adapter: ModelAdapter | None = None,
    case: dict[str, str] | None = None,
    rubric: str | None = None,
) -> Verdict:
    """Grades one answer.

    Args:
        adapter: The adapter; the judge model comes from its settings.
            Required.
        case: The question, the answer and the reference material.
            Required.
        rubric: What a full-score answer must do. Required.

    Returns:
        The judge's verdict.
    """
    # log.debug("Takes the adapter, which the caller must give")
    adapter = required(adapter=adapter)
    # log.debug("Takes the case, which the caller must give")
    case = required(case=case)
    # log.debug("Takes the rubric, which the caller must give")
    rubric = required(rubric=rubric)
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
    adapter: ModelAdapter | None = None,
    graded: list[dict[str, Any]] | None = None,
    rubric: str | None = None,
) -> dict[str, float]:
    """Returns how often the judge matches a person's grade.

    Args:
        adapter: The adapter the judge runs on. Required.
        graded: Rows of question, answer, reference and human_score.
            Required.
        rubric: The rubric both the person and the judge used. Required.

    Returns:
        The count, exact agreement and agreement within one point.
    """
    # log.debug("Takes the adapter, which the caller must give")
    adapter = required(adapter=adapter)
    # log.debug("Takes the graded answers, which the caller must give")
    graded = required(graded=graded)
    # log.debug("Takes the rubric, which the caller must give")
    rubric = required(rubric=rubric)
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
