########################################################################
#                 standards/kds/standards/gitdates.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Reads from git which files a repository holds,   #
#                     when each was created and last changed.          #
########################################################################
"""Git facts the checks need: the file list and each file's dates."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the marker that starts each commit in the log")
COMMIT_MARK = "@@"
# log.debug("Sets the log format: the marker and the author date")
LOG_FORMAT = f"--format={COMMIT_MARK}%ad"
# log.debug("Sets the git binary; the PATH lookup is deliberate")
GIT = "git"


# log.debug("Defines what git says about the repository's files")
@dataclass
class History:
    """Each file's created and last-modified dates, and dirty files.

    Attributes:
        created: The date each current path was first added.
        modified: The date each current path was last changed.
        dirty: Paths with changes not yet committed.
        today: Today's date, for files changed but not committed.
    """

    # log.debug("Holds each path's first-added date")
    created: dict[str, str] = field(default_factory=dict)
    # log.debug("Holds each path's last-changed date")
    modified: dict[str, str] = field(default_factory=dict)
    # log.debug("Holds the paths with uncommitted changes")
    dirty: set[str] = field(default_factory=set)
    # log.debug("Holds today's date as YYYY-MM-DD")
    today: str = field(default_factory=lambda: date.today().isoformat())

    # log.debug("Defines the date a header's Created on must show")
    def created_on(self, path: str) -> str:
        """Return the date the path was first committed, or today."""
        # log.debug("Returns the recorded date, or today for a new file")
        return self.created.get(path, self.today)

    # log.debug("Defines the date a header's Last modified must show")
    def modified_on(self, path: str) -> str:
        """Return today for a changed file, else the commit date."""
        # log.debug("Returns today when the file has uncommitted changes")
        if path in self.dirty or path not in self.modified:
            # log.debug("Returns today's date")
            return self.today
        # log.debug("Returns the date of its latest commit")
        return self.modified[path]


# log.debug("Defines how git is run and its output read")
def _git(root: Path, *args: str) -> str:
    """Run git in `root` with fixed arguments and return its output."""
    # log.debug("Runs git without a shell and captures the output")
    result = subprocess.run(  # noqa: S603 - fixed arguments, no shell
        [GIT, *args], cwd=root, capture_output=True, text=True, check=True
    )
    # log.debug("Returns what git printed")
    return result.stdout


# log.debug("Defines the list of files a commit would hold")
def repo_files(root: Path) -> list[str]:
    """Return tracked files plus new files that are not ignored."""
    # log.debug("Asks git for tracked and new, unignored files")
    out = _git(root, "ls-files", "--cached", "--others", "--exclude-standard")
    # log.debug("Returns the unique paths, sorted, that still exist")
    return sorted({p for p in out.splitlines() if p and (root / p).is_file()})


# log.debug("Defines how the whole history is read in one pass")
def read_history(root: Path) -> History:
    """Read every file's created and modified dates, following renames.

    Args:
        root: The repository root.

    Returns:
        The dates for every path that exists now, and the dirty paths.
    """
    # log.debug("Starts an empty history")
    history = History()
    # log.debug("Reads every commit, newest first, with renames found")
    out = _git(root, "log", "-M", "--name-status", "--date=short", LOG_FORMAT)
    # log.debug("Maps older names to the path they have now")
    alias: dict[str, str] = {}
    # log.debug("Holds the date of the commit being read")
    when = history.today
    # log.debug("Walks the log one line at a time")
    for line in out.splitlines():
        # log.debug("Reads a commit's date when the line starts one")
        if line.startswith(COMMIT_MARK):
            # log.debug("Keeps the date for the files that follow")
            when = line[len(COMMIT_MARK) :]
            # log.debug("Moves to the next line")
            continue
        # log.debug("Splits a file line into status and paths")
        parts = line.split("\t")
        # log.debug("Skips blank lines between commits")
        if len(parts) < 2:  # noqa: PLR2004 - a status and at least one path
            # log.debug("Moves to the next line")
            continue
        # log.debug("Records this file line under its current name")
        _record(history, alias, parts, when)
    # log.debug("Adds the files that differ from the last commit")
    history.dirty = _dirty(root)
    # log.debug("Returns the full history")
    return history


# log.debug("Defines how one file line updates the history")
def _record(history: History, alias: dict[str, str], parts: list[str], when: str) -> None:
    """Record one --name-status line of the log."""
    # log.debug("Reads the status letter: A, M, D or R")
    status = parts[0][0]
    # log.debug("Takes the path the file had after this commit")
    path = parts[-1]
    # log.debug("Translates it to the name the file has now")
    current = alias.get(path, path)
    # log.debug("Notes an older name for a renamed file")
    if status == "R":
        # log.debug("Points the old name at the current name")
        alias[parts[1]] = current
    # log.debug("Keeps the newest date seen as the last change")
    if status != "D":
        # log.debug("Sets the last-changed date if none is set yet")
        history.modified.setdefault(current, when)
    # log.debug("Moves the created date back on every add")
    if status == "A":
        # log.debug("Sets the created date to this, older, commit")
        history.created[current] = when


# log.debug("Defines the set of files with uncommitted changes")
def _dirty(root: Path) -> set[str]:
    """Return paths that are staged, changed or new."""
    # log.debug("Asks git for the short status of every file")
    out = _git(root, "status", "--porcelain", "--untracked-files=all")
    # log.debug("Returns each path, taking the new name of renames")
    return {line[3:].split(" -> ")[-1] for line in out.splitlines() if line}
