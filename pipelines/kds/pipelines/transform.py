########################################################################
#                                                                      #
#                 pipelines/kds/pipelines/transform.py                 #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

Runs dbt over the warehouse the loads filled, with the settings the
loads used: the dbt project's profiles.yml reads the DuckDB path and
the Databricks connection from the environment, which this module sets
from the settings. So the warehouse's location is written once, and
`dbt build` and the loads never disagree.

dbt runs as its own process, from this environment's dbt, so each run
starts clean and its log reads as dbt's own.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# Local
from kds.args import required
from kds.logs import get_logger, log_event
from kds.pipelines.config import SNOWFLAKE
from kds.pipelines.oidc import snowflake_token
from kds.pipelines.settings import PipelineSettings

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)


########################################################################
#                                                                      #
#                               dbt runs                               #
#                                                                      #
########################################################################
# log.debug("Defines the variables profiles.yml reads")
def dbt_env(settings: PipelineSettings | None = None) -> dict[str, str]:
    """Returns the variables profiles.yml reads, from the settings.

    Args:
        settings: The warehouse and the Databricks and Snowflake
            connections. Required.

    Returns:
        WAREHOUSE_PATH, the Databricks and Snowflake variables that
        are set, and, for Snowflake, a fresh token to sign in with.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the token, when there is one")
    token = settings.databricks_token
    # log.debug("Lists each variable and its value")
    values = {
        "WAREHOUSE_PATH": str(settings.warehouse_path.resolve()),
        "DATABRICKS_HOST": settings.databricks_host,
        "DATABRICKS_HTTP_PATH": settings.databricks_http_path,
        "DATABRICKS_CATALOG": settings.databricks_catalog,
        "DATABRICKS_TOKEN": token.get_secret_value() if token else None,
        "SNOWFLAKE_ACCOUNT": settings.snowflake_account,
        "SNOWFLAKE_DATABASE": settings.snowflake_database,
    }
    # log.debug("Adds the token Snowflake signs dbt in with, made just before dbt connects")
    if settings.warehouse_destination == SNOWFLAKE:
        # log.debug("Asks for it")
        values["SNOWFLAKE_TOKEN"] = snowflake_token(settings)
    # log.debug("Returns the ones that are set")
    return {k: v for k, v in values.items() if v}


# log.debug("Defines one dbt run")
def run_dbt(settings: PipelineSettings | None = None, args: Sequence[str] | None = None) -> bool:
    """Runs dbt with the settings' project, target and threads.

    Args:
        settings: The dbt project, target, threads and warehouse.
            Required.
        args: The dbt command and its options, such as ["build"].
            Required.

    Returns:
        True when dbt succeeded.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the command, which the caller must give")
    args = required(args=args)
    # log.debug("Makes the DuckDB file's folder, which DuckDB will not, for a build before a load")
    settings.warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    # log.debug("Points at the dbt project, which holds profiles.yml too")
    project = str(settings.dbt_project)
    # log.debug("Uses the dbt installed beside this Python")
    dbt = Path(sys.executable).with_name("dbt")
    # log.debug("Builds the command line")
    command = [
        str(dbt),
        *args,
        *("--project-dir", project, "--profiles-dir", project),
        *("--target", settings.dbt_target, "--threads", str(settings.dbt_threads)),
    ]
    # log.debug("Runs dbt as its own process, with the warehouse in its environment")
    done = subprocess.run(command, env=os.environ | dbt_env(settings), check=False)  # noqa: S603
    # log.debug("Logs how it ended")
    log_event(log, "dbt.done", command=args[0], status=done.returncode)
    # log.debug("Returns whether it succeeded")
    return done.returncode == 0
