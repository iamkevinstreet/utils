########################################################################
#                                                                      #
#                       logs/tests/test_spans.py                       #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Tests spans: when they turn on, what Langfuse receives, how a step
records its work and its errors, and how a run keeps its spans.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import base64
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Third-party
import pytest
from opentelemetry import trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pydantic import SecretStr

# Local
from kds.args import required
from kds.logs import collect, new_request_id, session, setup_spans, step, write_spans
from kds.logs.spans import Stamp, build_provider, exporters_for, langfuse_exporter
from kds.logs.steps import values
from kds.settings import Settings

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
# log.debug("Lists the variables that name a standard endpoint")
OTLP_VARIABLES = ("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT")
# log.debug("Sets the made-up Langfuse keys the tests use")
KEYS = ("pk-lf-test", "sk-lf-test")
# log.debug("Sets the address the tests' local server listens on")
LOCALHOST = "127.0.0.1"


########################################################################
#                                                                      #
#                              Span tests                              #
#                                                                      #
########################################################################
# log.debug("Defines a fixture that clears the standard endpoint variables")
@pytest.fixture
def no_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removes the standard OpenTelemetry endpoint variables.

    Args:
        monkeypatch: pytest's helper for patching the environment.
    """
    # log.debug("Removes each variable")
    for name in OTLP_VARIABLES:
        # log.debug("Removes it, if it is set")
        monkeypatch.delenv(name, raising=False)


# log.debug("Defines the test that spans stay off with nowhere to go")
@pytest.mark.usefixtures("no_endpoint")
def test_spans_stay_off_without_a_destination() -> None:
    """No keys, no endpoint and no run file build no provider."""
    # log.debug("Checks that nothing is built")
    assert build_provider(Settings(_env_file=None), service="t") is None


# log.debug("Defines the test that keeping a run's spans turns them on")
@pytest.mark.usefixtures("no_endpoint")
def test_keeping_spans_alone_turns_them_on() -> None:
    """spans_keep builds a provider, named for the service."""
    # log.debug("Builds the provider with spans_keep on")
    provider = build_provider(Settings(_env_file=None, spans_keep=True), service="t", version="1")
    # log.debug("Checks it was built, for the service")
    assert provider is not None and provider.resource.attributes["service.name"] == "t"


# log.debug("Defines the test that empty keys count as unset")
@pytest.mark.usefixtures("no_endpoint")
def test_empty_langfuse_keys_count_as_unset() -> None:
    """Both keys empty, as CI sets missing secrets: no exporter."""
    # log.debug("Builds the settings with the two keys set to nothing")
    settings = Settings(_env_file=None, langfuse_public_key="", langfuse_secret_key="")
    # log.debug("Checks neither Langfuse's exporter nor a provider is built")
    assert langfuse_exporter(settings) is None and build_provider(settings, service="t") is None


# log.debug("Defines the test of the standard endpoint variables")
def test_standard_variables_add_an_exporter(monkeypatch: pytest.MonkeyPatch) -> None:
    """OTEL_EXPORTER_OTLP_ENDPOINT alone adds one exporter.

    Args:
        monkeypatch: pytest's helper for patching the environment.
    """
    # log.debug("Names an endpoint the standard way")
    monkeypatch.setenv(OTLP_VARIABLES[1], f"http://{LOCALHOST}:4318")
    # log.debug("Checks one exporter is built for it")
    assert len(exporters_for(Settings(_env_file=None))) == 1


# log.debug("Defines the test of what Langfuse receives")
def test_langfuse_gets_spans_over_otlp_with_basic_auth() -> None:
    """Langfuse's path, basic authentication and an OTLP body arrive."""
    # log.debug("Starts the list of requests the server receives")
    received: list[tuple[str, str, bytes]] = []
    # log.debug("Starts a local server that records each request")
    server = HTTPServer((LOCALHOST, 0), _recorder(received))
    # log.debug("Serves requests on a thread of its own")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    # log.debug("Points the settings at the local server, with made-up keys")
    settings = Settings(
        _env_file=None,
        langfuse_base_url=f"http://{LOCALHOST}:{server.server_port}/",
        langfuse_public_key=SecretStr(KEYS[0]),
        langfuse_secret_key=SecretStr(KEYS[1]),
    )
    # log.debug("Builds the exporter Langfuse's keys ask for")
    exporter = langfuse_exporter(settings)
    # log.debug("Builds a provider that sends each span at once")
    provider = TracerProvider()
    # log.debug("Sends spans through the exporter as they end")
    provider.add_span_processor(SimpleSpanProcessor(exporter))  # type: ignore[arg-type]
    # log.debug("Opens and closes one span")
    with provider.get_tracer("test").start_as_current_span("hello"):
        # log.debug("Does nothing inside it")
        pass
    # log.debug("Stops the provider, then the server")
    provider.shutdown()
    # log.debug("Stops serving")
    server.shutdown()
    # log.debug("Closes the server's socket")
    server.server_close()
    # log.debug("Takes the one request the server received")
    path, auth, body = received[0]
    # log.debug("Reads the body as an OTLP export request")
    request = ExportTraceServiceRequest.FromString(body)
    # log.debug("Lists the span names it carries")
    names = [s.name for r in request.resource_spans for g in r.scope_spans for s in g.spans]
    # log.debug("Checks the path, the authentication and the span")
    assert (path, auth, names) == (
        "/api/public/otel/v1/traces",
        f"Basic {base64.b64encode(':'.join(KEYS).encode()).decode()}",
        ["hello"],
    )


# log.debug("Defines the request handler the local server uses")
def _recorder(
    received: list[tuple[str, str, bytes]] | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Returns a handler that keeps each POST's path, auth and body.

    Args:
        received: The list each request is added to. Required.

    Returns:
        The handler class.
    """
    # log.debug("Takes the list, which the caller must give")
    kept = required(received=received)

    # log.debug("Defines the handler")
    class Recorder(BaseHTTPRequestHandler):
        """Answers every POST with 200 after keeping it."""

        # log.debug("Defines how a POST is handled")
        def do_POST(self) -> None:  # fixed: BaseHTTPRequestHandler's method name
            """Keeps the request's path, auth header and body."""
            # log.debug("Reads the body")
            body = self.rfile.read(int(self.headers["Content-Length"]))
            # log.debug("Keeps what the test checks")
            kept.append((self.path, self.headers["Authorization"], body))
            # log.debug("Answers that the spans arrived")
            self.send_response(200)
            # log.debug("Ends the headers")
            self.end_headers()

        # log.debug("Defines the request log, which stays quiet")
        def log_message(self, format: str, *args: object) -> None:  # fixed: its signature
            """Writes nothing, so the test output stays clean.

            Args:
                format: The message format, unused.
                *args: The message's values, unused.
            """

    # log.debug("Returns the handler class")
    return Recorder


# log.debug("Defines the test that a step nests and carries its stamps")
def test_steps_nest_and_carry_request_and_session(spans: InMemorySpanExporter) -> None:
    """An inner step's parent is the outer step; both carry the ids.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Opens a request, a session, then two steps, one inside the other")
    with new_request_id("req-7"), session("run-1"), step("outer", {"gen_ai.x": "y"}, words=3):
        # log.debug("Opens the inner step")
        with step("inner"):
            # log.debug("Does nothing inside it")
            pass
    # log.debug("Takes the spans; the inner one ends first")
    inner, outer = spans.get_finished_spans()
    # log.debug("Checks the inner step's parent is the outer one")
    assert inner.parent is not None and inner.parent.span_id == outer.context.span_id
    # log.debug("Checks the outer step's attributes and stamps")
    assert {k: outer.attributes[k] for k in ("gen_ai.x", "words", "kds.request_id")} == {
        "gen_ai.x": "y",
        "words": 3,
        "kds.request_id": "req-7",
    }
    # log.debug("Checks both carry the session")
    assert inner.attributes["session.id"] == outer.attributes["session.id"] == "run-1"


# log.debug("Defines the test of redaction and error recording")
def test_steps_redact_and_record_errors_by_type(spans: InMemorySpanExporter) -> None:
    """Personal data is redacted; an error is recorded by type only.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Expects the error to reach the caller")
    with pytest.raises(ValueError, match="person"), step("check", contact="person@example.com"):
        # log.debug("Fails inside the step")
        raise ValueError("person@example.com is not on file")
    # log.debug("Takes the one span")
    (span,) = spans.get_finished_spans()
    # log.debug("Checks the email was redacted and the error typed")
    assert (span.attributes["contact"], span.attributes["error.type"]) == ("[EMAIL]", "ValueError")
    # log.debug("Checks the span failed and holds no message")
    assert span.status.status_code == StatusCode.ERROR and not span.events


# log.debug("Defines the test of how values are converted")
def test_values_hold_what_a_span_cannot() -> None:
    """None is dropped, lists stay, tables and paths become text."""
    # log.debug("Converts one of each kind")
    found = values({"a": None, "b": [1, 2], "c": {"k": 1}, "d": [1, "x"], "e": Path("x"), "f": []})
    # log.debug("Checks each conversion; an empty list stays a list")
    assert found == {"b": [1, 2], "c": '{"k": 1}', "d": '[1, "x"]', "e": "x", "f": []}


# log.debug("Defines the test of the public flag")
def test_public_traces_are_flagged_for_langfuse() -> None:
    """With spans_public, every span opens its trace to the link."""
    # log.debug("Builds a provider that stamps spans public")
    provider = TracerProvider()
    # log.debug("Adds the stamp, public")
    provider.add_span_processor(Stamp(public=True))
    # log.debug("Records the spans in memory")
    memory = InMemorySpanExporter()
    # log.debug("Adds the recorder")
    provider.add_span_processor(SimpleSpanProcessor(memory))
    # log.debug("Opens and closes one span")
    with provider.get_tracer("test").start_as_current_span("shown"):
        # log.debug("Does nothing inside it")
        pass
    # log.debug("Checks the flag Langfuse reads")
    assert memory.get_finished_spans()[0].attributes["langfuse.trace.public"] is True


# log.debug("Defines the test of a run's kept spans")
@pytest.mark.usefixtures("spans")
def test_a_run_keeps_and_writes_its_spans(tmp_path: Path) -> None:
    """Spans ending inside collect() are kept and written as lines.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Keeps the spans of one step")
    with collect() as kept, step("kept"):
        # log.debug("Does nothing inside it")
        pass
    # log.debug("Writes them to a file")
    path = write_spans(kept, tmp_path / "run.spans.jsonl")
    # log.debug("Reads the file back, one span per line")
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    # log.debug("Checks the one span is there, by name")
    assert [line["name"] for line in lines] == ["kept"]


# log.debug("Defines the test that setup keeps a provider in use")
def test_setup_keeps_the_provider_in_use() -> None:
    """A later setup returns the provider already in use."""
    # log.debug("Checks setup returns the session's provider")
    assert setup_spans(Settings(_env_file=None), service="t") is trace.get_tracer_provider()
