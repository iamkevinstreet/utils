########################################################################
#                  standards/kds/standards/pyrules.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks every Python statement has a logger line directly above it,
indented like it and saying what it does, and that no logger line sits
above a clause, where it would break the code. The line-by-line rules
(lines left on, widths, repeated literals) live in pylines.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import io
import logging
import re
import tokenize
from dataclasses import dataclass

# Local
from kds.args import required
from kds.standards import config
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the fewest words a logger description may have, from the config")
MIN_WORDS = config.MIN_WORDS
# log.debug("Takes the name of the rule every logger-line finding belongs to, from the config")
RULE = config.LOGGER_RULE

########################################################################
#                           Local constants                            #
########################################################################
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
# log.debug("Sets the message for a logger line above a clause")
CLAUSE_MSG = "a logger line above else/elif/except/finally/case breaks the code; put it inside"


########################################################################
#                             Logger lines                             #
########################################################################
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
def statements(source: str | None = None) -> list[Statement]:
    """Returns the start of every logical line in the source.

    Args:
        source: The file's Python source. Required.

    Returns:
        A Statement for each logical line, in file order.
    """
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
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
def _statement(
    tokens: list[tokenize.TokenInfo] | None = None, lines: list[str] | None = None
) -> Statement:
    """Describes one logical line from its tokens.

    Args:
        tokens: The line's tokens, without comments, indents or line
            breaks. Required.
        lines: The file's physical lines. Required.

    Returns:
        Where the line starts, its first token and text, and whether
        it is a lone string or opens a clause.
    """
    # log.debug("Takes the tokens, which the caller must give")
    tokens = required(tokens=tokens)
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
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
def check_logger_lines(path: str | None = None, source: str | None = None) -> list[Finding]:
    """Checks every statement has a logger line directly above it.

    Args:
        path: The file's path from the repository root. Required.
        source: The file's Python source. Required.

    Returns:
        A finding for each statement whose logger line is missing,
        indented wrongly or too short to say what the line does, and
        for each logger line above a clause.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
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
def _exempt(stmt: Statement | None = None, after_decorator: bool | None = None) -> bool:
    """Returns True for statements the logger-line rule exempts.

    Args:
        stmt: The statement. Required.
        after_decorator: True when the statement before is a
            decorator. Required.

    Returns:
        True for an import, a docstring, a clause or the logger's
        creation, and for each decorator after the first and the def
        or class they wrap.
    """
    # log.debug("Takes the stmt, which the caller must give")
    stmt = required(stmt=stmt)
    # log.debug("Takes the after decorator, which the caller must give")
    after_decorator = required(after_decorator=after_decorator)
    # log.debug("Exempts imports, docstrings, clauses, logger creation")
    if stmt.first in IMPORTS or stmt.only_string or stmt.clause or CREATE_RE.match(stmt.text):
        # log.debug("Returns exempt")
        return True
    # log.debug("Exempts later decorators and the def or class they wrap")
    return after_decorator and (stmt.first in ("@", "def", "class", "async"))


# log.debug("Defines the checks on the line above a statement")
def _check_above(
    path: str | None = None, stmt: Statement | None = None, match: re.Match[str] | None = None
) -> list[Finding]:
    """Returns findings for a missing or malformed logger line.

    Args:
        path: The file's path from the repository root. Required.
        stmt: The statement that needs a logger line. Required.
        match: The line above, matched against the logger-line form;
            None when it is not a logger line.

    Returns:
        One finding when the logger line is missing; otherwise one for
        a wrong indent and one for a description too short.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the stmt, which the caller must give")
    stmt = required(stmt=stmt)
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
