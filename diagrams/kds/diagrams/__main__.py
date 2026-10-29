########################################################################
#                  diagrams/kds/diagrams/__main__.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

The kds-diagrams command: draws every diagram in a spec file, such as
docs/diagrams.toml.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import argparse
import logging
from pathlib import Path

# Local
from kds.diagrams.spec import render_file

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                             Command line                             #
########################################################################
# log.debug("Defines the command's entry point")
def main(argv: list[str] | None = None) -> int:
    """Draws each diagram in each spec file named on the command line.

    Args:
        argv: The arguments after the command's name; None reads them
            from the command line.

    Returns:
        The exit status: 0 once every diagram is written.
    """
    # log.debug("Describes the command and its one argument")
    parser = argparse.ArgumentParser(prog="kds-diagrams", description="Draw README diagrams.")
    # log.debug("Takes one or more spec files")
    parser.add_argument("specs", nargs="+", type=Path, help="TOML files of [[diagram]] tables")
    # log.debug("Reads the arguments")
    args = parser.parse_args(argv)
    # log.debug("Draws each spec's diagrams")
    for spec in args.specs:
        # log.debug("Reports each file written")
        for path in render_file(spec):
            # log.debug("Prints the path")
            print(f"wrote {path}")
    # log.debug("Returns success")
    return 0


# log.debug("Runs the command when the module is run directly")
if __name__ == "__main__":
    # log.debug("Exits with the command's status")
    raise SystemExit(main())
