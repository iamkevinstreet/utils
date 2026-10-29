########################################################################
#                  standards/kds/standards/jsrules.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Checks TypeScript, JavaScript and Astro          #
#                     frontmatter: a logger line above every           #
#                     statement, none left on.                         #
########################################################################
"""The script rules, read line by line from Prettier-formatted code."""

from __future__ import annotations

import logging
import re

from kds.standards.findings import Finding

# Module constants
log = logging.getLogger(__name__)
# log.debug("Matches a commented logger line; captures indent, text")
LOGGER_RE = re.compile(r"^(?P<indent>\s*)// log\.debug\('(?P<desc>[^']+)'\)$")
# log.debug("Matches a logger line someone left switched on")
LIVE_RE = re.compile(r"^\s*log\.debug\(")
# log.debug("Matches string literals, to blank them before scanning")
STRING_RE = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`")
# log.debug("Lists the characters that end a statement or block line")
ENDS = (";", "{", "}")
# log.debug("Lists how a line that continues the last one starts; | and & cover unions")
CONTINUES = ("}", ")", "]", ".", "?", ":", "&", "|", "+", "-", "*", "/", "=>", ",")
# log.debug("Lists statement starts that need no logger line")
EXEMPT = (
    "import ",
    "export {",
    "export *",
    "export type",
    "type ",
    "interface ",
    "declare ",
    "case ",
    "default:",
    "export interface",
    "const log =",
)
# log.debug("Lists line starts whose braces hold types, not code")
TYPE_STARTS = ("interface ", "export interface ", "type ", "export type ", "enum ", "export enum ")
# log.debug("Matches code before a { that opens a block, not a value")
BLOCK_BEFORE = re.compile(
    r"(\)|=>|\belse|\btry|\bfinally|\bdo|^)\s*$|^(export\s+)?(class|async|function)\b"
)
# log.debug("Matches code before a { that opens a function body inside a call")
CALLBACK_BEFORE = re.compile(r"(\)|=>)\s*$")
# log.debug("Names the rule every finding here belongs to")
RULE = "logger-line"
# log.debug("Sets the fewest words a logger description may have")
MIN_WORDS = 2
# log.debug("Sets the marker that starts a line comment")
COMMENT = "//"
# log.debug("Names a bracket that opens a block of code")
BLOCK = "block"
# log.debug("Names a bracket that opens a value")
LITERAL = "literal"
# log.debug("Names a brace that opens a type's body")
TYPE = "type"
# log.debug("Sets the fence that opens and closes Astro frontmatter")
FENCE = "---"


# log.debug("Defines which lines of a file hold script code")
def script_lines(path: str, source: str) -> list[tuple[int, str]]:
    """Return (line number, text) for each line of script code."""
    # log.debug("Numbers every line from 1")
    numbered = list(enumerate(source.splitlines(), start=1))
    # log.debug("Returns every line for a plain script file")
    if not path.endswith(".astro"):
        # log.debug("Returns the whole file")
        return numbered
    # log.debug("Finds the rows of the frontmatter's two fences")
    fences = [n for n, text in numbered if text.strip() == FENCE][:2]
    # log.debug("Returns nothing when the component has no frontmatter")
    if len(fences) < 2:  # noqa: PLR2004 - an opening and a closing fence
        # log.debug("Returns an empty list")
        return []
    # log.debug("Returns the lines between the two fences")
    return [(n, text) for n, text in numbered if fences[0] < n < fences[1]]


# log.debug("Defines how statement starts are found")
def statement_rows(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Return (line number, text) for each statement's first line."""
    # log.debug("Starts an empty list of statement starts")
    starts: list[tuple[int, str]] = []
    # log.debug("Tracks open brackets: code blocks or value literals")
    stack: list[str] = []
    # log.debug("Tracks whether a template string is still open")
    in_template = False
    # log.debug("Treats the file's start as the end of a statement")
    previous = ";"
    # log.debug("Walks the script lines in order")
    for number, raw in lines:
        # log.debug("Removes the line's surrounding spaces")
        line = raw.strip()
        # log.debug("Skips lines inside an open template string")
        if in_template:
            # log.debug("Closes the template on an odd backtick count")
            in_template = line.count("`") % 2 == 0
            # log.debug("Moves to the next line")
            continue
        # log.debug("Skips blank lines and comments")
        if not line or line.startswith((COMMENT, "/*", "*")):
            # log.debug("Moves to the next line")
            continue
        # log.debug("Blanks strings and drops a trailing comment")
        code = _code_only(line)
        # log.debug("Decides whether this line starts a statement")
        if _starts(previous, stack, line):
            # log.debug("Records the statement start")
            starts.append((number, raw))
        # log.debug("Updates the open brackets from this line")
        _track(code, stack, line)
        # log.debug("Remembers the line's last character")
        previous = code.rstrip()[-1:] or previous
        # log.debug("Opens a template string left open by this line")
        in_template = code.count("`") % 2 == 1
    # log.debug("Returns every statement start")
    return starts


# log.debug("Defines how a line is reduced to its code")
def _code_only(line: str) -> str:
    """Return the line with strings blanked and comments removed."""
    # log.debug("Replaces each string with an empty pair of quotes")
    blanked = STRING_RE.sub('""', line)
    # log.debug("Cuts a trailing // comment")
    return blanked.split(COMMENT, 1)[0]


# log.debug("Defines the test for a statement start")
def _starts(previous: str, stack: list[str], line: str) -> bool:
    """Return True when this line begins a new statement."""
    # log.debug("Says no inside a value literal or type body")
    if stack and stack[-1] != BLOCK:
        # log.debug("Returns no")
        return False
    # log.debug("Says yes after an end, unless the line continues")
    return previous in ENDS and not line.startswith(CONTINUES)


# log.debug("Defines how brackets on a line update the stack")
def _track(code: str, stack: list[str], line: str) -> None:
    """Push each opening bracket's kind and pop each closing one."""
    # log.debug("Walks the line's characters with their positions")
    for index, char in enumerate(code):
        # log.debug("Pops the innermost bracket on a closer")
        if char in "}])" and stack:
            # log.debug("Removes the innermost open bracket")
            stack.pop()
        # log.debug("Pushes the kind of each opening bracket")
        if char in "{[(":
            # log.debug("Notes whether the bracket sits inside a call, array or object")
            inside = bool(stack) and stack[-1] != BLOCK
            # log.debug("Classifies the bracket from the code before it")
            stack.append(_kind(char, code[:index], line, inside=inside))


# log.debug("Defines what kind of bracket an opener is")
def _kind(char: str, before: str, line: str, *, inside: bool) -> str:
    """Return block for a code block, else type or literal.

    Inside a call, array or object, a { opens an object unless it
    follows => or ) and so opens a callback's body.
    """
    # log.debug("Treats [ and ( as value brackets")
    if char != "{":
        # log.debug("Returns literal")
        return LITERAL
    # log.debug("Treats braces on a type declaration as a type body")
    if line.startswith(TYPE_STARTS):
        # log.debug("Returns type")
        return TYPE
    # log.debug("Treats a { inside a value as an object, unless a callback opens")
    if inside:
        # log.debug("Returns block for a callback body, literal for an object")
        return BLOCK if CALLBACK_BEFORE.search(before.rstrip()) else LITERAL
    # log.debug("Returns block when the code before reads like one")
    return BLOCK if BLOCK_BEFORE.search(before.rstrip()) else LITERAL


# log.debug("Defines the logger-line rule for one script file")
def check_logger_lines(path: str, source: str) -> list[Finding]:
    """Check every statement has a logger line directly above it."""
    # log.debug("Takes the lines that hold script code")
    lines = script_lines(path, source)
    # log.debug("Indexes the whole file by line number")
    by_number = dict(enumerate(source.splitlines(), start=1))
    # log.debug("Starts with no findings")
    found: list[Finding] = []
    # log.debug("Walks every statement start")
    for number, raw in statement_rows(lines):
        # log.debug("Skips statements the logger-line rule exempts")
        if raw.strip().startswith(EXEMPT):
            # log.debug("Moves to the next statement")
            continue
        # log.debug("Matches the line above against the logger form")
        match = LOGGER_RE.match(by_number.get(number - 1, ""))
        # log.debug("Measures the statement's indent")
        indent = len(raw) - len(raw.lstrip())
        # log.debug("Records a missing or misplaced logger line")
        if not match or len(match.group("indent")) != indent:
            # log.debug("Adds the finding for this statement")
            found.append(Finding(path, number, RULE, "needs a logger line directly above it"))
        elif len(match.group("desc").split()) < MIN_WORDS:
            # log.debug("Records a description too short to help")
            found.append(Finding(path, number - 1, RULE, "describe what the line does"))
    # log.debug("Returns every finding")
    return found


# log.debug("Defines the check for logger lines left on")
def check_live(path: str, source: str) -> list[Finding]:
    """Flag any logger line left switched on."""
    # log.debug("Returns a finding for each live logger line")
    return [
        Finding(path, number, "trace-off", "logger line left on; run trace off")
        for number, text in script_lines(path, source)
        if LIVE_RE.match(text)
    ]
