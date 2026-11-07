########################################################################
#                                                                      #
#                  llm/tests/test_anthropic_spans.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Tests that a call through the Anthropic SDK records only the adapter's
chat span. The SDK's own span, which repeats the call with the
account's ids, is off, and no trace header leaves with the request.
The API is a stand-in on the client's own transport, so nothing leaves
the machine.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Third-party
import anthropic
import httpx2
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Local
from kds.args import required
from kds.llm.adapter import ModelAdapter
from kds.llm.anthropic_provider import AnthropicProvider

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
# log.debug("Names the model every test calls")
MODEL = "claude-sonnet-5-5"
# log.debug("Sets the key the stand-in accepts, which is no real key")
KEY = "test-key"
# log.debug("Names the header that carries a trace id to another service")
TRACEPARENT = "traceparent"
# log.debug("Names the span the SDK opens for each call when its spans are on")
SDK_SPAN = "anthropic.messages.create"
# log.debug("Sets the stand-in's answer, in the Messages API's shape")
REPLY = {
    "id": "msg_test",
    "type": "message",
    "role": "assistant",
    "model": MODEL,
    "content": [{"type": "text", "text": "ok"}],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 3, "output_tokens": 1},
}


########################################################################
#                                                                      #
#                         Anthropic span tests                         #
#                                                                      #
########################################################################
# log.debug("Defines a transport that answers every call as the API would")
def _stand_in(sent: list[httpx2.Request] | None = None) -> httpx2.Client:
    """Returns an HTTP client whose every request gets REPLY.

    Args:
        sent: The list each request is added to. Required.

    Returns:
        The client, which never reaches the network.
    """
    # log.debug("Takes the list of requests, which the caller must give")
    sent = required(sent=sent)

    # log.debug("Defines the answer to one request")
    def answer(request: httpx2.Request | None = None) -> httpx2.Response:
        """Keeps the request and answers it.

        Args:
            request: The request the client sent. Required.

        Returns:
            REPLY, with status 200.
        """
        # log.debug("Takes the request, which the caller must give")
        request = required(request=request)
        # log.debug("Keeps it, for the test to read")
        sent.append(request)
        # log.debug("Answers as the API would")
        return httpx2.Response(200, json=REPLY)

    # log.debug("Returns a client on that transport")
    return httpx2.Client(transport=httpx2.MockTransport(answer))


# log.debug("Defines the test that a plain client records its own span")
def test_a_plain_client_records_its_own_span(spans: InMemorySpanExporter) -> None:
    """The SDK's default: its own span and a trace header per call.

    This is what the provider turns off; without it, the next test
    would pass whatever the provider did.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Starts the list of requests sent")
    sent: list[httpx2.Request] = []
    # log.debug("Opens a client with the SDK's defaults, on the stand-in")
    client = anthropic.Anthropic(api_key=KEY, http_client=_stand_in(sent), max_retries=0)
    # log.debug("Makes one call")
    client.messages.create(
        model=MODEL, max_tokens=16, messages=[{"role": "user", "content": "hi"}]
    )
    # log.debug("Checks the SDK opened its span and sent a trace header")
    assert [s.name for s in spans.get_finished_spans()] == [SDK_SPAN]
    # log.debug("Checks the header went with the request")
    assert TRACEPARENT in sent[0].headers


# log.debug("Defines the test that the provider records only the chat span")
def test_the_provider_records_only_the_chat_span(spans: InMemorySpanExporter) -> None:
    """One call through the adapter: one chat span, no trace header.

    Args:
        spans: The spans this test records.
    """
    # log.debug("Starts the list of requests sent")
    sent: list[httpx2.Request] = []
    # log.debug("Builds the provider as a project does")
    provider = AnthropicProvider(api_key=KEY, timeout_s=5.0)
    # log.debug("Moves its client onto the stand-in, keeping every other option")
    provider._client = provider._client.with_options(http_client=_stand_in(sent))
    # log.debug("Makes one call through the adapter")
    ModelAdapter(provider, model=MODEL, sleep=lambda _: None).complete("hi")
    # log.debug("Checks the chat span is the only span")
    assert [s.name for s in spans.get_finished_spans()] == [f"chat {MODEL}"]
    # log.debug("Checks no trace header went with the request")
    assert TRACEPARENT not in sent[0].headers
