"""Provider-neutral request and response types."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["user", "assistant", "tool"]


class Message(BaseModel):
    role: Role
    content: str
    # For role="tool": the id of the tool call this message answers.
    tool_call_id: str | None = None
    # For role="assistant": tool calls the model made in this turn.
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema for the arguments


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class Completion(BaseModel):
    text: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    stop_reason: str | None = None
    model: str
    provider: str
    usage: Usage
    latency_ms: int
    cost_usd: float | None = None
    request_id: str = "-"
