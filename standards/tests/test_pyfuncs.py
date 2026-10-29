########################################################################
#                   standards/tests/test_pyfuncs.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests the function rules: every parameter has a default unless a
framework fills it; the doc block opens with a sentence, lists every
parameter and says what comes back; and Required in the doc block
matches required() or a missing() guard in the body.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import ast
import logging
import textwrap

# Local
from kds.standards import pyfuncs
from kds.standards.findings import Finding

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets a function that follows every rule")
GOOD = textwrap.dedent(
    '''\
    def due(notice: date | None = None, days: int = 30) -> date:
        """Returns the day a response is due.

        Args:
            notice: The notice's date. Required.
            days: How many days the respondent has.

        Returns:
            The due date.
        """
        notice = required(notice=notice)
        return notice + timedelta(days=days)
    '''
)


########################################################################
#                            Function tests                            #
########################################################################
# log.debug("Defines how a source's function findings are worked out")
def messages(source: str = "") -> list[str]:
    """Returns the messages of the function findings for some source.

    Args:
        source: The Python source to check.

    Returns:
        Each finding's message, in order.
    """
    # log.debug("Checks the source's functions")
    found: list[Finding] = pyfuncs.check_functions("m.py", ast.parse(source), source.splitlines())
    # log.debug("Returns the messages")
    return [f.message for f in found]


# log.debug("Defines the test: a function that follows the rules has no findings")
def test_a_good_function_has_no_findings() -> None:
    """Defaults, doc block and required() all agree."""
    # log.debug("Checks there are no findings")
    assert messages(GOOD) == []


# log.debug("Defines the test: a parameter with no default is a finding")
def test_a_parameter_with_no_default_is_a_finding() -> None:
    """A required parameter without a None default is flagged."""
    # log.debug("Drops the notice's default")
    bare = GOOD.replace("notice: date | None = None", "notice: date")
    # log.debug("Checks the finding asks for a default")
    assert "give notice a default: None where there is no natural one" in messages(bare)


# log.debug("Defines the test: framework-filled functions keep their parameters")
def test_framework_functions_keep_their_parameters() -> None:
    """Fixtures, routes, tests and fixed signatures need no defaults."""
    # log.debug("Builds four functions a framework or a library fills")
    source = textwrap.dedent(
        '''\
        @pytest.fixture
        def client(tmp_path: Path) -> Client:
            """Builds a client.

            Args:
                tmp_path: A folder.

            Returns:
                The client.
            """

        @router.get("/x")
        def route(request: Request) -> dict[str, str]:
            """Answers.

            Args:
                request: The request.

            Returns:
                The answer.
            """

        def test_it(client: Client) -> None:
            """Tests it.

            Args:
                client: The client.
            """

        class Quiet(Filter):
            """Keeps quiet."""

            def filter(self, record: LogRecord) -> bool:  # fixed: logging.Filter's signature
                """Filters.

                Args:
                    record: The record.

                Returns:
                    Whether to keep it.
                """
        '''
    )
    # log.debug("Checks none of them is asked for a default")
    assert messages(source) == []


# log.debug("Defines the test: each doc block problem is a finding")
def test_each_doc_block_problem_is_a_finding() -> None:
    """A run-on summary, a missing entry, no Returns, a placeholder."""
    # log.debug("Breaks the doc block four ways")
    broken = (
        GOOD.replace(
            "Returns the day a response is due.", "Returns the day\n    a response is due"
        )
        .replace("        days: How many days the respondent has.\n", "")
        .replace("\n    Returns:\n        The due date.\n", "\n")
        .replace("The notice's date.", "TODO.")
    )
    # log.debug("Reads the messages")
    found = messages(broken)
    # log.debug("Checks each problem is named")
    assert {
        "end the doc block's first line with a full stop",
        "leave a blank line after the first line",
        "Args must list, in order: notice, days",
        "say what comes back under Returns:",
        "replace each TODO with a description",
    } <= set(found)


# log.debug("Defines the test: Required without required() is a finding")
def test_required_without_required_call_is_a_finding() -> None:
    """A parameter called Required must be taken with required()."""
    # log.debug("Removes the required() call")
    untaken = GOOD.replace("    notice = required(notice=notice)\n", "")
    # log.debug("Checks the finding names the parameter")
    assert "notice is called Required; take it with required()" in messages(untaken)


# log.debug("Defines the test: a missing() guard takes a union-typed parameter")
def test_a_missing_guard_takes_a_parameter() -> None:
    """The guard form counts as taking the parameter."""
    # log.debug("Replaces required() with the guard")
    guarded = GOOD.replace(
        "    notice = required(notice=notice)\n",
        "    if notice is None:\n        raise missing(notice=notice)\n",
    )
    # log.debug("Checks there are no findings")
    assert messages(guarded) == []


# log.debug("Defines the test: a stub may call a parameter Required")
def test_a_stub_may_call_a_parameter_required() -> None:
    """An interface's stub documents what implementations must take."""
    # log.debug("Turns the body into a stub")
    stub = GOOD.replace(
        "    notice = required(notice=notice)\n    return notice + timedelta(days=days)\n",
        "    ...\n",
    )
    # log.debug("Checks there are no findings")
    assert messages(stub) == []


# log.debug("Defines the test: a function may run 60 lines below its doc block, not 61")
def test_a_function_runs_at_most_sixty_lines_below_its_doc_block() -> None:
    """Every line below the doc block counts, up to 60."""
    # log.debug("Pads the good function to exactly 60 lines below its doc block")
    fits = GOOD.replace(
        "    notice = required(notice=notice)\n",
        "    notice = required(notice=notice)\n" + '    # log.debug("Waits")\n' * 58,
    )
    # log.debug("Adds one more line")
    long = fits.replace("    return notice", '    # log.debug("Returns")\n    return notice')
    # log.debug("Checks only the longer one is flagged, with its count")
    assert (messages(fits), messages(long)) == (
        [],
        ["due runs 61 lines below its doc block; at most 60, so split it"],
    )


# log.debug("Defines the test: with no doc block, the comments above the body count")
def test_a_function_with_no_doc_block_counts_from_its_first_comment() -> None:
    """The comments above the first statement count as its lines."""
    # log.debug("Writes a test with 61 lines below its signature, comments first")
    source = "def test_long() -> None:\n" + '    # log.debug("Waits")\n' * 60 + "    pass\n"
    # log.debug("Checks it is flagged with all 61 lines, besides its missing doc block")
    assert messages(source) == [
        "test_long needs a doc block",
        "test_long runs 61 lines below its doc block; at most 60, so split it",
    ]
