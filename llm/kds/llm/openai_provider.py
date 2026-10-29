########################################################################
#                    llm/kds/llm/openai_provider.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

OpenAI and Azure OpenAI chat completions behind the Provider interface,
plus embeddings.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging
import time
from typing import Any

# Third-party
import openai

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

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Names the key a tool's details sit under")
FUNCTION = "function"


########################################################################
#                      OpenAI chat and embeddings                      #
########################################################################
# log.debug("Names the keys every chat message carries")
ROLE, CONTENT = "role", "content"


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
        api_key: str | None = None,
        timeout_s: float | None = None,
        *,
        azure_endpoint: str | None = None,
        azure_api_version: str | None = None,
    ) -> None:
        """Opens an OpenAI client, or Azure's when given an endpoint.

        Args:
            api_key: The OpenAI or Azure OpenAI API key. Required.
            timeout_s: The most seconds one call may take. Required.
            azure_endpoint: The Azure OpenAI resource's address; None
                for OpenAI itself.
            azure_api_version: The Azure OpenAI API version, used only
                with an endpoint.
        """
        # log.debug("Takes the api key, which the caller must give")
        api_key = required(api_key=api_key)
        # log.debug("Takes the timeout s, which the caller must give")
        timeout_s = required(timeout_s=timeout_s)
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
    def _convert(
        messages: list[Message] | None = None, system: str | None = None
    ) -> list[dict[str, Any]]:
        """Turns messages into OpenAI's shape, system prompt first.

        Args:
            messages: The provider-neutral conversation. Required.
            system: The system prompt, sent as the first turn if given.

        Returns:
            The turns as chat completions takes them.
        """
        # log.debug("Takes the messages, which the caller must give")
        messages = required(messages=messages)
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
            tools: Any tools the model may call, offered as functions.
            max_tokens: The most tokens the answer may use. Required.
            temperature: The sampling temperature. Required.
            json_mode: True to ask for a JSON object through the
                response format. Required.

        Returns:
            The answer as a provider-neutral completion.
        """
        # log.debug("Takes the model, which the caller must give")
        model = required(model=model)
        # log.debug("Takes the messages, which the caller must give")
        messages = required(messages=messages)
        # log.debug("Takes the max tokens, which the caller must give")
        max_tokens = required(max_tokens=max_tokens)
        # log.debug("Takes the temperature, which the caller must give")
        temperature = required(temperature=temperature)
        # log.debug("Takes the json mode, which the caller must give")
        json_mode = required(json_mode=json_mode)
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
    def _completion(self, response: Any = None, latency_ms: int | None = None) -> Completion:
        """Reads the first choice's text and tool calls.

        Args:
            response: The chat completions response. Required.
            latency_ms: How long the call took, in milliseconds.
                Required.

        Returns:
            The provider-neutral completion, with usage and timing.
        """
        # log.debug("Takes the response, which the caller must give")
        response = required(response=response)
        # log.debug("Takes the call's time in milliseconds, which the caller must give")
        latency_ms = required(latency_ms=latency_ms)
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
    def embed(
        self, *, model: str | None = None, texts: list[str] | None = None
    ) -> list[list[float]]:
        """Returns one embedding vector per text.

        Args:
            model: The embedding model to call. Required.
            texts: The texts to embed. Required.

        Returns:
            One vector per text, in the order given.
        """
        # log.debug("Takes the model, which the caller must give")
        model = required(model=model)
        # log.debug("Takes the texts, which the caller must give")
        texts = required(texts=texts)
        # log.debug("Calls the embeddings endpoint")
        response = self._client.embeddings.create(model=model, input=texts)
        # log.debug("Returns the vectors in order")
        return [item.embedding for item in response.data]


# log.debug("Defines how a call's argument text becomes a dict")
def _arguments(text: str | None = None) -> dict[str, Any]:
    """Parses the arguments; keeps text that is not JSON under _raw.

    Args:
        text: The arguments as the model wrote them, as JSON; None or
            empty reads as no arguments.

    Returns:
        The arguments as a dict; text that is not JSON sits under _raw.
    """
    # log.debug("Tries to parse the arguments as JSON")
    try:
        # log.debug("Parses the arguments")
        parsed: dict[str, Any] = json.loads(text or "{}")
    except json.JSONDecodeError:
        # log.debug("Returns the raw text so the caller can see it")
        return {"_raw": text}
    # log.debug("Returns the parsed arguments")
    return parsed
