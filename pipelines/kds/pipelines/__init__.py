########################################################################
#                                                                      #
#                 pipelines/kds/pipelines/__init__.py                  #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

What every project's data layers run on: the shared settings, dlt
loads into DuckDB or Databricks, dbt runs over the same warehouse, and
the one command a project's Makefile, CI and DAGs call.

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
from kds.pipelines.config import DUCKDB, Destination
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
    "DUCKDB",
    "Destination",
    "PipelineSettings",
    "dbt_env",
    "destination",
    "load",
    "run_command",
    "run_dbt",
]
