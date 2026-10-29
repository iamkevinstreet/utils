########################################################################
#                       llm/kds/llm/providers.py                       #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Builds the provider the settings name, and stops #
#                     early with a clear message when a key is         #
#                     missing.                                         #
########################################################################
"""The one place a concrete provider is chosen."""

from __future__ import annotations

import logging

from kds.llm.anthropic_provider import AnthropicProvider
from kds.llm.base import Provider
from kds.llm.fake import FakeProvider
from kds.llm.openai_provider import OpenAIProvider
from kds.settings import Settings

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the advice every missing-key error ends with")
FIX = "add it to .env (see .env.example)"


# log.debug("Defines the error for a provider chosen without its key")
class MissingKeyError(RuntimeError):
    """The settings chose a provider whose key is not set."""


# log.debug("Defines the factory that builds the configured provider")
def build_provider(settings: Settings) -> Provider:
    """Return the provider `settings.llm_provider` names.

    Raises:
        MissingKeyError: The chosen provider's key or endpoint is unset.
    """
    # log.debug("Reads which provider was chosen")
    choice = settings.llm_provider
    # log.debug("Builds Anthropic when chosen")
    if choice == "anthropic":
        # log.debug("Stops when its key is missing")
        if settings.anthropic_api_key is None:
            # log.debug("Raises naming the missing key")
            raise MissingKeyError(f"ANTHROPIC_API_KEY is not set; {FIX}")
        # log.debug("Returns the Anthropic provider")
        return AnthropicProvider(
            settings.anthropic_api_key.get_secret_value(), settings.llm_timeout_s
        )
    # log.debug("Builds OpenAI when chosen")
    if choice == "openai":
        # log.debug("Stops when its key is missing")
        if settings.openai_api_key is None:
            # log.debug("Raises naming the missing key")
            raise MissingKeyError(f"OPENAI_API_KEY is not set; {FIX}")
        # log.debug("Returns the OpenAI provider")
        return OpenAIProvider(settings.openai_api_key.get_secret_value(), settings.llm_timeout_s)
    # log.debug("Builds Azure OpenAI when chosen")
    if choice == "azure":
        # log.debug("Stops when its key or endpoint is missing")
        if settings.azure_openai_api_key is None or not settings.azure_openai_endpoint:
            # log.debug("Raises naming both settings")
            raise MissingKeyError(
                f"AZURE_OPENAI_API_KEY and [azure_openai] endpoint must both be set; {FIX}"
            )
        # log.debug("Returns the OpenAI provider pointed at Azure")
        return OpenAIProvider(
            settings.azure_openai_api_key.get_secret_value(),
            settings.llm_timeout_s,
            azure_endpoint=settings.azure_openai_endpoint,
            azure_api_version=settings.azure_openai_api_version,
        )
    # log.debug("Returns the offline provider for fake, the default")
    return FakeProvider()
