########################################################################
#                    diagrams/kds/diagrams/spec.py                     #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Reads diagrams written as data in a TOML file    #
#                     and builds each one, so layouts stay reviewable. #
########################################################################
"""Diagrams as data: a TOML file of zones, components, arrows, bands.

Each `[[diagram]]` names its output `file`, its size and title block,
then lists its parts. Parts are drawn zones first, then components,
arrows and bands, so the order inside the file does not matter.

    [[diagram]]
    file = "architecture.svg"
    width = 1000
    height = 720
    title = "Demo at a glance"
    subtitle = "One idea."
    caption = "How to read it."

    [[diagram.component]]
    box = [28, 150, 440, 70]
    name = "API"
    details = ["FastAPI, /api/v1"]
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

from kds.diagrams import Diagram
from kds.diagrams.svg import Box

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the encoding the spec file is read in")
ENCODING = "utf-8"
# log.debug("Names the key that holds a part's rectangle")
BOX = "box"
# log.debug("Names the keys that title a zone or band")
TITLE = "title"
# log.debug("Names the key that holds a diagram's output file")
FILE = "file"


# log.debug("Defines how one diagram is built from its table")
def build(table: dict[str, Any]) -> Diagram:
    """Return the diagram a `[[diagram]]` table describes.

    Raises:
        ValueError: A required key is missing; the message names it.
    """
    # log.debug("Reads the keys every diagram must have")
    try:
        # log.debug("Creates the canvas and title block")
        d = Diagram(
            table["width"], table["height"], table[TITLE], table["subtitle"], table["caption"]
        )
        # log.debug("Adds each zone")
        for z in table.get("zone", []):
            # log.debug("Draws the zone")
            d.zone(Box(*z[BOX]), z[TITLE], z.get("rule", ""))
        # log.debug("Adds each component")
        for c in table.get("component", []):
            # log.debug("Draws the component")
            d.component(Box(*c[BOX]), c["name"], c.get("details", []), c.get("note", ""))
        # log.debug("Adds each arrow")
        for a in table.get("arrow", []):
            # log.debug("Draws the arrow, its points as pairs")
            d.arrow(
                [tuple(p) for p in a["points"]],
                a.get("label", ""),
                tuple(a.get("at", (0, 0))),
                a.get("accent", False),
            )
        # log.debug("Adds each band")
        for b in table.get("band", []):
            # log.debug("Draws the band")
            d.band(Box(*b[BOX]), b[TITLE], b.get("lines", []))
    except KeyError as missing:
        # log.debug("Names the missing key and the diagram it belongs to")
        msg = f"diagram {table.get(FILE, '?')!r} is missing the key {missing}"
        # log.debug("Raises it")
        raise ValueError(msg) from missing
    # log.debug("Returns the built diagram")
    return d


# log.debug("Defines how a whole spec file is drawn")
def render_file(spec: Path) -> list[Path]:
    """Write each diagram in `spec` beside it; return the paths."""
    # log.debug("Reads the spec")
    tables = tomllib.loads(spec.read_text(encoding=ENCODING)).get("diagram", [])
    # log.debug("Starts the list of files written")
    written: list[Path] = []
    # log.debug("Builds and writes each diagram")
    for table in tables:
        # log.debug("Names the output beside the spec")
        out = spec.parent / table[FILE]
        # log.debug("Builds the diagram and writes it")
        build(table).write(out)
        # log.debug("Records the file")
        written.append(out)
    # log.debug("Returns the files written")
    return written
