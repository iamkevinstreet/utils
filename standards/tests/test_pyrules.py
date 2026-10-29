########################################################################
#                   standards/tests/test_pyrules.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests the Python rules: logger lines and their   #
#                     exemptions, live lines, widths, literals.        #
########################################################################
"""Tests for the Python rules."""

from __future__ import annotations

import logging
import textwrap

from kds.standards import pyrules

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets a file that follows every logger-line rule")
GOOD = textwrap.dedent('''\
    """A module."""

    import os

    # Module constants
    log = logging.getLogger(__name__)
    # log.debug("Sets the folder the module reads")
    ROOT = os.getcwd()


    # log.debug("Defines the function that picks a branch")
    @staticmethod
    @decorated
    def pick(flag: bool) -> str:
        """Pick a branch."""
        # log.debug("Chooses the branch from the flag")
        if flag:
            # log.debug("Returns the yes branch")
            return "yes"
        else:
            # log.debug("Returns the no branch, flag being false")
            return "no"
    ''')


# log.debug("Defines the test that a correct file has no findings")
def test_good_file_has_no_findings() -> None:
    """Imports, docstrings, clauses, stacked decorators are exempt."""
    # log.debug("Checks the good file has no logger-line findings")
    assert pyrules.check_logger_lines("good.py", GOOD) == []


# log.debug("Defines the test that a bare statement is caught")
def test_statement_without_logger_line() -> None:
    """A statement with no logger line above it is a finding."""
    # log.debug("Removes one logger line from the good file")
    bad = GOOD.replace('    # log.debug("Chooses the branch from the flag")\n', "")
    # log.debug("Checks exactly that statement is reported")
    assert [f.line for f in pyrules.check_logger_lines("bad.py", bad)] == [16]


# log.debug("Defines the test that a logger line above else is caught")
def test_logger_line_above_else_breaks_code() -> None:
    """A logger line directly above else would break the code."""
    # log.debug("Puts a logger line above the else line")
    bad = GOOD.replace("    else:", '    # log.debug("Takes the other branch")\n    else:')
    # log.debug("Checks the finding names the clause rule")
    assert any("breaks the code" in f.message for f in pyrules.check_logger_lines("x.py", bad))


# log.debug("Defines the test that a live logger line is caught")
def test_live_logger_line() -> None:
    """A logger line left on is a finding."""
    # log.debug("Switches one logger line on")
    live = GOOD.replace('# log.debug("Returns the yes branch")', 'log.debug("Returns yes")')
    # log.debug("Checks the trace-off rule fires")
    assert any(f.rule == "trace-off" for f in pyrules.check_lines("x.py", live))


# log.debug("Defines the test that a repeated literal is caught")
def test_repeated_literal() -> None:
    """A string used twice inside functions is a finding."""
    # log.debug("Builds a function that repeats a string")
    source = 'def f():\n    a = "utf-8"\n    b = "utf-8"\n'
    # log.debug("Checks the literal rule reports it once")
    assert len(pyrules.check_literals("x.py", source)) == 1
