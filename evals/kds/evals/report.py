########################################################################
#                      evals/kds/evals/report.py                       #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Compares two runs as a before-and-after table    #
#                     and writes the changelog line a case study       #
#                     needs.                                           #
########################################################################
"""Run comparison and changelog lines."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from kds.evals.runner import RunResult
from kds.evals.summary import fmt

# Module constants
log = logging.getLogger(__name__)


# log.debug("Defines how a saved run is read back")
def load_run(path: Path | str) -> RunResult:
    """Return the run saved as JSON at `path`."""
    # log.debug("Reads and validates the saved run")
    return RunResult.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


# log.debug("Defines the change between two values")
def _change(before: object, after: object) -> str:
    """Return after minus before, signed; blank for non-numbers."""
    # log.debug("Returns nothing unless both are numbers")
    if not (isinstance(before, int | float) and isinstance(after, int | float)):
        # log.debug("Returns an empty cell")
        return ""
    # log.debug("Returns the signed difference, trailing zeros trimmed")
    return f"{after - before:+.4f}".rstrip("0").rstrip(".")


# log.debug("Defines the before-and-after table")
def compare(before: RunResult, after: RunResult, keys: list[str] | None = None) -> str:
    """Return a Markdown table of each measure before and after."""
    # log.debug("Uses the given measures, or every one either run has")
    keys = keys or sorted(set(before.summary) | set(after.summary))
    # log.debug("Writes the header rows, naming each run and its model")
    lines = [
        f"| Measure | {before.name} ({before.model}) | {after.name} ({after.model}) | Change |",
        "| --- | --- | --- | --- |",
    ]
    # log.debug("Adds one row per measure")
    for key in keys:
        # log.debug("Reads the measure from both runs")
        b, a = before.summary.get(key), after.summary.get(key)
        # log.debug("Adds the row with the change")
        lines.append(f"| {key} | {_cell(b)} | {_cell(a)} | {_change(b, a)} |")
    # log.debug("Returns the table with a final newline")
    return "\n".join(lines) + "\n"


# log.debug("Defines the one-line changelog entry")
def changelog_line(
    version: str, date: str, note: str, runs: tuple[RunResult, RunResult], key: str
) -> str:
    """Return "- **v0.2, Oct 20, 2026.** <note>: <key> 0 -> 1."."""
    # log.debug("Splits the pair into before and after")
    before, after = runs
    # log.debug("Returns the line with the measure's two values")
    return (
        f"- **{version}, {date}.** {note}: {key} "
        f"{_cell(before.summary.get(key))} -> {_cell(after.summary.get(key))}."
    )


# log.debug("Defines how a value is shown in a cell")
def _cell(value: object) -> str:
    """Show None as an empty cell, anything else as the report does."""
    # log.debug("Returns empty for no value, else the formatted value")
    return "" if value is None else fmt(value)
