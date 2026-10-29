########################################################################
#                       logs/tests/test_logs.py                        #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-29                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests the JSON lines, request ids, one-time      #
#                     setup and the HH:MM:SS trace format.             #
########################################################################
"""Tests for kds.logs setup, events and traces."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from kds.logs import (
    HANDLER_NAME,
    TraceFormatter,
    elapsed,
    get_logger,
    log_event,
    new_request_id,
    setup_logging,
)
from kds.settings import Settings

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the pattern every trace line must match")
TRACE_LINE = re.compile(r"\d{2}:\d{2}:\d{2} - Splits the question")


# log.debug("Defines a fixture that removes this module's handlers")
@pytest.fixture
def clean_root() -> Iterator[logging.Logger]:
    """Yield the root logger, then remove and close our handlers."""
    # log.debug("Finds the root logger")
    root = logging.getLogger()
    # log.debug("Hands it to the test")
    yield root
    # log.debug("Removes each handler the setup added")
    for handler in [h for h in root.handlers if h.get_name() == HANDLER_NAME]:
        # log.debug("Detaches the handler")
        root.removeHandler(handler)
        # log.debug("Closes its file or stream")
        handler.close()


# log.debug("Defines the test that the clock reads HH:MM:SS")
def test_elapsed_format() -> None:
    """The elapsed time is three two-digit fields."""
    # log.debug("Checks the clock's shape")
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", elapsed())


# log.debug("Defines the test of the trace line's format")
def test_trace_line_format() -> None:
    """A debug record prints as HH:MM:SS - its message."""
    # log.debug("Builds a debug record by hand")
    record = logging.LogRecord("t", logging.DEBUG, __file__, 1, "Splits the question", None, None)
    # log.debug("Checks the formatted line")
    assert TRACE_LINE.fullmatch(TraceFormatter().format(record))


# log.debug("Defines the test of an event written as JSON")
def test_event_is_redacted_json(tmp_path: Path, clean_root: logging.Logger) -> None:
    """An event becomes one JSON line with its request id, redacted."""
    # log.debug("Sets up logging into the test's folder")
    path = setup_logging(Settings(_env_file=None, log_dir=tmp_path))
    # log.debug("Logs an event holding an email, inside a request")
    with new_request_id("req-1"):
        # log.debug("Logs the event")
        log_event(get_logger("test"), "intake.start", email="person@example.com")
    # log.debug("Reads the last line of the log file")
    line = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    # log.debug("Checks the request id was attached")
    assert line["request_id"] == "req-1"
    # log.debug("Checks the email was redacted")
    assert line["email"] == "[EMAIL]"


# log.debug("Defines the test that setup runs only once")
def test_setup_is_idempotent(tmp_path: Path, clean_root: logging.Logger) -> None:
    """A second setup adds no handlers and returns the same file."""
    # log.debug("Builds settings that log into the test's folder")
    settings = Settings(_env_file=None, log_dir=tmp_path)
    # log.debug("Sets up logging the first time")
    first = setup_logging(settings)
    # log.debug("Counts the root logger's handlers")
    count = len(clean_root.handlers)
    # log.debug("Checks a second setup returns the same file")
    assert setup_logging(settings) == first
    # log.debug("Checks it added no handlers")
    assert len(clean_root.handlers) == count
