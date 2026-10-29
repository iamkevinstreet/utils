########################################################################
#                  standards/tests/test_jssections.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the section rules for scripts and stylesheets: imports under their
labels, constants from the config under Global constants, code under the
logic's banner, and a stylesheet's @import under the Imports banner.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Local
from kds.standards import header as hdr
from kds.standards import jssections
from kds.standards import sections as sec
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets a script that follows every section rule")
GOOD = "\n".join(
    [
        *hdr.render("src/lib/tally.ts", "2026-10-29", "2026-10-29", "Counts.", hdr.SLASH),
        "",
        *hdr.box(sec.IMPORTS, hdr.SLASH),
        "// Standard library",
        "import { readFileSync } from 'node:fs';",
        "",
        "// Third-party",
        "import { useState } from 'react';",
        "",
        "// Local",
        "import { CONFIG } from './config';",
        "",
        *hdr.box(sec.GLOBALS, hdr.SLASH),
        "// log.debug('Takes the limit from the config')",
        "const LIMIT = CONFIG.limit;",
        "",
        *hdr.box(sec.LOCALS, hdr.SLASH),
        "// log.debug('Names the word for none')",
        "const NONE = 'none';",
        "",
        *hdr.box("Run tally", hdr.SLASH),
        "/** A count. */",
        "type Count = number;",
        "",
        "// log.debug('Defines the tally')",
        "export function tally(): Count {",
        "  // log.debug('Returns the limit')",
        "  return LIMIT;",
        "}",
        "",
    ]
)


########################################################################
#                           Script sections                            #
########################################################################
# log.debug("Defines how a script's section findings are worked out")
def findings(source: str = "", path: str = "src/lib/tally.ts") -> list[Finding]:
    """Returns the section findings for a script.

    Args:
        source: The script's text.
        path: The script's path from the repository root.

    Returns:
        The findings.
    """
    # log.debug("Splits the script into lines")
    lines = source.splitlines()
    # log.debug("Reads the header, to look for banners after it")
    header, _ = hdr.parse(source, hdr.SLASH)
    # log.debug("Finds the banners after the header")
    banners = sec.find_banners(lines, header.last + 1 if header else 0, hdr.SLASH)
    # log.debug("Returns the banner findings, then the section findings")
    return sec.check_banners(path, banners) + jssections.check_script(path, lines, banners)


# log.debug("Defines the test: a script that follows the rules has no findings")
def test_a_good_script_has_no_findings() -> None:
    """Every banner, label and statement is where it belongs."""
    # log.debug("Checks there are no findings")
    assert findings(GOOD) == []


# log.debug("Defines the test: an import under the wrong label is a finding")
def test_an_import_under_the_wrong_label_is_a_finding() -> None:
    """A relative import under Third-party is misfiled."""
    # log.debug("Files the local import under the Third-party label")
    misfiled = GOOD.replace("\n\n// Local\nimport { CONFIG }", "\nimport { CONFIG }")
    # log.debug("Checks the finding names the Local label")
    assert any(f.message == "belongs under // Local" for f in findings(misfiled))


# log.debug("Defines the test: a long import is read to its end")
def test_an_import_over_many_lines_is_read_to_its_source() -> None:
    """A config import of ten names, one per line, still names them."""
    # log.debug("Writes the config import over twelve lines, CONFIG last")
    names = "".join(f"  NAME{n},\n" for n in range(9)) + "  CONFIG,\n"
    # log.debug("Puts it in place of the one-line import")
    long = GOOD.replace(
        "import { CONFIG } from './config';", "import {\n" + names + "} from './config';"
    )
    # log.debug("Checks the constant taken from CONFIG is still a global constant")
    assert findings(long) == []


# log.debug("Defines the test: a config value among the local constants is a finding")
def test_a_config_value_among_local_constants_is_a_finding() -> None:
    """A constant taken from the config goes under Global constants."""
    # log.debug("Moves the config value under the Local constants")
    moved = GOOD.replace(
        "const NONE = 'none';",
        "const NONE = 'none';\n// log.debug('Takes a size')\nconst SIZE = CONFIG.size;",
    )
    # log.debug("Checks the finding names the Global constants")
    assert any(f.message == "belongs under the Global constants banner" for f in findings(moved))


# log.debug("Defines the test: a stylesheet's @import outside its banner is a finding")
def test_a_css_import_outside_its_banner_is_a_finding() -> None:
    """An @import below the logic's banner is out of place."""
    # log.debug("Builds a stylesheet whose @import sits in its logic")
    lines = [*hdr.box("Hero", hdr.BLOCK), "@import url('x.css');"]
    # log.debug("Checks the one finding")
    assert len(jssections.check_css("a.css", lines, sec.find_banners(lines, 0, hdr.BLOCK))) == 1
