########################################################################
#                                                                      #
#                      evals/kds/evals/runner.py                       #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-11-09

Runs a system over evaluation cases and writes the results as JSON and
Markdown.

The runner knows nothing about any project. A project supplies two
functions:

    system_fn(case) -> output          # runs the system on one case
    scorer_fn(case, output) -> scores  # a flat dict of numbers, bools

and the runner handles the rest: timing, cost (from the adapter's call
record), failures, the summary and the report files.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging
import time
import traceback
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Third-party
from opentelemetry.sdk.trace import ReadableSpan
from pydantic import BaseModel, Field

# Local
from kds.args import missing, required
from kds.evals import config
from kds.evals.case import EvalCase
from kds.evals.spans import case_span, scored
from kds.evals.summary import summarise, to_markdown
from kds.llm.adapter import ModelAdapter
from kds.llm.pricing import prices_as_of
from kds.logs import collect, flush_spans, log_event, new_request_id, session, write_spans

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the decimal places a case's cost is kept to, from the config")
COST_PLACES = config.COST_PLACES

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the milliseconds in a second, for latency")
MS = 1000
# log.debug("Sets how much of a failing case's traceback is logged")
TRACE_CHARS = 2000
# log.debug("Sets the timestamp format in result file names")
STAMP = "%Y%m%dT%H%M%SZ"
# log.debug("Sets the encoding result files are written in")
ENCODING = "utf-8"
# log.debug("Sets the precision of the run's start and finish times")
TIMESPEC = "seconds"
# log.debug("Ends the name of the file a run's spans are kept in")
SPANS_SUFFIX = ".spans.jsonl"


########################################################################
#                                                                      #
#                           Evaluation runs                            #
#                                                                      #
########################################################################
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
    # log.debug("Holds the system's wall-clock time on the case, not the scorer's")
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
    case: EvalCase | None = None,
    adapter: ModelAdapter | None = None,
    system_fn: Callable[[EvalCase], Any] | None = None,
    scorer_fn: Callable[[EvalCase, Any], dict[str, Any]] | None = None,
    *,
    run: str = "",
) -> CaseResult:
    """Runs and scores one case; a failure is recorded, never raised.

    The case runs in its own span, which records its scores. Its time
    is the system's alone: a scorer that calls a model, such as an LLM
    judge, does not add to it.

    Args:
        case: The case to run. Required.
        adapter: The model adapter the system calls; its call record
            gives the case's calls and cost. Required.
        system_fn: Runs the system on a case and returns its output.
            Required.
        scorer_fn: Scores a case's output as a flat dict. Required.
        run: The run's name, recorded on the case's span.

    Returns:
        The case's scores, output, error, time, cost and call count.
    """
    # log.debug("Takes the case, which the caller must give")
    case = required(case=case)
    # log.debug("Takes the adapter, which the caller must give")
    adapter = required(adapter=adapter)
    # log.debug("Takes the system under test, which the caller must give")
    system_fn = required(system_fn=system_fn)
    # log.debug("Takes the scorer, which the caller must give")
    scorer_fn = required(scorer_fn=scorer_fn)
    # log.debug("Notes the call count before the case")
    calls_before = len(adapter.calls)
    # log.debug("Notes the spend before the case")
    spent_before = adapter.spent_usd
    # log.debug("Starts the clock")
    started = time.perf_counter()
    # log.debug("Assumes no output, no scores and no error until it runs")
    output, scores, error, failure = None, {}, None, None
    # log.debug("Assumes no time for the system until it returns")
    elapsed: float | None = None
    # log.debug("Runs the case in its own span")
    with case_span(run, case) as span:
        # log.debug("Tries the case; a failing case must not stop the run")
        try:
            # log.debug("Runs the system on the case")
            output = system_fn(case)
            # log.debug("Stops the clock before scoring, so the time is the system's")
            elapsed = time.perf_counter() - started
            # log.debug("Scores the output")
            scores = scorer_fn(case, output)
        except Exception as exc:  # noqa: BLE001 - one case's failure is a result, not a crash
            # log.debug("Notes the error's type for the span")
            failure = type(exc).__name__
            # log.debug("Records the error's type and message")
            error = f"{failure}: {exc}"
            # log.debug("Logs the error with the end of its traceback")
            log_event(
                log,
                "eval.case_error",
                logging.WARNING,
                case_id=case.id,
                error=error,
                trace=traceback.format_exc()[-TRACE_CHARS:],
            )
        # log.debug("Records the scores, and the failure if there was one")
        scored(span, scores, failure)
    # log.debug("Returns the case's result")
    return CaseResult(
        case_id=case.id,
        tags=case.tags,
        ok=error is None,
        scores=scores,
        output=_jsonable(output),
        error=error,
        latency_ms=int((time.perf_counter() - started if elapsed is None else elapsed) * MS),
        cost_usd=round(adapter.spent_usd - spent_before, COST_PLACES),
        calls=len(adapter.calls) - calls_before,
    )


# log.debug("Defines a whole evaluation run")
def run_eval(
    *,
    name: str | None = None,
    cases: list[EvalCase] | None = None,
    adapter: ModelAdapter | None = None,
    system_fn: Callable[[EvalCase], Any] | None = None,
    scorer_fn: Callable[[EvalCase, Any], dict[str, Any]] | None = None,
    out_dir: Path | str | None = None,
    keep_output: bool = True,
) -> RunResult:
    """Runs every case, then writes <name>-<time>.json and .md files.

    Each case runs under its own request id, "<name>:<case id>", so
    its log lines can be found together, and in its own span; the run's
    spans share a session named "<name>-<time>". When spans_keep is on,
    the spans are also written to <name>-<time>.spans.jsonl. Pass
    keep_output=False when the system saves its outputs itself and the
    results file should hold only the scores.

    Args:
        name: The run's name, used in file names and request ids.
            Required.
        cases: The cases to run, in order. Required.
        adapter: The model adapter the system calls; it gives the
            run's model, provider and cost. Required.
        system_fn: Runs the system on a case and returns its output.
            Required.
        scorer_fn: Scores a case's output as a flat dict of numbers
            and booleans. Required.
        out_dir: The folder the result files go in. Required.
        keep_output: Whether the results keep each case's output.

    Returns:
        The run, also written to `out_dir` with a <name>-latest.md copy.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Takes the cases, which the caller must give")
    cases = required(cases=cases)
    # log.debug("Takes the adapter, which the caller must give")
    adapter = required(adapter=adapter)
    # log.debug("Takes the system under test, which the caller must give")
    system_fn = required(system_fn=system_fn)
    # log.debug("Takes the scorer, which the caller must give")
    scorer_fn = required(scorer_fn=scorer_fn)
    # log.debug("Stops when the caller left out the out dir")
    if out_dir is None:
        # log.debug("Raises the missing-argument error")
        raise missing(out_dir=out_dir)
    # log.debug("Notes when the run started")
    started = datetime.now(UTC)
    # log.debug("Names the run's files by when it started")
    stamp = started.strftime(STAMP)
    # log.debug("Runs the cases as one session, keeping their spans if asked")
    with session(f"{name}-{stamp}"), collect() as kept:
        # log.debug("Runs and scores every case")
        results = _run_all(name, cases, adapter, system_fn, scorer_fn, keep_output=keep_output)
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
    # log.debug("Writes the run's result files, and its spans if asked")
    write_run(run, Path(out_dir), stamp, kept if adapter.settings.spans_keep else ())
    # log.debug("Sends any spans still waiting to be sent")
    flush_spans()
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
def write_run(
    run: RunResult | None = None,
    out_dir: Path | None = None,
    stamp: str | None = None,
    spans: Sequence[ReadableSpan] = (),
) -> None:
    """Writes the run as JSON and Markdown; refreshes the latest copy.

    Args:
        run: The finished run. Required.
        out_dir: The folder the files go in, created if needed.
            Required.
        stamp: The run's start time as the file names show it.
            Required.
        spans: The run's spans, written beside the results when there
            are any.
    """
    # log.debug("Takes the run, which the caller must give")
    run = required(run=run)
    # log.debug("Takes the output folder, which the caller must give")
    out_dir = required(out_dir=out_dir)
    # log.debug("Takes the time stamp for the file names, which the caller must give")
    stamp = required(stamp=stamp)
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
    # log.debug("Writes the run's spans beside them, when any were kept")
    if spans:
        # log.debug("Writes one span per line")
        write_spans(spans, out_dir / f"{run.name}-{stamp}{SPANS_SUFFIX}")


# log.debug("Defines how every case of a run is run")
def _run_all(
    name: str | None = None,
    cases: list[EvalCase] | None = None,
    adapter: ModelAdapter | None = None,
    system_fn: Callable[[EvalCase], Any] | None = None,
    scorer_fn: Callable[[EvalCase, Any], dict[str, Any]] | None = None,
    *,
    keep_output: bool = True,
) -> list[CaseResult]:
    """Runs and scores each case under its own request id.

    Args:
        name: The run's name. Required.
        cases: The cases to run, in order. Required.
        adapter: The model adapter the system calls. Required.
        system_fn: Runs the system on a case. Required.
        scorer_fn: Scores a case's output. Required.
        keep_output: Whether the results keep each case's output.

    Returns:
        Each case's result, in order.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Takes the adapter, which the caller must give")
    adapter = required(adapter=adapter)
    # log.debug("Takes the system under test, which the caller must give")
    system_fn = required(system_fn=system_fn)
    # log.debug("Takes the scorer, which the caller must give")
    scorer_fn = required(scorer_fn=scorer_fn)
    # log.debug("Starts the list of case results")
    results: list[CaseResult] = []
    # log.debug("Runs each case under its own request id")
    for case in required(cases=cases):
        # log.debug("Opens the case's request id")
        with new_request_id(f"{name}:{case.id}"):
            # log.debug("Runs and scores the case")
            result = run_case(case, adapter, system_fn, scorer_fn, run=name)
        # log.debug("Keeps the result, without its output if asked")
        results.append(result if keep_output else result.model_copy(update={"output": None}))
    # log.debug("Returns the results")
    return results


# log.debug("Defines how any output becomes JSON-safe")
def _jsonable(value: Any = None) -> Any:
    """Returns a model as a dict, JSON as is, anything else as text.

    Args:
        value: What the system returned.

    Returns:
        A pydantic model's dict, a value JSON can hold as it is, or
        anything else as its repr.
    """
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
