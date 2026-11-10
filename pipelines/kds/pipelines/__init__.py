########################################################################
#                                                                      #
#                 pipelines/kds/pipelines/__init__.py                  #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

What every project's data layers run on: the shared settings, dlt
loads into DuckDB, Databricks or Snowflake, dbt runs over the same
warehouse, and the one command a project's Makefile, CI and DAGs call.
On Snowflake a GitHub job signs in as itself, with its OIDC token.

Usage, in a project's pipelines/__main__.py:
    from kds.pipelines import run_command
    loads = {"charges": load_charges}
    raise SystemExit(run_command(loads, get_app_settings))
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Local
from kds.pipelines.command import run_command
from kds.pipelines.config import DATABRICKS, DUCKDB, SNOWFLAKE, Destination
from kds.pipelines.oidc import github_token, snowflake_audience, snowflake_token
from kds.pipelines.settings import PipelineSettings
from kds.pipelines.transform import dbt_env, run_dbt
from kds.pipelines.warehouse import destination, load

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Lists what the package offers")
__all__ = [
    "DATABRICKS",
    "DUCKDB",
    "SNOWFLAKE",
    "Destination",
    "PipelineSettings",
    "dbt_env",
    "destination",
    "github_token",
    "load",
    "run_command",
    "run_dbt",
    "snowflake_audience",
    "snowflake_token",
]
