"""A model-as-judge for answers that cannot be scored by exact match, with a calibration check.

A judge is only as good as its agreement with a person. `calibrate` runs the judge over cases that a human has
already graded and reports the agreement rate, which belongs in the results table next to any judged metric.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from kds.llm.adapter import ModelAdapter

JUDGE_SYSTEM = """You grade an answer against a rubric. Be strict and literal. A claim that is not supported
by the reference material is wrong even if it sounds plausible. Output JSON only."""


class Verdict(BaseModel):
    score: int = Field(
        ge=0, le=2, description="0 = wrong or unsupported, 1 = partly right, 2 = right and complete"
    )
    reason: str


def judge(
    adapter: ModelAdapter,
    *,
    question: str,
    answer: str,
    reference: str,
    rubric: str,
    model: str | None = None,
) -> Verdict:
    prompt = (
        f"Question:\n{question}\n\nReference material (the only source of truth):\n{reference}\n\n"
        f'Rubric:\n{rubric}\n\nAnswer to grade:\n{answer}\n\nReturn {{"score": 0|1|2, "reason": "..."}}.'
    )
    verdict, _ = adapter.complete_json(
        prompt, Verdict, system=JUDGE_SYSTEM, model=model or adapter.settings.llm_judge_model
    )
    return verdict


def calibrate(
    adapter: ModelAdapter,
    graded: list[dict],
    *,
    rubric: str,
    model: str | None = None,
) -> dict[str, float]:
    """`graded` rows: {question, answer, reference, human_score}. Returns agreement with the human grades."""
    exact = 0
    within_one = 0
    for row in graded:
        v = judge(
            adapter,
            question=row["question"],
            answer=row["answer"],
            reference=row["reference"],
            rubric=rubric,
            model=model,
        )
        diff = abs(v.score - int(row["human_score"]))
        exact += diff == 0
        within_one += diff <= 1
    n = max(1, len(graded))
    return {"n": float(len(graded)), "exact_agreement": exact / n, "within_one": within_one / n}
