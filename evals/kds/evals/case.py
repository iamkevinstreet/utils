########################################################################
#                       evals/kds/evals/case.py                        #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

An evaluation case: input, expected output and tags; and the loader that
refuses duplicate ids.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

# Third-party
from pydantic import BaseModel, Field

# Local
from kds.args import missing

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the start of a comment line in a .jsonl case file")
COMMENT = "#"


########################################################################
#                           Evaluation cases                           #
########################################################################
# log.debug("Defines one evaluation case")
class EvalCase(BaseModel):
    """An input, the expected output, and tags for slicing results."""

    # log.debug("Holds the case's unique id")
    id: str
    # log.debug("Holds what the system under test receives")
    input: dict[str, Any]
    # log.debug("Holds what a correct system returns")
    expected: dict[str, Any] = Field(default_factory=dict)
    # log.debug("Holds labels results are grouped by, such as hard")
    tags: list[str] = Field(default_factory=list)
    # log.debug("Holds a note on why the case exists")
    notes: str | None = None


# log.debug("Defines the loader for a case file")
def load_cases(path: Path | str | None = None) -> list[EvalCase]:
    """Loads cases from .jsonl (one per line) or .json (a list).

    Args:
        path: The case file to read. Required.

    Returns:
        The cases, in the order the file lists them.

    Raises:
        ValueError: Two cases share an id.
    """
    # log.debug("Stops when the caller left out the path")
    if path is None:
        # log.debug("Raises the missing-argument error")
        raise missing(path=path)
    # log.debug("Points at the file")
    file = Path(path)
    # log.debug("Reads its text")
    text = file.read_text(encoding="utf-8")
    # log.debug("Reads one case per line, skipping blanks and comments")
    if file.suffix == ".jsonl":
        # log.debug("Parses each line that holds a case")
        rows = [
            json.loads(line)
            for line in text.splitlines()
            if line.strip() and not line.startswith(COMMENT)
        ]
    else:
        # log.debug("Parses the whole file as a list")
        rows = json.loads(text)
    # log.debug("Validates each row as a case")
    cases = [EvalCase.model_validate(row) for row in rows]
    # log.debug("Finds any id used more than once")
    ids = [case.id for case in cases]
    # log.debug("Lists the repeated ids, sorted")
    repeated = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    # log.debug("Stops when any id repeats")
    if repeated:
        # log.debug("Raises naming the repeated ids")
        raise ValueError(f"duplicate case ids: {repeated}")
    # log.debug("Returns the cases")
    return cases
