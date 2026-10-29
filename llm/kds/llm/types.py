########################################################################
#                         llm/kds/llm/types.py                         #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The provider-neutral request and response types  #
#                     every provider converts to and from.             #
########################################################################
"""Provider-neutral messages, tool calls, usage and completions."""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

# Module constants
log = logging.getLogger(__name__)
# log.debug("Lists who can speak in a conversation")
Role = Literal["user", "assistant", "tool"]


# log.debug("Defines a tool the model may call")
class ToolSpec(BaseModel):
    """A tool offered to the model: its name, purpose and arguments."""

    # log.debug("Holds the name the model calls the tool by")
    name: str
    # log.debug("Holds what the tool does, which the model reads")
    description: str
    # log.debug("Holds the JSON schema of the tool's arguments")
    parameters: dict[str, Any]


# log.debug("Defines one call the model made to a tool")
class ToolCall(BaseModel):
    """A tool call: the provider's id for it, the tool and arguments."""

    # log.debug("Holds the provider's id, echoed back with the result")
    id: str
    # log.debug("Holds the name of the tool called")
    name: str
    # log.debug("Holds the arguments the model chose")
    arguments: dict[str, Any]


# log.debug("Defines one turn of a conversation")
class Message(BaseModel):
    """One turn: who spoke, what was said, and any tool traffic."""

    # log.debug("Holds who spoke")
    role: Role
    # log.debug("Holds what was said, or a tool's result")
    content: str
    # log.debug("Holds, for a tool turn, the call this result answers")
    tool_call_id: str | None = None
    # log.debug("Holds, for an assistant turn, the tools it called")
    tool_calls: list[ToolCall] = Field(default_factory=list)


# log.debug("Defines the tokens one call used")
class Usage(BaseModel):
    """Tokens read and written by one call."""

    # log.debug("Holds the tokens the model read")
    input_tokens: int = 0
    # log.debug("Holds the tokens the model wrote")
    output_tokens: int = 0

    # log.debug("Defines the total of both")
    @property
    def total(self) -> int:
        """Return input and output tokens together."""
        # log.debug("Returns the sum")
        return self.input_tokens + self.output_tokens


# log.debug("Defines the result of one call to a model")
class Completion(BaseModel):
    """A model's answer, with what it cost and how long it took."""

    # log.debug("Holds the answer's text")
    text: str
    # log.debug("Holds the tools the model asked to call")
    tool_calls: list[ToolCall] = Field(default_factory=list)
    # log.debug("Holds why the model stopped")
    stop_reason: str | None = None
    # log.debug("Holds the model that answered, as the provider named it")
    model: str
    # log.debug("Holds the provider that served the call")
    provider: str
    # log.debug("Holds the tokens used")
    usage: Usage
    # log.debug("Holds the call's wall-clock time in milliseconds")
    latency_ms: int
    # log.debug("Holds the call's cost at list price, None if unpriced")
    cost_usd: float | None = None
    # log.debug("Holds the request id the call was made under")
    request_id: str = "-"
