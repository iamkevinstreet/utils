########################################################################
#                         llm/kds/llm/base.py                          #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

The interface every model provider implements, so any one can stand in
for another.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from typing import Protocol

# Local
from kds.llm.types import Completion, Message, ToolSpec

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                          Provider interface                          #
########################################################################
# log.debug("Defines what every provider must offer")
class Provider(Protocol):
    """A model provider. The adapter talks only to this interface."""

    # log.debug("Holds the provider's short name, such as anthropic")
    name: str

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
        """Sends the conversation and returns the model's completion.

        Args:
            model: The model to call. Required.
            messages: The conversation, in order. Required.
            system: The system prompt, if any.
            tools: Any tools the model may call.
            max_tokens: The most tokens the answer may use. Required.
            temperature: The sampling temperature. Required.
            json_mode: True to ask for a single JSON object. Required.

        Returns:
            The answer as a provider-neutral completion.
        """

    # log.debug("Defines turning texts into vectors")
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
