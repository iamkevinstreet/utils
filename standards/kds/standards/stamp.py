########################################################################
#                   standards/kds/standards/stamp.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Writes the header box: adds one to a new file,   #
#                     and keeps titles and dates true on every commit. #
########################################################################
"""Header writing: insert a new box, refresh dates and titles."""

from __future__ import annotations

import logging
from pathlib import Path

from kds.standards import header as hdr
from kds.standards.gitdates import History

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the encoding every file is read and written in")
ENCODING = "utf-8"


# log.debug("Defines how a header is added to a file without one")
def insert(root: Path, path: str, purpose: str, history: History) -> str:
    """Add a header box to a file that has none.

    Args:
        root: The repository root.
        path: The file's path from the root.
        purpose: What the file is for, at most 140 characters.
        history: The repository's dates, from `read_history`.

    Returns:
        An empty string on success, or why the box was not added.
    """
    # log.debug("Finds the file's comment style")
    style = hdr.style_for(path)
    # log.debug("Refuses files that carry no header")
    if style is None:
        # log.debug("Returns why nothing was added")
        return f"{path}: this kind of file carries no header"
    # log.debug("Refuses a purpose over the limit")
    if len(purpose) > hdr.PURPOSE_MAX:
        # log.debug("Returns the limit")
        return f"{path}: purpose must be at most {hdr.PURPOSE_MAX} characters"
    # log.debug("Reads the file")
    target = root / path
    # log.debug("Holds the file's current text")
    text = target.read_text(encoding=ENCODING)
    # log.debug("Refuses a file that already has a header")
    if hdr.parse(text, style)[0] is not None:
        # log.debug("Returns that the file is already stamped")
        return f"{path}: already has a header"
    # log.debug("Draws the new box with the file's dates")
    box = hdr.render(path, history.created_on(path), history.modified_on(path), purpose)
    # log.debug("Writes the box above the file's text")
    target.write_text(_join(box, text, style), encoding=ENCODING)
    # log.debug("Returns success")
    return ""


# log.debug("Defines how the box and the existing text are joined")
def _join(box: list[str], text: str, style: str) -> str:
    """Return the file's text with the box placed at the top."""
    # log.debug("Splits the text so a #! line can stay first")
    lines = text.splitlines()
    # log.debug("Keeps a #! line above the box")
    keep = lines[:1] if lines and lines[0].startswith("#!") else []
    # log.debug("Takes the rest of the file below the box")
    rest = lines[len(keep) :]
    # log.debug("Draws the box with the style's comment prefix")
    boxed = hdr.wrap(box, style)
    # log.debug("Checks whether an Astro file already has frontmatter")
    fenced = bool(rest) and rest[0].strip() == hdr.FENCE
    # log.debug("Merges an Astro box into the existing frontmatter")
    if style == hdr.ASTRO and fenced:
        # log.debug("Drops the existing opening fence; the box brings one")
        rest = rest[1:]
    elif style == hdr.ASTRO:
        # log.debug("Closes a new frontmatter that holds only the box")
        boxed.append(hdr.FENCE)
    # log.debug("Returns the joined file with a final newline")
    return "\n".join([*keep, *boxed, *rest]) + "\n"


# log.debug("Defines how an existing header is refreshed")
def refresh(root: Path, path: str, history: History) -> bool:
    """Rewrite a file's header with its true title and dates.

    Args:
        root: The repository root.
        path: The file's path from the root.
        history: The repository's dates, from `read_history`.

    Returns:
        True when the file was changed.
    """
    # log.debug("Finds the file's comment style")
    style = hdr.style_for(path)
    # log.debug("Reads the file")
    target = root / path
    # log.debug("Returns no change for files without a style")
    if style is None or not target.is_file():
        # log.debug("Returns unchanged")
        return False
    # log.debug("Holds the file's current text")
    text = target.read_text(encoding=ENCODING)
    # log.debug("Reads the existing header")
    found, _ = hdr.parse(text, style)
    # log.debug("Returns no change when there is no header to refresh")
    if found is None:
        # log.debug("Returns unchanged")
        return False
    # log.debug("Draws the box again with the true title and dates")
    box = hdr.render(path, history.created_on(path), history.modified_on(path), found.purpose)
    # log.debug("Applies the comment prefix for the style")
    prefixed = hdr.wrap(box, style)
    # log.debug("Drops the wrapper's opener, which stays in place")
    body = prefixed[1:] if style in hdr.WRAPS else prefixed
    # log.debug("Drops a block or HTML closer, which also stays")
    body = body[:-1] if style in ("block", "html") else body
    # log.debug("Splits the file into lines")
    lines = text.splitlines()
    # log.debug("Replaces the old box lines with the new ones")
    updated = [*lines[: found.first], *body, *lines[found.last + 1 :]]
    # log.debug("Joins the lines with a final newline")
    new_text = "\n".join(updated) + "\n"
    # log.debug("Returns no change when nothing differs")
    if new_text == text:
        # log.debug("Returns unchanged")
        return False
    # log.debug("Writes the refreshed file")
    target.write_text(new_text, encoding=ENCODING)
    # log.debug("Returns changed")
    return True
