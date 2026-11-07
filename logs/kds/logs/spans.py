########################################################################
#                                                                      #
#                        logs/kds/logs/spans.py                        #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Spans: OpenTelemetry tracing for every project, off until there is
somewhere to send them.

A span is one timed step of the work, nested under the step that called
it. setup_spans() turns spans on when they have a destination: Langfuse,
when its keys are set; any endpoint the standard
OTEL_EXPORTER_OTLP_ENDPOINT variables name; or an evaluation run's own
file, when spans_keep is on. With none of these it sets nothing, and
every span is a no-op.

Each span carries the request id of the work it belongs to, so a log
line and a span can be matched, and the session it ran in, which
Langfuse shows as one session.

Usage, once when a service or a run starts:
    setup_spans(settings, service="grounded-qa", version=__version__)
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import base64
import contextvars
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

# Third-party
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

# Local
from kds.args import required
from kds.logs.request import current_request_id
from kds.logs.steps import KEEPER
from kds.settings import Settings, get_settings

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
# log.debug("Holds the session the work running now belongs to")
_SESSION: contextvars.ContextVar[str | None] = contextvars.ContextVar("session", default=None)
# log.debug("Names the attribute that carries a span's request id")
REQUEST_ID: Final = "kds.request_id"
# log.debug("Names the attribute Langfuse groups a session's traces by")
SESSION_ID: Final = "session.id"
# log.debug("Names the attribute that opens a trace to anyone with its link")
PUBLIC: Final = "langfuse.trace.public"
# log.debug("Sets the path Langfuse takes OpenTelemetry spans on")
LANGFUSE_PATH: Final = "/api/public/otel/v1/traces"
# log.debug("Lists the variables that name a standard OpenTelemetry endpoint")
OTLP_VARIABLES: Final = ("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT")
# log.debug("Sets how long a flush may wait for the exporters, in ms")
FLUSH_MS = 30_000


########################################################################
#                                                                      #
#                                Spans                                 #
#                                                                      #
########################################################################
# log.debug("Defines the processor that stamps each span as it starts")
class Stamp(SpanProcessor):
    """Stamps each span with its request id, session and visibility."""

    # log.debug("Defines the constructor")
    def __init__(self, public: bool = False) -> None:
        """Keeps whether traces are open to anyone with their link.

        Args:
            public: True to mark each trace public in Langfuse.
        """
        # log.debug("Keeps the visibility")
        self.public = public

    # log.debug("Defines what happens as each span starts")
    def on_start(  # fixed: SpanProcessor's signature
        self, span: Span, parent_context: Context | None = None
    ) -> None:
        """Sets the request id, the session if any, and visibility.

        Args:
            span: The span that is starting.
            parent_context: The context it starts in; unused.
        """
        # log.debug("Sets the request id of the work the span belongs to")
        span.set_attribute(REQUEST_ID, current_request_id())
        # log.debug("Reads the session the work runs in, if any")
        session = _SESSION.get()
        # log.debug("Sets the session when there is one")
        if session is not None:
            # log.debug("Sets it as Langfuse reads it")
            span.set_attribute(SESSION_ID, session)
        # log.debug("Opens the trace to its link when the settings ask")
        if self.public:
            # log.debug("Sets the flag Langfuse reads")
            span.set_attribute(PUBLIC, True)


# log.debug("Defines the one-time setup of spans for a process")
def setup_spans(
    settings: Settings | None = None, *, service: str | None = None, version: str = ""
) -> TracerProvider | None:
    """Turns spans on for the process when they have a destination.

    Safe to call more than once: once spans are on, later calls return
    the provider already in use and change nothing.

    Args:
        settings: The settings; the shared ones by default.
        service: The name the spans are recorded under, such as
            "grounded-qa". Required.
        version: The service's version.

    Returns:
        The provider in use, or None when spans have no destination.
    """
    # log.debug("Takes the service name, which the caller must give")
    service = required(service=service)
    # log.debug("Finds the provider already in use, if any")
    current = trace.get_tracer_provider()
    # log.debug("Keeps it when spans are on already")
    if isinstance(current, TracerProvider):
        # log.debug("Returns the provider in use")
        return current
    # log.debug("Builds a provider for wherever the spans go")
    provider = build_provider(settings or get_settings(), service=service, version=version)
    # log.debug("Puts it in use when there is somewhere to send spans")
    if provider is not None:
        # log.debug("Sets it for the whole process")
        trace.set_tracer_provider(provider)
    # log.debug("Returns the provider, or None when spans stay off")
    return provider


# log.debug("Defines how a provider is built from the settings")
def build_provider(
    settings: Settings | None = None, *, service: str | None = None, version: str = ""
) -> TracerProvider | None:
    """Returns a provider for the destinations the settings name.

    Args:
        settings: The settings. Required.
        service: The name the spans are recorded under. Required.
        version: The service's version.

    Returns:
        The provider, or None when the settings name no destination.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the service name, which the caller must give")
    service = required(service=service)
    # log.debug("Builds an exporter for each destination the settings name")
    exporters = exporters_for(settings)
    # log.debug("Stops when there is nowhere to send spans")
    if not exporters and not settings.spans_keep:
        # log.debug("Returns None, so spans stay off")
        return None
    # log.debug("Names the service and version every span is recorded under")
    resource = Resource.create({SERVICE_NAME: service, SERVICE_VERSION: version})
    # log.debug("Creates the provider")
    provider = TracerProvider(resource=resource)
    # log.debug("Stamps each span with its request id, session and visibility")
    provider.add_span_processor(Stamp(public=settings.spans_public))
    # log.debug("Sends spans to each destination in batches")
    for exporter in exporters:
        # log.debug("Adds a batching processor for the exporter")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    # log.debug("Lets evaluation runs keep their spans when the settings ask")
    if settings.spans_keep:
        # log.debug("Adds the keeper")
        provider.add_span_processor(KEEPER)
    # log.debug("Logs where spans go, never a key")
    log.info("spans on for %s: %d exporters", service, len(exporters))
    # log.debug("Returns the provider")
    return provider


# log.debug("Defines the exporters the settings ask for")
def exporters_for(settings: Settings | None = None) -> list[SpanExporter]:
    """Returns an exporter for Langfuse and one for a standard endpoint.

    Args:
        settings: The settings. Required.

    Returns:
        The exporters: Langfuse's when its keys are set, and the
        standard one when an OTEL_EXPORTER_OTLP endpoint variable is
        set; empty when neither is.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Starts with no exporters")
    exporters: list[SpanExporter] = []
    # log.debug("Builds Langfuse's exporter when both keys are set")
    langfuse = langfuse_exporter(settings)
    # log.debug("Adds it when there is one")
    if langfuse is not None:
        # log.debug("Adds Langfuse's exporter")
        exporters.append(langfuse)
    # log.debug("Adds the standard exporter when its endpoint is named")
    if any(os.environ.get(name) for name in OTLP_VARIABLES):
        # log.debug("Builds it from the standard variables")
        exporters.append(OTLPSpanExporter())
    # log.debug("Returns the exporters")
    return exporters


# log.debug("Defines the exporter that sends spans to Langfuse")
def langfuse_exporter(settings: Settings | None = None) -> OTLPSpanExporter | None:
    """Returns an exporter to Langfuse's OpenTelemetry endpoint.

    Langfuse takes spans over OTLP on HTTP, with the public and secret
    keys as basic authentication.

    Args:
        settings: The settings, with the keys and the address.
            Required.

    Returns:
        The exporter, or None unless both keys are set.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Reads the two keys")
    public, secret = settings.langfuse_public_key, settings.langfuse_secret_key
    # log.debug("Stops unless both are set")
    if public is None or secret is None:
        # log.debug("Returns None, so Langfuse gets nothing")
        return None
    # log.debug("Joins the keys as basic authentication expects")
    pair = f"{public.get_secret_value()}:{secret.get_secret_value()}".encode()
    # log.debug("Returns the exporter for Langfuse's endpoint")
    return OTLPSpanExporter(
        endpoint=settings.langfuse_base_url.rstrip("/") + LANGFUSE_PATH,
        headers={"Authorization": f"Basic {base64.b64encode(pair).decode()}"},
    )


# log.debug("Defines the block whose spans share a session")
@contextmanager
def session(value: str | None = None) -> Iterator[str]:
    """Stamps every span started inside the block with one session id.

    Args:
        value: The session id, such as an evaluation run's name and
            start time. Required.

    Yields:
        The session id.
    """
    # log.debug("Takes the session id, which the caller must give")
    value = required(value=value)
    # log.debug("Sets it for this context, keeping a token to undo it")
    token = _SESSION.set(value)
    # log.debug("Runs the block, restoring the old session however it ends")
    try:
        # log.debug("Hands the session id to the block")
        yield value
    finally:
        # log.debug("Restores the session that was there before")
        _SESSION.reset(token)


# log.debug("Defines the wait for spans still being sent")
def flush_spans(timeout_ms: int = FLUSH_MS) -> bool:
    """Sends every finished span still waiting in a batch.

    A run calls this before it exits, so its last spans are not lost.

    Args:
        timeout_ms: How long to wait for the exporters.

    Returns:
        True when everything was sent, or spans are off.
    """
    # log.debug("Finds the provider in use")
    provider = trace.get_tracer_provider()
    # log.debug("Returns at once when spans are off")
    if not isinstance(provider, TracerProvider):
        # log.debug("Returns that there was nothing to send")
        return True
    # log.debug("Waits for the batches and returns whether they went")
    return provider.force_flush(timeout_ms)
