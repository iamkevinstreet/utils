########################################################################
#                                                                      #
#                 pipelines/kds/pipelines/settings.py                  #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

The settings every project's data layers share: where the warehouse
is (one DuckDB file, or Databricks), where dlt keeps its state, and how
dbt runs. A project's config module subclasses PipelineSettings and adds
its own sources' settings, so its config/config.toml holds both.

Databricks is the destination only with its host, HTTP path and token
all set. The token is a secret, so it comes from config/.env or the
environment, never config.toml.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from pathlib import Path
from typing import Final, Self

# Third-party
from pydantic import Field, SecretStr, field_validator, model_validator

# Local
from kds.logs import get_logger
from kds.pipelines.config import DUCKDB, Destination
from kds.settings import Settings

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the prefix a browser shows before a host")
SCHEME: Final = "https://"


########################################################################
#                                                                      #
#                               Settings                               #
#                                                                      #
########################################################################
# log.debug("Defines the settings every project's data layers share")
class PipelineSettings(Settings):
    """The warehouse, dlt's state, dbt and Databricks, for a project."""

    # log.debug("Holds where loads go: duckdb or databricks")
    warehouse_destination: Destination = DUCKDB
    # log.debug("Holds the DuckDB file, on a laptop and in CI")
    warehouse_path: Path = Path("data/generated/warehouse.duckdb")
    # log.debug("Holds where dlt keeps each pipeline's state")
    warehouse_state: Path = Path("data/generated/dlt")

    # log.debug("Holds the dbt project's folder, which also holds profiles.yml")
    dbt_project: Path = Path("dbt")
    # log.debug("Holds dbt's target: dev builds in DuckDB, prod in Databricks")
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

    # log.debug("Defines the check that Databricks is set up whole")
    @model_validator(mode="after")
    def _databricks_whole(self) -> Self:
        """Refuses Databricks as the destination without its connection.

        Returns:
            The settings, unchanged.

        Raises:
            ValueError: When Databricks is the destination without its
                host, HTTP path and token.
        """
        # log.debug("Lists what a Databricks load needs")
        needed = (self.databricks_host, self.databricks_http_path, self.databricks_token)
        # log.debug("Refuses Databricks half set up")
        if self.warehouse_destination != DUCKDB and not all(needed):
            # log.debug("Raises, naming what is needed")
            raise ValueError("databricks needs DATABRICKS_HOST, _HTTP_PATH and _TOKEN")
        # log.debug("Returns the settings")
        return self
