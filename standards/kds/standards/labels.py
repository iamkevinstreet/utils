########################################################################
#                  standards/kds/standards/labels.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Puts each import group's label back above its first import. Sorting
imports moves a label with the import it sat on, so after ruff or
ESLint sorts a file the labels can drift; stamp calls this to take the
old labels out of the import block and write each one above the first
import of its group, after a blank line.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import logging

# Local
from kds.args import required
from kds.standards import header, jssections, pyimports
from kds.standards import sections as sec

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the prefix of a Python label line")
HASH_PREFIX = "# "
# log.debug("Sets the character that ends a script statement")
END = ";"
# log.debug("Sets the character a banner's border ends with")
WALL = "#"
# log.debug("Sets the import that ruff keeps apart from the rest of its group")
FUTURE = "from __future__ import"
# log.debug("Lists how a Python import line starts")
IMPORT_STARTS = ("import ", "from ")


########################################################################
#                            Import labels                             #
########################################################################
# log.debug("Defines how a Python module's labels are put back in place")
def relabel_python(
    lines: list[str] | None = None, local_names: frozenset[str] = frozenset()
) -> list[str]:
    """Returns a module's lines with each import group's label in place.

    Args:
        lines: The module's lines. Required.
        local_names: The top-level names of the repository's modules.

    Returns:
        The lines, unchanged when the module will not parse or has no
        top-level imports.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Finds the import block's first and last lines")
    span = _python_span(lines)
    # log.debug("Returns the lines unchanged when there is no import block")
    if span is None:
        # log.debug("Returns them")
        return lines
    # log.debug("Takes the old labels out of the block")
    kept = _unlabelled(lines, span, HASH_PREFIX)
    # log.debug("Reads the imports again, now the labels are gone")
    tree = ast.parse("\n".join(kept))
    # log.debug("Lists each top-level import's first line and group")
    imports = [
        (stmt.lineno - 1, pyimports.group_of(stmt, local_names))
        for stmt in tree.body
        if isinstance(stmt, ast.Import | ast.ImportFrom)
    ]
    # log.debug("Writes a label above each group")
    out = _labelled(kept, imports, HASH_PREFIX)
    # log.debug("Finds the __future__ import, which ruff keeps apart")
    future = next((i for i, line in enumerate(out) if line.startswith(FUTURE)), None)
    # log.debug("Keeps a blank line after it when an import follows")
    if future is not None and future + 1 < len(out) and out[future + 1].startswith(IMPORT_STARTS):
        # log.debug("Adds the blank line")
        out.insert(future + 1, "")
    # log.debug("Returns the lines")
    return out


# log.debug("Defines how a module's import block is found")
def _python_span(lines: list[str] | None = None) -> tuple[int, int] | None:
    """Returns the first and last line of a module's top-level imports.

    Args:
        lines: The module's lines. Required.

    Returns:
        The indexes of the first import's first line and the last
        import's last line, or None when there are none or the module
        will not parse.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Parses the module, giving up on one that will not parse")
    try:
        # log.debug("Parses it")
        tree = ast.parse("\n".join(lines))
    except SyntaxError:
        # log.debug("Returns no block")
        return None
    # log.debug("Lists the top-level imports")
    stmts = [s for s in tree.body if isinstance(s, ast.Import | ast.ImportFrom)]
    # log.debug("Returns the span, or None when there are no imports")
    return (stmts[0].lineno - 1, (stmts[-1].end_lineno or stmts[-1].lineno) - 1) if stmts else None


# log.debug("Defines how a script's labels are put back in place")
def relabel_script(lines: list[str] | None = None) -> list[str]:
    """Returns a script's lines with each import group's label in place.

    Args:
        lines: The script's lines. Required.

    Returns:
        The lines, unchanged when the script has no imports.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Lists each import's first and last line")
    found = _script_imports(lines)
    # log.debug("Returns the lines unchanged when there are no imports")
    if not found:
        # log.debug("Returns them")
        return lines
    # log.debug("Takes the old labels out of the block")
    kept = _unlabelled(lines, (found[0][0], found[-1][1]), header.SLASH_PREFIX)
    # log.debug("Lists each import's first line and group, now the labels are gone")
    imports = [
        (first, jssections.group_of(" ".join(kept[first : last + 1])))
        for first, last in _script_imports(kept)
    ]
    # log.debug("Returns the lines with a label above each group")
    return _labelled(kept, imports, header.SLASH_PREFIX)


# log.debug("Defines how a script's imports are found")
def _script_imports(lines: list[str] | None = None) -> list[tuple[int, int]]:
    """Returns each import's first and last line, the last ending in ;.

    Args:
        lines: The script's lines. Required.

    Returns:
        The indexes of each import's first and last line, in order.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Starts with no imports")
    found: list[tuple[int, int]] = []
    # log.debug("Walks the lines")
    for index, line in enumerate(lines):
        # log.debug("Skips lines that do not start an import")
        if not jssections.IMPORT_RE.match(line):
            # log.debug("Moves to the next line")
            continue
        # log.debug("Finds the line that ends the import")
        last = next(
            (j for j in range(index, len(lines)) if lines[j].rstrip().endswith(END)), index
        )
        # log.debug("Records the import")
        found.append((index, last))
    # log.debug("Returns the imports")
    return found


# log.debug("Defines how old labels and blank lines leave an import block")
def _unlabelled(
    lines: list[str] | None = None, span: tuple[int, int] = (0, 0), prefix: str = ""
) -> list[str]:
    """Returns the lines without the labels and blank lines of a block.

    The labels and the blank lines between groups are written again
    afterwards, so a label that drifted leaves no stray blank behind.

    Args:
        lines: The file's lines. Required.
        span: The block's first and last line.
        prefix: What starts a label line in this language.

    Returns:
        The lines, with each label and blank line in the block removed.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Returns every line but a label or blank from just above the block to its end")
    return [
        line
        for i, line in enumerate(lines)
        if not (span[0] - 1 <= i <= span[1] and (_is_label(line, prefix) or not line.strip()))
    ]


# log.debug("Defines the test for a label line")
def _is_label(line: str = "", prefix: str = "") -> bool:
    """Returns whether a line is one of the import groups' labels.

    Args:
        line: The line.
        prefix: What starts a label line in this language.

    Returns:
        True for a label line.
    """
    # log.debug("Returns whether the line is the prefix and a group's name")
    return line.startswith(prefix) and line.removeprefix(prefix) in sec.GROUPS


# log.debug("Defines how a label is written above each group")
def _labelled(
    lines: list[str] | None = None, imports: list[tuple[int, str]] | None = None, prefix: str = ""
) -> list[str]:
    """Returns the lines with a label above each group's first import.

    Args:
        lines: The file's lines, without labels. Required.
        imports: Each import's first line and group, in order. Required.
        prefix: What starts a label line in this language.

    Returns:
        The lines with the labels written in.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Takes the imports, which the caller must give")
    imports = required(imports=imports)
    # log.debug("Keeps the first import of each group")
    heads = {group: index for index, group in reversed(imports)}
    # log.debug("Copies the lines")
    out = list(lines)
    # log.debug("Writes the labels from the bottom up, so the indexes hold")
    for group, index in sorted(heads.items(), key=lambda pair: pair[1], reverse=True):
        # log.debug("Adds a blank line first unless one or a banner is above")
        gap = (
            [""]
            if index > 0 and out[index - 1].strip() and not out[index - 1].endswith(WALL)
            else []
        )
        # log.debug("Writes the label above the group's first import")
        out[index:index] = [*gap, prefix + group]
    # log.debug("Returns the lines")
    return out
