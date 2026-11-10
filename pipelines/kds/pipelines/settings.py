########################################################################
#                                                                      #
#                 pipelines/kds/pipelines/settings.py                  #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

The settings every project's data layers share: where the warehouse
is (one DuckDB file, Databricks or Snowflake), where dlt keeps its
state, and how dbt runs. A project's config module subclasses
PipelineSettings and adds its own sources' settings, so its
config/config.toml holds both.

Databricks is the destination only with its host, HTTP path and token
all set; Snowflake only with its account. Tokens are secrets, so they
come from config/.env or the environment, never config.toml. Snowflake
needs no stored token at all in a GitHub workflow, which signs in with
the workflow's own identity (kds.pipelines.oidc).
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from pathlib import Path
from typing import Self

# Third-party
from pydantic import Field, SecretStr, field_validator, model_validator

# Local
from kds.logs import get_logger
from kds.pipelines.config import (
    DATABRICKS,
    DUCKDB,
    SCHEME,
    SNOWFLAKE,
    SNOWFLAKE_DOMAIN,
    Destination,
)
from kds.settings import Settings

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)


########################################################################
#                                                                      #
#                               Settings                               #
#                                                                      #
########################################################################
# log.debug("Defines the settings every project's data layers share")
class PipelineSettings(Settings):
    """The warehouse, dlt's state, dbt, Databricks and Snowflake."""

    # log.debug("Holds where loads go: duckdb, databricks or snowflake")
    warehouse_destination: Destination = DUCKDB
    # log.debug("Holds the DuckDB file, on a laptop and in CI")
    warehouse_path: Path = Path("data/generated/warehouse.duckdb")
    # log.debug("Holds where dlt keeps each pipeline's state")
    warehouse_state: Path = Path("data/generated/dlt")

    # log.debug("Holds the dbt project's folder, which also holds profiles.yml")
    dbt_project: Path = Path("dbt")
    # log.debug("Holds dbt's target: dev is DuckDB, prod Databricks, snowflake Snowflake")
    dbt_target: str = "dev"
    # log.debug("Holds how many models dbt builds at once")
    dbt_threads: int = Field(default=4, ge=1, le=16)

    # log.debug("Holds the Unity Catalog catalog every schema lives in")
    databricks_catalog: str = "kds"
    # log.debug("Holds the Databricks workspace's host")
    databricks_host: str | None = None
    # log.debug("Holds the SQL warehouse's HTTP path")
    databricks_http_path: str | None = None
    # log.debug("Holds the Databricks token, a secret")
    databricks_token: SecretStr | None = None
    # log.debug("Holds the Snowflake account, ORGNAME-ACCOUNTNAME")
    snowflake_account: str | None = None
    # log.debug("Holds the Snowflake database every schema lives in")
    snowflake_database: str = "KDS"
    # log.debug("Holds a token Snowflake signs in with, else the workflow's own")
    snowflake_token: SecretStr | None = None

    # log.debug("Holds the encoding every file is read and written in")
    files_encoding: str = "utf-8"

    # log.debug("Defines how a pasted host is made bare")
    @field_validator("databricks_host")
    @classmethod
    def _bare_host(cls, host: str | None = None) -> str | None:
        """Strips a scheme and a trailing slash from the host.

        dbt and dlt take the bare host name; a browser shows https://
        in front of it.

        Args:
            host: The host as set, or None.

        Returns:
            The bare host name, or None.
        """
        # log.debug("Returns the host without its scheme or trailing slash")
        return host.removeprefix(SCHEME).rstrip("/") if host else host

    # log.debug("Defines how a pasted Snowflake account is made its identifier")
    @field_validator("snowflake_account")
    @classmethod
    def _account_id(cls, account: str | None = None) -> str | None:
        """Takes the account's identifier from it or from its address.

        Snowsight shows ORGNAME-ACCOUNTNAME; a browser shows the same
        inside https://orgname-accountname.snowflakecomputing.com.

        Args:
            account: The account as set, or None.

        Returns:
            ORGNAME-ACCOUNTNAME in capitals, or None.
        """
        # log.debug("Returns None as it came")
        if not account:
            # log.debug("Returns it")
            return account
        # log.debug("Strips the scheme, the domain and any path")
        bare = account.removeprefix(SCHEME).split("/")[0].removesuffix(SNOWFLAKE_DOMAIN)
        # log.debug("Returns it in capitals, as Snowsight shows it")
        return bare.upper()

    # log.debug("Defines the check that the destination is set up whole")
    @model_validator(mode="after")
    def _destination_whole(self) -> Self:
        """Refuses a destination without its connection.

        Returns:
            The settings, unchanged.

        Raises:
            ValueError: When Databricks is the destination without its
                host, HTTP path and token, or Snowflake without its
                account.
        """
        # log.debug("Lists what each destination needs, by the variable that sets it")
        needs: dict[str, dict[str, object]] = {
            DATABRICKS: {
                "DATABRICKS_HOST": self.databricks_host,
                "DATABRICKS_HTTP_PATH": self.databricks_http_path,
                "DATABRICKS_TOKEN": self.databricks_token,
            },
            SNOWFLAKE: {"SNOWFLAKE_ACCOUNT": self.snowflake_account},
        }
        # log.debug("Lists what this destination lacks")
        missing = [k for k, v in needs.get(self.warehouse_destination, {}).items() if not v]
        # log.debug("Refuses a destination half set up")
        if missing:
            # log.debug("Raises, naming what is needed")
            raise ValueError(f"{self.warehouse_destination} needs {', '.join(missing)}")
        # log.debug("Returns the settings")
        return self
