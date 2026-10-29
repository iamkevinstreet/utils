########################################################################
#                      evals/kds/evals/report.py                       #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Compares two runs as a before-and-after table and writes the changelog
line a case study needs.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging
from pathlib import Path

# Local
from kds.args import missing, required
from kds.evals.runner import RunResult
from kds.evals.summary import fmt

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                            Run comparison                            #
########################################################################
# log.debug("Defines how a saved run is read back")
def load_run(path: Path | str | None = None) -> RunResult:
    """Returns the run saved as JSON at `path`.

    Args:
        path: The JSON file run_eval wrote. Required.

    Returns:
        The run, as run_eval returned it.
    """
    # log.debug("Stops when the caller left out the path")
    if path is None:
        # log.debug("Raises the missing-argument error")
        raise missing(path=path)
    # log.debug("Reads and validates the saved run")
    return RunResult.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


# log.debug("Defines the change between two values")
def _change(before: object = None, after: object = None) -> str:
    """Returns after minus before, signed; blank for non-numbers.

    Args:
        before: The measure in the earlier run; None when it has none.
        after: The measure in the later run; None when it has none.

    Returns:
        The change to four places with its sign, trailing zeros
        trimmed, or an empty string unless both values are numbers.
    """
    # log.debug("Returns nothing unless both are numbers")
    if not (isinstance(before, int | float) and isinstance(after, int | float)):
        # log.debug("Returns an empty cell")
        return ""
    # log.debug("Returns the signed difference, trailing zeros trimmed")
    return f"{after - before:+.4f}".rstrip("0").rstrip(".")


# log.debug("Defines the before-and-after table")
def compare(
    before: RunResult | None = None, after: RunResult | None = None, keys: list[str] | None = None
) -> str:
    """Returns a Markdown table of each measure before and after.

    Args:
        before: The earlier run. Required.
        after: The later run. Required.
        keys: The measures to show, in order; None or an empty list
            shows every measure either run has, sorted.

    Returns:
        The table as Markdown, ending in a newline.
    """
    # log.debug("Takes the earlier run, which the caller must give")
    before = required(before=before)
    # log.debug("Takes the later run, which the caller must give")
    after = required(after=after)
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
    version: str | None = None,
    date: str | None = None,
    note: str | None = None,
    runs: tuple[RunResult, RunResult] | None = None,
    key: str | None = None,
) -> str:
    """Returns "- **v0.2, Oct 20, 2026.** <note>: <key> 0 -> 1.".

    Args:
        version: The release, such as "v0.2". Required.
        date: The release date as the line shows it. Required.
        note: What changed. Required.
        runs: The runs before and after the change. Required.
        key: The measure quoted from both runs. Required.

    Returns:
        One Markdown list item with the measure before and after.
    """
    # log.debug("Takes the version, which the caller must give")
    version = required(version=version)
    # log.debug("Takes the date, which the caller must give")
    date = required(date=date)
    # log.debug("Takes the note, which the caller must give")
    note = required(note=note)
    # log.debug("Takes the runs, which the caller must give")
    runs = required(runs=runs)
    # log.debug("Takes the key, which the caller must give")
    key = required(key=key)
    # log.debug("Splits the pair into before and after")
    before, after = runs
    # log.debug("Returns the line with the measure's two values")
    return (
        f"- **{version}, {date}.** {note}: {key} "
        f"{_cell(before.summary.get(key))} -> {_cell(after.summary.get(key))}."
    )


# log.debug("Defines how a value is shown in a cell")
def _cell(value: object = None) -> str:
    """Shows None as an empty cell, anything else as the report does.

    Args:
        value: The value to show; None when the run has no such
            measure.

    Returns:
        An empty string for None, else the value as fmt shows it.
    """
    # log.debug("Returns empty for no value, else the formatted value")
    return "" if value is None else fmt(value)
