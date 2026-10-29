########################################################################
#                  standards/kds/standards/toggle.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Turns the logger lines on to trace a run, and off again before a
commit, by uncommenting or commenting them in place. It reaches Python
files and scripts, and leaves dependency, build and git folders alone.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import re
from pathlib import Path

# Local
from kds.args import required
from kds.standards import config

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the encoding every file is read and written in, from the config")
ENCODING = config.ENCODING
# log.debug("Takes the script extensions the switch reaches, from the config")
SCRIPTS = config.SCRIPTS

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Matches a commented Python logger line")
PY_OFF = re.compile(r'^(\s*)# (log\.debug\(")', re.MULTILINE)
# log.debug("Matches a live Python logger line")
PY_ON = re.compile(r'^(\s*)(log\.debug\(")', re.MULTILINE)
# log.debug("Matches a commented script logger line")
JS_OFF = re.compile(r"^(\s*)// (log\.debug\(')", re.MULTILINE)
# log.debug("Matches a live script logger line")
JS_ON = re.compile(r"^(\s*)(log\.debug\(')", re.MULTILINE)
# log.debug("Sets the extension of Python files")
PY = ".py"
# log.debug("Lists folders the switch never touches")
SKIP = ("node_modules", ".venv", "dist", ".git")


########################################################################
#                             Trace switch                             #
########################################################################
# log.debug("Defines the switch over a file or folder")
def switch(target: Path | None = None, on: bool | None = None) -> int:
    """Turns every logger line in a file or under a folder on or off.

    Args:
        target: A file, or a folder to walk. Required.
        on: True to uncomment the lines, False to comment them.
            Required.

    Returns:
        How many files changed.
    """
    # log.debug("Takes the target, which the caller must give")
    target = required(target=target)
    # log.debug("Takes the on, which the caller must give")
    on = required(on=on)
    # log.debug("Lists the files to switch: one, or all under a folder")
    files = [target] if target.is_file() else sorted(target.rglob("*"))
    # log.debug("Switches each file and counts the ones that changed")
    return sum(_switch_file(path, on) for path in files if _eligible(path))


# log.debug("Defines which files the switch may change")
def _eligible(path: Path | None = None) -> bool:
    """Returns True for Python and script files outside skipped dirs.

    Args:
        path: The path to test. Required.

    Returns:
        True when the switch may change the file.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Refuses anything under a skipped folder")
    if any(part in SKIP for part in path.parts):
        # log.debug("Returns not eligible")
        return False
    # log.debug("Accepts Python and script files")
    return path.is_file() and (path.suffix == PY or path.suffix in SCRIPTS)


# log.debug("Defines the switch for one file")
def _switch_file(path: Path | None = None, on: bool | None = None) -> bool:
    """Switches one file's logger lines; returns True if it changed.

    Args:
        path: The file to switch. Required.
        on: True to uncomment the lines, False to comment them.
            Required.

    Returns:
        True when the file was rewritten.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the on, which the caller must give")
    on = required(on=on)
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
