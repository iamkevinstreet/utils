########################################################################
#                 standards/kds/standards/sections.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Finds the section banners that cut a file after its header, and checks
they come in the code standard's order: Imports, Global constants,
Local constants, then one banner naming the file's job, which runs to
the end of the file. A section with nothing in it is left out. The
checks on what each section may hold live with each language's rules.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from dataclasses import dataclass

# Local
from kds.args import required
from kds.standards import header as hdr
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Names the imports section")
IMPORTS = "Imports"
# log.debug("Names the section of values taken from the config")
GLOBALS = "Global constants"
# log.debug("Names the section of values only this file uses")
LOCALS = "Local constants"
# log.debug("Lists the fixed sections, in the order they come")
FIXED = (IMPORTS, GLOBALS, LOCALS)
# log.debug("Sets the rank of the logic section, after every fixed one")
LOGIC_RANK = len(FIXED)
# log.debug("Lists the import groups' labels, in the order they come")
GROUPS = ("Standard library", "Third-party", "Local")
# log.debug("Lists extensions whose files carry a header but no sections")
NO_SECTIONS = (".yml", ".yaml", ".toml")
# log.debug("Names the logic section where a file needs one")
LOGIC = "logic"
# log.debug("Sets the message for a file with code but no logic banner")
LOGIC_MESSAGE = "needs a banner naming the file's job above its logic"
# log.debug("Sets the message for a banner whose name is off centre")
CENTRE_MESSAGE = "centre the section's name; run kds-standards stamp"
# log.debug("Names the rule every section finding belongs to")
RULE = "sections"


########################################################################
#                           Section banners                            #
########################################################################
# log.debug("Defines one banner found in a file")
@dataclass(frozen=True)
class Banner:
    """A section banner: its label and where its box sits.

    Attributes:
        label: The section's name, as centred in the box.
        first: Index of the banner's first line.
        last: Index of the banner's last line.
        centred: True when the label is centred exactly.
        label_line: Index of the line that holds the label.
    """

    # log.debug("Holds the section's name")
    label: str
    # log.debug("Holds the index of the banner's first line")
    first: int
    # log.debug("Holds the index of the banner's last line")
    last: int
    # log.debug("Holds whether the label is centred exactly")
    centred: bool
    # log.debug("Holds the index of the line that holds the label")
    label_line: int = 0

    # log.debug("Defines the banner's place in the section order")
    @property
    def rank(self) -> int:
        """Returns where the section comes: 0 to 2 fixed, 3 the logic.

        Returns:
            The section's rank.
        """
        # log.debug("Returns a fixed section's place, or the logic's")
        return FIXED.index(self.label) if self.label in FIXED else LOGIC_RANK


# log.debug("Defines whether a file is cut into sections at all")
def has_sections(path: str | None = None) -> bool:
    """Returns whether a file with a header is also cut into sections.

    Args:
        path: The file's path from the repository root. Required.

    Returns:
        False for YAML and TOML, whose own keys are their sections.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Returns whether the extension is one that has sections")
    return not path.endswith(NO_SECTIONS)


# log.debug("Defines how banners are found after a header")
def find_banners(
    lines: list[str] | None = None, start: int = 0, style: str = hdr.PYTHON
) -> list[Banner]:
    """Returns every banner in a file, from a line onwards.

    Args:
        lines: The file's lines. Required.
        start: The index to look from, after the header.
        style: The file's header style.

    Returns:
        The banners, in file order.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Draws an empty banner to learn the style's shape")
    shape = hdr.box("", style)
    # log.debug("Finds where the label line sits in that shape")
    at = next(i for i, line in enumerate(shape) if line.endswith(hdr.title_line("")))
    # log.debug("Starts with no banners")
    found: list[Banner] = []
    # log.debug("Tries every line as the start of a banner")
    for first in range(start, len(lines) - len(shape) + 1):
        # log.debug("Takes as many lines as a banner has")
        window = lines[first : first + len(shape)]
        # log.debug("Skips lines that do not match the banner's shape")
        if not _fits(window, shape, at):
            # log.debug("Moves to the next line")
            continue
        # log.debug("Reads the label line without its prefix")
        raw = window[at][len(shape[at]) - hdr.WIDTH :]
        # log.debug("Reads the label from between the walls")
        label = raw[1:-1].strip()
        # log.debug("Records the banner")
        found.append(
            Banner(
                label=label,
                first=first,
                last=first + len(shape) - 1,
                centred=raw == hdr.title_line(label),
                label_line=first + at,
            )
        )
    # log.debug("Returns the banners")
    return found


# log.debug("Defines the test for lines that make a banner")
def _fits(window: list[str] | None = None, shape: list[str] | None = None, at: int = 0) -> bool:
    """Returns whether lines have a banner's shape, whatever its label.

    Args:
        window: The lines to test. Required.
        shape: An empty banner in the file's style. Required.
        at: The index of the label line in the shape.

    Returns:
        True when every line but the label matches, and the label line
        is a walled line of the box's width.
    """
    # log.debug("Takes the lines, which the caller must give")
    window = required(window=window)
    # log.debug("Takes the shape, which the caller must give")
    shape = required(shape=shape)
    # log.debug("Checks every line but the label matches the shape")
    if any(a != b for i, (a, b) in enumerate(zip(window, shape, strict=True)) if i != at):
        # log.debug("Returns no match")
        return False
    # log.debug("Reads the label line without its prefix")
    raw = window[at][len(shape[at]) - hdr.WIDTH :]
    # log.debug("Reads what sits between the walls")
    label = raw[1:-1].strip()
    # log.debug("Returns whether it is walled, the box's width and holds a label")
    return (
        len(window[at]) == len(shape[at])
        and raw.startswith("#")
        and raw.endswith("#")
        and bool(label)
        and set(label) != {"#"}
    )


# log.debug("Defines the checks on the banners' labels and order")
def check_banners(path: str = "", banners: list[Banner] | None = None) -> list[Finding]:
    """Checks banners are centred, known, in order and not repeated.

    Args:
        path: The file's path from the repository root.
        banners: The file's banners, in file order. Required.

    Returns:
        A finding for each banner out of place.
    """
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Remembers the rank of the section before")
    previous = -1
    # log.debug("Walks the banners in file order")
    for banner in banners:
        # log.debug("Flags a label that is not centred exactly")
        if not banner.centred:
            # log.debug("Records the off-centre label")
            found.append(Finding(path, banner.label_line + 1, RULE, CENTRE_MESSAGE))
        # log.debug("Flags a section out of order or repeated")
        if banner.rank < previous or (banner.rank == previous and banner.rank < LOGIC_RANK):
            # log.debug("Records the misplaced section")
            found.append(Finding(path, banner.first + 1, RULE, _order_message(banner.label)))
        elif banner.rank == previous:
            # log.debug("Records a second logic section")
            found.append(Finding(path, banner.first + 1, RULE, "one logic section per file"))
        # log.debug("Remembers this banner's rank")
        previous = banner.rank
    # log.debug("Returns every finding")
    return found


# log.debug("Defines the message for a section out of order")
def _order_message(label: str = "") -> str:
    """Returns the message for a section that is out of place.

    Args:
        label: The misplaced section's name.

    Returns:
        A message naming the order sections come in.
    """
    # log.debug("Returns the order the sections must follow")
    return f"{label!r} is out of order: Imports, Global constants, Local constants, the logic"


# log.debug("Defines which section a line falls in")
def section_of(banners: list[Banner] | None = None, index: int = 0) -> Banner | None:
    """Returns the banner whose section holds a line, None before any.

    Args:
        banners: The file's banners, in file order. Required.
        index: The line's index in the file.

    Returns:
        The last banner that starts at or above the line, or None.
    """
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Returns the last banner above the line, if any")
    return next((b for b in reversed(banners) if b.first <= index), None)


# log.debug("Defines the check that a section's banner exists")
def check_present(
    path: str = "", banners: list[Banner] | None = None, needs: tuple[str, ...] = ()
) -> list[Finding]:
    """Flags each section a file needs but has no banner for.

    Args:
        path: The file's path from the repository root.
        banners: The file's banners, in file order. Required.
        needs: The sections the file's content calls for; the logic is
            named by LOGIC, as its label is the file's own.

    Returns:
        A finding for each missing banner.
    """
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Collects the ranks the file has banners for")
    ranks = {b.rank for b in banners}
    # log.debug("Returns a finding for each needed section with no banner")
    return [
        Finding(path, 1, RULE, f"needs a {name!r} banner" if name in FIXED else LOGIC_MESSAGE)
        for name in needs
        if (FIXED.index(name) if name in FIXED else LOGIC_RANK) not in ranks
    ]
