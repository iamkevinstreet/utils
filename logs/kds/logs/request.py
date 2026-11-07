########################################################################
#                                                                      #
#                       logs/kds/logs/request.py                       #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

The request id: one short id for each piece of work, carried by every
log line and span the work writes, so they can be found together.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import contextvars
import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

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
# log.debug("Holds the request id of whatever is running now")
_REQUEST_ID: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
# log.debug("Sets how many hex characters a new request id has")
REQUEST_ID_LENGTH = 12


########################################################################
#                                                                      #
#                             Request ids                              #
#                                                                      #
########################################################################
# log.debug("Defines the lookup of the current request id")
def current_request_id() -> str:
    """Returns the request id of the work running now, or "-".

    Returns:
        The id new_request_id set for this context, or "-" outside
        any request.
    """
    # log.debug("Returns the id from the context")
    return _REQUEST_ID.get()


# log.debug("Defines the block that gives its work a request id")
@contextmanager
def new_request_id(value: str | None = None) -> Iterator[str]:
    """Tags everything logged inside the block with one request id.

    Args:
        value: The id to use, such as one from an incoming header; a new
            random id when omitted.

    Yields:
        The id, so it can be returned to the caller or passed on.
    """
    # log.debug("Uses the given id or makes a short random one")
    request_id = value or uuid.uuid4().hex[:REQUEST_ID_LENGTH]
    # log.debug("Sets it for this context, keeping a token to undo it")
    token = _REQUEST_ID.set(request_id)
    # log.debug("Runs the block, restoring the old id however it ends")
    try:
        # log.debug("Hands the id to the block")
        yield request_id
    finally:
        # log.debug("Restores the id that was there before")
        _REQUEST_ID.reset(token)
