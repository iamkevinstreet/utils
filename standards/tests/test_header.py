########################################################################
#                    standards/tests/test_header.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests that the header box renders, parses back   #
#                     and is checked the way the standard says.        #
########################################################################
"""Tests for the header box."""

from __future__ import annotations

import logging

from kds.standards import header as hdr

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets a path used as every test box's title")
PATH = "backend/app/answer.py"
# log.debug("Sets a date used for both of every test box's dates")
DAY = "2026-10-28"
# log.debug("Sets a purpose long enough to wrap onto two lines")
PURPOSE = "Answers a question from the approved sources only and abstains when they do not."


# log.debug("Defines the test that every rendered line is 72 wide")
def test_render_is_72_wide() -> None:
    """Every line of a rendered box is exactly 72 characters."""
    # log.debug("Renders a box with a two-line purpose")
    box = hdr.render(PATH, DAY, DAY, PURPOSE)
    # log.debug("Checks each line's width")
    assert all(len(line) == hdr.WIDTH for line in box)


# log.debug("Defines the test that a box parses back to its fields")
def test_round_trip_in_each_style() -> None:
    """A rendered box parses back to the same fields in every style."""
    # log.debug("Renders the box once")
    box = hdr.render(PATH, DAY, DAY, PURPOSE)
    # log.debug("Tries each comment style")
    for style in ("hash", "slash", "block", "astro", "html"):
        # log.debug("Wraps the box for the style and adds some code")
        text = "\n".join([*hdr.wrap(box, style), "code"]) + "\n"
        # log.debug("Parses the box back out")
        found, problem = hdr.parse(text, style)
        # log.debug("Checks it parsed with no problem")
        assert found is not None, (style, problem)
        # log.debug("Checks the fields survived the round trip")
        assert (found.title, found.created, found.purpose) == (PATH, DAY, PURPOSE)


# log.debug("Defines the test that a missing box is reported")
def test_missing_box_is_reported() -> None:
    """A file without the box parses to None and a reason."""
    # log.debug("Parses a file that starts with code")
    found, problem = hdr.parse("import os\n", "hash")
    # log.debug("Checks nothing was found and a reason given")
    assert found is None and "header box" in problem


# log.debug("Defines the test that wrong values are each reported")
def test_check_fields_reports_each_wrong_value() -> None:
    """Wrong title, stale date and long purpose are three findings."""
    # log.debug("Builds a box with three wrong values")
    box = hdr.render("old/name.py", DAY, "2026-01-01", "x" * 141)
    # log.debug("Parses the box")
    found, _ = hdr.parse("\n".join(box) + "\n", "hash")
    # log.debug("Checks the values against the true path and dates")
    findings = hdr.check_fields(found, PATH, DAY, DAY)
    # log.debug("Checks one finding for each wrong value")
    assert len(findings) == 3
