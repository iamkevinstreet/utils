########################################################################
#                                                                      #
#                  standards/kds/standards/header.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-11-03

Draws the header every source file starts with: a box that holds only
the file's path, then a doc block with the author, the created and last
modified dates, a blank line and the description. In Python the doc
block is the module docstring; every other language writes it as its
own doc comment, after the box. Every section banner is the same box
with the section's name in it. Reading a header back is parsing's job.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
import textwrap
from pathlib import PurePosixPath

# Local
from kds.args import required
from kds.standards import config

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the fence that opens Astro frontmatter, from the config")
FENCE = config.FENCE

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the box's full width, inside PEP 8's comment width")
WIDTH = 72
# log.debug("Sets the width between the box's two side walls")
INNER = WIDTH - 2
# log.debug("Sets the full-width rule that opens and closes every box")
BORDER = "#" * WIDTH
# log.debug("Sets the walled blank line above and below every box's title")
BUFFER = f"#{'':{INNER}}#"
# log.debug("Sets the width of the label column in the doc block")
LABEL_WIDTH = 19
# log.debug("Sets the author every header names")
AUTHOR = "Kevin Street"
# log.debug("Lists the doc block's labels, in order")
LABELS = ("Author", "Created on", "Last modified on")
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
# log.debug("Lists file names with no extension that use # comments: build files and dotfiles")
HASH_NAMES = (
    "Dockerfile",
    "Makefile",
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    ".gitleaksignore",
    ".prettierignore",
    ".dockerignore",
)
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
# log.debug("Sets how many lines the box takes: border, buffer, title, buffer, border")
BOX_LINES = 5
# log.debug("Sets where the title sits in the box, counted from its border")
TITLE_AT = 2


########################################################################
#                                                                      #
#                            Header drawing                            #
#                                                                      #
########################################################################
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

    The file header and every section banner use the same box: a
    border, a blank walled line, the title, another blank walled line
    and a border.

    Args:
        title: The text to centre in the box.
        style: The file's header style.

    Returns:
        The box's lines, with the style's prefix or wrapper.
    """
    # log.debug("Draws the border, a buffer, the title line, a buffer and the border")
    lines = [BORDER, BUFFER, title_line(title), BUFFER, BORDER]
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


# log.debug("Defines where a box's title line sits in a style")
def title_at(style: str = PYTHON) -> int:
    """Returns the index of the title line in a box of a style.

    Args:
        style: The file's header style.

    Returns:
        The title line's index in the lines box() returns: one more
        for a style that wraps the box in a comment.
    """
    # log.debug("Counts the wrapper's opening line when the style has one")
    return TITLE_AT + (1 if style in BOX_WRAPS else 0)


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
