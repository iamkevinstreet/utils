"""OpenAI and Azure OpenAI (chat completions) behind the Provider interface."""

from __future__ import annotations

import json
import time
from typing import Any

from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        azure_endpoint: str | None = None,
        azure_api_version: str | None = None,
    ):
        import openai

        if azure_endpoint:
            self.name = "azure"
            self._client = openai.AzureOpenAI(
                api_key=api_key, azure_endpoint=azure_endpoint, api_version=azure_api_version or "2024-10-21"
            )
        else:
            self._client = openai.OpenAI(api_key=api_key)

    @staticmethod
    def _convert(messages: list[Message], system: str | None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "tool":
                out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
            elif m.role == "assistant" and m.tool_calls:
                out.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                            }
                            for tc in m.tool_calls
                        ],
                    }
                )
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    def complete(
        self,
        *,
        model: str,
        messages: list[Message],
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> Completion:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": self._convert(messages, system),
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
                }
                for t in tools
            ]
        started = time.perf_counter()
        resp = self._client.chat.completions.create(**kwargs)
        latency = int((time.perf_counter() - started) * 1000)
        choice = resp.choices[0]
        tool_calls: list[ToolCall] = []
        for tc in choice.message.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        usage = Usage(
            input_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
        )
        return Completion(
            text=choice.message.content or "",
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason,
            model=resp.model,
            provider=self.name,
            usage=usage,
            latency_ms=latency,
        )

    def embed(self, *, model: str, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in resp.data]
