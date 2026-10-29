########################################################################
#                  settings/kds/settings/__init__.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Typed, read-only settings: values from           #
#                     config/settings.toml, secrets from .env.         #
########################################################################
"""kds.settings: one typed home for every setting a project reads.

Values come from, highest priority first: arguments, environment
variables, `.env`, `config/settings.toml`, then the defaults below.
Secrets are `SecretStr`, are refused in settings.toml, and are masked
in every log line, repr and error message.

Usage, in a project's one config module:
    class AppSettings(Settings):
        answer_min_score: float = 0.35

    @lru_cache(maxsize=1)
    def get_app_settings() -> AppSettings:
        return AppSettings()
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from kds.settings.toml import TomlSource, is_secret

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the model that does the work and grades it by default")
DEFAULT_MODEL = "claude-sonnet-5-5"
# log.debug("Sets the text a secret that is set is shown as")
MASK = "********"
# log.debug("Sets the text a secret that is missing is shown as")
UNSET = "unset"
# log.debug("Lists the model providers the adapter can use")
Provider = Literal["anthropic", "openai", "azure", "fake"]
# log.debug("Lists the log levels a service can run at")
Level = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
# log.debug("Lists what the package exports")
__all__ = ["Level", "Provider", "Settings", "describe", "get_settings"]


# log.debug("Defines the settings every project shares")
class Settings(BaseSettings):
    """Shared settings. A project subclasses this to add its own.

    Each field's TOML name is its section and key joined by an
    underscore: `[llm] model` sets `llm_model`, as does `LLM_MODEL`.
    """

    # log.debug("Reads .env, ignores unknown names, and freezes the result")
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )

    # log.debug("Holds which provider the model adapter calls")
    llm_provider: Provider = "fake"
    # log.debug("Holds the model that does the work")
    llm_model: str = DEFAULT_MODEL
    # log.debug("Holds the model that grades answers in evaluations")
    llm_judge_model: str = DEFAULT_MODEL
    # log.debug("Holds the model that turns text into vectors")
    llm_embedding_model: str = "text-embedding-3-small"
    # log.debug("Holds the most tokens one answer may use")
    llm_max_tokens: int = Field(default=2048, gt=0)
    # log.debug("Holds the sampling temperature; 0 keeps runs repeatable")
    llm_temperature: float = Field(default=0.0, ge=0, le=1)
    # log.debug("Holds how often a call that may yet succeed is retried")
    llm_max_retries: int = Field(default=3, ge=0, le=10)
    # log.debug("Holds how long one call may take before it is abandoned")
    llm_timeout_s: float = Field(default=60.0, gt=0)

    # log.debug("Holds the Anthropic key, a secret")
    anthropic_api_key: SecretStr | None = None
    # log.debug("Holds the OpenAI key, a secret")
    openai_api_key: SecretStr | None = None
    # log.debug("Holds the Azure OpenAI key, a secret")
    azure_openai_api_key: SecretStr | None = None
    # log.debug("Holds the Azure OpenAI resource address")
    azure_openai_endpoint: str | None = None
    # log.debug("Holds the Azure OpenAI API version")
    azure_openai_api_version: str = "2024-10-21"

    # log.debug("Holds the spend at which an evaluation run stops, in USD")
    eval_budget_usd: float = Field(default=5.0, ge=0)

    # log.debug("Holds the folder structured logs are written to")
    log_dir: Path = Path("logs")
    # log.debug("Holds the lowest level written to the logs")
    log_level: Level = "INFO"
    # log.debug("Holds whether personal data is redacted from logs")
    log_redact: bool = True
    # log.debug("Holds whether logger lines print as HH:MM:SS traces")
    log_trace: bool = False

    # log.debug("Defines the order the sources are read in")
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Arguments, then the environment, .env, settings.toml."""
        # log.debug("Returns the sources, highest priority first")
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlSource(settings_cls),
            file_secret_settings,
        )


# log.debug("Defines the loader the shared libraries call")
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the shared settings, built and validated once.

    Tests that change the environment call `get_settings.cache_clear()`.
    """
    # log.debug("Builds and validates the settings")
    return Settings()


# log.debug("Defines the startup summary with secrets masked")
def describe(settings: Settings) -> dict[str, str]:
    """Return every setting as text, secrets only as set or unset.

    A service logs this once at startup, so the log shows exactly
    what it ran with and never what a key is.
    """
    # log.debug("Starts the summary")
    shown: dict[str, str] = {}
    # log.debug("Walks every field the settings class declares")
    for name, field in type(settings).model_fields.items():
        # log.debug("Reads the field's value")
        value = getattr(settings, name)
        # log.debug("Shows a secret only as set or unset, else the value")
        shown[name] = (MASK if value else UNSET) if is_secret(field) else str(value)
    # log.debug("Returns the summary")
    return shown
