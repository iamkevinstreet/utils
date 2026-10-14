"""A scripted provider for tests and offline evaluation runs.

Responses are queued in order, or produced by a function of the last user message. It never touches the
network, so the whole evaluation pipeline can run in CI.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import deque
from collections.abc import Callable

from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

Responder = Callable[[list[Message]], str | dict | Completion]


class FakeProvider:
    name = "fake"

    def __init__(
        self, responses: list[str | dict | Completion] | None = None, responder: Responder | None = None
    ):
        self._queue: deque[str | dict | Completion] = deque(responses or [])
        self._responder = responder
        self.calls: list[dict] = []

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
        started = time.perf_counter()
        self.calls.append({"model": model, "system": system, "messages": [m.model_dump() for m in messages]})
        if self._queue:
            scripted = self._queue.popleft()
        elif self._responder is not None:
            scripted = self._responder(messages)
        else:
            scripted = "" if not json_mode else "{}"
        if isinstance(scripted, Completion):
            return scripted
        tool_calls: list[ToolCall] = []
        if isinstance(scripted, dict) and "tool_calls" in scripted:
            tool_calls = [ToolCall(**tc) for tc in scripted["tool_calls"]]
            text = scripted.get("text", "")
        elif isinstance(scripted, dict):
            text = json.dumps(scripted)
        else:
            text = scripted
        prompt_chars = sum(len(m.content) for m in messages) + len(system or "")
        usage = Usage(input_tokens=max(1, prompt_chars // 4), output_tokens=max(1, len(text) // 4))
        return Completion(
            text=text,
            tool_calls=tool_calls,
            stop_reason="tool_use" if tool_calls else "end_turn",
            model=model,
            provider=self.name,
            usage=usage,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def embed(self, *, model: str, texts: list[str]) -> list[list[float]]:
        # Deterministic pseudo-embeddings: good enough to exercise retrieval code paths in tests.
        out: list[list[float]] = []
        for t in texts:
            digest = hashlib.sha256(t.encode()).digest()
            out.append([(b - 128) / 128 for b in digest[:32]])
        return out
