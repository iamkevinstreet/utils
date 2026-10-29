########################################################################
#                        llm/kds/llm/errors.py                         #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

The errors the adapter raises, and the test that says whether a failed
call is worth retrying.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Third-party
import anthropic
import openai

# Local
from kds.args import required

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists the HTTP statuses that can succeed if tried again")
RETRY_STATUSES = frozenset({408, 409, 429})
# log.debug("Sets the lowest server-error status, also retried")
SERVER_ERROR = 500


########################################################################
#                          Errors and retries                          #
########################################################################
# log.debug("Defines the error for a run that has spent its budget")
class BudgetExceededError(RuntimeError):
    """The run reached its spending limit; no further calls are made."""


# log.debug("Defines the error for output that never matched the schema")
class StructuredOutputError(ValueError):
    """The model's output did not validate, even after one repair."""


# log.debug("Defines the error for a call that may succeed if retried")
class TransientError(RuntimeError):
    """A failure that may succeed if tried again; fakes raise it."""


# log.debug("Defines the test for a provider failure worth retrying")
def is_transient(error: Exception | None = None) -> bool:
    """Returns True for failures that can succeed if tried again.

    Retried: connection failures and timeouts; statuses 408, 409, 429
    and any 5xx (Anthropic's 529 overload included). Never retried:
    bad requests, auth failures, missing models: retrying cannot help.

    Args:
        error: The error a provider call raised. Required.

    Returns:
        True when trying the call again may succeed.
    """
    # log.debug("Takes the error, which the caller must give")
    error = required(error=error)
    # log.debug("Retries our own transient error and dropped connections")
    if isinstance(
        error, TransientError | anthropic.APIConnectionError | openai.APIConnectionError
    ):
        # log.debug("Returns retry")
        return True
    # log.debug("Returns no retry for anything that is not an HTTP error")
    if not isinstance(error, anthropic.APIStatusError | openai.APIStatusError):
        # log.debug("Returns no retry")
        return False
    # log.debug("Returns retry for a retryable status or a server error")
    return error.status_code in RETRY_STATUSES or error.status_code >= SERVER_ERROR
