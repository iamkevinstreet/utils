########################################################################
#                                                                      #
#                   standards/tests/test_gitdates.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests reading dates from git on a repository with no commit yet, as a
project just copied from the template is: every file reads as new, so
stamp and check run before the first commit.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

# Local
from kds.standards.gitdates import read_history

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)


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
