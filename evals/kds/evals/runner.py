########################################################################
#                      evals/kds/evals/runner.py                       #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Runs a system over cases, scoring, timing and    #
#                     pricing each; writes JSON and Markdown results.  #
########################################################################
"""The evaluation runner.

It knows nothing about any project. A project supplies two functions:

    system_fn(case) -> output          # runs the system on one case
    scorer_fn(case, output) -> scores  # a flat dict of numbers, bools

and the runner handles timing, cost (from the adapter's call record),
failures, the summary and the report files.
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from kds.evals.case import EvalCase
from kds.evals.summary import summarise, to_markdown
from kds.llm.adapter import ModelAdapter
from kds.llm.pricing import prices_as_of
from kds.logs import log_event, new_request_id

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the milliseconds in a second, for latency")
MS = 1000
# log.debug("Sets how much of a failing case's traceback is logged")
TRACE_CHARS = 2000
# log.debug("Sets the decimal places a case's cost is kept to")
COST_PLACES = 6
# log.debug("Sets the timestamp format in result file names")
STAMP = "%Y%m%dT%H%M%SZ"
# log.debug("Sets the encoding result files are written in")
ENCODING = "utf-8"
# log.debug("Sets the precision of the run's start and finish times")
TIMESPEC = "seconds"


# log.debug("Defines the result of one case")
class CaseResult(BaseModel):
    """One case's outcome: its scores, output, time, cost and calls."""

    # log.debug("Holds the case's id")
    case_id: str
    # log.debug("Holds the case's tags")
    tags: list[str] = Field(default_factory=list)
    # log.debug("Holds whether the system ran without raising")
    ok: bool
    # log.debug("Holds the scorer's numbers")
    scores: dict[str, Any] = Field(default_factory=dict)
    # log.debug("Holds what the system returned")
    output: Any = None
    # log.debug("Holds the error, when the system raised")
    error: str | None = None
    # log.debug("Holds the case's wall-clock time")
    latency_ms: int
    # log.debug("Holds what the case's model calls cost")
    cost_usd: float
    # log.debug("Holds how many model calls the case made")
    calls: int


# log.debug("Defines the result of a whole run")
class RunResult(BaseModel):
    """A run: what ran, when, at which prices, and every case."""

    # log.debug("Holds the run's name")
    name: str
    # log.debug("Holds the model that ran")
    model: str
    # log.debug("Holds the provider that served it")
    provider: str
    # log.debug("Holds when the run started, in UTC")
    started_at: str
    # log.debug("Holds when it finished")
    finished_at: str
    # log.debug("Holds the date of the price table used")
    prices_as_of: str
    # log.debug("Holds the number of cases")
    cases: int
    # log.debug("Holds the number of cases that raised")
    failures: int
    # log.debug("Holds the averaged scores and the time and cost figures")
    summary: dict[str, Any]
    # log.debug("Holds every case's result")
    results: list[CaseResult]


# log.debug("Defines how one case is run")
def run_case(
    case: EvalCase,
    adapter: ModelAdapter,
    system_fn: Callable[[EvalCase], Any],
    scorer_fn: Callable[[EvalCase, Any], dict[str, Any]],
) -> CaseResult:
    """Run and score one case; a failure is recorded, never raised."""
    # log.debug("Notes the call count before the case")
    calls_before = len(adapter.calls)
    # log.debug("Notes the spend before the case")
    spent_before = adapter.spent_usd
    # log.debug("Starts the clock")
    started = time.perf_counter()
    # log.debug("Assumes no output, no scores and no error until it runs")
    output, scores, error = None, {}, None
    # log.debug("Tries the case; a failing case must not stop the run")
    try:
        # log.debug("Runs the system on the case")
        output = system_fn(case)
        # log.debug("Scores the output")
        scores = scorer_fn(case, output)
    except Exception as exc:  # noqa: BLE001 - one case's failure is a result, not a crash
        # log.debug("Records the error's type and message")
        error = f"{type(exc).__name__}: {exc}"
        # log.debug("Logs the error with the end of its traceback")
        log_event(
            log,
            "eval.case_error",
            logging.WARNING,
            case_id=case.id,
            error=error,
            trace=traceback.format_exc()[-TRACE_CHARS:],
        )
    # log.debug("Returns the case's result")
    return CaseResult(
        case_id=case.id,
        tags=case.tags,
        ok=error is None,
        scores=scores,
        output=_jsonable(output),
        error=error,
        latency_ms=int((time.perf_counter() - started) * MS),
        cost_usd=round(adapter.spent_usd - spent_before, COST_PLACES),
        calls=len(adapter.calls) - calls_before,
    )


# log.debug("Defines a whole evaluation run")
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
    """Run every case, then write <name>-<time>.json and .md files.

    Each case runs under its own request id, "<name>:<case id>", so
    its log lines can be found together. Pass keep_output=False when
    the system saves its outputs itself and the results file should
    hold only the scores.

    Returns:
        The run, also written to `out_dir` with a <name>-latest.md copy.
    """
    # log.debug("Notes when the run started")
    started = datetime.now(UTC)
    # log.debug("Starts the list of case results")
    results: list[CaseResult] = []
    # log.debug("Runs each case under its own request id")
    for case in cases:
        # log.debug("Opens the case's request id")
        with new_request_id(f"{name}:{case.id}"):
            # log.debug("Runs and scores the case")
            result = run_case(case, adapter, system_fn, scorer_fn)
        # log.debug("Keeps the result, without its output if asked")
        results.append(result if keep_output else result.model_copy(update={"output": None}))
    # log.debug("Assembles the run with its summary")
    run = RunResult(
        name=name,
        model=adapter.model,
        provider=adapter.provider.name,
        started_at=started.isoformat(timespec=TIMESPEC),
        finished_at=datetime.now(UTC).isoformat(timespec=TIMESPEC),
        prices_as_of=prices_as_of(),
        cases=len(results),
        failures=sum(not r.ok for r in results),
        summary=summarise(results),
        results=results,
    )
    # log.debug("Writes the run's result files")
    write_run(run, Path(out_dir), started.strftime(STAMP))
    # log.debug("Logs the run's outcome")
    log_event(
        log,
        "eval.run_done",
        name=name,
        cases=run.cases,
        failures=run.failures,
        summary=run.summary,
    )
    # log.debug("Returns the run")
    return run


# log.debug("Defines how a run is saved")
def write_run(run: RunResult, out_dir: Path, stamp: str) -> None:
    """Write the run as JSON and Markdown; refresh the latest copy."""
    # log.debug("Creates the results folder")
    out_dir.mkdir(parents=True, exist_ok=True)
    # log.debug("Renders the Markdown report once")
    report = to_markdown(run)
    # log.debug("Writes the full results as JSON")
    (out_dir / f"{run.name}-{stamp}.json").write_text(run.model_dump_json(indent=2), ENCODING)
    # log.debug("Writes the report beside it")
    (out_dir / f"{run.name}-{stamp}.md").write_text(report, ENCODING)
    # log.debug("Writes the report again as the latest")
    (out_dir / f"{run.name}-latest.md").write_text(report, ENCODING)


# log.debug("Defines how any output becomes JSON-safe")
def _jsonable(value: Any) -> Any:
    """Return a model as a dict, JSON as is, anything else as text."""
    # log.debug("Dumps a pydantic model to a dict")
    if isinstance(value, BaseModel):
        # log.debug("Returns the dict")
        return value.model_dump()
    # log.debug("Tries the value as JSON")
    try:
        # log.debug("Checks it serialises")
        json.dumps(value)
    except TypeError:
        # log.debug("Returns its text form when it does not")
        return repr(value)
    # log.debug("Returns it unchanged when it does")
    return value
