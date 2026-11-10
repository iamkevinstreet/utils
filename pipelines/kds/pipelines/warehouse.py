########################################################################
#                                                                      #
#                 pipelines/kds/pipelines/warehouse.py                 #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

Loads a dlt source into the warehouse the settings name: one DuckDB
file on a laptop and in CI, Databricks in production. The source code
is the same for both; only the destination changes.

dlt's usage telemetry is turned off before any pipeline exists, and its
state is kept beside the DuckDB file, under data/generated/, so a clean
clone starts clean.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from typing import Any, Final

# Third-party
import dlt
from dlt.common.pipeline import LoadInfo

# Local
from kds.args import required
from kds.logs import get_logger, log_event
from kds.pipelines.config import DUCKDB, OIDC, SNOWFLAKE, WORKLOAD_IDENTITY
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
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Names dlt's switch for its anonymous usage reports")
TELEMETRY: Final = "runtime.dlthub_telemetry"


########################################################################
#                                                                      #
#                               Loading                                #
#                                                                      #
########################################################################
# log.debug("Defines the destination a load goes to")
def destination(settings: PipelineSettings | None = None) -> Any:
    """Returns dlt's DuckDB, Databricks or Snowflake destination.

    Args:
        settings: The destination and where it is. Required.

    Returns:
        The destination, ready for a pipeline.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Uses one DuckDB file when the settings say so")
    if settings.warehouse_destination == DUCKDB:
        # log.debug("Makes the file's folder")
        settings.warehouse_path.parent.mkdir(parents=True, exist_ok=True)
        # log.debug("Returns the DuckDB destination")
        return dlt.destinations.duckdb(str(settings.warehouse_path))
    # log.debug("Signs in to Snowflake as the workload itself, when the settings say so")
    if settings.warehouse_destination == SNOWFLAKE:
        # log.debug("Returns the Snowflake destination, its service user found by the token")
        return dlt.destinations.snowflake(
            credentials={
                "host": settings.snowflake_account,
                "database": settings.snowflake_database,
                "authenticator": WORKLOAD_IDENTITY,
                "workload_identity_provider": OIDC,
                "token": snowflake_token(settings),
            }
        )
    # log.debug("Takes the token, which the settings check guarantees")
    token = required(databricks_token=settings.databricks_token)
    # log.debug("Returns the Databricks destination")
    return dlt.destinations.databricks(
        credentials={
            "server_hostname": settings.databricks_host,
            "http_path": settings.databricks_http_path,
            "access_token": token.get_secret_value(),
            "catalog": settings.databricks_catalog,
        }
    )


# log.debug("Defines one load of a source into a dataset")
def load(
    settings: PipelineSettings | None = None,
    *,
    name: str | None = None,
    dataset: str | None = None,
    source: Any = None,
) -> LoadInfo:
    """Runs the source into the dataset and fails if any job failed.

    Args:
        settings: The destination and where dlt keeps its state.
            Required.
        name: The pipeline's name, which names its state. Required.
        dataset: The schema the tables load into. Required.
        source: The dlt source. Required.

    Returns:
        dlt's account of the load: packages, jobs and their tables.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Takes the pipeline's name, which the caller must give")
    name = required(name=name)
    # log.debug("Takes the dataset, which the caller must give")
    dataset = required(dataset=dataset)
    # log.debug("Takes the source, which the caller must give")
    source = required(source=source)
    # log.debug("Turns dlt's usage reports off before the pipeline exists")
    dlt.config[TELEMETRY] = False
    # log.debug("Builds the pipeline, with its state under the settings' folder")
    pipeline = dlt.pipeline(
        pipeline_name=name,
        destination=destination(settings),
        dataset_name=dataset,
        pipelines_dir=str(settings.warehouse_state),
    )
    # log.debug("Runs the source")
    info = pipeline.run(source)
    # log.debug("Fails the load when any job failed")
    info.raise_on_failed_jobs()
    # log.debug("Logs the load")
    log_event(log, "load.done", pipeline=name, dataset=dataset, packages=len(info.loads_ids))
    # log.debug("Returns dlt's account of it")
    return info
