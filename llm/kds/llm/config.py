########################################################################
#                        llm/kds/llm/config.py                         #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

The values the model adapter's modules share, each named once. A library
cannot read a project's config files, so the values two of its modules
use live here.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from typing import Final

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Sets the milliseconds in a second, for timing each call")
MS: Final = 1000
# log.debug("Names the key that says who speaks in a message")
ROLE: Final = "role"
# log.debug("Names the key that holds what a message or block says")
CONTENT: Final = "content"
# log.debug("Names the key that says what kind a content block is")
TYPE: Final = "type"
# log.debug("Names the key that holds a tool's name")
NAME: Final = "name"
# log.debug("Names the role of the person or program asking")
USER: Final = "user"
# log.debug("Names the role of the model answering")
ASSISTANT: Final = "assistant"
