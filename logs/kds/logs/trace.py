########################################################################
#                        logs/kds/logs/trace.py                        #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

The time since the process started as HH:MM:SS, and the trace output the
logger lines print.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import sys
import time

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Notes when this module loaded, as the process start")
_STARTED = time.monotonic()
# log.debug("Sets the seconds in an hour, for the HH part")
SECONDS_PER_HOUR = 3600
# log.debug("Sets the seconds in a minute, for the MM part")
SECONDS_PER_MINUTE = 60
# log.debug("Sets the format every trace line uses")
TRACE_FORMAT = "%(elapsed)s - %(message)s"


########################################################################
#                             Trace lines                              #
########################################################################
# log.debug("Defines the clock every trace line reads")
def elapsed() -> str:
    """Returns the time since the process started, as HH:MM:SS.

    Returns:
        The hours, minutes and seconds, each at least two digits.
    """
    # log.debug("Measures whole seconds since the process started")
    seconds = int(time.monotonic() - _STARTED)
    # log.debug("Splits the seconds into hours and the remainder")
    hours, rest = divmod(seconds, SECONDS_PER_HOUR)
    # log.debug("Splits the remainder into minutes and seconds")
    minutes, seconds = divmod(rest, SECONDS_PER_MINUTE)
    # log.debug("Returns the three parts as two-digit fields")
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# log.debug("Defines the formatter that puts the clock first")
class TraceFormatter(logging.Formatter):
    """Formats each record as 'HH:MM:SS - message'."""

    # log.debug("Defines the constructor with the trace format")
    def __init__(self) -> None:
        """Uses the trace format for every record."""
        # log.debug("Hands the trace format to the base formatter")
        super().__init__(TRACE_FORMAT)

    # log.debug("Defines how one record becomes one trace line")
    def format(self, record: logging.LogRecord) -> str:  # fixed: logging.Formatter's signature
        """Stamps the record with the elapsed time, then formats it.

        Args:
            record: The record to format.

        Returns:
            The line: the elapsed time, a dash and the message.
        """
        # log.debug("Stamps the record with the time since start")
        record.elapsed = elapsed()
        # log.debug("Returns the record in the trace format")
        return super().format(record)


# log.debug("Defines the switch that prints trace lines to stderr")
def trace_to_stderr(level: int = logging.DEBUG) -> logging.Handler:
    """Prints every record at `level` or above to stderr as a trace.

    Args:
        level: The lowest level printed; debug shows every logger line.

    Returns:
        The handler, so a caller can remove it again.
    """
    # log.debug("Creates a handler that writes to stderr")
    handler = logging.StreamHandler(sys.stderr)
    # log.debug("Gives the handler the trace format")
    handler.setFormatter(TraceFormatter())
    # log.debug("Sets the handler to the requested level")
    handler.setLevel(level)
    # log.debug("Finds the root logger every module logger feeds")
    root = logging.getLogger()
    # log.debug("Lets the root logger pass records at that level")
    root.setLevel(min(root.level or level, level))
    # log.debug("Attaches the trace handler to the root logger")
    root.addHandler(handler)
    # log.debug("Returns the handler to the caller")
    return handler
