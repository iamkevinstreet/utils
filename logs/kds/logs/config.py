########################################################################
#                                                                      #
#                       logs/kds/logs/config.py                        #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

The values more than one file of kds.logs uses.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
from typing import Final

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
# log.debug("Sets the encoding log and span files are written in")
ENCODING: Final = "utf-8"
# log.debug("Names the attribute that says what kind of error ended a span")
ERROR_TYPE: Final = "error.type"
