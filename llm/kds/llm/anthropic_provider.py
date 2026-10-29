########################################################################
#                  llm/kds/llm/anthropic_provider.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Anthropic's Messages API behind the Provider interface: tools, JSON
mode, usage, latency.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import inspect
import json
import logging
import time
from typing import Any, Final

# Third-party
import anthropic

# Local
from kds.args import required
from kds.llm import config
from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the milliseconds in a second, for latency, from the config")
MS = config.MS
# log.debug("Takes the key that says who speaks, from the config")
ROLE: Final = config.ROLE
# log.debug("Takes the key that holds what a message says, from the config")
CONTENT: Final = config.CONTENT
# log.debug("Takes the key that says a block's kind, from the config")
TYPE: Final = config.TYPE
# log.debug("Takes the key that holds a tool's name, from the config")
NAME: Final = config.NAME
# log.debug("Takes the asking role's name, from the config")
USER: Final = config.USER
# log.debug("Takes the answering role's name, from the config")
ASSISTANT: Final = config.ASSISTANT

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the instruction added to the system prompt in JSON mode")
JSON_INSTRUCTION = "\n\nRespond with a single JSON object and nothing else."
# log.debug("Names the sampling setting not every SDK version takes")
TEMPERATURE = "temperature"
# log.debug("Names the content block type that holds text")
TEXT = "text"
# log.debug("Names the content block type that calls a tool")
TOOL_USE = "tool_use"


########################################################################
#                        Anthropic Messages API                        #
########################################################################


# log.debug("Defines the Anthropic provider")
class AnthropicProvider:
    """Calls Claude through the Anthropic SDK; the SDK never retries."""

    # log.debug("Names the provider in logs and reports")
    name = "anthropic"

    # log.debug("Defines the constructor, which opens one client")
    def __init__(self, api_key: str | None = None, timeout_s: float | None = None) -> None:
        """Opens a client; the adapter, not the SDK, owns retries.

        Args:
            api_key: The Anthropic API key. Required.
            timeout_s: The most seconds one call may take. Required.
        """
        # log.debug("Takes the API key, which the caller must give")
        api_key = required(api_key=api_key)
        # log.debug("Takes the timeout in seconds, which the caller must give")
        timeout_s = required(timeout_s=timeout_s)
        # log.debug("Opens the client with a timeout and no SDK retries")
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=0)
        # log.debug("Notes whether this SDK version takes a temperature")
        self._accepts_temperature = (
            TEMPERATURE in inspect.signature(self._client.messages.create).parameters
        )

    # log.debug("Defines how our messages become Anthropic's")
    @staticmethod
    def _convert(messages: list[Message] | None = None) -> list[dict[str, Any]]:
        """Converts to Anthropic's shape; results share one user turn.

        Args:
            messages: The provider-neutral conversation. Required.

        Returns:
            The turns as Anthropic's Messages API takes them.
        """
        # log.debug("Takes the messages, which the caller must give")
        messages = required(messages=messages)
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
        model: str | None = None,
        messages: list[Message] | None = None,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        json_mode: bool | None = None,
    ) -> Completion:
        """Sends the conversation and returns the completion.

        Args:
            model: The model to call. Required.
            messages: The conversation, in order. Required.
            system: The system prompt, if any.
            tools: Any tools the model may call.
            max_tokens: The most tokens the answer may use. Required.
            temperature: The sampling temperature, sent only where the
                SDK takes one. Required.
            json_mode: True to ask for a single JSON object, through the
                system prompt. Required.

        Returns:
            The answer as a provider-neutral completion.
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
    def _completion(self, response: Any = None, latency_ms: int | None = None) -> Completion:
        """Joins the text blocks and collects the tool calls.

        Args:
            response: The Messages API's response. Required.
            latency_ms: How long the call took, in milliseconds.
                Required.

        Returns:
            The provider-neutral completion, with usage and timing.
        """
        # log.debug("Takes the response, which the caller must give")
        response = required(response=response)
        # log.debug("Takes the call's time in milliseconds, which the caller must give")
        latency_ms = required(latency_ms=latency_ms)
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
    def embed(
        self, *, model: str | None = None, texts: list[str] | None = None
    ) -> list[list[float]]:
        """Refuses, since Anthropic has no embeddings endpoint.

        Args:
            model: The embedding model asked for. Required.
            texts: The texts to embed. Required.

        Returns:
            Nothing: the call always raises.

        Raises:
            NotImplementedError: Always, naming the setting to change.
        """
        # log.debug("Takes the model, which the caller must give")
        model = required(model=model)
        # log.debug("Takes the texts, which the caller must give")
        texts = required(texts=texts)
        # log.debug("Raises with the setting that fixes it")
        msg = "Anthropic has no embeddings endpoint; set [llm] provider to openai for embeddings"
        # log.debug("Raises it")
        raise NotImplementedError(msg)
