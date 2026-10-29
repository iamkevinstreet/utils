########################################################################
#                  standards/kds/standards/header.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Writes, reads and checks the header box every    #
#                     source file starts with, in each language.       #
########################################################################
"""The header box: render it, find it in a file, check its fields."""

from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass
from pathlib import PurePosixPath

from kds.standards.findings import Finding

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the box's full width, inside PEP 8's comment width")
WIDTH = 72
# log.debug("Sets the width between the box's two side walls")
INNER = WIDTH - 2
# log.debug("Sets the width of the label column inside the box")
LABEL_WIDTH = 19
# log.debug("Sets where values start: two spaces plus the labels")
VALUE_COL = 2 + LABEL_WIDTH
# log.debug("Sets the purpose's wrap width, one space before the wall")
PURPOSE_WIDTH = INNER - VALUE_COL - 1
# log.debug("Sets the most characters a purpose may have")
PURPOSE_MAX = 140
# log.debug("Sets the author every header names")
AUTHOR = "Kevin Street"
# log.debug("Sets the full-width rule that opens and closes the box")
BORDER = "#" * WIDTH
# log.debug("Sets the labels, in the order the box lists them")
LABELS = ("Author:", "Created on:", "Last modified on:", "Purpose:")
# log.debug("Matches an ISO date, the only date form allowed")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# log.debug("Matches a labelled line and captures label and value")
FIELD_RE = re.compile(r"^#  (Author|Created on|Last modified on|Purpose):\s+(.*?)\s*#$")
# log.debug("Matches a purpose line that continues the one above")
MORE_RE = re.compile(rf"^# {{{VALUE_COL}}}(\S.*?)\s*#$")
# log.debug("Splits the labels: three one-line fields, then purpose")
SINGLE_LABELS, PURPOSE_LABEL = LABELS[:-1], LABELS[-1]
# log.debug("Names the purpose field as the box's lines spell it")
PURPOSE = PURPOSE_LABEL[:-1]
# log.debug("Names the style for // comment files")
SLASH = "slash"
# log.debug("Names the style for Astro components")
ASTRO = "astro"
# log.debug("Sets the prefix script styles put before each line")
PREFIX = "// "
# log.debug("Names the rule every header finding belongs to")
RULE = "header"
# log.debug("Maps each comment style to the extensions that use it")
STYLES = {
    "hash": (".py", ".sh", ".bash", ".yml", ".yaml", ".toml"),
    SLASH: (".ts", ".tsx", ".js", ".mjs", ".cjs"),
    "block": (".css", ".scss"),
    ASTRO: (".astro",),
    "html": (".html", ".htm"),
}
# log.debug("Lists file names with no extension that use # comments")
HASH_NAMES = ("Dockerfile", "Makefile")
# log.debug("Sets how many lines open the box: border, title, border")
OPENING = 3
# log.debug("Sets the fence that opens Astro frontmatter")
FENCE = "---"
# log.debug("Sets the opening and closing lines of wrapped styles")
WRAPS = {"block": ("/*", "*/"), "html": ("<!--", "-->"), ASTRO: (FENCE, None)}


# log.debug("Defines the parsed fields of one header box")
@dataclass(frozen=True)
class Header:
    """The fields of a header box, and the lines it occupies.

    Attributes:
        title: The centred title (the file's path).
        author: The author's name.
        created: The Created on date.
        modified: The Last modified on date.
        purpose: The purpose, rejoined into one line.
        first: Index of the box's first line in the file.
        last: Index of the box's last line in the file.
    """

    # log.debug("Holds the centred title")
    title: str
    # log.debug("Holds the author's name")
    author: str
    # log.debug("Holds the Created on date")
    created: str
    # log.debug("Holds the Last modified on date")
    modified: str
    # log.debug("Holds the purpose as one line")
    purpose: str
    # log.debug("Holds the index of the box's first line")
    first: int
    # log.debug("Holds the index of the box's last line")
    last: int


# log.debug("Defines how a file's comment style is chosen")
def style_for(path: str) -> str | None:
    """Return the comment style of a file's header, or None."""
    # log.debug("Reads the file's name and extension")
    name = PurePosixPath(path)
    # log.debug("Treats Dockerfile and Makefile as # files")
    if name.name in HASH_NAMES:
        # log.debug("Returns the hash style for a named build file")
        return "hash"
    # log.debug("Looks for the extension among each style's list")
    for style, extensions in STYLES.items():
        # log.debug("Returns the style whose list holds the extension")
        if name.suffix in extensions:
            # log.debug("Returns the matching style")
            return style
    # log.debug("Returns None: this kind of file carries no box")
    return None


# log.debug("Defines how the box's lines are drawn")
def render(title: str, created: str, modified: str, purpose: str) -> list[str]:
    """Return the box's lines, without any comment prefix.

    Args:
        title: The file's path from the repository root.
        created: The Created on date (YYYY-MM-DD).
        modified: The Last modified on date (YYYY-MM-DD).
        purpose: What the file is for, at most 140 characters.

    Returns:
        The lines of the box, each exactly 72 characters.
    """
    # log.debug("Starts with the border, the title and the border")
    lines = [BORDER, f"#{title:^{INNER}}#", BORDER]
    # log.debug("Pairs each single-line label with its value")
    for label, value in zip(SINGLE_LABELS, (AUTHOR, created, modified), strict=True):
        # log.debug("Adds a padded line for that label and value")
        lines.append(_field_line(label, value))
    # log.debug("Wraps the purpose to fit beside its label")
    wrapped = textwrap.wrap(purpose, PURPOSE_WIDTH) or [""]
    # log.debug("Adds the purpose's first line beside its label")
    lines.append(_field_line(PURPOSE_LABEL, wrapped[0]))
    # log.debug("Adds each further purpose line under the first")
    for more in wrapped[1:]:
        # log.debug("Indents the line to the value column")
        lines.append(f"#{' ' * VALUE_COL}{more:<{INNER - VALUE_COL}}#")
    # log.debug("Closes the box with the border")
    lines.append(BORDER)
    # log.debug("Returns the finished box")
    return lines


# log.debug("Defines how one labelled line is padded")
def _field_line(label: str, value: str) -> str:
    """Return one labelled line, padded to the box's width."""
    # log.debug("Builds the inner text: indent, label, value")
    inner = f"  {label:<{LABEL_WIDTH}}{value}"
    # log.debug("Pads the inner text and adds the side walls")
    return f"#{inner:<{INNER}}#"


# log.debug("Defines how a box is given its comment prefix")
def wrap(lines: list[str], style: str) -> list[str]:
    """Return the box's lines as they appear in a file of `style`."""
    # log.debug("Prefixes each line with // for script files")
    body = [f"{PREFIX}{line}" for line in lines] if style in (SLASH, ASTRO) else list(lines)
    # log.debug("Finds any opening and closing lines for the style")
    opener, closer = WRAPS.get(style, (None, None))
    # log.debug("Returns the lines with the style's wrapper, if any")
    return ([opener] if opener else []) + body + ([closer] if closer else [])


# log.debug("Defines how the box is found and read in a file")
def parse(text: str, style: str) -> tuple[Header | None, str]:
    """Find the header box at the top of a file and read its fields.

    Args:
        text: The file's full text.
        style: The file's comment style, from `style_for`.

    Returns:
        The header and an empty string, or None and what is wrong.
    """
    # log.debug("Splits the file into lines")
    lines = text.splitlines()
    # log.debug("Skips a script's #! line when there is one")
    start = 1 if lines and lines[0].startswith("#!") else 0
    # log.debug("Skips the wrapper's opening line for wrapped styles")
    if style in WRAPS:
        # log.debug("Checks the first line is the style's opener")
        if len(lines) <= start or lines[start].strip() != WRAPS[style][0]:
            # log.debug("Reports a missing opener as no header")
            return None, f"the file must open with {WRAPS[style][0]} and the header box"
        # log.debug("Moves past the opener")
        start += 1
    # log.debug("Strips each line's comment prefix")
    plain = [_unprefix(line, style) for line in lines[start:]]
    # log.debug("Reads the box from the stripped lines")
    return _read_box(plain, start)


# log.debug("Defines how a line's comment prefix is removed")
def _unprefix(line: str, style: str) -> str:
    """Return the line without its `// ` prefix in script styles."""
    # log.debug("Removes // and one space where the style uses them")
    if style in (SLASH, ASTRO) and line.startswith(PREFIX):
        # log.debug("Returns the line after the prefix")
        return line[len(PREFIX) :]
    # log.debug("Returns the line unchanged otherwise")
    return line


# log.debug("Defines how the box's lines are checked and read")
def _read_box(plain: list[str], offset: int) -> tuple[Header | None, str]:
    """Read the box from lines that start with it."""
    # log.debug("Checks the box opens with a border, title, border")
    if len(plain) < OPENING or plain[0] != BORDER or plain[2] != BORDER:
        # log.debug("Reports a missing or broken opening")
        return None, "the file must start with the 72-character header box"
    # log.debug("Reads the title from between the side walls")
    title = plain[1][1:-1].strip() if len(plain[1]) == WIDTH else ""
    # log.debug("Collects each label's values from the field lines")
    fields: dict[str, list[str]] = {}
    # log.debug("Remembers the last label seen, for purpose lines")
    last_label = ""
    # log.debug("Walks the lines after the title until the border")
    for index, line in enumerate(plain[OPENING:], start=OPENING):
        # log.debug("Stops at the closing border")
        if line == BORDER:
            # log.debug("Builds the header from what was collected")
            return _finish(title, fields, offset, offset + index)
        # log.debug("Checks every box line is exactly 72 characters")
        if len(line) != WIDTH:
            # log.debug("Reports a line of the wrong width")
            return None, f"header line {offset + index + 1} must be {WIDTH} characters wide"
        # log.debug("Tries the line as a labelled field")
        match = FIELD_RE.match(line)
        # log.debug("Tries it as a continued purpose line otherwise")
        more = MORE_RE.match(line)
        # log.debug("Records a labelled value under its label")
        if match:
            # log.debug("Remembers this label for any continuation")
            last_label = match.group(1)
            # log.debug("Starts the label's list with its value")
            fields[last_label] = [match.group(2)]
        elif more and last_label == PURPOSE:
            # log.debug("Appends the continued text")
            fields[PURPOSE].append(more.group(1))
        else:
            # log.debug("Reports any other line as not fitting the format")
            return None, f"header line {offset + index + 1} is not a field line"
    # log.debug("Reports a box with no closing border")
    return None, "the header box has no closing border"


# log.debug("Defines how collected fields become a Header")
def _finish(
    title: str, fields: dict[str, list[str]], first: int, last: int
) -> tuple[Header | None, str]:
    """Return the header if every field is present."""
    # log.debug("Lists the labels the box is missing")
    missing = [label[:-1] for label in LABELS if label[:-1] not in fields]
    # log.debug("Reports missing labels by name")
    if missing:
        # log.debug("Returns the list of missing labels")
        return None, "the header box is missing " + ", ".join(missing)
    # log.debug("Builds the header from the fields")
    header = Header(
        title=title,
        author=fields["Author"][0],
        created=fields["Created on"][0],
        modified=fields["Last modified on"][0],
        purpose=" ".join(fields[PURPOSE]),
        first=first,
        last=last,
    )
    # log.debug("Returns the header with no error")
    return header, ""


# log.debug("Defines the checks on a header's values")
def check_fields(header: Header, path: str, created: str, modified: str) -> list[Finding]:
    """Check a header's values against the file and its git history.

    Args:
        header: The parsed header.
        path: The file's path from the repository root.
        created: The Created on date git implies.
        modified: The Last modified on date git implies.

    Returns:
        A finding for each value that is wrong.
    """
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Lists each check: whether it fails and the message")
    checks = (
        (header.title != path, f"title must be the file's path, {path}"),
        (header.author != AUTHOR, f"author must be {AUTHOR}"),
        (not DATE_RE.match(header.created), "Created on must be a date, YYYY-MM-DD"),
        (not DATE_RE.match(header.modified), "Last modified on must be a date, YYYY-MM-DD"),
        (header.created != created, f"Created on must be {created}, when git first saw the file"),
        (
            header.modified != modified,
            f"Last modified on must be {modified}; run kds-standards stamp",
        ),
        (not header.purpose, "Purpose must say what the file is for"),
        (len(header.purpose) > PURPOSE_MAX, f"Purpose must be at most {PURPOSE_MAX} characters"),
    )
    # log.debug("Keeps a finding for each check that fails")
    for failed, message in checks:
        # log.debug("Records the failed check against line 1")
        if failed:
            # log.debug("Adds the finding")
            found.append(Finding(path, 1, RULE, message))
    # log.debug("Returns every finding")
    return found
