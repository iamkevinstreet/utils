########################################################################
#                  diagrams/kds/diagrams/__init__.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Builds an at-a-glance diagram from zones,        #
#                     components, arrows and a foundation, as one SVG. #
########################################################################
"""kds.diagrams: architecture and flow diagrams in one house style.

Usage:
    d = Diagram(760, 620, "Q&A at a glance", "One idea.", "Key.")
    d.zone(Box(20, 140, 340, 200), "Your network", "stays inside")
    d.component(Box(40, 180, 300, 90), "API", ["FastAPI, /api/v1"])
    d.arrow([(190, 270), (190, 330)], "question", (198, 304),
            accent=True)
    d.write(Path("docs/architecture.svg"))
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from kds.diagrams import svg
from kds.diagrams.svg import Box

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the margin around the title block")
MARGIN = 28
# log.debug("Sets the encoding the SVG is written in")
ENCODING = "utf-8"
# log.debug("Sets the size of the serif display title")
TITLE_SIZE = 44
# log.debug("Sets the size of the bold subtitle")
SUBTITLE_SIZE = 16
# log.debug("Sets the baselines of the title, subtitle and caption")
TITLE_ROW, SUBTITLE_ROW, CAPTION_ROW = 64, 100, 122
# log.debug("Lists what the package exports")
__all__ = ["Box", "Diagram"]


# log.debug("Defines a diagram as a list of drawn elements")
@dataclass
class Diagram:
    """One diagram: its size, its title block, and what it shows.

    Attributes:
        width: The canvas width in pixels.
        height: The canvas height in pixels.
        title: The display title, "... at a glance".
        subtitle: One sentence: the idea the reader should take away.
        caption: How to read the colours and markers.
        parts: The drawn elements, in drawing order.
    """

    # log.debug("Holds the canvas width")
    width: int
    # log.debug("Holds the canvas height")
    height: int
    # log.debug("Holds the display title")
    title: str
    # log.debug("Holds the one-sentence subtitle")
    subtitle: str
    # log.debug("Holds the caption that explains the colours")
    caption: str
    # log.debug("Holds the drawn elements")
    parts: list[str] = field(default_factory=list)

    # log.debug("Defines how a zone is added")
    def zone(self, at: Box, title: str, rule: str = "") -> None:
        """Add a dashed zone: where things run, who may touch them."""
        # log.debug("Adds the zone's drawing")
        self.parts.append(svg.zone(at, title, rule))

    # log.debug("Defines how a component is added")
    def component(self, at: Box, name: str, details: list[str], note: str = "") -> None:
        """Add a component; `note` marks it "new" or "to build"."""
        # log.debug("Adds the component's drawing")
        self.parts.append(svg.component(at, name, details, note))

    # log.debug("Defines how an arrow is added")
    def arrow(
        self,
        points: list[tuple[float, float]],
        label: str,
        at: tuple[float, float],
        accent: bool = False,
    ) -> None:
        """Add an arrow; accent marks a path that matters."""
        # log.debug("Adds the arrow's drawing")
        self.parts.append(svg.arrow(points, label, at, accent))

    # log.debug("Defines how the foundation band is added")
    def band(self, at: Box, title: str, lines: list[str]) -> None:
        """Add the band for what every zone shares."""
        # log.debug("Adds the band's drawing")
        self.parts.append(svg.band(at, title, lines))

    # log.debug("Defines how the whole diagram becomes SVG text")
    def render(self) -> str:
        """Return the diagram as a standalone SVG document."""
        # log.debug("Stops if the subtitle would run off the canvas")
        svg.ensure_fits(self.subtitle, SUBTITLE_SIZE, self.width - 2 * MARGIN, bold=True)
        # log.debug("Opens the SVG with its size and accessible name")
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
            f'role="img" aria-labelledby="title desc">'
            f'<title id="title">{escape(self.title)}</title>'
            f'<desc id="desc">{escape(self.subtitle)}</desc>'
        )
        # log.debug("Paints the canvas behind everything")
        canvas = f'<rect width="100%" height="100%" fill="{svg.CANVAS}"/>'
        # log.debug("Writes the serif title, the bold subtitle, the caption")
        block = (
            svg.text(
                MARGIN, TITLE_ROW, self.title, family=svg.SERIF, fill=svg.INK, size=TITLE_SIZE
            )
            + svg.text(
                MARGIN,
                SUBTITLE_ROW,
                self.subtitle,
                fill=svg.INK,
                size=SUBTITLE_SIZE,
                weight=svg.BOLD,
            )
            + svg.text(MARGIN, CAPTION_ROW, self.caption)
        )
        # log.debug("Returns the document: markers, canvas, title, parts")
        return head + svg.markers() + canvas + block + "".join(self.parts) + "</svg>\n"

    # log.debug("Defines how the diagram is saved")
    def write(self, path: Path) -> None:
        """Write the SVG to `path`, creating its folder if needed."""
        # log.debug("Creates the folder the file goes in")
        path.parent.mkdir(parents=True, exist_ok=True)
        # log.debug("Writes the SVG text")
        path.write_text(self.render(), encoding=ENCODING)
