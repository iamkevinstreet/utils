"""Settings for every prototype. Values come from the environment or a .env file; nothing is hard-coded.

Secrets are `SecretStr` so they never appear in logs or reprs by accident.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["anthropic", "openai", "azure", "fake"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: Provider = "fake"
    llm_model: str = "claude-sonnet-5-5"
    llm_judge_model: str = "claude-sonnet-5-5"
    llm_embedding_model: str = "text-embedding-3-small"

    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    azure_openai_api_key: SecretStr | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str = "2024-10-21"

    eval_budget_usd: float = Field(default=5.0, ge=0)
    log_dir: Path = Path("./logs")
    log_redact: bool = True

    entra_tenant_id: str | None = None
    entra_client_id: str | None = None
    entra_client_secret: SecretStr | None = None

    @property
    def entra_configured(self) -> bool:
        return bool(self.entra_tenant_id and self.entra_client_id and self.entra_client_secret)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
