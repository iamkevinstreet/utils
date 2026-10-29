########################################################################
#                     diagrams/kds/diagrams/svg.py                     #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Draws the at-a-glance diagram style as SVG:      #
#                     zones, components, arrows and the foundation.    #
########################################################################
"""SVG drawing for the house diagram style, one element at a time."""

from __future__ import annotations

import logging
from html import escape
from typing import NamedTuple

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the canvas colour")
CANVAS = "#121212"
# log.debug("Sets the fill of components, a step above the canvas")
FILL = "#1b1b1b"
# log.debug("Sets the fill of the foundation band")
BAND_FILL = "#202020"
# log.debug("Sets the outline of components")
EDGE = "#3d3d3d"
# log.debug("Sets the dashed outline of zones")
ZONE = "#4a4a4a"
# log.debug("Sets the colour of headings and names")
INK = "#f2f2f2"
# log.debug("Sets the colour of detail text and plain arrows")
MUTED = "#a3a3a3"
# log.debug("Sets the one accent, for the paths that matter")
ACCENT = "#5b8def"
# log.debug("Sets the serif stack for the display title")
SERIF = "Georgia, 'Times New Roman', serif"
# log.debug("Sets the sans stack for everything else")
SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
# log.debug("Sets the corner radius of components and zones")
RADIUS = 8
# log.debug("Sets the height of one line of detail text")
LINE = 17
# log.debug("Sets the size of detail text")
SMALL = 12.5
# log.debug("Sets the size of names and zone titles")
NAME = 14
# log.debug("Sets the space between a box's edge and its text")
PAD = 14
# log.debug("Sets the baseline of a box's name, below its top edge")
NAME_ROW = 24
# log.debug("Sets the baseline of a component's first detail line")
DETAIL_ROW = 44
# log.debug("Sets the baseline of the band's title")
BAND_TITLE_ROW = 26
# log.debug("Sets the baseline of the band's first line")
BAND_LINE_ROW = 48
# log.debug("Sets the most detail lines a component shows")
MAX_DETAILS = 3
# log.debug("Sets the average glyph width, as a share of the font size")
GLYPH = 0.56
# log.debug("Sets the average width of a bold glyph")
BOLD_GLYPH = 0.6
# log.debug("Sets the font weight of names and titles")
BOLD = 700
# log.debug("Sets the font weight of ordinary text")
REGULAR = 400
# log.debug("Names the anchor that centres text on its x")
MIDDLE = "middle"
# log.debug("Names the arrowhead of a plain arrow")
PLAIN_HEAD = "plain"
# log.debug("Names the arrowhead of an accent arrow")
ACCENT_HEAD = "accent"
# log.debug("Maps short style names to their SVG attribute names")
ATTRIBUTES = {
    "size": "font-size",
    "weight": "font-weight",
    "family": "font-family",
    "anchor": "text-anchor",
}


# log.debug("Defines a rectangle on the canvas")
class Box(NamedTuple):
    """A rectangle on the canvas, in pixels from the top left."""

    # log.debug("Holds the left edge")
    x: float
    # log.debug("Holds the top edge")
    y: float
    # log.debug("Holds the width")
    w: float
    # log.debug("Holds the height")
    h: float


# log.debug("Defines the estimate of how wide a line of text runs")
def width_of(value: str, size: float, bold: bool = False) -> float:
    """Return the rough width of `value` in pixels at `size`.

    SVG text never wraps, so a line that runs past its box overlaps
    whatever is next to it. The estimate is generous on purpose: a
    diagram that passes it fits in every common font.
    """
    # log.debug("Returns the glyph count times the average glyph width")
    return len(value) * size * (BOLD_GLYPH if bold else GLYPH)


# log.debug("Defines the guard that stops text overflowing its box")
def ensure_fits(value: str, size: float, room: float, bold: bool = False) -> None:
    """Raise ValueError when `value` would run past `room` pixels."""
    # log.debug("Estimates the line's width")
    needed = width_of(value, size, bold)
    # log.debug("Stops with a fix-it message when it does not fit")
    if needed > room:
        # log.debug("Words the error: the line, its width, the room")
        msg = f"{value!r} needs about {needed:.0f}px; the box has {room:.0f}px. Widen the box."
        # log.debug("Raises it")
        raise ValueError(msg)


# log.debug("Defines how one text element is written")
def text(x: float, y: float, value: str, **style: str | float) -> str:
    """Return an SVG text element; keyword style becomes attributes.

    Args:
        x: The left (or centre, with anchor) of the text.
        y: The baseline.
        value: The words, escaped for XML.
        **style: fill, size, weight, family or anchor, and `note`:
            muted words in brackets after the value.

    Returns:
        The element as a string.
    """
    # log.debug("Takes the trailing note out of the style, if any")
    note = str(style.pop("note", ""))
    # log.debug("Lays the caller's style over the defaults")
    attrs = {"family": SANS, "fill": MUTED, "size": SMALL} | style
    # log.debug("Writes the attributes in a stable order, by SVG name")
    rendered = " ".join(
        f'{ATTRIBUTES.get(k, k)}="{escape(str(v))}"' for k, v in sorted(attrs.items())
    )
    # log.debug("Writes the note as a muted, regular-weight span")
    tail = (
        f'<tspan fill="{MUTED}" font-weight="{REGULAR}"> ({escape(note)})</tspan>' if note else ""
    )
    # log.debug("Returns the text element")
    return f'<text x="{x:g}" y="{y:g}" {rendered}>{escape(value)}{tail}</text>'


# log.debug("Defines how a rounded box is written")
def rect(at: Box, *, fill: str, stroke: str, dashed: bool = False) -> str:
    """Return a rounded rectangle, solid or dashed."""
    # log.debug("Adds a dash pattern for zones")
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    # log.debug("Returns the rectangle element")
    return (
        f'<rect x="{at.x:g}" y="{at.y:g}" width="{at.w:g}" height="{at.h:g}" '
        f'rx="{RADIUS}" fill="{fill}" stroke="{stroke}" stroke-width="1"{dash}/>'
    )


# log.debug("Defines how a zone is drawn")
def zone(at: Box, title: str, rule: str) -> str:
    """Return a dashed zone with its title and its rule after a dot."""
    # log.debug("Joins the title and its rule with a middle dot")
    label = f"{title} · {rule}" if rule else title
    # log.debug("Stops if the label would run past the zone")
    ensure_fits(label, NAME, at.w - 2 * PAD, bold=True)
    # log.debug("Draws the dashed outline with no fill")
    outline = rect(at, fill="none", stroke=ZONE, dashed=True)
    # log.debug("Returns the outline and its label, top left")
    return outline + text(at.x + PAD, at.y + NAME_ROW, label, fill=INK, size=NAME, weight=BOLD)


# log.debug("Defines how a component is drawn")
def component(at: Box, name: str, details: list[str], note: str = "") -> str:
    """Return a component: its box, its name, and up to three lines.

    Args:
        at: Where the box goes.
        name: The component's name, bold and centred.
        details: Up to three short lines of grey detail.
        note: A muted marker after the name: "new" or "to build".

    Returns:
        The component's elements as one string.
    """
    # log.debug("Stops if the name and its note would overflow")
    ensure_fits(f"{name} ({note})" if note else name, NAME, at.w - 2 * PAD, bold=True)
    # log.debug("Draws the component's box")
    parts = [rect(at, fill=FILL, stroke=EDGE)]
    # log.debug("Centres the name across the top of the box")
    parts.append(
        text(
            at.x + at.w / 2,
            at.y + NAME_ROW,
            name,
            fill=INK,
            size=NAME,
            weight=BOLD,
            anchor=MIDDLE,
            note=note,
        )
    )
    # log.debug("Centres a single detail line, else aligns them left")
    centred = len(details) == 1
    # log.debug("Writes each detail line under the name")
    for index, detail in enumerate(details[:MAX_DETAILS]):
        # log.debug("Stops if the line would overflow the box")
        ensure_fits(detail, SMALL, at.w - 2 * PAD)
        # log.debug("Places the line on its own row")
        row = at.y + DETAIL_ROW + index * LINE
        # log.debug("Adds the line, centred or left-aligned")
        parts.append(
            text(at.x + at.w / 2, row, detail, anchor=MIDDLE)
            if centred
            else text(at.x + PAD, row, detail)
        )
    # log.debug("Returns the component's elements")
    return "".join(parts)


# log.debug("Defines how an arrow is drawn")
def arrow(
    points: list[tuple[float, float]], label: str, at: tuple[float, float], accent: bool = False
) -> str:
    """Return a polyline arrow with its label.

    Args:
        points: The corners of the path, start to end.
        label: What crosses the arrow.
        at: Where the label's left baseline goes.
        accent: True for a path that matters, drawn in the accent.

    Returns:
        The path, its arrowhead marker reference and its label.
    """
    # log.debug("Picks the colour, weight and head for plain or accent")
    colour, width, head = (ACCENT, 2, ACCENT_HEAD) if accent else (MUTED, 1.2, PLAIN_HEAD)
    # log.debug("Joins the corners into a path")
    path = "M" + " L".join(f"{x:g} {y:g}" for x, y in points)
    # log.debug("Writes the path with its arrowhead")
    line = (
        f'<path d="{path}" fill="none" stroke="{colour}" stroke-width="{width}" '
        f'marker-end="url(#{head})"/>'
    )
    # log.debug("Returns the bare path when the arrow has no label")
    if not label:
        # log.debug("Returns the path alone")
        return line
    # log.debug("Returns the path and its label, bold white when accent")
    return line + text(
        *at, label, fill=INK if accent else MUTED, weight=BOLD if accent else REGULAR
    )


# log.debug("Defines how the foundation band is drawn")
def band(at: Box, title: str, lines: list[str]) -> str:
    """Return the foundation band: what every zone shares."""
    # log.debug("Stops if any of the band's lines would overflow")
    for line in lines:
        # log.debug("Checks one line against the band's width")
        ensure_fits(line, SMALL, at.w - 2 * PAD)
    # log.debug("Draws the band's filled box")
    parts = [rect(at, fill=BAND_FILL, stroke=EDGE)]
    # log.debug("Writes its title")
    parts.append(text(at.x + PAD, at.y + BAND_TITLE_ROW, title, fill=INK, size=NAME, weight=BOLD))
    # log.debug("Writes each line of what is shared")
    parts += [
        text(at.x + PAD, at.y + BAND_LINE_ROW + i * LINE, line) for i, line in enumerate(lines)
    ]
    # log.debug("Returns the band's elements")
    return "".join(parts)


# log.debug("Defines the arrowhead markers every diagram uses")
def markers() -> str:
    """Return the defs for the plain and accent arrowheads."""
    # log.debug("Writes one marker per arrow colour")
    heads = "".join(
        f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="{colour}"/></marker>'
        for name, colour in ((PLAIN_HEAD, MUTED), (ACCENT_HEAD, ACCENT))
    )
    # log.debug("Returns the markers inside defs")
    return f"<defs>{heads}</defs>"
