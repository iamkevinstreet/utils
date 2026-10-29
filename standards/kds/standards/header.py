########################################################################
#                  standards/kds/standards/header.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Writes, reads and checks the header every source file starts with: a
box that holds only the file's path, then a doc block with the author,
the created and last modified dates, a blank line and the description.
In Python the doc block is the module docstring; every other language
writes it as its own doc comment, after the box.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass
from pathlib import PurePosixPath

# Local
from kds.args import required
from kds.standards import config
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the fence that opens Astro frontmatter, from the config")
FENCE = config.FENCE

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the box's full width, inside PEP 8's comment width")
WIDTH = 72
# log.debug("Sets the width between the box's two side walls")
INNER = WIDTH - 2
# log.debug("Sets the full-width rule that opens and closes every box")
BORDER = "#" * WIDTH
# log.debug("Sets the width of the label column in the doc block")
LABEL_WIDTH = 19
# log.debug("Sets the author every header names")
AUTHOR = "Kevin Street"
# log.debug("Lists the doc block's labels, in order")
LABELS = ("Author", "Created on", "Last modified on")
# log.debug("Matches an ISO date, the only date form allowed")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# log.debug("Matches one labelled line and captures the label and value")
FIELD_RE = re.compile(r"^(Author|Created on|Last modified on):\s+(\S.*?)\s*$")
# log.debug("Names the style of Python files, whose doc block is a docstring")
PYTHON = "python"
# log.debug("Names the style of other files written with # comments")
HASH = "hash"
# log.debug("Names the style of TypeScript and JavaScript files")
SLASH = "slash"
# log.debug("Names the style of CSS files")
BLOCK = "block"
# log.debug("Names the style of Astro components")
ASTRO = "astro"
# log.debug("Names the style of HTML templates")
HTML = "html"
# log.debug("Maps each style to the extensions that use it")
STYLES = {
    PYTHON: (".py",),
    HASH: (".sh", ".bash", ".yml", ".yaml", ".toml"),
    SLASH: (".ts", ".tsx", ".js", ".mjs", ".cjs"),
    BLOCK: (".css", ".scss"),
    ASTRO: (".astro",),
    HTML: (".html", ".htm"),
}
# log.debug("Lists file names with no extension that use # comments")
HASH_NAMES = ("Dockerfile", "Makefile")
# log.debug("Sets the prefix // styles put before each box line")
SLASH_PREFIX = "// "
# log.debug("Sets the lines that wrap the box in the wrapped styles")
BOX_WRAPS = {BLOCK: ("/*", "*/"), HTML: ("<!--", "-->")}
# log.debug("Sets how each style opens, prefixes and closes its doc block")
DOC_FORMS = {
    PYTHON: ('"""', "", '"""'),
    HASH: ("", "# ", ""),
    SLASH: ("/**", " * ", " */"),
    ASTRO: ("/**", " * ", " */"),
    BLOCK: ("/*", " * ", " */"),
    HTML: ("<!--", "", "-->"),
}
# log.debug("Sets how many lines the box takes: border, title, border")
BOX_LINES = 3
# log.debug("Names the rule every header finding belongs to")
RULE = "header"


########################################################################
#                             File header                              #
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


# log.debug("Defines how a file's header style is chosen")
def style_for(path: str | None = None) -> str | None:
    """Returns the header style of a file, or None when it carries none.

    Args:
        path: The file's path from the repository root. Required.

    Returns:
        The style's name, or None for a kind of file with no header.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Reads the file's name and extension")
    name = PurePosixPath(path)
    # log.debug("Treats Dockerfile and Makefile as # files")
    if name.name in HASH_NAMES:
        # log.debug("Returns the hash style for a named build file")
        return HASH
    # log.debug("Looks for the extension among each style's list")
    for style, extensions in STYLES.items():
        # log.debug("Returns the style whose list holds the extension")
        if name.suffix in extensions:
            # log.debug("Returns the matching style")
            return style
    # log.debug("Returns None: this kind of file carries no header")
    return None


# log.debug("Defines how a box's title line is drawn")
def title_line(title: str = "") -> str:
    """Returns the box line that holds a centred title.

    Args:
        title: The text to centre: a file's path or a section's name.

    Returns:
        The line, exactly 72 characters wide.
    """
    # log.debug("Centres the title between the two side walls")
    return f"#{title:^{INNER}}#"


# log.debug("Defines how the box is drawn in a style")
def box(title: str = "", style: str = PYTHON) -> list[str]:
    """Returns a box's lines as a file of the style writes them.

    The file header and every section banner use the same box.

    Args:
        title: The text to centre in the box.
        style: The file's header style.

    Returns:
        The box's lines, with the style's prefix or wrapper.
    """
    # log.debug("Draws the border, the title line and the border")
    lines = [BORDER, title_line(title), BORDER]
    # log.debug("Prefixes each line with // for script styles")
    if style in (SLASH, ASTRO):
        # log.debug("Returns the prefixed lines")
        return [f"{SLASH_PREFIX}{line}" for line in lines]
    # log.debug("Wraps the lines in a comment for CSS and HTML")
    if style in BOX_WRAPS:
        # log.debug("Returns the lines inside the style's comment")
        return [BOX_WRAPS[style][0], *lines, BOX_WRAPS[style][1]]
    # log.debug("Returns the plain lines for # styles")
    return lines


# log.debug("Defines how the doc block is drawn in a style")
def doc_block(
    created: str = "", modified: str = "", description: str = "", style: str = PYTHON
) -> list[str]:
    """Returns the header's doc block as a file of the style writes it.

    Args:
        created: The Created on date (YYYY-MM-DD).
        modified: The Last modified on date (YYYY-MM-DD).
        description: What the file is for, as plain sentences.
        style: The file's header style.

    Returns:
        The doc block's lines, opener and closer included.
    """
    # log.debug("Reads how the style opens, prefixes and closes the block")
    opener, prefix, closer = DOC_FORMS[style]
    # log.debug("Pads each label to the label column")
    fields = [
        f"{label + ':':<{LABEL_WIDTH}}{value}"
        for label, value in zip(LABELS, (AUTHOR, created, modified), strict=True)
    ]
    # log.debug("Wraps the description so each line fits in 72 characters")
    text = textwrap.wrap(description, WIDTH - len(prefix)) or [""]
    # log.debug("Prefixes every line, keeping blank lines free of trailing space")
    body = [f"{prefix}{line}".rstrip() for line in [*fields, "", *text]]
    # log.debug("Returns the block with its opener and closer where the style has them")
    return ([opener] if opener else []) + body + ([closer] if closer else [])


# log.debug("Defines how a whole header is drawn")
def render(
    title: str = "",
    created: str = "",
    modified: str = "",
    description: str = "",
    style: str | None = None,
) -> list[str]:
    """Returns a file's whole header: the box, then the doc block.

    Args:
        title: The file's path from the repository root.
        created: The Created on date (YYYY-MM-DD).
        modified: The Last modified on date (YYYY-MM-DD).
        description: What the file is for, as plain sentences.
        style: The file's header style. Required.

    Returns:
        The header's lines, starting with Astro's fence for components.
    """
    # log.debug("Takes the style, which the caller must give")
    style = required(style=style)
    # log.debug("Opens the frontmatter first in an Astro component")
    fence = [FENCE] if style == ASTRO else []
    # log.debug("Returns the fence, the box and the doc block")
    return fence + box(title, style) + doc_block(created, modified, description, style)


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
    if style == ASTRO:
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
    lines: list[str] | None = None, start: int = 0, style: str = PYTHON
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
    expected = box("", style)
    # log.debug("Takes as many lines as the box has")
    found = lines[start : start + len(expected)]
    # log.debug("Finds where the title sits inside the box")
    at = expected.index(next(line for line in expected if line.endswith(title_line(""))))
    # log.debug("Checks every line but the title matches the drawn box")
    if len(found) < len(expected) or any(
        a != b for i, (a, b) in enumerate(zip(found, expected, strict=True)) if i != at
    ):
        # log.debug("Reports a missing or broken box")
        return None, "the file must start with the 72-character box holding its path"
    # log.debug("Reads the title line without its prefix")
    raw = found[at].removeprefix(SLASH_PREFIX) if style in (SLASH, ASTRO) else found[at]
    # log.debug("Checks the title line is exactly the box's width")
    if len(raw) != WIDTH or not (raw.startswith("#") and raw.endswith("#")):
        # log.debug("Reports a title line of the wrong shape")
        return None, f"header line {start + at + 1} must be {WIDTH} characters, walls included"
    # log.debug("Reads the doc block after the box")
    return _read_doc(lines, start + len(expected), style, (raw[1:-1].strip(), start + at, raw))


# log.debug("Defines how the doc block is checked and read")
def _read_doc(
    lines: list[str] | None = None,
    start: int = 0,
    style: str = PYTHON,
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
    opener, prefix, closer = DOC_FORMS[style]
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
        if not closer and line == BORDER:
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
    matches = [FIELD_RE.match(line) for line in body[: len(LABELS)]]
    # log.debug("Reads the labels the lines actually carry")
    labels = tuple(m.group(1) if m else "" for m in matches)
    # log.debug("Reports fields that are missing or out of order")
    if labels != LABELS:
        # log.debug("Returns the problem with the expected labels")
        return None, "the doc block must start with Author, Created on and Last modified on"
    # log.debug("Reports a description not set apart by a blank line")
    if len(body) <= len(LABELS) or body[len(LABELS)].strip():
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
        description=" ".join(line.strip() for line in body[len(LABELS) + 1 :]).strip(),
        title_line=titled[1],
        created_line=first + 1,
        modified_line=first + 2,
        last=last,
        centred=titled[2] == title_line(titled[0]),
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
        (header.author != AUTHOR, header.created_line - 1, f"Author must be {AUTHOR}"),
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
