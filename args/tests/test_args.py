########################################################################
#                       args/tests/test_args.py                        #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests that required() hands back a value the caller gave and stops,
naming the argument, when the caller left it out.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from datetime import date

# Third-party
import pytest

# Local
from kds.args import missing, required

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                          Required arguments                          #
########################################################################
# log.debug("Defines the test: a given value comes back unchanged")
def test_a_given_value_comes_back() -> None:
    """Returns exactly the value the caller passed."""
    # log.debug("Takes a date that was given")
    taken = required(notice_date=date(2026, 3, 2))
    # log.debug("Checks it is the same date")
    assert taken == date(2026, 3, 2)


# log.debug("Defines the test: falsy values are values, not missing")
def test_falsy_values_are_not_missing() -> None:
    """Only None means left out: zero, "" and False are values."""
    # log.debug("Checks zero, empty text, an empty list and False come back")
    assert [required(v=v) for v in (0, "", [], False)] == [0, "", [], False]


# log.debug("Defines the test: a missing argument is named in the error")
def test_a_missing_argument_is_named() -> None:
    """The error names the argument, as Python's own error does."""
    # log.debug("Checks None raises TypeError naming notice_date")
    with pytest.raises(TypeError, match="missing required argument: 'notice_date'"):
        # log.debug("Takes an argument the caller left out")
        required(notice_date=None)


# log.debug("Defines the test: exactly one argument is taken")
def test_exactly_one_argument_is_taken() -> None:
    """None or several arguments are a mistake in the call itself."""
    # log.debug("Checks a call with no argument is refused")
    with pytest.raises(TypeError, match="exactly one argument"):
        # log.debug("Calls it with nothing")
        required()
    # log.debug("Checks a call with two arguments is refused")
    with pytest.raises(TypeError, match="exactly one argument"):
        # log.debug("Calls it with two")
        required(a=1, b=2)


# log.debug("Defines the test: missing() names the argument for a guard")
def test_missing_names_the_argument() -> None:
    """The guard's error matches the one required() raises."""
    # log.debug("Builds the error for a union-typed argument left out")
    error = missing(path=None)
    # log.debug("Checks it is a TypeError naming the argument")
    assert isinstance(error, TypeError) and str(error) == "missing required argument: 'path'"


# log.debug("Defines the test: a guard narrows a union the way the standard writes it")
def test_a_guard_raises_for_a_union_left_out() -> None:
    """The guard form stops a call that left a union-typed value out."""

    # log.debug("Defines a function that takes a path as text or a Path")
    def size(path: str | int | None = None) -> int:
        """Returns the length of a value's text.

        Args:
            path: The value, as text or a number. Required.

        Returns:
            How many characters its text has.
        """
        # log.debug("Stops when the caller left out the path")
        if path is None:
            # log.debug("Raises the missing-argument error")
            raise missing(path=path)
        # log.debug("Returns the length of its text")
        return len(str(path))

    # log.debug("Checks a given value is measured")
    assert size(123) == 3
    # log.debug("Checks a value left out stops the call")
    with pytest.raises(TypeError, match="'path'"):
        # log.debug("Calls it without the path")
        size()
