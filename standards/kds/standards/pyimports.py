########################################################################
#                 standards/kds/standards/pyimports.py                 #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks a Python module's imports sit in their three groups, each under
its label: # Standard library (Python's own modules and __future__),
# Third-party (installed packages, our kds packages included) and
# Local (the repository's own modules), in that order.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import logging
import sys
from itertools import pairwise

# Local
from kds.args import missing, required
from kds.standards import config
from kds.standards import sections as sec
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the name of the rule every import-label finding belongs to, from the config")
IMPORT_RULE = config.IMPORT_RULE

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the prefix of a label line")
LABEL_PREFIX = "# "


########################################################################
#                            Import groups                             #
########################################################################
# log.debug("Defines the checks on the import groups' labels")
def check_labels(
    path: str = "",
    imports: list[ast.stmt] | None = None,
    lines: list[str] | None = None,
    banners: list[sec.Banner] | None = None,
    local_names: frozenset[str] = frozenset(),
) -> list[Finding]:
    """Checks each import sits under the label of its group.

    Args:
        path: The file's path from the repository root.
        imports: The module's top-level import statements. Required.
        lines: The file's lines. Required.
        banners: The file's banners, in file order. Required.
        local_names: The top-level names of this repository's modules.

    Returns:
        A finding for each import under the wrong label or none, and
        each label out of order.
    """
    # log.debug("Takes the imports, which the caller must give")
    imports = required(imports=imports)
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Takes the banners, which the caller must give")
    banners = required(banners=banners)
    # log.debug("Finds each label line and its group, in file order")
    labels = [
        (i, line.removeprefix(LABEL_PREFIX))
        for i, line in enumerate(lines)
        if line.startswith(LABEL_PREFIX) and line.removeprefix(LABEL_PREFIX) in sec.GROUPS
    ]
    # log.debug("Flags labels whose groups are out of order")
    found = [
        Finding(path, i + 1, IMPORT_RULE, "import groups go: standard library, third-party, local")
        for (_, a), (i, b) in pairwise(labels)
        if sec.GROUPS.index(b) <= sec.GROUPS.index(a)
    ]
    # log.debug("Walks each import that is not a TYPE_CHECKING block")
    for stmt in (s for s in imports if isinstance(s, ast.Import | ast.ImportFrom)):
        # log.debug("Finds the label above the import, if any")
        above = next((g for i, g in reversed(labels) if i < stmt.lineno - 1), None)
        # log.debug("Works out which group the import belongs to")
        group = group_of(stmt, local_names)
        # log.debug("Flags an import under the wrong label or none")
        if above != group:
            # log.debug("Records the misplaced import")
            found.append(Finding(path, stmt.lineno, IMPORT_RULE, f"belongs under # {group}"))
    # log.debug("Returns every finding")
    return found


# log.debug("Defines which group an import belongs to")
def group_of(
    stmt: ast.Import | ast.ImportFrom | None = None, local_names: frozenset[str] = frozenset()
) -> str:
    """Returns the group an import belongs to.

    Args:
        stmt: The import statement. Required.
        local_names: The top-level names of this repository's modules.

    Returns:
        Standard library, Third-party or Local.
    """
    # log.debug("Stops when the caller left out the stmt")
    if stmt is None:
        # log.debug("Raises the missing-argument error")
        raise missing(stmt=stmt)
    # log.debug("Puts a relative import with this repository's modules")
    if isinstance(stmt, ast.ImportFrom) and stmt.level:
        # log.debug("Returns the local group")
        return sec.GROUPS[2]
    # log.debug("Reads the imported module's first segment")
    top = (stmt.module or "" if isinstance(stmt, ast.ImportFrom) else stmt.names[0].name).split(
        "."
    )[0]
    # log.debug("Puts __future__ and the standard library first")
    if top == "__future__" or top in sys.stdlib_module_names:
        # log.debug("Returns the standard library group")
        return sec.GROUPS[0]
    # log.debug("Returns local for this repository's modules, third-party otherwise")
    return sec.GROUPS[2] if top in local_names else sec.GROUPS[1]
