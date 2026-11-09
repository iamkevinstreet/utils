########################################################################
#                                                                      #
#                           tests/support.py                           #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

What the tests share: the repository's root, and settings that keep a
test's warehouse, dlt's state and its logs in a folder of its own.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

from pathlib import Path
from typing import Final

# Third-party
from kds.args import required
from kds.logs import get_logger

# Local
from pipelines.config import AppSettings

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
# log.debug("Sets the repository's root, where config/ and dbt/ are")
REPO: Final = Path(__file__).resolve().parents[1]


########################################################################
#                                                                      #
#                             Test helpers                             #
#                                                                      #
########################################################################
# log.debug("Defines settings that keep a test's files in its own folder")
def settings_in(folder: Path | None = None) -> AppSettings:
    """Returns settings with the warehouse, state and logs in folder.

    Args:
        folder: A temporary folder. Required.

    Returns:
        The settings, everything else as configured.
    """
    # log.debug("Takes the folder, which the caller must give")
    folder = required(folder=folder)
    # log.debug("Returns the settings")
    return AppSettings(
        warehouse_path=folder / "warehouse.duckdb",
        warehouse_state=folder / "dlt",
        log_dir=folder / "logs",
    )
