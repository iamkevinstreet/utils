########################################################################
#                   diagrams/tests/test_diagrams.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests that diagrams render as valid SVG, escape  #
#                     their text and refuse text that would overflow.  #
########################################################################
"""Tests for kds.diagrams."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from kds.diagrams import Box, Diagram
from kds.diagrams.spec import render_file

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the SVG namespace ElementTree prefixes every tag with")
NS = "{http://www.w3.org/2000/svg}"


# log.debug("Defines a small diagram every test starts from")
def _diagram() -> Diagram:
    """Return a diagram with one zone, two parts, an arrow, a band."""
    # log.debug("Creates the canvas and its title block")
    d = Diagram(600, 420, "Demo at a glance", "Data stays inside.", "Blue: data.")
    # log.debug("Adds a zone around both components")
    d.zone(Box(20, 140, 560, 160), "Your environment", "nothing leaves it")
    # log.debug("Adds the first component")
    d.component(Box(40, 180, 220, 90), "API", ["FastAPI", "/api/v1"])
    # log.debug("Adds the second component, marked new")
    d.component(Box(340, 180, 220, 90), "Store", ["Postgres"], note="new")
    # log.debug("Joins them with an accent arrow")
    d.arrow([(260, 225), (340, 225)], "rows", (284, 216), accent=True)
    # log.debug("Adds the foundation band")
    d.band(Box(20, 320, 560, 80), "Foundation", ["Python 3.12 & <tests>"])
    # log.debug("Returns the diagram")
    return d


# log.debug("Defines the test that the output parses as SVG")
def test_renders_valid_svg(tmp_path: Path) -> None:
    """The written file is well-formed SVG with an accessible name."""
    # log.debug("Points at a folder that does not exist yet")
    path = tmp_path / "docs" / "architecture.svg"
    # log.debug("Writes the diagram, creating the folder")
    _diagram().write(path)
    # log.debug("Parses the file back")
    root = ET.parse(path).getroot()  # noqa: S314 - the file was written by this test
    # log.debug("Checks the root element is an SVG")
    assert root.tag == f"{NS}svg"
    # log.debug("Checks the title element names the diagram")
    assert root.findtext(f"{NS}title") == "Demo at a glance"


# log.debug("Defines the test that text is escaped")
def test_text_is_escaped() -> None:
    """Ampersands and angle brackets in labels are escaped."""
    # log.debug("Checks the band line was escaped")
    assert "Python 3.12 &amp; &lt;tests&gt;" in _diagram().render()


# log.debug("Defines the test that a marker note is drawn muted")
def test_note_is_drawn() -> None:
    """A note renders as a muted span after the component's name."""
    # log.debug("Checks the note's span is in the output")
    assert "> (new)</tspan>" in _diagram().render()


# log.debug("Defines the test that overflowing text is refused")
def test_overflow_is_refused() -> None:
    """A detail line wider than its box raises with a fix-it message."""
    # log.debug("Starts from the demo diagram")
    d = _diagram()
    # log.debug("Expects the overflow error with its advice")
    with pytest.raises(ValueError, match="Widen the box"):
        # log.debug("Adds a long line to a narrow box")
        d.component(Box(0, 0, 80, 60), "X", ["a line far too long for so narrow a box"])


# log.debug("Defines the test that a TOML spec draws its diagrams")
def test_spec_file_is_drawn(tmp_path: Path) -> None:
    """Each [[diagram]] in a spec is written beside it."""
    # log.debug("Names the spec file")
    spec = tmp_path / "diagrams.toml"
    # log.debug("Writes a spec with one diagram and one component")
    spec.write_text(
        '[[diagram]]\nfile = "a.svg"\nwidth = 400\nheight = 300\ntitle = "A"\n'
        'subtitle = "B"\ncaption = "C"\n[[diagram.component]]\nbox = [20, 140, 200, 60]\n'
        'name = "API"\n',
        encoding="utf-8",
    )
    # log.debug("Checks the one file was written")
    assert render_file(spec) == [tmp_path / "a.svg"]


# log.debug("Defines the test that a missing key is named")
def test_spec_missing_key_is_named(tmp_path: Path) -> None:
    """A diagram without its title fails with the key's name."""
    # log.debug("Names the spec file")
    spec = tmp_path / "diagrams.toml"
    # log.debug("Writes a diagram with no title")
    spec.write_text(
        '[[diagram]]\nfile = "a.svg"\nwidth = 1\nheight = 1\nsubtitle = "B"\ncaption = "C"\n',
        encoding="utf-8",
    )
    # log.debug("Expects the error to name the missing key")
    with pytest.raises(ValueError, match="title"):
        # log.debug("Draws the spec")
        render_file(spec)
