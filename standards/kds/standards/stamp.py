########################################################################
#                                                                      #
#                   standards/kds/standards/stamp.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-11-03

Writes headers: adds a whole header to a file that has none, and
refreshes an existing header's title and dates from git, so a moved
file's box names its new path and every date matches the history. A
refresh also recentres every section banner's name, and brings a box
drawn in the old three-line form (no blank walled line above and below
its title) to the current form.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import ast
import logging
from pathlib import Path

# Local
from kds.args import required
from kds.standards import config, labels, parsing
from kds.standards import header as hdr
from kds.standards import sections as sec
from kds.standards.gitdates import History

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the encoding every file is read and written in, from the config")
ENCODING = config.ENCODING

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the extension of an Astro component")
ASTRO_SUFFIX = ".astro"
# log.debug("Sets how many fences a component's frontmatter has")
FENCES = 2
# log.debug("Sets how many lines the old form of the box took: border, title, border")
OLD_BOX_LINES = 3


########################################################################
#                                                                      #
#                            Header writing                            #
#                                                                      #
########################################################################
# log.debug("Defines how a header is added to a file")
def insert(
    root: Path | None = None,
    path: str | None = None,
    description: str = "",
    history: History | None = None,
) -> str:
    """Adds a header to a file that has none.

    Args:
        root: The repository root. Required.
        path: The file's path from the root. Required.
        description: What the file is for, as plain sentences.
        history: The repository's dates, from read_history. Required.

    Returns:
        An empty string on success, or why the header was not added.
    """
    # log.debug("Takes the root, which the caller must give")
    root = required(root=root)
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the history, which the caller must give")
    history = required(history=history)
    # log.debug("Finds the file's header style")
    style = hdr.style_for(path)
    # log.debug("Refuses a kind of file that carries no header")
    if style is None:
        # log.debug("Returns why")
        return f"{path}: this kind of file carries no header"
    # log.debug("Refuses an empty description")
    if not description.strip():
        # log.debug("Returns why")
        return f"{path}: give the file a description"
    # log.debug("Reads the file")
    text = (root / path).read_text(encoding=ENCODING)
    # log.debug("Refuses a file that already has a header")
    if parsing.parse(text, style)[0] is not None:
        # log.debug("Returns why")
        return f"{path}: already has a header"
    # log.debug("Refuses a Python file whose docstring would become a second one")
    if style == hdr.PYTHON and _has_docstring(text):
        # log.debug("Returns why")
        return f"{path}: fold its docstring into the description, then remove it"
    # log.debug("Draws the header with the file's dates")
    lines = hdr.render(
        path, history.created_on(path), history.modified_on(path), description, style
    )
    # log.debug("Writes the file with the header at the top")
    (root / path).write_text(_join(lines, text, style), encoding=ENCODING)
    # log.debug("Returns success")
    return ""


# log.debug("Defines the test for a Python file that already has a docstring")
def _has_docstring(text: str = "") -> bool:
    """Returns whether Python source opens with a module docstring.

    Args:
        text: The file's Python source.

    Returns:
        True when the module has a docstring.
    """
    # log.debug("Returns whether the parsed module carries a docstring")
    return ast.get_docstring(ast.parse(text)) is not None


# log.debug("Defines how the header is placed above the file's text")
def _join(header: list[str] | None = None, text: str = "", style: str = hdr.PYTHON) -> str:
    """Returns the file's text with the header at the top.

    Args:
        header: The header's lines, from render. Required.
        text: The file's text without a header.
        style: The file's header style.

    Returns:
        The new text, ending with a newline.
    """
    # log.debug("Takes the header, which the caller must give")
    header = required(header=header)
    # log.debug("Splits the file into lines")
    lines = text.splitlines()
    # log.debug("Keeps a script's #! line above the header")
    keep = lines[:1] if lines and lines[0].startswith("#!") else []
    # log.debug("Takes the lines after the #! line")
    rest = lines[len(keep) :]
    # log.debug("Notes whether an Astro component already has frontmatter")
    fenced = bool(rest) and rest[0].strip() == hdr.FENCE
    # log.debug("Drops the old opening fence: the header brings its own")
    if style == hdr.ASTRO and fenced:
        # log.debug("Removes the fence")
        rest = rest[1:]
    elif style == hdr.ASTRO:
        # log.debug("Closes the new frontmatter for a component that had none")
        header = [*header, hdr.FENCE]
    # log.debug("Returns the joined text, blank line after the header")
    return "\n".join([*keep, *header, "", *rest]) + "\n"


# log.debug("Defines how a header's title and dates are refreshed")
def refresh(
    root: Path | None = None,
    path: str | None = None,
    history: History | None = None,
    local_names: frozenset[str] = frozenset(),
) -> bool:
    """Rewrites a file's header, banners and import labels in place.

    Args:
        root: The repository root. Required.
        path: The file's path from the root. Required.
        history: The repository's dates, from read_history. Required.
        local_names: The top-level names of the repository's own
            modules, for sorting Python imports into their groups.

    Returns:
        True when the file was changed.
    """
    # log.debug("Takes the root, which the caller must give")
    root = required(root=root)
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the history, which the caller must give")
    history = required(history=history)
    # log.debug("Finds the file's header style")
    style = hdr.style_for(path)
    # log.debug("Points at the file")
    target = root / path
    # log.debug("Leaves alone a file with no header style or no file")
    if style is None or not target.is_file():
        # log.debug("Returns unchanged")
        return False
    # log.debug("Reads the file")
    text = target.read_text(encoding=ENCODING)
    # log.debug("Brings any old three-line box to the current form")
    widened = _widened(text, style)
    # log.debug("Finds the header")
    found, _ = parsing.parse(widened, style)
    # log.debug("Leaves alone a file whose header cannot be read")
    if found is None:
        # log.debug("Returns unchanged")
        return False
    # log.debug("Splits the file into lines")
    lines = widened.splitlines()
    # log.debug("Redraws the title line, keeping the style's prefix")
    lines[found.title_line] = _prefixed(hdr.title_line(path), lines[found.title_line])
    # log.debug("Rewrites the Created on line with git's date")
    lines[found.created_line] = _dated(lines[found.created_line], history.created_on(path))
    # log.debug("Rewrites the Last modified on line with git's date")
    lines[found.modified_line] = _dated(lines[found.modified_line], history.modified_on(path))
    # log.debug("Recentres every section banner's name")
    for banner in sec.find_banners(lines, found.last + 1, style):
        # log.debug("Redraws the banner's name line, keeping the style's prefix")
        lines[banner.label_line] = _prefixed(
            hdr.title_line(banner.label), lines[banner.label_line]
        )
    # log.debug("Puts each import group's label back above its first import")
    lines = _relabelled(path, lines, local_names)
    # log.debug("Joins the lines, keeping the final newline")
    new_text = "\n".join(lines) + "\n"
    # log.debug("Leaves the file alone when nothing changed")
    if new_text == text:
        # log.debug("Returns unchanged")
        return False
    # log.debug("Writes the refreshed file")
    target.write_text(new_text, encoding=ENCODING)
    # log.debug("Returns changed")
    return True


# log.debug("Defines how old three-line boxes are brought to the current form")
def _widened(text: str = "", style: str = hdr.PYTHON) -> str:
    """Returns the text with every old three-line box given its buffers.

    The old form was a border, the title and a border. The current form
    puts a blank walled line between the title and each border.

    Args:
        text: The file's text.
        style: The file's header style.

    Returns:
        The text, each old box rewritten; unchanged when there is none.
    """
    # log.debug("Reads the prefix the style puts before each box line")
    prefix = hdr.SLASH_PREFIX if style in (hdr.SLASH, hdr.ASTRO) else ""
    # log.debug("Draws the border and the buffer as the style writes them")
    border, buffer = f"{prefix}{hdr.BORDER}", f"{prefix}{hdr.BUFFER}"
    # log.debug("Splits the file into lines")
    lines = text.splitlines()
    # log.debug("Starts with no lines rewritten")
    out: list[str] = []
    # log.debug("Starts at the first line")
    index = 0
    # log.debug("Walks the lines, looking for the start of an old box")
    while index < len(lines):
        # log.debug("Takes the three lines an old box would occupy")
        window = lines[index : index + OLD_BOX_LINES]
        # log.debug("Rewrites an old box as the current one")
        if len(window) == OLD_BOX_LINES and _is_old_box(window, border, buffer, prefix):
            # log.debug("Adds the border, a buffer, the title, a buffer and the border")
            out += [border, buffer, window[1], buffer, border]
            # log.debug("Skips past the old box")
            index += OLD_BOX_LINES
        else:
            # log.debug("Keeps the line as it is")
            out.append(lines[index])
            # log.debug("Moves to the next line")
            index += 1
    # log.debug("Returns the text, keeping the final newline")
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


# log.debug("Defines the test for the old form of the box")
def _is_old_box(
    window: list[str] | None = None, border: str = "", buffer: str = "", prefix: str = ""
) -> bool:
    """Returns whether three lines are a box in the old form.

    Args:
        window: Three lines of the file. Required.
        border: The border as the style writes it.
        buffer: The blank walled line as the style writes it.
        prefix: The prefix the style puts before each box line.

    Returns:
        True for a border, a walled title line that is not a buffer,
        and a border.
    """
    # log.debug("Takes the window, which the caller must give")
    window = required(window=window)
    # log.debug("Reads the middle line without its prefix")
    middle = window[1].removeprefix(prefix) if prefix else window[1]
    # log.debug("Returns whether the lines are border, walled title, border")
    return (
        window[0] == border
        and window[2] == border
        and window[1] != buffer
        and window[1].startswith(prefix)
        and len(middle) == hdr.WIDTH
        and middle.startswith("#")
        and middle.endswith("#")
        and set(middle) != {"#"}
    )


# log.debug("Defines how a new line keeps the old line's prefix")
def _prefixed(new: str = "", old: str = "") -> str:
    """Returns a box line with whatever came before the old one's wall.

    Args:
        new: The redrawn box line, starting with its # wall.
        old: The line it replaces, which may start with // .

    Returns:
        The new line behind the old line's prefix.
    """
    # log.debug("Returns the old prefix, up to its first #, then the new line")
    return old[: old.index("#")] + new if "#" in old else new


# log.debug("Defines how a date line takes a new date")
def _dated(line: str = "", date: str = "") -> str:
    """Returns a labelled date line with its date replaced.

    Args:
        line: The Created on or Last modified on line, prefix and all.
        date: The new date (YYYY-MM-DD).

    Returns:
        The line with the new date in the value column.
    """
    # log.debug("Finds where the label's colon ends")
    colon = line.index(":") + 1
    # log.debug("Keeps the prefix and label, pads to the value column, adds the date")
    return line[:colon] + " " * (hdr.LABEL_WIDTH - _label_length(line)) + date


# log.debug("Defines how long a line's label is, colon included")
def _label_length(line: str = "") -> int:
    """Returns the length of a date line's label, without its prefix.

    Args:
        line: The Created on or Last modified on line.

    Returns:
        The label's length, colon included.
    """
    # log.debug("Finds the label among the header's labels")
    label = next(name for name in hdr.LABELS if f"{name}:" in line)
    # log.debug("Returns its length with the colon")
    return len(label) + 1


# log.debug("Defines how a file's import labels are put back in place")
def _relabelled(
    path: str = "", lines: list[str] | None = None, local_names: frozenset[str] = frozenset()
) -> list[str]:
    """Returns a file's lines with its import labels in place.

    Args:
        path: The file's path from the repository root.
        lines: The file's lines. Required.
        local_names: The top-level names of the repository's modules.

    Returns:
        The lines; anything but Python or a script comes back as it was.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Relabels a Python module")
    if path.endswith(config.PYTHON_SUFFIX):
        # log.debug("Returns the relabelled module")
        return labels.relabel_python(lines, local_names)
    # log.debug("Leaves alone anything that is not a script")
    if not path.endswith(config.SCRIPTS):
        # log.debug("Returns the lines unchanged")
        return lines
    # log.debug("Finds the two frontmatter fences of an Astro component")
    fences = [i for i, line in enumerate(lines) if line.strip() == config.FENCE][:2]
    # log.debug("Relabels a plain script whole")
    if not path.endswith(ASTRO_SUFFIX) or len(fences) < FENCES:
        # log.debug("Returns the relabelled script")
        return labels.relabel_script(lines)
    # log.debug("Returns a component with only its frontmatter relabelled")
    inside = labels.relabel_script(lines[fences[0] + 1 : fences[1]])
    # log.debug("Joins the component back together")
    return [*lines[: fences[0] + 1], *inside, *lines[fences[1] :]]
