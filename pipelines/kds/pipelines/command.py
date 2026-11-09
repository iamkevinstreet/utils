########################################################################
#                                                                      #
#                  pipelines/kds/pipelines/command.py                  #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

The one command a project's Makefile, CI and DAGs run, `python -m
pipelines`: `load NAME` runs one of the project's loads, and `dbt ...`
passes the rest to dbt over the same warehouse. A project names its
loads and how its settings are read; everything else is here, so every
project's command reads and behaves the same.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from typing import Final

# Local
from kds.args import required
from kds.logs import get_logger, setup_logging
from kds.pipelines.settings import PipelineSettings
from kds.pipelines.transform import run_dbt

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
# log.debug("Sets the subcommand that runs a load")
LOAD: Final = "load"
# log.debug("Sets the subcommand that runs dbt")
DBT: Final = "dbt"
# log.debug("Sets what the command does, for its help")
ABOUT: Final = "Load the warehouse's sources, or run dbt over them."


########################################################################
#                                                                      #
#                             The command                              #
#                                                                      #
########################################################################
# log.debug("Defines the command line every project's pipelines share")
def run_command[S: PipelineSettings](
    loads: Mapping[str, Callable[[S], None]] | None = None,
    get_settings: Callable[[], S] | None = None,
    argv: Sequence[str] | None = None,
) -> int:
    """Runs one load or one dbt command.

    Args:
        loads: Each load the project has, by its name on the command
            line. Required.
        get_settings: Reads the project's settings. Required.
        argv: The command's arguments; the process's own when None.

    Returns:
        0 on success; 1 when dbt failed. A failed load raises.
    """
    # log.debug("Takes the loads, which the caller must give")
    loads = required(loads=loads)
    # log.debug("Takes how the settings are read, which the caller must give")
    get_settings = required(get_settings=get_settings)
    # log.debug("Describes the command")
    parser = argparse.ArgumentParser(prog="pipelines", description=ABOUT)
    # log.debug("Adds the two subcommands")
    commands = parser.add_subparsers(dest="command", required=True)
    # log.debug("Adds the load subcommand, by the load's name")
    commands.add_parser(LOAD, help="load one source").add_argument("name", choices=list(loads))
    # log.debug("Adds the dbt subcommand, passing everything after it through")
    commands.add_parser(DBT, help="run dbt").add_argument("args", nargs=argparse.REMAINDER)
    # log.debug("Parses the command line")
    args = parser.parse_args(argv)
    # log.debug("Reads the settings")
    settings = get_settings()
    # log.debug("Starts logging to the configured folder")
    setup_logging(settings)
    # log.debug("Runs a load")
    if args.command == LOAD:
        # log.debug("Runs the named load")
        loads[args.name](settings)
        # log.debug("Reports success")
        return 0
    # log.debug("Runs dbt, failing the command when dbt failed")
    return 0 if run_dbt(settings, args.args) else 1
