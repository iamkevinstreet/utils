########################################################################
#                   standards/tests/test_sections.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the section rules for Python: banners come in order, centred and
once each; each statement sits in its section; the logger opens the
Global constants; and each import sits under its group's label.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import logging

# Local
from kds.standards import header as hdr
from kds.standards import pysections
from kds.standards import sections as sec
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the names the test repository's own modules go by")
LOCAL = frozenset({"pkg"})
# log.debug("Sets a module that follows every section rule")
GOOD = "\n".join(
    [
        *hdr.render("pkg/good.py", "2026-10-29", "2026-10-29", "Does one job.", hdr.PYTHON),
        "",
        *hdr.box(sec.IMPORTS),
        "# Standard library",
        "from __future__ import annotations",
        "",
        "import logging",
        "",
        "# Third-party",
        "import pydantic",
        "",
        "# Local",
        "from pkg.config import SETTINGS",
        "",
        *hdr.box(sec.GLOBALS),
        "log = logging.getLogger(__name__)",
        '# log.debug("Takes the limit from the config")',
        "LIMIT = SETTINGS.limit",
        "",
        *hdr.box(sec.LOCALS),
        '# log.debug("Names the thing")',
        'NAME = "thing"',
        "",
        "",
        *hdr.box("Thing maker"),
        '# log.debug("Defines the maker")',
        "def make() -> str:",
        '    """Makes the thing."""',
        '    # log.debug("Returns the thing")',
        "    return NAME",
        "",
    ]
)


########################################################################
#                            Section tests                             #
########################################################################
# log.debug("Defines how a module's section findings are worked out")
def findings(source: str = "") -> list[Finding]:
    """Returns the banner and section findings for a module.

    Args:
        source: The module's text.

    Returns:
        The findings, banners first.
    """
    # log.debug("Splits the module into lines")
    lines = source.splitlines()
    # log.debug("Finds its banners after the header")
    banners = sec.find_banners(lines, 10, hdr.PYTHON)
    # log.debug("Returns the banner findings, then the section findings")
    return sec.check_banners("m.py", banners) + pysections.check_module(
        "m.py", ast.parse(source), lines, banners, LOCAL
    )


# log.debug("Defines the test: a module that follows the rules has no findings")
def test_a_good_module_has_no_findings() -> None:
    """Every banner, label and statement is where it belongs."""
    # log.debug("Checks there are no findings")
    assert findings(GOOD) == []


# log.debug("Defines the test: banners out of order are a finding")
def test_banners_out_of_order_are_a_finding() -> None:
    """Local constants above Global constants is out of order."""
    # log.debug("Swaps the two constants banners' names")
    swapped = (
        GOOD.replace(sec.GLOBALS.center(hdr.INNER), "@@")
        .replace(sec.LOCALS.center(hdr.INNER), sec.GLOBALS.center(hdr.INNER))
        .replace("@@", sec.LOCALS.center(hdr.INNER))
    )
    # log.debug("Checks one finding says the order")
    assert any("out of order" in f.message for f in findings(swapped))


# log.debug("Defines the test: an off-centre banner is a finding")
def test_an_off_centre_banner_is_a_finding() -> None:
    """A banner's name must sit in the centre of its box."""
    # log.debug("Moves the Imports banner's name to the left wall")
    moved = GOOD.replace(sec.IMPORTS.center(hdr.INNER), sec.IMPORTS.ljust(hdr.INNER))
    # log.debug("Checks the finding asks for it to be centred")
    assert [f.message for f in findings(moved)] == [sec.CENTRE_MESSAGE]


# log.debug("Defines the test: a constant in the logic is a finding")
def test_a_constant_in_the_logic_is_a_finding() -> None:
    """A constant below the logic's banner belongs above it."""
    # log.debug("Adds a constant at the end of the module")
    late = GOOD + '# log.debug("Names another thing")\nOTHER = "other"\n'
    # log.debug("Checks the finding names the Local constants")
    assert any("Local constants" in f.message for f in findings(late))


# log.debug("Defines the test: a config value among the local constants is a finding")
def test_a_config_value_among_local_constants_is_a_finding() -> None:
    """A value taken from the config belongs under Global constants."""
    # log.debug("Moves the config value under the Local constants banner")
    moved = GOOD.replace(
        '# log.debug("Names the thing")',
        '# log.debug("Takes the size from the config")\nSIZE = SETTINGS.size\n'
        '# log.debug("Names the thing")',
    )
    # log.debug("Checks the finding names the Global constants")
    assert any("Global constants" in f.message for f in findings(moved))


# log.debug("Defines the test: an import under the wrong label is a finding")
def test_an_import_under_the_wrong_label_is_a_finding() -> None:
    """A third-party package under the Local label is misfiled."""
    # log.debug("Files pydantic under the Local label")
    misfiled = GOOD.replace(
        "# Third-party\nimport pydantic\n\n# Local\n", "# Local\nimport pydantic\n"
    )
    # log.debug("Checks the finding names the right label")
    assert any(f.message == "belongs under # Third-party" for f in findings(misfiled))


# log.debug("Defines the test: code with no logic banner is a finding")
def test_code_with_no_logic_banner_is_a_finding() -> None:
    """A function needs a banner naming the file's job above it."""
    # log.debug("Removes the logic's banner")
    bare = GOOD.replace("\n".join(hdr.box("Thing maker")) + "\n", "")
    # log.debug("Checks a finding asks for the banner")
    assert any(f.message == sec.LOGIC_MESSAGE for f in findings(bare))
