########################################################################
#                                                                      #
#                  standards/kds/standards/parsing.py                  #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-03
Last modified on:  2026-11-03

Reads and checks the header every source file starts with: finds the
box and the doc block that header draws, reads the path, the author,
the dates and the description out of them, and checks each value
against the file's path and its git history.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

# Local
from kds.args import required
from kds.standards import config
from kds.standards import header as hdr
from kds.standards.findings import Finding

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the fence that opens and closes Astro frontmatter, from the config")
FENCE = config.FENCE

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Matches an ISO date, the only date form allowed")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# log.debug("Matches one labelled line and captures the label and value")
FIELD_RE = re.compile(r"^(Author|Created on|Last modified on):\s+(\S.*?)\s*$")
# log.debug("Names the rule every header finding belongs to")
RULE = "header"


########################################################################
#                                                                      #
#                            Header reading                            #
#                                                                      #
########################################################################
# log.debug("Defines the parsed fields of one file header")
@dataclass(frozen=True)
class Header:
    """The fields of a file header, and the lines it occupies.

    Attributes:
        title: The box's centred title, the file's path.
        author: The author's name.
        created: The Created on date.
        modified: The Last modified on date.
        description: The description, rejoined into one line.
        title_line: Index of the title line in the file.
        created_line: Index of the Created on line.
        modified_line: Index of the Last modified on line.
        last: Index of the header's last line.
        centred: True when the title is centred exactly.
    """

    # log.debug("Holds the centred title")
    title: str
    # log.debug("Holds the author's name")
    author: str
    # log.debug("Holds the Created on date")
    created: str
    # log.debug("Holds the Last modified on date")
    modified: str
    # log.debug("Holds the description as one line")
    description: str
    # log.debug("Holds the index of the title line")
    title_line: int
    # log.debug("Holds the index of the Created on line")
    created_line: int
    # log.debug("Holds the index of the Last modified on line")
    modified_line: int
    # log.debug("Holds the index of the header's last line")
    last: int
    # log.debug("Holds whether the title is centred exactly")
    centred: bool = True


# log.debug("Defines how a header is found and read in a file")
def parse(text: str = "", style: str | None = None) -> tuple[Header | None, str]:
    """Finds the header at the top of a file and reads its fields.

    Args:
        text: The file's full text.
        style: The file's header style, from style_for. Required.

    Returns:
        The header and an empty string, or None and what is wrong.
    """
    # log.debug("Takes the style, which the caller must give")
    style = required(style=style)
    # log.debug("Splits the file into lines")
    lines = text.splitlines()
    # log.debug("Skips a script's #! line when there is one")
    start = 1 if lines and lines[0].startswith("#!") else 0
    # log.debug("Skips Astro's opening fence")
    if style == hdr.ASTRO:
        # log.debug("Reports a component that does not open with its fence")
        if len(lines) <= start or lines[start].strip() != FENCE:
            # log.debug("Returns the problem")
            return None, "the component must open with --- and the header"
        # log.debug("Moves past the fence")
        start += 1
    # log.debug("Reads the box, then the doc block after it")
    return _read_box(lines, start, style)


# log.debug("Defines how the box is checked and its title read")
def _read_box(
    lines: list[str] | None = None, start: int = 0, style: str = hdr.PYTHON
) -> tuple[Header | None, str]:
    """Reads the box at a line, then hands on to the doc block reader.

    Args:
        lines: The file's lines. Required.
        start: The index the box should start at.
        style: The file's header style.

    Returns:
        The header and an empty string, or None and what is wrong.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Draws the box this style expects, with a placeholder title")
    expected = hdr.box("", style)
    # log.debug("Takes as many lines as the box has")
    found = lines[start : start + len(expected)]
    # log.debug("Finds where the title sits inside the box")
    at = hdr.title_at(style)
    # log.debug("Checks every line but the title matches the drawn box")
    if len(found) < len(expected) or any(
        a != b for i, (a, b) in enumerate(zip(found, expected, strict=True)) if i != at
    ):
        # log.debug("Reports a missing or broken box")
        return None, "the file must start with the 72-character box holding its path"
    # log.debug("Reads the title line without its prefix")
    raw = (
        found[at].removeprefix(hdr.SLASH_PREFIX) if style in (hdr.SLASH, hdr.ASTRO) else found[at]
    )
    # log.debug("Checks the title line is exactly the box's width")
    if len(raw) != hdr.WIDTH or not (raw.startswith("#") and raw.endswith("#")):
        # log.debug("Reports a title line of the wrong shape")
        return None, f"header line {start + at + 1} must be {hdr.WIDTH} characters, walls included"
    # log.debug("Reads the doc block after the box")
    return _read_doc(lines, start + len(expected), style, (raw[1:-1].strip(), start + at, raw))


# log.debug("Defines how the doc block is checked and read")
def _read_doc(
    lines: list[str] | None = None,
    start: int = 0,
    style: str = hdr.PYTHON,
    titled: tuple[str, int, str] = ("", 0, ""),
) -> tuple[Header | None, str]:
    """Reads the doc block that starts at a line.

    Args:
        lines: The file's lines. Required.
        start: The index the doc block should start at.
        style: The file's header style.
        titled: The box's title, the index of its line and the line.

    Returns:
        The header and an empty string, or None and what is wrong.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Reads how the style opens, prefixes and closes the block")
    opener, prefix, closer = hdr.DOC_FORMS[style]
    # log.debug("Checks the opener when the style has one")
    if opener and (len(lines) <= start or lines[start] != opener):
        # log.debug("Reports a missing doc block")
        return None, f"line {start + 1} must open the doc block with {opener}"
    # log.debug("Collects the block's lines without their prefix")
    body, end = _doc_lines(lines, start + (1 if opener else 0), prefix, closer)
    # log.debug("Reports a block that never closes")
    if end < 0:
        # log.debug("Returns the problem")
        return None, "the doc block has no end"
    # log.debug("Reads the fields and the description from the lines")
    return _fields(body, start + (1 if opener else 0), titled, end)


# log.debug("Defines how the doc block's own lines are collected")
def _doc_lines(
    lines: list[str] | None = None, first: int = 0, prefix: str = "", closer: str = ""
) -> tuple[list[str], int]:
    """Returns the doc block's lines, unprefixed, and its last index.

    Args:
        lines: The file's lines. Required.
        first: The index of the block's first field line.
        prefix: What starts each of the block's lines.
        closer: The line that ends the block; empty for # blocks.

    Returns:
        The lines without their prefix, and the index of the
        block's last line, or -1 when the block never ends.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Starts with no lines")
    body: list[str] = []
    # log.debug("Walks the lines after the opener")
    for index in range(first, len(lines)):
        # log.debug("Reads the line")
        line = lines[index]
        # log.debug("Ends at the closer in styles that have one")
        if closer and line == closer:
            # log.debug("Returns the lines and the closer's index")
            return body, index
        # log.debug("Ends a # block at the first line that is not a comment")
        if not closer and not (line == prefix.rstrip() or line.startswith(prefix)):
            # log.debug("Returns the lines and the last comment line's index")
            return body, index - 1
        # log.debug("Ends a # block at a box border, which opens a banner")
        if not closer and line == hdr.BORDER:
            # log.debug("Returns the lines before the border")
            return body, index - 1
        # log.debug("Keeps the line without its prefix")
        body.append(line[len(prefix) :] if line.startswith(prefix) else "")
    # log.debug("Returns the lines of a # block that runs to the end of the file")
    return (body, len(lines) - 1) if not closer else (body, -1)


# log.debug("Defines how the fields and description are read from the block")
def _fields(
    body: list[str] | None = None,
    first: int = 0,
    titled: tuple[str, int, str] = ("", 0, ""),
    last: int = 0,
) -> tuple[Header | None, str]:
    """Reads the three labelled lines, a blank line and the description.

    Args:
        body: The doc block's lines, without their prefix. Required.
        first: The index of the block's first field line in the file.
        titled: The box's title, the index of its line and the line.
        last: The index of the header's last line.

    Returns:
        The header and an empty string, or None and what is wrong.
    """
    # log.debug("Takes the lines, which the caller must give")
    body = required(body=body)
    # log.debug("Matches the first three lines against the labelled form")
    matches = [FIELD_RE.match(line) for line in body[: len(hdr.LABELS)]]
    # log.debug("Reads the labels the lines actually carry")
    labels = tuple(m.group(1) if m else "" for m in matches)
    # log.debug("Reports fields that are missing or out of order")
    if labels != hdr.LABELS:
        # log.debug("Returns the problem with the expected labels")
        return None, "the doc block must start with Author, Created on and Last modified on"
    # log.debug("Reports a description not set apart by a blank line")
    if len(body) <= len(hdr.LABELS) or body[len(hdr.LABELS)].strip():
        # log.debug("Returns the problem")
        return None, "a blank line must come between the dates and the description"
    # log.debug("Reads each field's value")
    author, created, modified = (m.group(2) for m in matches if m)
    # log.debug("Returns the header")
    return Header(
        title=titled[0],
        author=author,
        created=created,
        modified=modified,
        description=" ".join(line.strip() for line in body[len(hdr.LABELS) + 1 :]).strip(),
        title_line=titled[1],
        created_line=first + 1,
        modified_line=first + 2,
        last=last,
        centred=titled[2] == hdr.title_line(titled[0]),
    ), ""


# log.debug("Defines the checks on a header's values")
def check_fields(
    header: Header | None = None, path: str = "", created: str = "", modified: str = ""
) -> list[Finding]:
    """Checks a header's values against the file and its git history.

    Args:
        header: The parsed header. Required.
        path: The file's path from the repository root.
        created: The Created on date git implies.
        modified: The Last modified on date git implies.

    Returns:
        A finding for each value that is wrong.
    """
    # log.debug("Takes the header, which the caller must give")
    header = required(header=header)
    # log.debug("Lists each check: whether it fails, its line and the message")
    checks = (
        (header.title != path, header.title_line, f"the box must hold the file's path, {path}"),
        (not header.centred, header.title_line, "centre the path; run kds-standards stamp"),
        (header.author != hdr.AUTHOR, header.created_line - 1, f"Author must be {hdr.AUTHOR}"),
        (
            not DATE_RE.match(header.created) or header.created != created,
            header.created_line,
            f"Created on must be {created}, when git first saw the file",
        ),
        (
            not DATE_RE.match(header.modified) or header.modified != modified,
            header.modified_line,
            f"Last modified on must be {modified}; run kds-standards stamp",
        ),
        (not header.description, header.last, "the doc block must describe the file"),
    )
    # log.debug("Returns a finding for each check that fails, on its 1-based line")
    return [Finding(path, line + 1, RULE, message) for failed, line, message in checks if failed]
