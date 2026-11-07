########################################################################
#                                                                      #
#                    llm/tests/test_genai_spans.py                     #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Tests the spans the adapter opens for model and embedding calls, and
the agent, tool and search spans a project opens: their names, their
GenAI attributes, and content recorded only when asked for.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging

# Third-party
import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

# Local
from kds.args import required
from kds.llm.adapter import ModelAdapter
from kds.llm.errors import TransientError
from kds.llm.fake import FakeProvider
from kds.llm.spans import agent, documents, retrieval, tool, tool_result
from kds.llm.types import Completion
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
# log.debug("Names the model the fake answers as")
FAKE_MODEL = "fake-model"
# log.debug("Names the attribute that holds the operation")
OPERATION = "gen_ai.operation.name"


########################################################################
#                                                                      #
#                           GenAI span tests                           #
#                                                                      #
########################################################################
# log.debug("Defines a provider that fails before it answers")
class Flaky(FakeProvider):
    """Raises `error` for the first `failures` calls, then answers."""

    # log.debug("Defines the constructor")
    def __init__(self, failures: int | None = None, error: Exception | None = None) -> None:
        """Scripts `failures` failures, then the answer "ok".

        Args:
            failures: How many calls fail before one answers.
                Required.
            error: The error each failing call raises. Required.
        """
        # log.debug("Takes the failure count, which the caller must give")
        failures = required(failures=failures)
        # log.debug("Takes the error, which the caller must give")
        error = required(error=error)
        # log.debug("Scripts the answer that comes after the failures")
        super().__init__(["ok"])
        # log.debug("Keeps the failures left")
        self.failures = failures
        # log.debug("Keeps the error")
        self.error = error

    # log.debug("Defines a call that fails while failures remain")
    def complete(self, **request: object) -> Completion:  # type: ignore[override]
        """Raises while failures remain, then answers normally.

        Args:
            **request: The call's keyword arguments, passed on.

        Returns:
            The plain fake's completion, once the failures run out.
        """
        # log.debug("Fails while failures remain")
        if self.failures:
            # log.debug("Counts one failure off")
            self.failures -= 1
            # log.debug("Raises the scripted error")
            raise self.error
        # log.debug("Answers as the plain fake does")
        return super().complete(**request)  # type: ignore[arg-type]


# log.debug("Defines the adapter the tests call")
def _adapter(provider: FakeProvider | None = None) -> ModelAdapter:
    """Returns an adapter on `provider` whose retries do not wait.

    Args:
        provider: The fake provider. Required.

    Returns:
        The adapter, on the fake model.
    """
    # log.debug("Takes the provider, which the caller must give")
    provider = required(provider=provider)
    # log.debug("Returns the adapter")
    return ModelAdapter(provider, model=FAKE_MODEL, sleep=lambda _: None)


# log.debug("Defines the test that a model call is a chat span")
def test_a_call_is_a_chat_span(spans: InMemorySpanExporter) -> None:
    """One call: a client span with the GenAI names, and no content.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Makes one call")
    _adapter(FakeProvider(["ok"])).complete("hi", system="be brief")
    # log.debug("Takes the one span")
    (span,) = spans.get_finished_spans()
    # log.debug("Reads its attributes")
    found = dict(span.attributes or {})
    # log.debug("Checks its name, kind and GenAI attributes")
    assert (span.name, span.kind) == (f"chat {FAKE_MODEL}", SpanKind.CLIENT)
    # log.debug("Checks the operation, provider and models")
    assert {k: found[k] for k in (OPERATION, "gen_ai.provider.name", "gen_ai.request.model")} == {
        OPERATION: "chat",
        "gen_ai.provider.name": "fake",
        "gen_ai.request.model": FAKE_MODEL,
    }
    # log.debug("Checks the tokens are there and the content is not")
    assert "gen_ai.usage.input_tokens" in found and "gen_ai.input.messages" not in found


# log.debug("Defines the test that content is recorded only when asked for")
def test_content_is_recorded_when_asked(
    spans: InMemorySpanExporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With spans_content on, the prompt and the answer are recorded.

    Args:
        spans: The spans this test records.
        monkeypatch: pytest's helper for patching the environment.
    """
    # log.debug("Turns content on")
    monkeypatch.setenv("SPANS_CONTENT", "true")
    # log.debug("Reloads the settings")
    get_settings.cache_clear()
    # log.debug("Makes one call")
    _adapter(FakeProvider(["ok"])).complete("hi", system="be brief")
    # log.debug("Reads the span's attributes")
    found = dict(spans.get_finished_spans()[0].attributes or {})
    # log.debug("Reads the conversation sent")
    sent = json.loads(str(found["gen_ai.input.messages"]))
    # log.debug("Checks the turn, the system prompt and the answer")
    assert sent == [{"role": "user", "parts": [{"type": "text", "content": "hi"}]}]
    # log.debug("Checks the system prompt and the answer were recorded")
    assert "be brief" in str(found["gen_ai.system_instructions"])
    # log.debug("Checks the answer")
    assert '"content": "ok"' in str(found["gen_ai.output.messages"])


# log.debug("Defines the test that retries are recorded on the call")
def test_retries_are_events_on_the_call(spans: InMemorySpanExporter) -> None:
    """Two transient failures: one chat span with two retry events.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Makes a call that fails twice before it answers")
    _adapter(Flaky(2, TransientError("overloaded"))).complete("hi")
    # log.debug("Takes the one span")
    (span,) = spans.get_finished_spans()
    # log.debug("Checks the two retries")
    assert [event.name for event in span.events] == ["retry", "retry"]


# log.debug("Defines the test that a failed call is marked by type")
def test_a_failed_call_is_marked_by_type(spans: InMemorySpanExporter) -> None:
    """A call that cannot succeed: a failed span naming the error type.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Expects the error")
    with pytest.raises(ValueError, match="bad"):
        # log.debug("Makes a call that fails for good")
        _adapter(Flaky(1, ValueError("bad"))).complete("hi")
    # log.debug("Takes the one span")
    (span,) = spans.get_finished_spans()
    # log.debug("Checks it failed, with the error's type")
    assert (span.status.status_code, (span.attributes or {})["error.type"]) == (
        StatusCode.ERROR,
        "ValueError",
    )


# log.debug("Defines the test of agent, tool and search spans")
def test_agent_tool_and_search_spans_nest(spans: InMemorySpanExporter) -> None:
    """An agent's tool call and search sit inside its span.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Runs an agent that calls a tool and searches")
    with agent("intake", model=FAKE_MODEL):
        # log.debug("Calls a tool")
        with tool("search_clients", call_id="t1", arguments={"name": "Acme"}) as call:
            # log.debug("Records what the tool returned")
            tool_result(call, ["c1"])
        # log.debug("Searches the library for passages")
        with retrieval("overtime", top_k=3, source="library") as search:
            # log.debug("Records what the search found")
            documents(search, [("p1", 0.9)])
    # log.debug("Takes the spans; the agent's ends last")
    used, searched, ran = spans.get_finished_spans()
    # log.debug("Checks the names")
    assert [s.name for s in (used, searched, ran)] == [
        "execute_tool search_clients",
        "retrieval",
        "invoke_agent intake",
    ]
    # log.debug("Checks the tool and the search sit inside the agent's span")
    assert {s.parent.span_id for s in (used, searched) if s.parent} == {ran.context.span_id}
    # log.debug("Checks the tool's arguments stayed out, content being off")
    assert "gen_ai.tool.call.arguments" not in (used.attributes or {})
    # log.debug("Checks what the search found, by id and score")
    assert json.loads(str((searched.attributes or {})["gen_ai.retrieval.documents"])) == [
        {"id": "p1", "score": 0.9}
    ]


# log.debug("Defines the test that an embedding call is a span")
def test_an_embedding_call_is_a_span(spans: InMemorySpanExporter) -> None:
    """Embedding two texts opens one embeddings span.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Embeds two texts")
    _adapter(FakeProvider()).embed(["a", "b"], model="vectors")
    # log.debug("Takes the one span")
    (span,) = spans.get_finished_spans()
    # log.debug("Checks its name and the number of texts")
    assert (span.name, (span.attributes or {})["texts"]) == ("embeddings vectors", 2)
