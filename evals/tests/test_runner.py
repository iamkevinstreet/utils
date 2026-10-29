########################################################################
#                      evals/tests/test_runner.py                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Tests a whole run offline: scores, a failing case, the report, duplicate
ids, comparison.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

# Third-party
import pytest

# Local
from kds.args import required
from kds.evals.case import EvalCase, load_cases
from kds.evals.metrics import field_accuracy
from kds.evals.report import changelog_line, compare
from kds.evals.runner import run_eval
from kds.llm.adapter import ModelAdapter
from kds.llm.fake import FakeProvider

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the model name the price table lists at zero")
FAKE_MODEL = "fake-model"


########################################################################
#                         Evaluation run tests                         #
########################################################################
# log.debug("Defines three cases, two of them tagged hard")
def _cases() -> list[EvalCase]:
    """Returns one clean case and two hard ones.

    Returns:
        The cases c1, c2 and c3, in that order.
    """
    # log.debug("Returns the cases")
    return [
        EvalCase(id="c1", input={"doc": "A"}, expected={"name": "Acme LLC"}, tags=["clean"]),
        EvalCase(id="c2", input={"doc": "B"}, expected={"name": "Beta Inc"}, tags=["hard"]),
        EvalCase(id="c3", input={"doc": "C"}, expected={"name": "Gamma Co"}, tags=["hard"]),
    ]


# log.debug("Defines the test of a whole run")
def test_run_eval_end_to_end(tmp_path: Path) -> None:
    """One right, one wrong, one failure: scored, reported, logged.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Scripts a right answer, a wrong one and a failure")
    adapter = ModelAdapter(
        FakeProvider(['{"name": "Acme LLC"}', '{"name": "x"}', "boom"]), model=FAKE_MODEL
    )

    # log.debug("Defines the system: one call, parsed as JSON")
    def system_fn(case: EvalCase | None = None) -> Any:
        """Answers the case, failing on the scripted boom.

        Args:
            case: The case to answer. Required.

        Returns:
            The model's scripted reply, parsed as JSON.
        """
        # log.debug("Takes the case, which the caller must give")
        case = required(case=case)
        # log.debug("Calls the model with the case's document")
        text = adapter.complete(case.input["doc"]).text
        # log.debug("Fails the way a broken system would")
        if text == "boom":
            # log.debug("Raises the scripted failure")
            raise RuntimeError("provider exploded")
        # log.debug("Returns the parsed answer")
        return json.loads(text)

    # log.debug("Runs the evaluation")
    run = run_eval(
        name="demo",
        cases=_cases(),
        adapter=adapter,
        system_fn=system_fn,
        scorer_fn=lambda c, o: field_accuracy(o, c.expected, ["name"]),
        out_dir=tmp_path,
    )
    # log.debug("Checks the counts and the averaged accuracy")
    assert (run.cases, run.failures, run.summary["accuracy"]) == (3, 1, 0.5)
    # log.debug("Reads the latest report")
    report = (tmp_path / "demo-latest.md").read_text(encoding="utf-8")
    # log.debug("Checks it shows the score, the failure and the tag row")
    assert "| accuracy | 0.5 |" in report and "provider exploded" in report
    # log.debug("Checks the hard tag covers its two cases")
    assert "| hard | 2 |" in report


# log.debug("Defines the test that outputs can be left out")
def test_outputs_can_be_dropped(tmp_path: Path) -> None:
    """keep_output=False keeps scores and drops the outputs.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Runs one case, dropping its output")
    run = run_eval(
        name="lean",
        cases=_cases()[:1],
        adapter=ModelAdapter(FakeProvider()),
        system_fn=lambda c: c.expected,
        scorer_fn=lambda c, o: {"acc": 1.0},
        out_dir=tmp_path,
        keep_output=False,
    )
    # log.debug("Checks the score stayed and the output went")
    assert run.results[0].scores == {"acc": 1.0} and run.results[0].output is None


# log.debug("Defines the test that repeated ids are refused")
def test_load_cases_rejects_duplicate_ids(tmp_path: Path) -> None:
    """Two cases with one id stop the load.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Writes a file with the same id twice")
    path = tmp_path / "cases.jsonl"
    # log.debug("Writes two cases sharing an id")
    path.write_text('{"id": "a", "input": {}}\n{"id": "a", "input": {}}\n', encoding="utf-8")
    # log.debug("Expects the duplicate error")
    with pytest.raises(ValueError, match="duplicate"):
        # log.debug("Loads the file")
        load_cases(path)


# log.debug("Defines the test of the comparison table and changelog")
def test_compare_and_changelog(tmp_path: Path) -> None:
    """Two runs give a +1 change and a changelog line.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Builds an adapter both runs share")
    adapter = ModelAdapter(FakeProvider(), model=FAKE_MODEL)
    # log.debug("Runs a version that scores zero")
    before = run_eval(
        name="v1",
        cases=_cases(),
        adapter=adapter,
        system_fn=lambda c: None,
        scorer_fn=lambda c, o: {"acc": 0.0},
        out_dir=tmp_path,
    )
    # log.debug("Runs a version that scores one")
    after = run_eval(
        name="v2",
        cases=_cases(),
        adapter=adapter,
        system_fn=lambda c: None,
        scorer_fn=lambda c, o: {"acc": 1.0},
        out_dir=tmp_path,
    )
    # log.debug("Checks the comparison row")
    assert "| acc | 0 | 1 | +1 |" in compare(before, after, ["acc"])
    # log.debug("Writes the changelog line")
    line = changelog_line("v0.2", "Oct 20, 2026", "Added checks", (before, after), "acc")
    # log.debug("Checks the line")
    assert line == "- **v0.2, Oct 20, 2026.** Added checks: acc 0 -> 1."
