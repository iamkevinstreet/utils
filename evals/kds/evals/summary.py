########################################################################
#                      evals/kds/evals/summary.py                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Averages a run's scores, adds time and cost figures, and writes the
Markdown results table.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

# Local
from kds.args import required
from kds.evals import config
from kds.evals.metrics import mean, percentile

# log.debug("Imports the run types for annotations only, avoiding a cycle")
if TYPE_CHECKING:
    from kds.evals.runner import CaseResult, RunResult

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the decimal places the cost per case is kept to, from the config")
COST_PLACES = config.COST_PLACES

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the decimal places averaged scores are kept to")
SCORE_PLACES = 4
# log.debug("Sets the size above which a number is shown whole")
LARGE = 1000
# log.debug("Sets the median and tail percentiles reported")
MEDIAN, TAIL = 50, 95
# log.debug("Sets the separator between table cells, and the row end")
SEP, END = " | ", " |"


########################################################################
#                            Run summaries                             #
########################################################################


# log.debug("Defines the score names a set of results shares")
def score_keys(results: list[CaseResult] | None = None) -> list[str]:
    """Returns the sorted names of every numeric or boolean score.

    Args:
        results: The case results to look through. Required.

    Returns:
        The names, each once, in alphabetical order.
    """
    # log.debug("Takes the results, which the caller must give")
    results = required(results=results)
    # log.debug("Collects names whose values are numbers or booleans")
    return sorted(
        {k for r in results for k, v in r.scores.items() if isinstance(v, bool | int | float)}
    )


# log.debug("Defines a run's summary")
def summarise(results: list[CaseResult] | None = None) -> dict[str, Any]:
    """Averages each score over the cases that ran; adds time and cost.

    Failed cases count in the failure rate, latency and cost, but not
    in the score averages, which would otherwise mix in zeros.

    Args:
        results: The case results of a run, or of one tag's cases.
            Required.

    Returns:
        Each score's mean, the median and 95th percentile latency, the
        total and per-case cost, and the failure rate.
    """
    # log.debug("Takes the results, which the caller must give")
    results = required(results=results)
    # log.debug("Keeps the cases that ran")
    ok = [r for r in results if r.ok]
    # log.debug("Averages each score over those cases")
    summary: dict[str, Any] = {
        key: round(mean([float(r.scores[key]) for r in ok if key in r.scores]), SCORE_PLACES)
        for key in score_keys(ok)
    }
    # log.debug("Lists every case's latency")
    latencies = [r.latency_ms for r in results]
    # log.debug("Lists every case's cost")
    costs = [r.cost_usd for r in results]
    # log.debug("Adds the median and tail latency, total and mean cost")
    summary |= {
        "latency_p50_ms": percentile(latencies, MEDIAN),
        "latency_p95_ms": percentile(latencies, TAIL),
        "cost_total_usd": round(sum(costs), SCORE_PLACES),
        "cost_per_case_usd": round(mean(costs), COST_PLACES),
        "failure_rate": round((len(results) - len(ok)) / len(results), SCORE_PLACES)
        if results
        else 0.0,
    }
    # log.debug("Returns the summary")
    return summary


# log.debug("Defines how a number is shown in the report")
def fmt(value: Any = None) -> str:
    """Shows floats without trailing zeros, and large ones whole.

    Args:
        value: The value to show.

    Returns:
        A float to four places with trailing zeros trimmed, or whole
        with commas once its size reaches 1,000; anything else as
        plain text.
    """
    # log.debug("Shows anything but a float as it is")
    if not isinstance(value, float):
        # log.debug("Returns its text")
        return str(value)
    # log.debug("Shows a large float whole, with thousands commas")
    if abs(value) >= LARGE:
        # log.debug("Returns the whole number")
        return f"{value:,.0f}"
    # log.debug("Returns four places with trailing zeros trimmed")
    return f"{value:.4f}".rstrip("0").rstrip(".")


# log.debug("Defines the Markdown report of a run")
def to_markdown(run: RunResult | None = None) -> str:
    """Returns the report: the summary, a table by tag, the failures.

    Args:
        run: The run to report on. Required.

    Returns:
        The report as Markdown, ending in a newline.
    """
    # log.debug("Takes the run, which the caller must give")
    run = required(run=run)
    # log.debug("Writes the title, the run's facts and the summary table")
    lines = [
        f"# {run.name}",
        "",
        f"Model: `{run.model}` ({run.provider}). Cases: {run.cases}. Failures: {run.failures}. "
        f"Run: {run.started_at}. Prices as of {run.prices_as_of}.",
        "",
        "| Measure | Value |",
        "| --- | --- |",
        *(f"| {k} | {fmt(v)} |" for k, v in run.summary.items()),
    ]
    # log.debug("Adds the table by tag")
    lines += _by_tag(run)
    # log.debug("Lists the cases that failed")
    failed = [r for r in run.results if not r.ok]
    # log.debug("Adds the failures section when any failed")
    if failed:
        # log.debug("Adds one line per failed case")
        lines += ["", "## Failures", "", *(f"- `{r.case_id}`: {r.error}" for r in failed)]
    # log.debug("Returns the report with a final newline")
    return "\n".join(lines) + "\n"


# log.debug("Defines the table that breaks scores down by tag")
def _by_tag(run: RunResult | None = None) -> list[str]:
    """Returns the by-tag table's lines, or none if no case has tags.

    Args:
        run: The run whose cases are broken down by tag. Required.

    Returns:
        The section's heading and table, one row per tag, or an empty
        list.
    """
    # log.debug("Takes the run, which the caller must give")
    run = required(run=run)
    # log.debug("Collects every tag used")
    tags = sorted({t for r in run.results for t in r.tags})
    # log.debug("Returns nothing when there are no tags")
    if not tags:
        # log.debug("Returns an empty list")
        return []
    # log.debug("Finds the score columns")
    keys = score_keys(run.results)
    # log.debug("Writes the heading and the table's header rows")
    lines = [
        "",
        "## By tag",
        "",
        "| Tag | Cases | " + SEP.join(keys) + END,
        "| --- | --- | " + SEP.join("---" for _ in keys) + END,
    ]
    # log.debug("Adds a row per tag, summarising its cases")
    for tag in tags:
        # log.debug("Picks the cases with the tag")
        subset = [r for r in run.results if tag in r.tags]
        # log.debug("Summarises them")
        summary = summarise(subset)
        # log.debug("Adds the tag's row")
        lines.append(
            f"| {tag} | {len(subset)} | " + SEP.join(fmt(summary.get(k)) for k in keys) + END
        )
    # log.debug("Returns the table's lines")
    return lines
