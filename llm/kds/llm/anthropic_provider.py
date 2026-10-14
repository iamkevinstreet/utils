"""Anthropic Messages API behind the Provider interface."""

from __future__ import annotations

import inspect
import json
import time
from typing import Any

from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._accepts_temperature = (
            "temperature" in inspect.signature(self._client.messages.create).parameters
        )

    @staticmethod
    def _convert(messages: list[Message]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "tool":
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}
                        ],
                    }
                )
            elif m.role == "assistant" and m.tool_calls:
                blocks: list[dict[str, Any]] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                out.append({"role": "assistant", "content": blocks})
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
            "max_tokens": max_tokens,
            "messages": self._convert(messages),
        }
        sys_prompt = system or ""
        if json_mode:
            sys_prompt = (sys_prompt + "\n\nRespond with a single JSON object and nothing else.").strip()
        if sys_prompt:
            kwargs["system"] = sys_prompt
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools
            ]
        if self._accepts_temperature:
            kwargs["temperature"] = temperature
        started = time.perf_counter()
        resp = self._client.messages.create(**kwargs)
        latency = int((time.perf_counter() - started) * 1000)
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(block.text)
            elif btype == "tool_use":
                args = block.input if isinstance(block.input, dict) else json.loads(json.dumps(block.input))
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=args))
        usage = Usage(input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens)
        return Completion(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=getattr(resp, "stop_reason", None),
            model=resp.model,
            provider=self.name,
            usage=usage,
            latency_ms=latency,
        )

    def embed(self, *, model: str, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Anthropic has no embeddings endpoint; set LLM_PROVIDER=openai for embeddings."
        )
