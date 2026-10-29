########################################################################
#                 standards/kds/standards/findings.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           One finding from a check: the rule broken, the   #
#                     file and line, and what to do about it.          #
########################################################################
"""Findings: what a check found, where, and under which rule."""

from __future__ import annotations

import logging
from dataclasses import dataclass

# Module constants
log = logging.getLogger(__name__)


# log.debug("Defines one finding: a rule broken at one place")
@dataclass(frozen=True, order=True)
class Finding:
    """A rule broken at one place in one file.

    Attributes:
        path: The file, relative to the repository root.
        line: The line number, or 0 when the finding is about the file.
        rule: The rule's short name, such as header or layout.
        message: What is wrong and how to fix it.
    """

    # log.debug("Holds the file the finding is in")
    path: str
    # log.debug("Holds the line number, 0 for the whole file")
    line: int
    # log.debug("Holds the rule's short name")
    rule: str
    # log.debug("Holds what is wrong and how to fix it")
    message: str

    # log.debug("Defines how a finding prints on one line")
    def __str__(self) -> str:
        """Return the finding as path:line: rule: message."""
        # log.debug("Formats the finding as path, line, rule, message")
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"
