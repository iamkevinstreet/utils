########################################################################
#                         llm/kds/llm/fake.py                          #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

A scripted, offline provider for tests and CI. Answers come from a
queue, in order, and then from a function of the conversation, when
one is given. It never touches the network, so a whole evaluation
pipeline can run in CI with no key.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any

# Local
from kds.args import missing, required
from kds.llm import config
from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the milliseconds in a second, for latency, from the config")
MS = config.MS

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists what a scripted answer may be")
Scripted = str | dict[str, Any] | Completion
# log.debug("Describes a function that answers from the conversation")
Responder = Callable[[list[Message]], Scripted]
# log.debug("Sets the characters counted as one token, roughly")
CHARS_PER_TOKEN = 4
# log.debug("Sets how many numbers a fake embedding has")
EMBEDDING_SIZE = 32
# log.debug("Sets the byte value that maps to zero in an embedding")
CENTRE = 128
# log.debug("Names the key a scripted answer lists tool calls under")
TOOL_CALLS = "tool_calls"


########################################################################
#                           Offline stand-in                           #
########################################################################
# log.debug("Defines the offline provider")
class FakeProvider:
    """A provider that answers from a script; it records every call."""

    # log.debug("Names the provider in logs and reports")
    name = "fake"

    # log.debug("Defines the constructor with a queue and a responder")
    def __init__(
        self, responses: list[Scripted] | None = None, responder: Responder | None = None
    ) -> None:
        """Queues `responses`; when they run out, asks `responder`.

        Args:
            responses: The scripted answers, given out in order, if any.
            responder: Answers from the conversation once the queue is
                empty; if None, an empty answer comes back instead.
        """
        # log.debug("Queues the scripted answers")
        self._queue: deque[Scripted] = deque(responses or [])
        # log.debug("Keeps the function that answers when the queue is empty")
        self._responder = responder
        # log.debug("Starts the record of calls, which tests inspect")
        self.calls: list[dict[str, Any]] = []

    # log.debug("Defines the next scripted answer")
    def _next(
        self, messages: list[Message] | None = None, json_mode: bool | None = None
    ) -> Scripted:
        """Returns the next queued answer, the responder's, or empty.

        Args:
            messages: The conversation, passed to the responder.
                Required.
            json_mode: Whether the call asked for JSON, which makes
                the empty answer "{}" rather than "". Required.

        Returns:
            The scripted answer: a string, a dict or a completion.
        """
        # log.debug("Takes the messages, which the caller must give")
        messages = required(messages=messages)
        # log.debug("Takes whether to ask for JSON, which the caller must give")
        json_mode = required(json_mode=json_mode)
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
        model: str | None = None,
        messages: list[Message] | None = None,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        json_mode: bool | None = None,
    ) -> Completion:
        """Records the call and returns the next scripted answer.

        Args:
            model: The model name, echoed in the completion. Required.
            messages: The conversation, recorded and passed to the
                responder. Required.
            system: The system prompt, recorded and counted as read.
            tools: Ignored; scripted answers name their own tool calls.
            max_tokens: Ignored; scripted answers are never cut short.
                Required.
            temperature: Ignored; scripted answers never vary.
                Required.
            json_mode: Whether the call asked for JSON, which makes
                the empty answer "{}". Required.

        Returns:
            The scripted answer as a completion with rough token
            counts; a scripted completion comes back untouched.
        """
        # log.debug("Takes the model, which the caller must give")
        model = required(model=model)
        # log.debug("Takes the messages, which the caller must give")
        messages = required(messages=messages)
        # log.debug("Takes the token limit, which the caller must give")
        max_tokens = required(max_tokens=max_tokens)
        # log.debug("Takes the temperature, which the caller must give")
        temperature = required(temperature=temperature)
        # log.debug("Takes whether to ask for JSON, which the caller must give")
        json_mode = required(json_mode=json_mode)
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
    def embed(
        self, *, model: str | None = None, texts: list[str] | None = None
    ) -> list[list[float]]:
        """Returns a repeatable vector per text, from its SHA-256.

        Enough to exercise retrieval code; not a semantic embedding.

        Args:
            model: The embedding model asked for; ignored. Required.
            texts: The texts to embed. Required.

        Returns:
            One vector per text, each number between -1 and 1.
        """
        # log.debug("Takes the model, which the caller must give")
        model = required(model=model)
        # log.debug("Takes the texts, which the caller must give")
        texts = required(texts=texts)
        # log.debug("Returns each text's digest bytes, scaled to -1..1")
        return [
            [
                (byte - CENTRE) / CENTRE
                for byte in hashlib.sha256(t.encode()).digest()[:EMBEDDING_SIZE]
            ]
            for t in texts
        ]


# log.debug("Defines how scripted tool calls are read")
def _calls(scripted: str | dict[str, Any] | None = None) -> list[ToolCall]:
    """Returns the tool calls a dict answer scripts; a string: none.

    Args:
        scripted: A scripted answer, a string or a dict. Required.

    Returns:
        The tool calls listed under the dict's "tool_calls" key.
    """
    # log.debug("Stops when the caller left out the scripted")
    if scripted is None:
        # log.debug("Raises the missing-argument error")
        raise missing(scripted=scripted)
    # log.debug("Returns no calls for a string answer")
    if isinstance(scripted, str):
        # log.debug("Returns an empty list")
        return []
    # log.debug("Returns each scripted call as a ToolCall")
    return [ToolCall(**call) for call in scripted.get(TOOL_CALLS, [])]


# log.debug("Defines how a scripted answer becomes text")
def _text(scripted: str | dict[str, Any] | None = None) -> str:
    """Returns a string as it is; a dict as its text field or as JSON.

    A dict that scripts tool calls carries its text in "text"; any
    other dict is the answer itself, returned as a JSON object.

    Args:
        scripted: A scripted answer, a string or a dict. Required.

    Returns:
        The answer's text.
    """
    # log.debug("Stops when the caller left out the scripted")
    if scripted is None:
        # log.debug("Raises the missing-argument error")
        raise missing(scripted=scripted)
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
