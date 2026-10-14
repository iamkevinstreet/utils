"""Run a system under test over a set of cases, score each one, and write a results file and a markdown table.

The runner knows nothing about any particular project. A project supplies two functions:

    system_fn(case) -> output            # calls the model, returns whatever the project produces
    scorer_fn(case, output) -> scores    # a flat dict of numbers and booleans for that case

and the runner handles timing, cost (from the adapter's call log), failures, aggregation and reporting.
"""

from __future__ import annotations

import json
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from kds.evals.case import EvalCase
from kds.evals.metrics import mean, percentile
from kds.llm.adapter import ModelAdapter
from kds.llm.pricing import prices_as_of
from kds.logs import get_logger, log_event, new_request_id

_log = get_logger("kds.evals")


class CaseResult(BaseModel):
    case_id: str
    tags: list[str] = Field(default_factory=list)
    ok: bool
    scores: dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    error: str | None = None
    latency_ms: int
    cost_usd: float
    calls: int


class RunResult(BaseModel):
    name: str
    model: str
    provider: str
    started_at: str
    finished_at: str
    prices_as_of: str
    cases: int
    failures: int
    summary: dict[str, Any]
    results: list[CaseResult]


def run_eval(
    *,
    name: str,
    cases: list[EvalCase],
    adapter: ModelAdapter,
    system_fn: Callable[[EvalCase], Any],
    scorer_fn: Callable[[EvalCase, Any], dict[str, Any]],
    out_dir: Path | str,
    keep_output: bool = True,
) -> RunResult:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    results: list[CaseResult] = []
    for case in cases:
        calls_before = len(adapter.calls)
        spent_before = adapter.spent_usd
        t0 = time.perf_counter()
        with new_request_id(f"{name}:{case.id}"):
            try:
                output = system_fn(case)
                scores = scorer_fn(case, output)
                ok, error = True, None
            except Exception as exc:  # noqa: BLE001 - a failing case must not stop the run
                output, scores, ok = None, {}, False
                error = f"{type(exc).__name__}: {exc}"
                log_event(
                    _log,
                    "eval.case_error",
                    case_id=case.id,
                    error=error,
                    trace=traceback.format_exc()[-2000:],
                )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        results.append(
            CaseResult(
                case_id=case.id,
                tags=case.tags,
                ok=ok,
                scores=scores,
                output=_jsonable(output) if keep_output else None,
                error=error,
                latency_ms=latency_ms,
                cost_usd=round(adapter.spent_usd - spent_before, 6),
                calls=len(adapter.calls) - calls_before,
            )
        )
    finished = datetime.now(UTC)
    summary = summarise(results)
    run = RunResult(
        name=name,
        model=adapter.model,
        provider=adapter.provider.name,
        started_at=started.isoformat(timespec="seconds"),
        finished_at=finished.isoformat(timespec="seconds"),
        prices_as_of=prices_as_of(),
        cases=len(results),
        failures=sum(1 for r in results if not r.ok),
        summary=summary,
        results=results,
    )
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    (out / f"{name}-{stamp}.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")
    (out / f"{name}-{stamp}.md").write_text(to_markdown(run), encoding="utf-8")
    (out / f"{name}-latest.md").write_text(to_markdown(run), encoding="utf-8")
    log_event(_log, "eval.run_done", name=name, cases=run.cases, failures=run.failures, summary=summary)
    return run


def summarise(results: list[CaseResult]) -> dict[str, Any]:
    """Average every numeric or boolean score across successful cases; add latency and cost percentiles."""
    ok = [r for r in results if r.ok]
    keys: set[str] = set()
    for r in ok:
        keys.update(k for k, v in r.scores.items() if isinstance(v, bool | int | float))
    summary: dict[str, Any] = {}
    for k in sorted(keys):
        vals = [float(r.scores[k]) for r in ok if k in r.scores]
        summary[k] = round(mean(vals), 4)
    lat = [r.latency_ms for r in results]
    cost = [r.cost_usd for r in results]
    summary["latency_p50_ms"] = percentile(lat, 50)
    summary["latency_p95_ms"] = percentile(lat, 95)
    summary["cost_total_usd"] = round(sum(cost), 4)
    summary["cost_per_case_usd"] = round(mean(cost), 6)
    summary["failure_rate"] = round((len(results) - len(ok)) / len(results), 4) if results else 0.0
    return summary


def to_markdown(run: RunResult) -> str:
    lines = [
        f"# {run.name}",
        "",
        f"Model: `{run.model}` ({run.provider}). Cases: {run.cases}. Failures: {run.failures}. "
        f"Run: {run.started_at}. Prices as of {run.prices_as_of}.",
        "",
        "| Measure | Value |",
        "| --- | --- |",
    ]
    for k, v in run.summary.items():
        lines.append(f"| {k} | {_fmt(v)} |")
    tags = sorted({t for r in run.results for t in r.tags})
    if tags:
        lines += ["", "## By tag", "", "| Tag | Cases | " + " | ".join(_score_keys(run)) + " |"]
        lines.append("| --- | --- | " + " | ".join("---" for _ in _score_keys(run)) + " |")
        for tag in tags:
            subset = [r for r in run.results if tag in r.tags]
            s = summarise(subset)
            lines.append(
                f"| {tag} | {len(subset)} | " + " | ".join(_fmt(s.get(k)) for k in _score_keys(run)) + " |"
            )
    failures = [r for r in run.results if not r.ok]
    if failures:
        lines += ["", "## Failures", ""]
        for r in failures:
            lines.append(f"- `{r.case_id}`: {r.error}")
    return "\n".join(lines) + "\n"


def _score_keys(run: RunResult) -> list[str]:
    keys: set[str] = set()
    for r in run.results:
        keys.update(k for k, v in r.scores.items() if isinstance(v, bool | int | float))
    return sorted(keys)


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.0f}"
    return str(v)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)
