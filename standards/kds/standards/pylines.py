########################################################################
#                  standards/kds/standards/pylines.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks a Python file's lines and literals: no logger line left switched
on, code within 99 characters and prose within 72, and no literal
repeated inside functions or classes, where a named constant belongs.
Prose is a docstring or a comment other than a logger line; strings of
one character and the numbers -1 to 2 never need a name.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import logging
from collections import Counter

# Local
from kds.args import required
from kds.standards.findings import Finding
from kds.standards.pyrules import LIVE_RE, LOGGER_RE

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the widest a line of code or logger line may be")
CODE_WIDTH = 99
# log.debug("Sets the widest a prose comment or docstring may be")
PROSE_WIDTH = 72
# log.debug("Lists numbers too small to need a name")
TRIVIAL = frozenset({-1, 0, 1, 2})


########################################################################
#                          Lines and literals                          #
########################################################################
# log.debug("Defines the checks on lines left on and line widths")
def check_lines(path: str | None = None, source: str | None = None) -> list[Finding]:
    """Checks no logger line is left on and every line fits its width.

    Args:
        path: The file's path from the repository root. Required.
        source: The file's Python source. Required.

    Returns:
        A finding for each logger line left on and each line wider
        than its limit.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Finds the rows that belong to docstrings")
    doc_rows = _docstring_rows(source)
    # log.debug("Walks every physical line with its number")
    for number, line in enumerate(source.splitlines(), start=1):
        # log.debug("Measures the line without its newline")
        width = len(line)
        # log.debug("Reads the line without indentation")
        stripped = line.strip()
        # log.debug("Flags a logger line left switched on")
        if LIVE_RE.match(line):
            # log.debug("Records the live logger line")
            found.append(Finding(path, number, "trace-off", "logger line left on; run trace off"))
        # log.debug("Decides the width limit for this line")
        limit = PROSE_WIDTH if _is_prose(stripped, number, doc_rows) else CODE_WIDTH
        # log.debug("Flags a line wider than its limit")
        if width > limit:
            # log.debug("Records the over-wide line")
            found.append(Finding(path, number, "width", f"{width} characters; at most {limit}"))
    # log.debug("Returns every finding")
    return found


# log.debug("Defines which lines are prose that wraps at 72")
def _is_prose(
    stripped: str | None = None, number: int | None = None, doc_rows: set[int] | None = None
) -> bool:
    """Returns True for docstring lines and plain comment lines.

    Args:
        stripped: The line without its indent. Required.
        number: The line's number, counted from 1. Required.
        doc_rows: The numbers of the lines docstrings occupy. Required.

    Returns:
        True when the line is prose, held to the narrower width.
    """
    # log.debug("Takes the stripped, which the caller must give")
    stripped = required(stripped=stripped)
    # log.debug("Takes the number, which the caller must give")
    number = required(number=number)
    # log.debug("Takes the docstring rows, which the caller must give")
    doc_rows = required(doc_rows=doc_rows)
    # log.debug("Treats docstring lines as prose")
    if number in doc_rows:
        # log.debug("Returns prose")
        return True
    # log.debug("Treats comments as prose unless logger or box lines")
    return stripped.startswith("# ") and not LOGGER_RE.match(stripped)


# log.debug("Defines how docstring rows are found")
def _docstring_rows(source: str | None = None) -> set[int]:
    """Returns the line numbers that docstrings occupy.

    Args:
        source: The file's Python source. Required.

    Returns:
        Every line, counted from 1, that the docstring of the module,
        a class or a function spans.
    """
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
    # log.debug("Parses the file into a syntax tree")
    tree = ast.parse(source)
    # log.debug("Starts an empty set of rows")
    rows: set[int] = set()
    # log.debug("Visits the module, every class and every function")
    for node in ast.walk(tree):
        # log.debug("Skips nodes that cannot carry a docstring")
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            # log.debug("Moves to the next node")
            continue
        # log.debug("Takes the node's first statement, if any")
        first = node.body[0] if node.body else None
        # log.debug("Records the rows of a string first statement")
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            # log.debug("Adds every row the docstring spans")
            rows.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    # log.debug("Returns the docstring rows")
    return rows


# log.debug("Defines the repeated-literal rule")
def check_literals(path: str | None = None, source: str | None = None) -> list[Finding]:
    """Flags literals used more than once outside module-level names.

    Args:
        path: The file's path from the repository root. Required.
        source: The file's Python source. Required.

    Returns:
        A finding for each literal used twice or more, with its count.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
    # log.debug("Parses the file into a syntax tree")
    tree = ast.parse(source)
    # log.debug("Collects literals from everything but the top level")
    values = Counter(_literals(tree))
    # log.debug("Returns a finding for each literal seen twice or more")
    return [
        Finding(path, line, "literal", f"{value!r} appears {count} times; name it a constant")
        for (value, line), count in _first_lines(tree, values).items()
    ]


# log.debug("Defines how literals inside functions are collected")
def _literals(tree: ast.Module | None = None) -> list[object]:
    """Returns every non-trivial literal below the module level.

    Args:
        tree: The parsed module. Required.

    Returns:
        Each literal's value, once for every use, with module-level
        assignments and expressions left out.
    """
    # log.debug("Takes the tree, which the caller must give")
    tree = required(tree=tree)
    # log.debug("Starts an empty list of values")
    found: list[object] = []
    # log.debug("Visits each top-level definition")
    for top in tree.body:
        # log.debug("Skips module-level assignments: they are constants")
        if isinstance(top, ast.Assign | ast.AnnAssign | ast.Expr):
            # log.debug("Moves to the next top-level node")
            continue
        # log.debug("Collects each literal below this definition")
        found.extend(v for v in _constants(top) if not _trivial(v))
    # log.debug("Returns the values")
    return found


# log.debug("Defines the literals too small to need a name")
def _trivial(value: object = None) -> bool:
    """Returns True for one-character strings and the numbers -1 to 2.

    Args:
        value: A literal's value.

    Returns:
        True when the value is too small to need a name.
    """
    # log.debug("Treats strings of one character or none as trivial")
    if isinstance(value, str):
        # log.debug("Returns whether the string is that short")
        return len(value) <= 1
    # log.debug("Treats the smallest numbers as trivial")
    return value in TRIVIAL


# log.debug("Defines how a node's literals are listed")
def _constants(node: ast.AST | None = None) -> list[object]:
    """Returns the literal values under a node, docstrings excluded.

    Args:
        node: The node to look under. Required.

    Returns:
        The value of each string or number literal, once for every
        use, leaving out docstrings and the fixed text of f-strings.
    """
    # log.debug("Takes the node, which the caller must give")
    node = required(node=node)
    # log.debug("Finds the docstring nodes to leave out")
    skip = {id(doc) for n in ast.walk(node) if (doc := _docstring(n)) is not None}
    # log.debug("Leaves out the text pieces inside f-strings")
    skip |= {id(part) for n in ast.walk(node) if isinstance(n, ast.JoinedStr) for part in n.values}
    # log.debug("Returns each str or number literal not left out")
    return [
        n.value
        for n in ast.walk(node)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str | int | float)
        and not isinstance(n.value, bool)
        and id(n) not in skip
    ]


# log.debug("Defines how a node's docstring is found")
def _docstring(node: ast.AST | None = None) -> ast.Constant | None:
    """Returns the string a node's body opens with, or None.

    Args:
        node: The node, which may have a body. Required.

    Returns:
        The string constant that opens the body; None when the node
        has no body or the body opens with anything else.
    """
    # log.debug("Takes the node, which the caller must give")
    node = required(node=node)
    # log.debug("Reads the node's body, if it has one")
    body = getattr(node, "body", None)
    # log.debug("Returns None unless the body opens with an expression")
    if not (isinstance(body, list) and body and isinstance(body[0], ast.Expr)):
        # log.debug("Returns no docstring")
        return None
    # log.debug("Reads the expression's value")
    value = body[0].value
    # log.debug("Returns it when it is a string constant")
    return value if isinstance(value, ast.Constant) and isinstance(value.value, str) else None


# log.debug("Defines where each repeated literal is first used")
def _first_lines(
    tree: ast.Module | None = None, counts: Counter[object] | None = None
) -> dict[tuple[object, int], int]:
    """Maps each repeated literal and its first line to its count.

    Args:
        tree: The parsed module. Required.
        counts: How many times each literal is used. Required.

    Returns:
        Each literal used twice or more, paired with the first line
        found for it, mapped to its count.
    """
    # log.debug("Takes the tree, which the caller must give")
    tree = required(tree=tree)
    # log.debug("Takes the counts, which the caller must give")
    counts = required(counts=counts)
    # log.debug("Keeps only the literals seen at least twice")
    repeated = {value: count for value, count in counts.items() if count > 1}
    # log.debug("Starts an empty map of first lines")
    first: dict[object, int] = {}
    # log.debug("Lists the docstrings, whose text is never a literal to name")
    docs = {id(d) for n in ast.walk(tree) if (d := _docstring(n)) is not None}
    # log.debug("Lists every literal that is not a docstring, in source order")
    nodes = sorted(
        (n for n in ast.walk(tree) if isinstance(n, ast.Constant) and id(n) not in docs),
        key=lambda n: (n.lineno, n.col_offset),
    )
    # log.debug("Walks every literal in source order")
    for node in nodes:
        # log.debug("Records the first line a repeated literal is on")
        if node.value in repeated and node.value not in first:
            # log.debug("Keeps that line")
            first[node.value] = node.lineno
    # log.debug("Returns each repeated literal with line and count")
    return {(value, first.get(value, 0)): count for value, count in repeated.items()}
