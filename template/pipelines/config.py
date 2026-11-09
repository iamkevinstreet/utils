########################################################################
#                                                                      #
#                         pipelines/config.py                          #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Every setting this project's loaders, build and DAGs read. The shared
ones (the warehouse, dlt's state, dbt and Databricks) come from
kds.pipelines; each source adds its own here, and config/config.toml
lists them all at their defaults. SETTINGS holds the settings loaded
once at import; functions that take settings still take them, so tests
can pass their own.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from functools import lru_cache
from typing import Final

# Third-party
from kds.logs import get_logger
from kds.pipelines import PipelineSettings

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
# log.debug("Defines this project's settings, the shared ones and its own")
class AppSettings(PipelineSettings):
    """Every setting the loaders, the build and the DAGs read."""


# log.debug("Defines how the settings are read")
@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    """Returns the settings, read once per process.

    Returns:
        The settings from config/config.toml, config/.env and the
        environment.
    """
    # log.debug("Reads the settings")
    return AppSettings()


# log.debug("Reads the settings once, for the values modules bind at import")
SETTINGS: Final = get_app_settings()
