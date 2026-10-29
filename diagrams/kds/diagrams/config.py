########################################################################
#                   diagrams/kds/diagrams/config.py                    #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

The values the diagram modules share, each named once. A library cannot
read a project's config files, so the values two of its modules use live
here.
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
# log.debug("Sets the encoding the spec is read and the drawings written in")
ENCODING = "utf-8"
