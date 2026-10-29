########################################################################
#                   standards/tests/test_pylines.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the line rules: a logger line left switched on, a line wider than
its limit, and a literal repeated inside functions are each a finding.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Local
from kds.standards import pylines

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                          Lines and literals                          #
########################################################################
# log.debug("Defines the test: a logger line left on is a finding")
def test_a_live_logger_line_is_a_finding() -> None:
    """A logger line switched on must be off again before a commit."""
    # log.debug("Checks the trace-off rule fires on a live line")
    assert [f.rule for f in pylines.check_lines("x.py", 'log.debug("Returns yes")\n')] == [
        "trace-off"
    ]


# log.debug("Defines the test: a comment wider than 72 is a finding")
def test_a_wide_comment_is_a_finding() -> None:
    """Prose wraps at 72 characters; code may run to 99."""
    # log.debug("Builds a comment of 73 characters and code of 99")
    source = "# " + "x" * 71 + "\nvalue = " + repr("y" * 89) + "\n"
    # log.debug("Checks only the comment is reported")
    assert [f.line for f in pylines.check_lines("x.py", source)] == [1]


# log.debug("Defines the test: a repeated literal is a finding")
def test_a_repeated_literal_is_a_finding() -> None:
    """A string used twice inside functions needs a name."""
    # log.debug("Builds a function that repeats a string")
    source = 'def f():\n    a = "utf-8"\n    b = "utf-8"\n'
    # log.debug("Checks the literal rule reports it once")
    assert len(pylines.check_literals("x.py", source)) == 1
