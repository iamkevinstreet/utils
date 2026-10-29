########################################################################
#                  standards/kds/standards/pyrules.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Checks Python files: a logger line above every   #
#                     statement, none left on, widths, repeated        #
#                     literals.                                        #
########################################################################
"""The Python rules: logger lines, trace switches, widths, literals."""

from __future__ import annotations

import ast
import io
import logging
import re
import tokenize
from collections import Counter
from dataclasses import dataclass

from kds.standards.findings import Finding

# Module constants
log = logging.getLogger(__name__)
# log.debug("Matches a commented logger line; captures indent, text")
LOGGER_RE = re.compile(r'^(?P<indent>\s*)# log\.debug\("(?P<desc>[^"%]+)"\)$')
# log.debug("Matches a logger line someone left switched on")
LIVE_RE = re.compile(r'^\s*log\.debug\("')
# log.debug("Matches the line that creates the module's logger")
CREATE_RE = re.compile(r"^log\s*=\s*(get_logger|logging\.getLogger)\(")
# log.debug("Lists keywords that open a clause of a compound statement")
CLAUSES = frozenset({"else", "elif", "except", "finally"})
# log.debug("Lists keywords that start an import")
IMPORTS = frozenset({"import", "from"})
# log.debug("Lists tokens that never start a logical line's text")
SKIP = frozenset({tokenize.NL, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT})
# log.debug("Sets the widest a line of code or logger line may be")
CODE_WIDTH = 99
# log.debug("Sets the widest a prose comment or docstring may be")
PROSE_WIDTH = 72
# log.debug("Sets the fewest words a logger description may have")
MIN_WORDS = 2
# log.debug("Lists numbers too small to need a name")
TRIVIAL = frozenset({-1, 0, 1, 2})
# log.debug("Names the rule every logger-line finding belongs to")
RULE = "logger-line"
# log.debug("Sets the message for a logger line above a clause")
CLAUSE_MSG = "a logger line above else/elif/except/finally/case breaks the code; put it inside"


# log.debug("Defines one logical line: where it starts and how")
@dataclass(frozen=True)
class Statement:
    """The start of one logical line of code.

    Attributes:
        row: The 1-based line the statement starts on.
        col: The column its first token starts at.
        first: Its first token's text.
        text: The whole first physical line, stripped.
        only_string: True when the line is a lone string (a docstring).
        clause: True for else, elif, except, finally and case lines.
    """

    # log.debug("Holds the line the statement starts on")
    row: int
    # log.debug("Holds the column it starts at")
    col: int
    # log.debug("Holds its first token")
    first: str
    # log.debug("Holds its first physical line")
    text: str
    # log.debug("Holds whether it is a lone string")
    only_string: bool
    # log.debug("Holds whether it opens a clause")
    clause: bool


# log.debug("Defines how a file is split into logical lines")
def statements(source: str) -> list[Statement]:
    """Return the start of every logical line in the source."""
    # log.debug("Splits the source into physical lines for lookups")
    lines = source.splitlines()
    # log.debug("Starts an empty list of statements")
    found: list[Statement] = []
    # log.debug("Holds the tokens of the logical line being read")
    current: list[tokenize.TokenInfo] = []
    # log.debug("Reads the source token by token")
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        # log.debug("Closes the logical line at a NEWLINE token")
        if tok.type in (tokenize.NEWLINE, tokenize.ENDMARKER):
            # log.debug("Records the line if it had any tokens")
            if current:
                # log.debug("Adds the statement this line starts")
                found.append(_statement(current, lines))
            # log.debug("Starts collecting the next logical line")
            current = []
        elif tok.type not in SKIP:
            # log.debug("Collects a token that belongs to the line")
            current.append(tok)
    # log.debug("Returns every statement start")
    return found


# log.debug("Defines how a logical line's tokens become a Statement")
def _statement(tokens: list[tokenize.TokenInfo], lines: list[str]) -> Statement:
    """Describe the logical line made of `tokens`."""
    # log.debug("Takes the line's first token")
    head = tokens[0]
    # log.debug("Takes the physical line the statement starts on")
    text = lines[head.start[0] - 1].strip()
    # log.debug("Treats case as a clause only in a match block form")
    is_case = head.string == "case" and text.endswith(":") and len(tokens) > 1
    # log.debug("Returns the statement's description")
    return Statement(
        row=head.start[0],
        col=head.start[1],
        first=head.string,
        text=text,
        only_string=len(tokens) == 1 and head.type == tokenize.STRING,
        clause=head.string in CLAUSES or is_case,
    )


# log.debug("Defines the logger-line rule for one Python file")
def check_logger_lines(path: str, source: str) -> list[Finding]:
    """Check every statement has a logger line directly above it."""
    # log.debug("Splits the source into physical lines")
    lines = source.splitlines()
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Remembers whether the previous line was a decorator")
    after_decorator = False
    # log.debug("Walks every statement in the file")
    for stmt in statements(source):
        # log.debug("Asks whether this statement needs a logger line")
        needs = not _exempt(stmt, after_decorator)
        # log.debug("Notes whether this statement is a decorator")
        after_decorator = stmt.first == "@"
        # log.debug("Reads the line directly above the statement")
        above = lines[stmt.row - 2] if stmt.row >= 2 else ""  # noqa: PLR2004 - 1-based rows
        # log.debug("Matches it against the logger-line form")
        match = LOGGER_RE.match(above)
        # log.debug("Flags a logger line above a clause: it breaks code")
        if stmt.clause and match:
            # log.debug("Records that the logger line must move inside")
            found.append(Finding(path, stmt.row - 1, RULE, CLAUSE_MSG))
        # log.debug("Checks a statement that needs a logger line")
        if needs:
            # log.debug("Records any problem with the line above")
            found.extend(_check_above(path, stmt, match))
    # log.debug("Returns every finding")
    return found


# log.debug("Defines which statements need no logger line")
def _exempt(stmt: Statement, after_decorator: bool) -> bool:
    """Return True for statements the logger-line rule exempts."""
    # log.debug("Exempts imports, docstrings, clauses, logger creation")
    if stmt.first in IMPORTS or stmt.only_string or stmt.clause or CREATE_RE.match(stmt.text):
        # log.debug("Returns exempt")
        return True
    # log.debug("Exempts later decorators and the def or class they wrap")
    return after_decorator and (stmt.first in ("@", "def", "class", "async"))


# log.debug("Defines the checks on the line above a statement")
def _check_above(path: str, stmt: Statement, match: re.Match[str] | None) -> list[Finding]:
    """Return findings for a missing or malformed logger line."""
    # log.debug("Reports a missing logger line")
    if not match:
        # log.debug("Returns the missing-line finding")
        return [Finding(path, stmt.row, RULE, "needs a logger line directly above it")]
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Checks the logger line sits at the statement's indent")
    if len(match.group("indent")) != stmt.col:
        # log.debug("Records the misaligned logger line")
        found.append(Finding(path, stmt.row - 1, RULE, "indent it like the line below"))
    # log.debug("Checks the description says something")
    if len(match.group("desc").split()) < MIN_WORDS:
        # log.debug("Records the too-short description")
        found.append(Finding(path, stmt.row - 1, RULE, "describe what the line does"))
    # log.debug("Returns the findings")
    return found


# log.debug("Defines the checks on lines left on and line widths")
def check_lines(path: str, source: str) -> list[Finding]:
    """Check no logger line is left on and every line fits its width."""
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
def _is_prose(stripped: str, number: int, doc_rows: set[int]) -> bool:
    """Return True for docstring lines and plain comment lines."""
    # log.debug("Treats docstring lines as prose")
    if number in doc_rows:
        # log.debug("Returns prose")
        return True
    # log.debug("Treats comments as prose unless logger or box lines")
    return stripped.startswith("# ") and not LOGGER_RE.match(stripped)


# log.debug("Defines how docstring rows are found")
def _docstring_rows(source: str) -> set[int]:
    """Return the line numbers that docstrings occupy."""
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
def check_literals(path: str, source: str) -> list[Finding]:
    """Flag literals used more than once outside module-level names."""
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
def _literals(tree: ast.Module) -> list[object]:
    """Return every non-trivial literal below the module level."""
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
def _trivial(value: object) -> bool:
    """Return True for one-character strings and the numbers -1 to 2."""
    # log.debug("Treats strings of one character or none as trivial")
    if isinstance(value, str):
        # log.debug("Returns whether the string is that short")
        return len(value) <= 1
    # log.debug("Treats the smallest numbers as trivial")
    return value in TRIVIAL


# log.debug("Defines how a node's literals are listed")
def _constants(node: ast.AST) -> list[object]:
    """Return the literal values under a node, docstrings excluded."""
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
def _docstring(node: ast.AST) -> ast.Constant | None:
    """Return the string a node's body opens with, or None."""
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
def _first_lines(tree: ast.Module, counts: Counter[object]) -> dict[tuple[object, int], int]:
    """Map each repeated literal and its first line to its count."""
    # log.debug("Keeps only the literals seen at least twice")
    repeated = {value: count for value, count in counts.items() if count > 1}
    # log.debug("Starts an empty map of first lines")
    first: dict[object, int] = {}
    # log.debug("Walks every literal in source order")
    for node in ast.walk(tree):
        # log.debug("Records the first line a repeated literal is on")
        if isinstance(node, ast.Constant) and node.value in repeated and node.value not in first:
            # log.debug("Keeps that line")
            first[node.value] = node.lineno
    # log.debug("Returns each repeated literal with line and count")
    return {(value, first.get(value, 0)): count for value, count in repeated.items()}
