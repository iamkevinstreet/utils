########################################################################
#                  standards/kds/standards/jsrules.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Checks each statement of a TypeScript or JavaScript file, or of an
Astro component's frontmatter, has a logger line directly above it,
indented like it and saying what it does, and that none is left
switched on. Scripts are not parsed but read line by line, as Prettier
formats them: a statement starts after a line ending in ;, { or }, and
a stack of the brackets still open tells a block of code from a value
or a type's body, whose lines are not statements.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import re

# Local
from kds.args import required
from kds.standards import config
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the fence that opens and closes Astro frontmatter, from the config")
FENCE = config.FENCE
# log.debug("Takes the fewest words a logger description may have, from the config")
MIN_WORDS = config.MIN_WORDS
# log.debug("Takes the name of the rule every finding here belongs to, from the config")
RULE = config.LOGGER_RULE

########################################################################
#                           Local constants                            #
########################################################################
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
# log.debug("Sets the marker that starts a line comment")
COMMENT = "//"
# log.debug("Names a bracket that opens a block of code")
CODE_BLOCK = "block"
# log.debug("Names a bracket that opens a value")
LITERAL = "literal"
# log.debug("Names a brace that opens a type's body")
TYPE = "type"


########################################################################
#                         Script logger lines                          #
########################################################################
# log.debug("Defines which lines of a file hold script code")
def script_lines(path: str | None = None, source: str | None = None) -> list[tuple[int, str]]:
    """Returns (line number, text) for each line of script code.

    Args:
        path: The file's path from the repository root, whose
            extension says whether it is an Astro component. Required.
        source: The file's text. Required.

    Returns:
        Every line of a plain script, numbered from 1; for an Astro
        component, only the lines between its two fences, and none
        when it has no frontmatter.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
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
def statement_rows(lines: list[tuple[int, str]] | None = None) -> list[tuple[int, str]]:
    """Returns (line number, text) for each statement's first line.

    Args:
        lines: The script's numbered lines, from script_lines. Required.

    Returns:
        The number and text, indent kept, of each line that starts a
        statement, in file order.
    """
    # log.debug("Takes the lines, which the caller must give")
    lines = required(lines=lines)
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
def _code_only(line: str | None = None) -> str:
    """Returns the line with strings blanked and comments removed.

    Args:
        line: The line, stripped of its indent. Required.

    Returns:
        The line's code, each string emptied and any trailing //
        comment cut.
    """
    # log.debug("Takes the line, which the caller must give")
    line = required(line=line)
    # log.debug("Replaces each string with an empty pair of quotes")
    blanked = STRING_RE.sub('""', line)
    # log.debug("Cuts a trailing // comment")
    return blanked.split(COMMENT, 1)[0]


# log.debug("Defines the test for a statement start")
def _starts(
    previous: str | None = None, stack: list[str] | None = None, line: str | None = None
) -> bool:
    """Returns True when this line begins a new statement.

    Args:
        previous: The last character of the code before this line.
            Required.
        stack: The kinds of the brackets still open, innermost last.
            Required.
        line: The line, stripped of its indent. Required.

    Returns:
        True in a block of code after a line ending in ;, { or },
        unless the line continues the one before.
    """
    # log.debug("Takes the previous, which the caller must give")
    previous = required(previous=previous)
    # log.debug("Takes the stack, which the caller must give")
    stack = required(stack=stack)
    # log.debug("Takes the line, which the caller must give")
    line = required(line=line)
    # log.debug("Says no inside a value literal or type body")
    if stack and stack[-1] != CODE_BLOCK:
        # log.debug("Returns no")
        return False
    # log.debug("Says yes after an end, unless the line continues")
    return previous in ENDS and not line.startswith(CONTINUES)


# log.debug("Defines how brackets on a line update the stack")
def _track(
    code: str | None = None, stack: list[str] | None = None, line: str | None = None
) -> None:
    """Pushes each opening bracket's kind and pops each closing one.

    Args:
        code: The line's code, from _code_only. Required.
        stack: The kinds of the brackets still open, innermost last,
            changed in place. Required.
        line: The line, stripped of its indent, whose start shows a
            type declaration. Required.
    """
    # log.debug("Takes the code, which the caller must give")
    code = required(code=code)
    # log.debug("Takes the stack, which the caller must give")
    stack = required(stack=stack)
    # log.debug("Takes the line, which the caller must give")
    line = required(line=line)
    # log.debug("Walks the line's characters with their positions")
    for index, char in enumerate(code):
        # log.debug("Pops the innermost bracket on a closer")
        if char in "}])" and stack:
            # log.debug("Removes the innermost open bracket")
            stack.pop()
        # log.debug("Pushes the kind of each opening bracket")
        if char in "{[(":
            # log.debug("Notes whether the bracket sits inside a call, array or object")
            inside = bool(stack) and stack[-1] != CODE_BLOCK
            # log.debug("Classifies the bracket from the code before it")
            stack.append(_kind(char, code[:index], line, inside=inside))


# log.debug("Defines what kind of bracket an opener is")
def _kind(
    char: str | None = None,
    before: str | None = None,
    line: str | None = None,
    *,
    inside: bool | None = None,
) -> str:
    """Returns block for a code block, else type or literal.

    Inside a call, array or object, a { opens an object unless it
    follows => or ) and so opens a callback's body.

    Args:
        char: The opening bracket: {, [ or (. Required.
        before: The line's code before the bracket. Required.
        line: The line, stripped of its indent, whose start shows a
            type declaration. Required.
        inside: True when the bracket sits inside a call, array or
            object. Required.

    Returns:
        The bracket's kind: block, type or literal.
    """
    # log.debug("Takes the bracket, which the caller must give")
    char = required(char=char)
    # log.debug("Takes the text before it, which the caller must give")
    before = required(before=before)
    # log.debug("Takes the line, which the caller must give")
    line = required(line=line)
    # log.debug("Takes whether it sits inside a value, which the caller must give")
    inside = required(inside=inside)
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
        return CODE_BLOCK if CALLBACK_BEFORE.search(before.rstrip()) else LITERAL
    # log.debug("Returns block when the code before reads like one")
    return CODE_BLOCK if BLOCK_BEFORE.search(before.rstrip()) else LITERAL


# log.debug("Defines the logger-line rule for one script file")
def check_logger_lines(path: str | None = None, source: str | None = None) -> list[Finding]:
    """Checks every statement has a logger line directly above it.

    Args:
        path: The file's path from the repository root. Required.
        source: The file's text. Required.

    Returns:
        A finding for each statement with no logger line directly
        above it at its indent, and for each description too short to
        say what the line does.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
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
        match = LOGGER_RE.match(by_number.get(_above_doc(by_number, number), ""))
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
def check_live(path: str | None = None, source: str | None = None) -> list[Finding]:
    """Flags any logger line left switched on.

    Args:
        path: The file's path from the repository root. Required.
        source: The file's text. Required.

    Returns:
        A finding for each live logger line in the script's code.
    """
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
    # log.debug("Returns a finding for each live logger line")
    return [
        Finding(path, number, "trace-off", "logger line left on; run trace off")
        for number, text in script_lines(path, source)
        if LIVE_RE.match(text)
    ]


# log.debug("Defines which line holds a statement's logger line")
def _above_doc(by_number: dict[int, str] | None = None, number: int = 1) -> int:
    """Returns the number of the line a statement's logger line sits on.

    It is the line directly above the statement, or, when a TSDoc block
    sits there, the line directly above the block.

    Args:
        by_number: The file's lines by number. Required.
        number: The statement's first line, counted from 1.

    Returns:
        The number of the line to read the logger line from.
    """
    # log.debug("Takes the lines, which the caller must give")
    by_number = required(by_number=by_number)
    # log.debug("Starts at the line directly above the statement")
    above = number - 1
    # log.debug("Returns that line unless it closes a doc block")
    if not by_number.get(above, "").strip().endswith("*/"):
        # log.debug("Returns the line above")
        return above
    # log.debug("Walks up to the line that opens the block")
    while above > 0 and not by_number.get(above, "").strip().startswith("/**"):
        # log.debug("Moves up one line")
        above -= 1
    # log.debug("Returns the line above the block")
    return above - 1
