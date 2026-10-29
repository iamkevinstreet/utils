########################################################################
#                    standards/tests/test_stamp.py                     #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests header writing: a refresh gives a moved file its new path and
git's dates and recentres every banner; an insert adds a whole header,
and refuses a Python file whose docstring would become a second one.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from pathlib import Path

# Local
from kds.standards import header as hdr
from kds.standards import stamp
from kds.standards.gitdates import History

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the path the moved file now lives at")
PATH = "src/pkg/moved.py"
# log.debug("Sets the date git first saw the file")
CREATED = "2026-10-01"
# log.debug("Sets the date of the file's latest commit")
MODIFIED = "2026-10-20"


########################################################################
#                             Stamp tests                              #
########################################################################
# log.debug("Defines the test: a refresh fixes the path, the dates and the banners")
def test_a_refresh_fixes_the_path_dates_and_banners(tmp_path: Path) -> None:
    """A file stamped under its old path and dates comes out true.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Draws a header for the file's old path and old dates")
    header = hdr.render("old/place.py", "2026-01-01", "2026-01-02", "Does one job.", hdr.PYTHON)
    # log.debug("Draws a banner whose name sits off centre")
    banner = [hdr.BORDER, "#" + "Imports".ljust(hdr.INNER) + "#", hdr.BORDER]
    # log.debug("Writes the file where it now lives")
    target = tmp_path / PATH
    # log.debug("Makes its folders")
    target.parent.mkdir(parents=True)
    # log.debug("Writes the header, the banner and an import")
    target.write_text("\n".join([*header, "", *banner, "import os"]) + "\n", encoding="utf-8")
    # log.debug("Refreshes the file from git's dates")
    changed = stamp.refresh(
        tmp_path, PATH, History(created={PATH: CREATED}, modified={PATH: MODIFIED})
    )
    # log.debug("Reads the file back")
    found, _ = hdr.parse(target.read_text(encoding="utf-8"), hdr.PYTHON)
    # log.debug("Checks the file changed and reads back with the true values")
    assert changed and found is not None
    # log.debug("Checks the path and both dates")
    assert (found.title, found.created, found.modified) == (PATH, CREATED, MODIFIED)
    # log.debug("Checks the banner's name is centred")
    assert hdr.title_line("Imports") in target.read_text(encoding="utf-8")


# log.debug("Defines the test: an insert adds a whole header")
def test_an_insert_adds_a_whole_header(tmp_path: Path) -> None:
    """A TypeScript file with no header gets the box and the doc block.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Writes a script with no header")
    (tmp_path / "tally.ts").write_text("export const ONE = 1;\n", encoding="utf-8")
    # log.debug("Adds the header")
    error = stamp.insert(tmp_path, "tally.ts", "Counts the saved runs.", History(today=MODIFIED))
    # log.debug("Reads the script back")
    found, _ = hdr.parse((tmp_path / "tally.ts").read_text(encoding="utf-8"), hdr.SLASH)
    # log.debug("Checks it worked and the description came through")
    assert error == "" and found is not None and found.description == "Counts the saved runs."


# log.debug("Defines the test: an insert refuses a module with a docstring")
def test_an_insert_refuses_a_module_with_a_docstring(tmp_path: Path) -> None:
    """The old docstring would become a second one, so it is refused.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Writes a module that has a docstring but no header")
    (tmp_path / "m.py").write_text('"""A module."""\n', encoding="utf-8")
    # log.debug("Tries to add a header")
    error = stamp.insert(tmp_path, "m.py", "Does one job.", History(today=MODIFIED))
    # log.debug("Checks the refusal says to fold the docstring in")
    assert "fold its docstring" in error
