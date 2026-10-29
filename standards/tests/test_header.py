########################################################################
#                    standards/tests/test_header.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the file header: drawn in every style it reads back with the same
fields, a file without one says why, and each wrong value is a finding.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Third-party
import pytest

# Local
from kds.standards import header as hdr

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the path the test headers name")
PATH = "backend/src/grounded_qa/answer.py"
# log.debug("Sets the date the test headers carry")
DAY = "2026-10-28"
# log.debug("Sets a description long enough to wrap")
DESCRIPTION = (
    "Answers a question from the approved sources only, and abstains when "
    "they do not cover it, so a reader never sees an answer without a source."
)
# log.debug("Lists every header style")
STYLES = (hdr.PYTHON, hdr.HASH, hdr.SLASH, hdr.BLOCK, hdr.ASTRO, hdr.HTML)


########################################################################
#                             Header tests                             #
########################################################################
# log.debug("Defines the test: a drawn header reads back in every style")
@pytest.mark.parametrize("style", STYLES)
def test_a_header_reads_back_in_every_style(style: str) -> None:
    """Drawn, then read, a header gives back the same fields.

    Args:
        style: The header style under test.
    """
    # log.debug("Draws the header above one line of code")
    text = "\n".join([*hdr.render(PATH, DAY, DAY, DESCRIPTION, style), "", "code"]) + "\n"
    # log.debug("Reads it back")
    found, problem = hdr.parse(text, style)
    # log.debug("Checks it was found")
    assert found is not None, problem
    # log.debug("Checks the fields and the description came back whole")
    assert (found.title, found.created, found.modified, found.description) == (
        PATH,
        DAY,
        DAY,
        DESCRIPTION,
    )


# log.debug("Defines the test: a Python header is a title box and a docstring")
def test_a_python_header_is_a_box_then_a_docstring() -> None:
    """The box holds only the path; the docstring holds the rest."""
    # log.debug("Draws a Python header")
    lines = hdr.render(PATH, DAY, DAY, "Answers questions.", hdr.PYTHON)
    # log.debug("Checks the box, the fields, the blank line and the description")
    assert lines == [
        hdr.BORDER,
        hdr.title_line(PATH),
        hdr.BORDER,
        '"""',
        "Author:            Kevin Street",
        f"Created on:        {DAY}",
        f"Last modified on:  {DAY}",
        "",
        "Answers questions.",
        '"""',
    ]


# log.debug("Defines the test: every box line is 72 characters")
def test_every_box_line_is_72_wide() -> None:
    """The title box fits PEP 8's width for comments."""
    # log.debug("Checks the three box lines")
    assert all(len(line) == hdr.WIDTH for line in hdr.box(PATH, hdr.PYTHON))


# log.debug("Defines the test: a file with no header says why")
def test_a_file_with_no_header_says_why() -> None:
    """A file without the box parses to None and a reason."""
    # log.debug("Reads a file that starts with code")
    found, problem = hdr.parse("import os\n", hdr.PYTHON)
    # log.debug("Checks the reason names the box")
    assert found is None and "box" in problem


# log.debug("Defines the test: the old box with fields inside is refused")
def test_the_old_box_is_refused() -> None:
    """A box with the fields inside it is the old form, and fails."""
    # log.debug("Builds an old-form box")
    old = "\n".join(
        [hdr.BORDER, hdr.title_line(PATH), hdr.BORDER, "#  Author:  Kevin Street" + " " * 46 + "#"]
    )
    # log.debug("Checks it does not read as a header")
    assert hdr.parse(old + "\n", hdr.PYTHON)[0] is None


# log.debug("Defines the test: each wrong value is a finding")
def test_each_wrong_value_is_a_finding() -> None:
    """A wrong title, a stale date and no description each show."""
    # log.debug("Draws a header for the old path, dated wrongly, with no description")
    text = "\n".join(hdr.render("old/name.py", DAY, "2026-01-01", "", hdr.PYTHON)) + "\n"
    # log.debug("Reads it back")
    found, _ = hdr.parse(text, hdr.PYTHON)
    # log.debug("Checks it was found")
    assert found is not None
    # log.debug("Lists the messages of the findings against the true values")
    messages = [f.message for f in hdr.check_fields(found, PATH, DAY, DAY)]
    # log.debug("Checks the title, the modified date and the description are named")
    assert len(messages) == 3 and "path" in messages[0] and "describe" in messages[-1]


# log.debug("Defines the test: an off-centre title is a finding")
def test_an_off_centre_title_is_a_finding() -> None:
    """The path must sit in the centre of its box."""
    # log.debug("Draws a header and shifts its title one space left")
    lines = hdr.render(PATH, DAY, DAY, "Answers questions.", hdr.PYTHON)
    # log.debug("Moves the title one space towards the left wall")
    lines[1] = "#" + lines[1][2:-1] + " #"
    # log.debug("Reads it back")
    found, _ = hdr.parse("\n".join(lines) + "\n", hdr.PYTHON)
    # log.debug("Checks it was found")
    assert found is not None
    # log.debug("Checks the one finding asks for the title to be centred")
    assert [f.message for f in hdr.check_fields(found, PATH, DAY, DAY)] == [
        "centre the path; run kds-standards stamp"
    ]
