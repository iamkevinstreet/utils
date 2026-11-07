########################################################################
#                                                                      #
#                    evals/tests/test_eval_spans.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Tests an evaluation run's spans: one per case, holding the case's model
calls and its scores, a failing case marked failed, and the run's spans
written beside its results when the settings ask.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

# Third-party
import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

# Local
from kds.args import required
from kds.evals.case import EvalCase
from kds.evals.runner import RunResult, run_eval
from kds.llm.adapter import ModelAdapter
from kds.llm.fake import FakeProvider
from kds.settings import get_settings

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Names the run every test makes")
RUN = "spanned"


########################################################################
#                                                                      #
#                        Evaluation span tests                         #
#                                                                      #
########################################################################
# log.debug("Defines the run every test makes")
def _run(out_dir: Path | None = None) -> RunResult:
    """Runs two cases: c1 answers and scores, c2 fails.

    Args:
        out_dir: The folder the result files go in. Required.

    Returns:
        The run.
    """
    # log.debug("Takes the folder, which the caller must give")
    out_dir = required(out_dir=out_dir)
    # log.debug("Builds an adapter on a fake that answers once")
    adapter = ModelAdapter(FakeProvider(["ok"]), model="fake-model")

    # log.debug("Defines the system under test")
    def system_fn(case: EvalCase | None = None) -> Any:
        """Calls the model for c1 and fails for c2.

        Args:
            case: The case to answer. Required.

        Returns:
            The model's answer.
        """
        # log.debug("Takes the case, which the caller must give")
        case = required(case=case)
        # log.debug("Fails on the second case")
        if case.id == "c2":
            # log.debug("Raises, as a broken system would")
            raise RuntimeError("broken")
        # log.debug("Returns the model's answer")
        return adapter.complete("hi").text

    # log.debug("Runs both cases")
    return run_eval(
        name=RUN,
        cases=[EvalCase(id="c1", input={}, tags=["clean"]), EvalCase(id="c2", input={})],
        adapter=adapter,
        system_fn=system_fn,
        scorer_fn=lambda c, o: {"right": o == "ok", "words": 1},
        out_dir=out_dir,
    )


# log.debug("Defines the test that each case is a span with its scores")
def test_each_case_is_a_span_with_its_scores(spans: InMemorySpanExporter, tmp_path: Path) -> None:
    """c1's span holds its model call, its scores and the session.

    Args:
        spans: The spans this test records.
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Runs the two cases")
    _run(tmp_path)
    # log.debug("Finds each span by name")
    named = {s.name: s for s in spans.get_finished_spans()}
    # log.debug("Takes the first case's span and its model call")
    case, call = named["eval c1"], named["chat fake-model"]
    # log.debug("Reads the case span's attributes")
    found = dict(case.attributes or {})
    # log.debug("Checks the model call sits inside the case")
    assert call.parent is not None and call.parent.span_id == case.context.span_id
    # log.debug("Checks the scores, the outcome and the session")
    assert (found["kds.eval.score.right"], found["kds.eval.ok"]) == (True, True)
    # log.debug("Checks the session names the run")
    assert str(found["session.id"]).startswith(f"{RUN}-")
    # log.debug("Checks each score is an evaluation result")
    assert [e.attributes["gen_ai.evaluation.name"] for e in case.events if e.attributes] == [
        "right",
        "words",
    ]


# log.debug("Defines the test that a failing case is marked failed")
def test_a_failing_case_is_marked_failed(spans: InMemorySpanExporter, tmp_path: Path) -> None:
    """c2's span failed, naming the error's type.

    Args:
        spans: The spans this test records.
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Runs the two cases")
    _run(tmp_path)
    # log.debug("Finds the second case's span")
    (case,) = [s for s in spans.get_finished_spans() if s.name == "eval c2"]
    # log.debug("Checks it failed, with the error's type")
    assert (case.status.status_code, (case.attributes or {})["error.type"]) == (
        StatusCode.ERROR,
        "RuntimeError",
    )


# log.debug("Defines the test that a run writes its spans only when asked")
@pytest.mark.usefixtures("spans")
def test_a_run_writes_its_spans_when_asked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No spans file by default; one line per span with spans_keep.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        monkeypatch: pytest's helper for patching the environment.
    """
    # log.debug("Runs once with the default settings")
    _run(tmp_path / "default")
    # log.debug("Checks no spans file was written")
    assert not list((tmp_path / "default").glob("*.spans.jsonl"))
    # log.debug("Turns spans_keep on")
    monkeypatch.setenv("SPANS_KEEP", "true")
    # log.debug("Reloads the settings")
    get_settings.cache_clear()
    # log.debug("Runs again")
    _run(tmp_path / "kept")
    # log.debug("Finds the spans file")
    (path,) = (tmp_path / "kept").glob(f"{RUN}-*.spans.jsonl")
    # log.debug("Checks it holds both cases and the model call")
    assert len(path.read_text(encoding="utf-8").splitlines()) == 3
