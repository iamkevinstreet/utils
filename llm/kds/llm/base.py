"""The interface every provider implements."""

from __future__ import annotations

from typing import Protocol

from kds.llm.types import Completion, Message, ToolSpec


class Provider(Protocol):
    name: str

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
    ) -> Completion: ...

    def embed(self, *, model: str, texts: list[str]) -> list[list[float]]: ...
