########################################################################
#                                                                      #
#                   standards/tests/test_gitdates.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

Tests reading dates from git: a repository with no commit yet, as a
project just copied from the template is, where every file reads as
new, so stamp and check run before the first commit; and a file renamed
since the last commit, by git or by hand, which keeps the date its old
name was created.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

# Local
from kds.args import required
from kds.standards.gitdates import read_history

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the day the first commit is dated, well before today")
FIRST_DAY = "2026-10-29"
# log.debug("Sets the text of the file that is renamed, long enough to tell apart")
TEXT = "".join(f"LINE_{n} = {n}\n" for n in range(20))


########################################################################
#                                                                      #
#                            Git date tests                            #
#                                                                      #
########################################################################
# log.debug("Defines the test that a new repository reads as all new")
def test_a_repository_with_no_commit_reads_as_all_new(tmp_path: Path) -> None:
    """No dates recorded, every file dirty, so every date is today.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Starts a repository with no commit")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607 - git from PATH
    # log.debug("Adds one file, not yet committed")
    (tmp_path / "new.py").write_text("VALUE = 1\n", encoding="utf-8")
    # log.debug("Reads the history")
    history = read_history(tmp_path)
    # log.debug("Checks nothing is recorded and the file's dates are today")
    assert (history.created, history.dirty, history.modified_on("new.py")) == (
        {},
        {"new.py"},
        history.today,
    )


# log.debug("Defines a repository with one file committed on the first day")
def _committed(root: Path | None = None) -> None:
    """Starts a repository at root with old.py committed on FIRST_DAY.

    Args:
        root: The folder to make the repository in. Required.
    """
    # log.debug("Takes the folder, which the caller must give")
    root = required(root=root)
    # log.debug("Starts the repository")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # noqa: S607 - git from PATH
    # log.debug("Writes the file")
    (root / "old.py").write_text(TEXT, encoding="utf-8")
    # log.debug("Stages it")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)  # noqa: S607 - git from PATH
    # log.debug("Sets the time of the first day")
    when = f"{FIRST_DAY}T12:00:00Z"
    # log.debug("Dates the commit on the first day and names who made it")
    env = os.environ | {
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "GIT_AUTHOR_NAME": "t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    # log.debug("Commits it")
    subprocess.run(["git", "commit", "-qm", "one"], cwd=root, check=True, env=env)  # noqa: S607


# log.debug("Defines the test that a rename git staged keeps its date")
def test_a_staged_rename_keeps_the_date_of_its_old_name(tmp_path: Path) -> None:
    """A rename staged with git mv keeps its old name's created date.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Commits the file on the first day")
    _committed(tmp_path)
    # log.debug("Renames it with git, without committing")
    subprocess.run(["git", "mv", "old.py", "new.py"], cwd=tmp_path, check=True)  # noqa: S607
    # log.debug("Reads the history")
    history = read_history(tmp_path)
    # log.debug("Checks the new name keeps the old date, and changed today")
    assert (history.created_on("new.py"), history.modified_on("new.py")) == (
        FIRST_DAY,
        history.today,
    )


# log.debug("Defines the test that a file moved by hand keeps its date")
def test_a_file_moved_by_hand_keeps_the_date_of_its_old_name(tmp_path: Path) -> None:
    """A file moved by hand, a line changed, is still a rename.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Commits the file on the first day")
    _committed(tmp_path)
    # log.debug("Moves it by hand")
    (tmp_path / "old.py").rename(tmp_path / "moved.py")
    # log.debug("Changes one line")
    (tmp_path / "moved.py").write_text(TEXT.replace("LINE_3", "LINE_THREE"), encoding="utf-8")
    # log.debug("Adds an unrelated new file beside it")
    (tmp_path / "other.py").write_text("OTHER = True\n", encoding="utf-8")
    # log.debug("Reads the history")
    history = read_history(tmp_path)
    # log.debug("Checks the moved file keeps the old date and the unrelated one is new")
    assert (history.created_on("moved.py"), history.created_on("other.py")) == (
        FIRST_DAY,
        history.today,
    )


# log.debug("Defines the test that a moved file staged under its new name alone keeps its date")
def test_a_moved_file_staged_under_its_new_name_keeps_its_date(tmp_path: Path) -> None:
    """A file moved by hand, only its new name staged, is a rename.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Commits the file on the first day")
    _committed(tmp_path)
    # log.debug("Moves it by hand")
    (tmp_path / "old.py").rename(tmp_path / "new.py")
    # log.debug("Stages the new name, leaving the old name's deletion unstaged")
    subprocess.run(["git", "add", "new.py"], cwd=tmp_path, check=True)  # noqa: S607
    # log.debug("Reads the history")
    history = read_history(tmp_path)
    # log.debug("Checks the new name keeps the old date")
    assert history.created_on("new.py") == FIRST_DAY
