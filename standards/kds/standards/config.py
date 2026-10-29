########################################################################
#                  standards/kds/standards/config.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

The values the checker's modules share, each named once. A library
cannot read a project's config files, so the values two of its modules
use live here, and each module takes them in its Global constants.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the encoding every file is read and written in")
ENCODING = "utf-8"
# log.debug("Sets the fence that opens and closes Astro frontmatter")
FENCE = "---"
# log.debug("Sets the fewest words a logger line's description may have")
MIN_WORDS = 2
# log.debug("Sets the last segment of a config module's path")
CONFIG_MODULE = "config"
# log.debug("Names the rule every import-label finding belongs to")
IMPORT_RULE = "imports"
# log.debug("Names the rule every logger-line finding belongs to")
LOGGER_RULE = "logger-line"
# log.debug("Names the rule every function finding belongs to")
FUNCTIONS_RULE = "functions"
# log.debug("Sets the extension of Python files")
PYTHON_SUFFIX = ".py"
# log.debug("Lists the script extensions, Astro components included")
SCRIPTS = (".ts", ".tsx", ".js", ".mjs", ".cjs", ".astro")
