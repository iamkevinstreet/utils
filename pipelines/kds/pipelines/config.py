########################################################################
#                                                                      #
#                  pipelines/kds/pipelines/config.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

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
Destination = Literal["duckdb", "databricks"]
# log.debug("Sets the destination that is a single DuckDB file")
DUCKDB: Final = "duckdb"
