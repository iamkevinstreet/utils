########################################################################
#                   standards/tests/test_jsrules.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the logger-line rule for scripts. A statement with no logger line
above it is a finding, and so are a one-word description and a logger
line left on. Imports and types need none; the lines of a union, an
object, a JSX tree or a template string are not statements of their
own, but a callback's body holds statements. An Astro component is
read only in its frontmatter.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Third-party
import pytest

# Local
from kds.args import required
from kds.standards.jsrules import check_live, check_logger_lines, script_lines, statement_rows

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                         Script logger lines                          #
########################################################################
# log.debug("Defines a helper that lists the lines flagged in a source")
def _flagged(source: str | None = None, path: str = "x.ts") -> list[int]:
    """Returns the line numbers the logger-line rule flags.

    Args:
        source: The script's text. Required.
        path: The path the script is checked under.

    Returns:
        The line of each finding, in order.
    """
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
    # log.debug("Returns the flagged line numbers")
    return [f.line for f in check_logger_lines(path, source)]


# log.debug("Defines the test that statements need logger lines")
def test_statements_without_logger_lines_are_flagged() -> None:
    """A statement with no logger line above it is flagged."""
    # log.debug("Builds a source with one logged and one bare statement")
    source = "// log.debug('Sets the count')\nconst a = 1;\nconst b = 2;\n"
    # log.debug("Checks only the bare statement is flagged")
    assert _flagged(source) == [3]


# log.debug("Defines the test of lines that never need a logger line")
def test_imports_types_and_cases_are_exempt() -> None:
    """Imports, type declarations and case labels need none."""
    # log.debug("Builds a source with each exempt kind")
    source = "import { a } from 'a';\nexport type T = string;\ninterface I {\n  x: number;\n}\n"
    # log.debug("Checks nothing is flagged")
    assert _flagged(source) == []


# log.debug("Defines the test that union members continue their type")
def test_multiline_union_members_are_not_statements() -> None:
    """Each `| {...}` line of a union continues the type declaration."""
    # log.debug("Builds a three-member union, one member per line")
    source = (
        "export type Part =\n"
        "  | { kind: 'a' }\n"
        "  | { kind: 'b' }\n"
        "  | { kind: 'c' };\n"
        "type Both = A &\n"
        "  B;\n"
    )
    # log.debug("Checks nothing is flagged")
    assert _flagged(source) == []


# log.debug("Defines the test that objects inside calls are not blocks")
def test_objects_inside_calls_and_arrays_are_literals() -> None:
    """A `{` on its own line inside a call or array opens an object."""
    # log.debug("Builds a call whose arguments are objects on their own lines")
    source = (
        "// log.debug('Exports the config')\n"
        "export default defineConfig(\n"
        "  { ignores: ['dist'] },\n"
        "  {\n"
        "    files: ['*.ts'],\n"
        "    rules: [\n"
        "      {\n"
        "        name: 'a',\n"
        "      },\n"
        "    ],\n"
        "  },\n"
        ");\n"
    )
    # log.debug("Checks no property line is mistaken for a statement")
    assert _flagged(source) == []


# log.debug("Defines the test that callbacks inside calls are still blocks")
def test_arrow_function_bodies_inside_calls_are_blocks() -> None:
    """Statements in a callback passed to a call need logger lines."""
    # log.debug("Builds an effect whose body has one bare statement")
    source = (
        "// log.debug('Runs once on mount')\n"
        "useEffect(() => {\n"
        "  // log.debug('Starts the timer')\n"
        "  start();\n"
        "  stop();\n"
        "}, []);\n"
    )
    # log.debug("Checks the bare statement inside the callback is flagged")
    assert _flagged(source) == [5]


# log.debug("Defines the test that JSX inside return needs no logger lines")
def test_jsx_inside_return_is_one_statement() -> None:
    """The lines of a returned JSX tree are one statement."""
    # log.debug("Builds a component returning JSX over several lines")
    source = (
        "// log.debug('Defines the view')\n"
        "export function View() {\n"
        "  // log.debug('Returns the markup')\n"
        "  return (\n"
        "    <div>\n"
        "      {items.map((item) => (\n"
        "        <p key={item}>{item}</p>\n"
        "      ))}\n"
        "    </div>\n"
        "  );\n"
        "}\n"
    )
    # log.debug("Checks nothing is flagged")
    assert _flagged(source, "View.tsx") == []


# log.debug("Defines the test that a short description is flagged")
def test_one_word_descriptions_are_flagged() -> None:
    """A logger line says what the line does, in two words or more."""
    # log.debug("Builds a statement under a one-word logger line")
    found = check_logger_lines("x.ts", "// log.debug('Asks')\nask();\n")
    # log.debug("Checks the description finding")
    assert [(f.line, f.message) for f in found] == [(1, "describe what the line does")]


# log.debug("Defines the test that Astro checks only its frontmatter")
def test_astro_checks_only_the_frontmatter() -> None:
    """Markup below the frontmatter fence is not script code."""
    # log.debug("Builds a component with one statement and markup")
    source = "---\n// log.debug('Reads the title')\nconst t = 'x';\n---\n<h1>{t}</h1>\n"
    # log.debug("Checks only the frontmatter lines are script lines")
    assert [text for _, text in script_lines("A.astro", source)] == [
        "// log.debug('Reads the title')",
        "const t = 'x';",
    ]


# log.debug("Defines the test that live logger lines are caught")
@pytest.mark.parametrize(
    ("line", "count"), [("  log.debug('On');", 1), ("  // log.debug('Off')", 0)]
)
def test_live_logger_lines_are_flagged(line: str, count: int) -> None:
    """A logger line left on is a finding; a commented one is not.

    Args:
        line: A script line, live or commented out.
        count: How many findings the line should give.
    """
    # log.debug("Checks the count")
    assert len(check_live("x.ts", line + "\n")) == count


# log.debug("Defines the test that template strings hide their contents")
def test_template_strings_are_not_parsed() -> None:
    """Lines inside a multi-line template string are not statements."""
    # log.debug("Builds a template string spanning lines")
    source = "// log.debug('Builds the text')\nconst t = `a;\nb {\n}`;\n"
    # log.debug("Checks only the declaration starts a statement")
    assert [n for n, _ in statement_rows(script_lines("x.ts", source))] == [2]
