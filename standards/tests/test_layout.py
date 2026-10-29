########################################################################
#                    standards/tests/test_layout.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the repository rules: how deep a file may sit and how long a
source file may run. It also tests the script rules' statement finder,
which skips the lines inside an object.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Local
from kds.standards import jsrules, layout

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                           Repository shape                           #
########################################################################
# log.debug("Defines the test for the folder-depth rule")
def test_depth_allows_one_more_in_an_area() -> None:
    """Three folders anywhere, four under frontend/ or backend/."""
    # log.debug("Checks three folders deep is allowed")
    assert layout.check_depth("a/b/c/file.py") == []
    # log.debug("Checks four folders deep is refused")
    assert layout.check_depth("a/b/c/d/file.py") != []
    # log.debug("Checks four deep under frontend/ is allowed")
    assert layout.check_depth("frontend/src/components/forms/Field.tsx") == []


# log.debug("Defines the test for the file-length rule")
def test_length_limit() -> None:
    """A 501-line source file is a finding; a 501-line README is not."""
    # log.debug("Builds 501 lines of text")
    text = "x\n" * 501
    # log.debug("Checks a long Python file is reported")
    assert layout.check_length("a.py", text) != []
    # log.debug("Checks a long Markdown file is not")
    assert layout.check_length("README.md", text) == []


# log.debug("Defines the test for the script statement finder")
def test_script_statements_skip_object_bodies() -> None:
    """Statements are found; lines inside an object literal are not."""
    # log.debug("Builds a script with a block and an object literal")
    source = "const a = {\n  b: 1,\n};\nif (a) {\n  run();\n}\n"
    # log.debug("Finds the statement starts")
    rows = [n for n, _ in jsrules.statement_rows(list(enumerate(source.splitlines(), 1)))]
    # log.debug("Checks only the three real statements are found")
    assert rows == [1, 4, 5]
