########################################################################
#                  standards/tests/test_constants.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the shared-constant rule: a constant one file imports from
another, and one name set to the same value in two files, belong in the
config; the config module itself, tests and data are left out.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Local
from kds.standards import constants

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets a module that names a constant")
STATE = 'PREFIX = "/api/v1"\n'
# log.debug("Sets a module that imports that constant")
APP = "from pkg.api.state import PREFIX\n"


########################################################################
#                           Shared constants                           #
########################################################################
# log.debug("Defines the test: an imported constant is a finding")
def test_an_imported_constant_is_a_finding() -> None:
    """The importing file is told the value belongs in the config."""
    # log.debug("Checks the two files")
    found = constants.check_shared({"src/pkg/api/state.py": STATE, "src/pkg/api/app.py": APP})
    # log.debug("Checks the one finding is on the importing file")
    assert [(f.path, f.rule) for f in found] == [("src/pkg/api/app.py", "constants")]


# log.debug("Defines the test: one constant set in two files is a finding")
def test_one_constant_set_in_two_files_is_a_finding() -> None:
    """The same name and value in two files is one value, twice."""
    # log.debug("Checks two files that both set the same encoding")
    found = constants.check_shared(
        {"a.py": 'ENCODING = "utf-8"\n', "b.py": 'ENCODING = "utf-8"\n'}
    )
    # log.debug("Checks both files are named")
    assert sorted(f.path for f in found) == ["a.py", "b.py"]


# log.debug("Defines the test: the config, tests and data are left out")
def test_config_tests_and_data_are_left_out() -> None:
    """Shared values go in the config; tests and data share freely."""
    # log.debug("Checks a config module, a test and a data module that share a value")
    found = constants.check_shared(
        {
            "src/pkg/config.py": STATE,
            "src/pkg/api/app.py": "from pkg.config import PREFIX\n",
            "tests/test_a.py": STATE,
            "tests/test_b.py": STATE,
            "src/data/copy.ts": "export const TITLE = 'Hi';\n",
            "src/pages/x.ts": "import { TITLE } from '../data/copy';\n",
        }
    )
    # log.debug("Checks there are no findings")
    assert found == []


# log.debug("Defines the test: an imported script constant is a finding")
def test_an_imported_script_constant_is_a_finding() -> None:
    """Scripts follow the same rule as Python."""
    # log.debug("Checks a script that imports a constant from another")
    found = constants.check_shared(
        {
            "src/lib/words.ts": "export const YES = 'Yes';\n",
            "src/components/Row.tsx": "import { YES } from '../lib/words';\n",
        }
    )
    # log.debug("Checks the finding is on the importing script")
    assert [f.path for f in found] == ["src/components/Row.tsx"]
