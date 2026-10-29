########################################################################
#                  standards/kds/standards/toggle.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Turns the logger lines on to trace a run, and    #
#                     off again before a commit.                       #
########################################################################
"""The trace switch: comment or uncomment every logger line."""

from __future__ import annotations

import logging
import re
from pathlib import Path

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the encoding every file is read and written in")
ENCODING = "utf-8"
# log.debug("Matches a commented Python logger line")
PY_OFF = re.compile(r'^(\s*)# (log\.debug\(")', re.MULTILINE)
# log.debug("Matches a live Python logger line")
PY_ON = re.compile(r'^(\s*)(log\.debug\(")', re.MULTILINE)
# log.debug("Matches a commented script logger line")
JS_OFF = re.compile(r"^(\s*)// (log\.debug\(')", re.MULTILINE)
# log.debug("Matches a live script logger line")
JS_ON = re.compile(r"^(\s*)(log\.debug\(')", re.MULTILINE)
# log.debug("Lists the script extensions the switch reaches")
SCRIPTS = (".ts", ".tsx", ".js", ".mjs", ".cjs", ".astro")
# log.debug("Sets the extension of Python files")
PY = ".py"
# log.debug("Lists folders the switch never touches")
SKIP = ("node_modules", ".venv", "dist", ".git")


# log.debug("Defines the switch over a file or folder")
def switch(target: Path, on: bool) -> int:
    """Turn every logger line under `target` on or off.

    Args:
        target: A file, or a folder to walk.
        on: True to uncomment the lines, False to comment them.

    Returns:
        How many files changed.
    """
    # log.debug("Lists the files to switch: one, or all under a folder")
    files = [target] if target.is_file() else sorted(target.rglob("*"))
    # log.debug("Switches each file and counts the ones that changed")
    return sum(_switch_file(path, on) for path in files if _eligible(path))


# log.debug("Defines which files the switch may change")
def _eligible(path: Path) -> bool:
    """Return True for Python and script files outside skipped dirs."""
    # log.debug("Refuses anything under a skipped folder")
    if any(part in SKIP for part in path.parts):
        # log.debug("Returns not eligible")
        return False
    # log.debug("Accepts Python and script files")
    return path.is_file() and (path.suffix == PY or path.suffix in SCRIPTS)


# log.debug("Defines the switch for one file")
def _switch_file(path: Path, on: bool) -> bool:
    """Switch one file's logger lines; return True if it changed."""
    # log.debug("Reads the file")
    text = path.read_text(encoding=ENCODING)
    # log.debug("Picks the patterns for Python or for scripts")
    off, live = (PY_OFF, PY_ON) if path.suffix == PY else (JS_OFF, JS_ON)
    # log.debug("Picks the comment marker for the language")
    mark = "# " if path.suffix == PY else "// "
    # log.debug("Uncomments or comments every logger line")
    new = off.sub(r"\1\2", text) if on else live.sub(rf"\1{mark}\2", text)
    # log.debug("Returns no change when nothing differs")
    if new == text:
        # log.debug("Returns unchanged")
        return False
    # log.debug("Writes the switched file")
    path.write_text(new, encoding=ENCODING)
    # log.debug("Returns changed")
    return True
