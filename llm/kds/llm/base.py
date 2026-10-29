########################################################################
#                         llm/kds/llm/base.py                          #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           The interface every model provider implements,   #
#                     so any one can stand in for another.             #
########################################################################
"""The Provider interface: complete a conversation, embed text."""

from __future__ import annotations

import logging
from typing import Protocol

from kds.llm.types import Completion, Message, ToolSpec

# Module constants
log = logging.getLogger(__name__)


# log.debug("Defines what every provider must offer")
class Provider(Protocol):
    """A model provider. The adapter talks only to this interface."""

    # log.debug("Holds the provider's short name, such as anthropic")
    name: str

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
        """Send the conversation and return the model's completion."""

    # log.debug("Defines turning texts into vectors")
    def embed(self, *, model: str, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per text."""
