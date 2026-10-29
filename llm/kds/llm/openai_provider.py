########################################################################
#                    llm/kds/llm/openai_provider.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           OpenAI and Azure OpenAI chat completions behind  #
#                     the Provider interface, plus embeddings.         #
########################################################################
"""The OpenAI and Azure OpenAI provider."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import openai

from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the milliseconds in a second, for latency")
MS = 1000
# log.debug("Names the keys every chat message carries")
ROLE, CONTENT = "role", "content"
# log.debug("Names the key a tool's details sit under")
FUNCTION = "function"
# log.debug("Names the keys for a part's type and a tool's name")
TYPE, NAME = "type", "name"
# log.debug("Names the tool and assistant roles")
TOOL, ASSISTANT = "tool", "assistant"


# log.debug("Defines the OpenAI provider, which also serves Azure")
class OpenAIProvider:
    """Calls OpenAI or Azure OpenAI; the SDK never retries."""

    # log.debug("Names the provider in logs and reports")
    name = "openai"

    # log.debug("Defines the constructor, which opens one client")
    def __init__(
        self,
        api_key: str,
        timeout_s: float,
        *,
        azure_endpoint: str | None = None,
        azure_api_version: str | None = None,
    ) -> None:
        """Open an OpenAI client, or Azure's when given an endpoint."""
        # log.debug("Opens an Azure client when an endpoint is given")
        if azure_endpoint:
            # log.debug("Names the provider azure in logs and reports")
            self.name = "azure"
            # log.debug("Opens the Azure client with no SDK retries")
            self._client: openai.OpenAI = openai.AzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=azure_api_version,
                timeout=timeout_s,
                max_retries=0,
            )
        else:
            # log.debug("Opens the OpenAI client with no SDK retries")
            self._client = openai.OpenAI(api_key=api_key, timeout=timeout_s, max_retries=0)

    # log.debug("Defines how our messages become OpenAI's")
    @staticmethod
    def _convert(messages: list[Message], system: str | None) -> list[dict[str, Any]]:
        """Turn messages into OpenAI's shape, system prompt first."""
        # log.debug("Starts with the system prompt, if any")
        out: list[dict[str, Any]] = [{ROLE: "system", CONTENT: system}] if system else []
        # log.debug("Converts each message in order")
        for m in messages:
            # log.debug("Sends a tool's result as a tool turn")
            if m.role == TOOL:
                # log.debug("Adds the result with the call it answers")
                out.append({ROLE: TOOL, "tool_call_id": m.tool_call_id, CONTENT: m.content})
            elif m.role == ASSISTANT and m.tool_calls:
                # log.debug("Writes each call as a function call")
                calls = [
                    {
                        "id": tc.id,
                        TYPE: FUNCTION,
                        FUNCTION: {NAME: tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in m.tool_calls
                ]
                # log.debug("Adds the assistant turn with its calls")
                out.append({ROLE: ASSISTANT, CONTENT: m.content or None, "tool_calls": calls})
            else:
                # log.debug("Copies a plain turn as it is")
                out.append({ROLE: m.role, CONTENT: m.content})
        # log.debug("Returns the converted turns")
        return out

    # log.debug("Defines one call to the model")
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
        # log.debug("Starts the request with the model, turns and limits")
        request: dict[str, Any] = {
            "model": model,
            "messages": self._convert(messages, system),
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
        }
        # log.debug("Asks for a JSON object when in JSON mode")
        if json_mode:
            # log.debug("Sets the JSON response format")
            request["response_format"] = {TYPE: "json_object"}
        # log.debug("Offers the tools, if any, as functions")
        if tools:
            # log.debug("Adds each tool's name, purpose and argument schema")
            request["tools"] = [
                {
                    TYPE: FUNCTION,
                    FUNCTION: {
                        NAME: t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
        # log.debug("Starts the clock")
        started = time.perf_counter()
        # log.debug("Calls chat completions")
        response = self._client.chat.completions.create(**request)
        # log.debug("Measures how long the call took")
        latency_ms = int((time.perf_counter() - started) * MS)
        # log.debug("Returns the response as a provider-neutral completion")
        return self._completion(response, latency_ms)

    # log.debug("Defines how OpenAI's response becomes a completion")
    def _completion(self, response: Any, latency_ms: int) -> Completion:
        """Read the first choice's text and tool calls."""
        # log.debug("Takes the first choice")
        choice = response.choices[0]
        # log.debug("Reads each tool call's arguments")
        calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=_arguments(tc.function.arguments))
            for tc in choice.message.tool_calls or []
        ]
        # log.debug("Returns the completion with usage and timing")
        return Completion(
            text=choice.message.content or "",
            tool_calls=calls,
            stop_reason=choice.finish_reason,
            model=response.model,
            provider=self.name,
            usage=Usage(
                input_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
            ),
            latency_ms=latency_ms,
        )

    # log.debug("Defines embeddings")
    def embed(self, *, model: str, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per text."""
        # log.debug("Calls the embeddings endpoint")
        response = self._client.embeddings.create(model=model, input=texts)
        # log.debug("Returns the vectors in order")
        return [item.embedding for item in response.data]


# log.debug("Defines how a call's argument text becomes a dict")
def _arguments(text: str | None) -> dict[str, Any]:
    """Parse the arguments; keep text that is not JSON under _raw."""
    # log.debug("Tries to parse the arguments as JSON")
    try:
        # log.debug("Parses the arguments")
        parsed: dict[str, Any] = json.loads(text or "{}")
    except json.JSONDecodeError:
        # log.debug("Returns the raw text so the caller can see it")
        return {"_raw": text}
    # log.debug("Returns the parsed arguments")
    return parsed
