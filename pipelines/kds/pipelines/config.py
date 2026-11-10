########################################################################
#                                                                      #
#                  pipelines/kds/pipelines/config.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

The values more than one file of kds.pipelines uses.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
from typing import Final, Literal

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
# log.debug("Types the warehouses a load can go to")
Destination = Literal["duckdb", "databricks", "snowflake"]
# log.debug("Sets the destination that is a single DuckDB file")
DUCKDB: Final = "duckdb"
# log.debug("Sets the destination that is a Databricks SQL warehouse")
DATABRICKS: Final = "databricks"
# log.debug("Sets the destination that is a Snowflake account")
SNOWFLAKE: Final = "snowflake"
# log.debug("Sets how Snowflake signs a workload in: by its own identity")
WORKLOAD_IDENTITY: Final = "WORKLOAD_IDENTITY"
# log.debug("Sets the kind of identity a workflow has: an OIDC token")
OIDC: Final = "OIDC"
# log.debug("Sets the part of a Snowflake account's address after its name")
SNOWFLAKE_DOMAIN: Final = ".snowflakecomputing.com"
# log.debug("Sets the prefix a browser shows before a host, the only scheme fetched")
SCHEME: Final = "https://"
