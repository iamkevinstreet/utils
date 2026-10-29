########################################################################
#                  standards/kds/standards/pydocs.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks a Python function's doc block: one first line that ends a
sentence and stands alone, an Args section listing every parameter in
signature order, a Returns or Yields section when the function hands
something back, and no TODO left where a description belongs.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import inspect
import logging
import re

# Local
from kds.args import missing, required
from kds.standards import config
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the name of the rule every doc block finding belongs to, from the config")
RULE = config.FUNCTIONS_RULE

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists what a doc block's first line may end with")
STOPS = (".", "?", "!")
# log.debug("Matches an entry in an Args section and captures its name")
ENTRY_RE = re.compile(r"^    (\*{0,2}\w+)(?: \([^)]*\))?:(.*)$")
# log.debug("Matches the line that opens any section of a doc block")
SECTION_RE = re.compile(r"^[A-Z][A-Za-z ]*:$")
# log.debug("Matches a placeholder left where a description belongs")
TODO_RE = re.compile(r"\bTODO\b")
# log.debug("Names the section that lists the parameters")
ARGS = "Args:"
# log.debug("Names the section that says what a function returns")
RETURNS = "Returns:"
# log.debug("Names the section that says what a generator yields")
YIELDS = "Yields:"
# log.debug("Lists the annotations that mean a function returns nothing")
NOTHING = frozenset({"None", "NoReturn", "Never"})
# log.debug("Lists the node types that open a scope of their own")
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


########################################################################
#                         Function doc blocks                          #
########################################################################
# log.debug("Defines the checks on a function's doc block")
def check_doc(
    path: str = "",
    node: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
    names: list[str] | None = None,
) -> list[Finding]:
    """Checks the first line, the Args, and the Returns or Yields.

    Args:
        path: The file's path from the repository root.
        node: The function. Required.
        names: The parameters the signature has, in order, *args and
            **kwargs with their stars. Required.

    Returns:
        A finding for each problem with the doc block.
    """
    # log.debug("Stops when the caller left out the node")
    if node is None:
        # log.debug("Raises the missing-argument error")
        raise missing(node=node)
    # log.debug("Takes the names, which the caller must give")
    names = required(names=names)
    # log.debug("Reads the docstring")
    doc = ast.get_docstring(node)
    # log.debug("Reports a function with no doc block")
    if not doc:
        # log.debug("Returns the finding")
        return [Finding(path, node.lineno, RULE, f"{node.name} needs a doc block")]
    # log.debug("Splits the doc block into lines, cleaned of their indent")
    lines = inspect.cleandoc(doc).splitlines()
    # log.debug("Starts with the first line's checks")
    found = _check_summary(path, node.lineno, lines)
    # log.debug("Flags an Args section that does not match the signature")
    if [name for name, _ in entries(lines)] != names:
        # log.debug("Records what Args must list")
        found.append(Finding(path, node.lineno, RULE, _args_message(names)))
    # log.debug("Flags a placeholder left in the doc block")
    if any(TODO_RE.search(line) for line in lines):
        # log.debug("Records the placeholder")
        found.append(Finding(path, node.lineno, RULE, "replace each TODO with a description"))
    # log.debug("Adds the Returns or Yields check")
    return found + _check_returns(path, node, lines)


# log.debug("Defines the checks on a doc block's first line")
def _check_summary(path: str = "", line: int = 0, lines: list[str] | None = None) -> list[Finding]:
    """Checks the first line ends a sentence and stands alone.

    Args:
        path: The file's path from the repository root.
        line: The function's line, for the findings.
        lines: The doc block's lines. Required.

    Returns:
        A finding for each problem with the first line.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Flags a first line that does not end a sentence")
    if not lines[0].rstrip().endswith(STOPS):
        # log.debug("Records the unfinished first line")
        found.append(Finding(path, line, RULE, "end the doc block's first line with a full stop"))
    # log.debug("Flags a second line that runs on from the first")
    if len(lines) > 1 and lines[1].strip():
        # log.debug("Records the run-on line")
        found.append(Finding(path, line, RULE, "leave a blank line after the first line"))
    # log.debug("Returns the findings")
    return found


# log.debug("Defines how an Args section's entries are read")
def entries(lines: list[str] | None = None) -> list[tuple[str, str]]:
    """Returns each Args entry's name and text, continuation included.

    Args:
        lines: The doc block's lines, cleaned of their indent. Required.

    Returns:
        Each entry's name, with any stars, and its whole text.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Finds the line that opens the Args section, if any")
    start = next((i for i, line in enumerate(lines) if line == ARGS), None)
    # log.debug("Returns nothing when there is no Args section")
    if start is None:
        # log.debug("Returns no entries")
        return []
    # log.debug("Starts with no entries")
    found: list[tuple[str, str]] = []
    # log.debug("Walks the lines after Args: until the next section")
    for line in lines[start + 1 :]:
        # log.debug("Stops at the next section's heading")
        if SECTION_RE.match(line):
            # log.debug("Leaves the loop")
            break
        # log.debug("Starts a new entry at a name and colon")
        match = ENTRY_RE.match(line)
        # log.debug("Records the entry, or adds a continuation to the last one")
        if match:
            # log.debug("Records the new entry")
            found.append((match.group(1), match.group(2).strip()))
        elif found and line.strip():
            # log.debug("Adds the continuation's text to the last entry")
            found[-1] = (found[-1][0], f"{found[-1][1]} {line.strip()}")
    # log.debug("Returns the entries")
    return found


# log.debug("Defines the message for an Args section that does not match")
def _args_message(names: list[str] | None = None) -> str:
    """Returns what an Args section must list.

    Args:
        names: The parameters the signature has, in order. Required.

    Returns:
        The message.
    """
    # log.debug("Takes the names, which the caller must give")
    names = required(names=names)
    # log.debug("Returns no Args for a function without parameters")
    if not names:
        # log.debug("Returns the message for a function without parameters")
        return "a function without parameters has no Args section"
    # log.debug("Returns the list Args must hold")
    return "Args must list, in order: " + ", ".join(names)


# log.debug("Defines the check on Returns and Yields")
def _check_returns(
    path: str = "",
    node: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
    lines: list[str] | None = None,
) -> list[Finding]:
    """Checks a function that hands something back says what.

    Args:
        path: The file's path from the repository root.
        node: The function. Required.
        lines: The doc block's lines. Required.

    Returns:
        One finding when Returns or Yields is missing, else none.
    """
    # log.debug("Stops when the caller left out the node")
    if node is None:
        # log.debug("Raises the missing-argument error")
        raise missing(node=node)
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
    # log.debug("Works out whether the function is a generator")
    yields = any(isinstance(n, ast.Yield | ast.YieldFrom) for n in own_nodes(node))
    # log.debug("Reads the return annotation's text, if any")
    annotation = ast.unparse(node.returns) if node.returns is not None else "None"
    # log.debug("Works out whether the function hands back nothing")
    nothing = annotation in NOTHING or node.name == "__init__"
    # log.debug("Names the section the function needs, if any")
    needed = YIELDS if yields else ("" if nothing else RETURNS)
    # log.debug("Returns a finding when the needed section is missing")
    if needed and needed not in lines:
        # log.debug("Returns the finding")
        return [Finding(path, node.lineno, RULE, f"say what comes back under {needed}")]
    # log.debug("Returns no findings")
    return []


# log.debug("Defines how a function's own nodes are walked")
def own_nodes(node: ast.AST | None = None) -> list[ast.AST]:
    """Returns every node in a function's body outside nested scopes.

    Args:
        node: The function. Required.

    Returns:
        The nodes, with nested functions, classes and lambdas left out.
    """
    # log.debug("Takes the function, which the caller must give")
    node = required(node=node)
    # log.debug("Starts with the function's direct children")
    stack = list(ast.iter_child_nodes(node))
    # log.debug("Starts with no nodes")
    found: list[ast.AST] = []
    # log.debug("Walks the tree, stopping at nested scopes")
    while stack:
        # log.debug("Takes the next node")
        child = stack.pop()
        # log.debug("Skips a nested function, class or lambda")
        if isinstance(child, SCOPES):
            # log.debug("Moves to the next node")
            continue
        # log.debug("Keeps the node")
        found.append(child)
        # log.debug("Adds its children to the walk")
        stack.extend(ast.iter_child_nodes(child))
    # log.debug("Returns the nodes")
    return found
