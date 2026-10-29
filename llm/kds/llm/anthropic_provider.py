########################################################################
#                  llm/kds/llm/anthropic_provider.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Anthropic's Messages API behind the Provider     #
#                     interface: tools, JSON mode, usage, latency.     #
########################################################################
"""The Anthropic provider."""

from __future__ import annotations

import inspect
import json
import logging
import time
from typing import Any

import anthropic

from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the instruction added to the system prompt in JSON mode")
JSON_INSTRUCTION = "\n\nRespond with a single JSON object and nothing else."
# log.debug("Sets the milliseconds in a second, for latency")
MS = 1000
# log.debug("Names the keys of a message and a content block")
ROLE, CONTENT, TYPE, NAME, TEXT = "role", "content", "type", "name", "text"
# log.debug("Names the two speakers and the tool-call block type")
USER, ASSISTANT, TOOL_USE = "user", "assistant", "tool_use"
# log.debug("Names the sampling setting not every SDK version takes")
TEMPERATURE = "temperature"


# log.debug("Defines the Anthropic provider")
class AnthropicProvider:
    """Calls Claude through the Anthropic SDK; the SDK never retries."""

    # log.debug("Names the provider in logs and reports")
    name = "anthropic"

    # log.debug("Defines the constructor, which opens one client")
    def __init__(self, api_key: str, timeout_s: float) -> None:
        """Open a client; the adapter, not the SDK, owns retries."""
        # log.debug("Opens the client with a timeout and no SDK retries")
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=0)
        # log.debug("Notes whether this SDK version takes a temperature")
        self._accepts_temperature = (
            TEMPERATURE in inspect.signature(self._client.messages.create).parameters
        )

    # log.debug("Defines how our messages become Anthropic's")
    @staticmethod
    def _convert(messages: list[Message]) -> list[dict[str, Any]]:
        """Convert to Anthropic's shape; results share one user turn."""
        # log.debug("Starts the converted list")
        out: list[dict[str, Any]] = []
        # log.debug("Converts each message in order")
        for m in messages:
            # log.debug("Sends a tool's result back as a user turn")
            if m.role == "tool":
                # log.debug("Wraps the result in a tool_result block")
                block = {TYPE: "tool_result", "tool_use_id": m.tool_call_id, CONTENT: m.content}
                # log.debug("Joins the results of one turn's calls, as the API asks")
                if out and out[-1][ROLE] == USER and isinstance(out[-1][CONTENT], list):
                    # log.debug("Adds the block to the results turn already open")
                    out[-1][CONTENT].append(block)
                else:
                    # log.debug("Opens a user turn for the results")
                    out.append({ROLE: USER, CONTENT: [block]})
            elif m.role == ASSISTANT and m.tool_calls:
                # log.debug("Keeps the assistant's text, if any, as a block")
                blocks: list[dict[str, Any]] = [{TYPE: TEXT, TEXT: m.content}] if m.content else []
                # log.debug("Adds a tool_use block for each call it made")
                blocks += [
                    {TYPE: TOOL_USE, "id": tc.id, NAME: tc.name, "input": tc.arguments}
                    for tc in m.tool_calls
                ]
                # log.debug("Adds the assistant turn with its blocks")
                out.append({ROLE: ASSISTANT, CONTENT: blocks})
            else:
                # log.debug("Copies a plain turn as it is")
                out.append({ROLE: m.role, CONTENT: m.content})
        # log.debug("Returns the converted turns")
        return out

    # log.debug("Defines one call to Claude")
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
        """Send the conversation and return the completion."""
        # log.debug("Starts the request with the model, limit and turns")
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": self._convert(messages),
        }
        # log.debug("Adds the JSON instruction to the system prompt if asked")
        prompt = ((system or "") + (JSON_INSTRUCTION if json_mode else "")).strip()
        # log.debug("Sends the system prompt only when there is one")
        if prompt:
            # log.debug("Adds the system prompt")
            request["system"] = prompt
        # log.debug("Offers the tools, if any, in Anthropic's shape")
        if tools:
            # log.debug("Adds each tool's name, purpose and argument schema")
            request["tools"] = [
                {NAME: t.name, "description": t.description, "input_schema": t.parameters}
                for t in tools
            ]
        # log.debug("Sets the temperature where this SDK accepts one")
        if self._accepts_temperature:
            # log.debug("Adds the temperature")
            request[TEMPERATURE] = temperature
        # log.debug("Starts the clock")
        started = time.perf_counter()
        # log.debug("Calls the Messages API")
        response = self._client.messages.create(**request)
        # log.debug("Measures how long the call took")
        latency_ms = int((time.perf_counter() - started) * MS)
        # log.debug("Returns the response as a provider-neutral completion")
        return self._completion(response, latency_ms)

    # log.debug("Defines how Anthropic's response becomes a completion")
    def _completion(self, response: Any, latency_ms: int) -> Completion:
        """Join the text blocks and collect the tool calls."""
        # log.debug("Starts the text parts and tool calls")
        texts: list[str] = []
        # log.debug("Starts the list of tool calls")
        calls: list[ToolCall] = []
        # log.debug("Reads each content block")
        for block in response.content:
            # log.debug("Keeps text blocks as text")
            if block.type == TEXT:
                # log.debug("Adds the block's text")
                texts.append(block.text)
            elif block.type == TOOL_USE:
                # log.debug("Copies the arguments into plain JSON types")
                arguments = json.loads(json.dumps(block.input))
                # log.debug("Adds the tool call")
                calls.append(ToolCall(id=block.id, name=block.name, arguments=arguments))
        # log.debug("Returns the completion with usage and timing")
        return Completion(
            text="".join(texts),
            tool_calls=calls,
            stop_reason=response.stop_reason,
            model=response.model,
            provider=self.name,
            usage=Usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            latency_ms=latency_ms,
        )

    # log.debug("Defines embeddings, which Anthropic does not offer")
    def embed(self, *, model: str, texts: list[str]) -> list[list[float]]:
        """Refuse: Anthropic has no embeddings endpoint."""
        # log.debug("Raises with the setting that fixes it")
        msg = "Anthropic has no embeddings endpoint; set [llm] provider to openai for embeddings"
        # log.debug("Raises it")
        raise NotImplementedError(msg)
