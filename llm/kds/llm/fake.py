########################################################################
#                         llm/kds/llm/fake.py                          #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           A scripted, offline provider for tests and CI:   #
#                     queued answers or a function, never the network. #
########################################################################
"""The offline stand-in provider.

Answers come from a queue, in order, or from a function of the
conversation. It never touches the network, so a whole evaluation
pipeline can run in CI with no key.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

# Module constants
log = logging.getLogger(__name__)
# log.debug("Lists what a scripted answer may be")
Scripted = str | dict[str, Any] | Completion
# log.debug("Describes a function that answers from the conversation")
Responder = Callable[[list[Message]], Scripted]
# log.debug("Sets the characters counted as one token, roughly")
CHARS_PER_TOKEN = 4
# log.debug("Sets the milliseconds in a second, for latency")
MS = 1000
# log.debug("Sets how many numbers a fake embedding has")
EMBEDDING_SIZE = 32
# log.debug("Sets the byte value that maps to zero in an embedding")
CENTRE = 128
# log.debug("Names the key a scripted answer lists tool calls under")
TOOL_CALLS = "tool_calls"


# log.debug("Defines the offline provider")
class FakeProvider:
    """A provider that answers from a script; it records every call."""

    # log.debug("Names the provider in logs and reports")
    name = "fake"

    # log.debug("Defines the constructor with a queue and a responder")
    def __init__(
        self, responses: list[Scripted] | None = None, responder: Responder | None = None
    ) -> None:
        """Queue `responses`; when they run out, ask `responder`."""
        # log.debug("Queues the scripted answers")
        self._queue: deque[Scripted] = deque(responses or [])
        # log.debug("Keeps the function that answers when the queue is empty")
        self._responder = responder
        # log.debug("Starts the record of calls, which tests inspect")
        self.calls: list[dict[str, Any]] = []

    # log.debug("Defines the next scripted answer")
    def _next(self, messages: list[Message], json_mode: bool) -> Scripted:
        """Return the next queued answer, the responder's, or empty."""
        # log.debug("Takes the next queued answer first")
        if self._queue:
            # log.debug("Returns it")
            return self._queue.popleft()
        # log.debug("Asks the responder when there is one")
        if self._responder is not None:
            # log.debug("Returns its answer")
            return self._responder(messages)
        # log.debug("Returns an empty answer of the right kind")
        return "{}" if json_mode else ""

    # log.debug("Defines one scripted call")
    def complete(
        self,
        *,
        model: str,
        messages: list[Message],
        system: str | None,
        tools: list[ToolSpec] | None,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> Completion:
        """Record the call and return the next scripted answer."""
        # log.debug("Starts the clock")
        started = time.perf_counter()
        # log.debug("Records what was asked")
        self.calls.append(
            {"model": model, "system": system, "messages": [m.model_dump() for m in messages]}
        )
        # log.debug("Gets the scripted answer")
        scripted = self._next(messages, json_mode)
        # log.debug("Returns a ready-made completion untouched")
        if isinstance(scripted, Completion):
            # log.debug("Returns it")
            return scripted
        # log.debug("Reads any tool calls the answer scripts")
        calls = _calls(scripted)
        # log.debug("Reads the answer's text")
        text = _text(scripted)
        # log.debug("Counts the characters the model would have read")
        read = sum(len(m.content) for m in messages) + len(system or "")
        # log.debug("Returns a completion with rough token counts")
        return Completion(
            text=text,
            tool_calls=calls,
            stop_reason="tool_use" if calls else "end_turn",
            model=model,
            provider=self.name,
            usage=Usage(
                input_tokens=max(1, read // CHARS_PER_TOKEN),
                output_tokens=max(1, len(text) // CHARS_PER_TOKEN),
            ),
            latency_ms=int((time.perf_counter() - started) * MS),
        )

    # log.debug("Defines repeatable stand-in embeddings")
    def embed(self, *, model: str, texts: list[str]) -> list[list[float]]:
        """Return a repeatable vector per text, from its SHA-256 digest.

        Enough to exercise retrieval code; not a semantic embedding.
        """
        # log.debug("Returns each text's digest bytes, scaled to -1..1")
        return [
            [
                (byte - CENTRE) / CENTRE
                for byte in hashlib.sha256(t.encode()).digest()[:EMBEDDING_SIZE]
            ]
            for t in texts
        ]


# log.debug("Defines how scripted tool calls are read")
def _calls(scripted: str | dict[str, Any]) -> list[ToolCall]:
    """Return the tool calls a dict answer scripts; a string: none."""
    # log.debug("Returns no calls for a string answer")
    if isinstance(scripted, str):
        # log.debug("Returns an empty list")
        return []
    # log.debug("Returns each scripted call as a ToolCall")
    return [ToolCall(**call) for call in scripted.get(TOOL_CALLS, [])]


# log.debug("Defines how a scripted answer becomes text")
def _text(scripted: str | dict[str, Any]) -> str:
    """Return a string as it is; a dict as its text field or as JSON.

    A dict that scripts tool calls carries its text in "text"; any
    other dict is the answer itself, returned as a JSON object.
    """
    # log.debug("Returns a string answer as it is")
    if isinstance(scripted, str):
        # log.debug("Returns the string")
        return scripted
    # log.debug("Returns the text beside scripted tool calls")
    if TOOL_CALLS in scripted:
        # log.debug("Returns the dict's text field, or nothing")
        return str(scripted.get("text", ""))
    # log.debug("Returns any other dict as a JSON object")
    return json.dumps(scripted)
