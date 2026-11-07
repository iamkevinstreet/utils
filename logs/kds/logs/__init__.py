########################################################################
#                                                                      #
#                      logs/kds/logs/__init__.py                       #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-11-07

Structured logs: one JSON object per line, a request id on each,
redaction, trace lines; and spans, the timed steps of the work, which
OpenTelemetry sends to Langfuse or any other tracing tool.

Usage, once when a service starts:
    setup_logging(settings)
    setup_spans(settings, service="grounded-qa")

then in any module:
    log = get_logger(__name__)
    with new_request_id(), step("intake"):
        log_event(log, "intake.start", email="person@example.com")

A line logged inside a span carries the span's trace id, so a log line
leads to its trace.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Third-party
from opentelemetry.trace import get_current_span

# Local
from kds.args import required
from kds.logs.config import ENCODING
from kds.logs.redact import redact, redact_obj
from kds.logs.request import current_request_id, new_request_id
from kds.logs.spans import flush_spans, session, setup_spans
from kds.logs.steps import collect, set_values, step, write_spans
from kds.logs.trace import TraceFormatter, elapsed, trace_to_stderr
from kds.settings import Settings, get_settings

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
# log.debug("Names the handlers this module adds, so it adds them once")
HANDLER_NAME = "kds.logs"
# log.debug("Names the record attribute an event's fields travel in")
EVENT = "event"
# log.debug("Lists what the package exports")
__all__ = [
    "TraceFormatter",
    "collect",
    "current_request_id",
    "elapsed",
    "flush_spans",
    "get_logger",
    "log_event",
    "new_request_id",
    "redact",
    "redact_obj",
    "session",
    "set_values",
    "setup_logging",
    "setup_spans",
    "step",
    "trace_to_stderr",
    "write_spans",
]


########################################################################
#                                                                      #
#                          Structured logging                          #
#                                                                      #
########################################################################
# log.debug("Defines the formatter that writes one JSON object per record")
class JsonFormatter(logging.Formatter):
    """Formats each record as one line of JSON with its request id."""

    # log.debug("Defines how one record becomes one JSON line")
    def format(self, record: logging.LogRecord) -> str:  # fixed: logging.Formatter's signature
        """Returns the record as a JSON object on a single line.

        Args:
            record: The record to format.

        Returns:
            One line of JSON: the time, level, logger, request id and
            message, any event fields, and the traceback if logged.
        """
        # log.debug("Collects the fields every line carries")
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": current_request_id(),
            "msg": record.getMessage(),
        }
        # log.debug("Adds the structured fields of an event, if any")
        payload |= getattr(record, EVENT, None) or {}
        # log.debug("Finds the span the line was logged in, if any")
        span = get_current_span().get_span_context()
        # log.debug("Adds the trace and span ids, so the line leads to its span")
        if span.is_valid:
            # log.debug("Writes both ids as hex, as tracing tools show them")
            payload |= {"trace_id": f"{span.trace_id:032x}", "span_id": f"{span.span_id:016x}"}
        # log.debug("Adds the traceback when an exception was logged")
        if record.exc_info:
            # log.debug("Formats the traceback into the line")
            payload["exc"] = self.formatException(record.exc_info)
        # log.debug("Returns the line, with anything unusual as text")
        return json.dumps(payload, default=str, ensure_ascii=False)


# log.debug("Defines the one-time setup of logging for a service")
def setup_logging(settings: Settings | None = None) -> Path:
    """Sends JSON lines to today's file and stderr; adds traces if on.

    Safe to call more than once: later calls change nothing.

    Args:
        settings: The service's settings; the shared ones by default.

    Returns:
        The path of today's log file.
    """
    # log.debug("Uses the shared settings unless the caller passed its own")
    settings = settings or get_settings()
    # log.debug("Names today's file in the configured folder")
    path = settings.log_dir / f"{datetime.now(UTC):%Y-%m-%d}.jsonl"
    # log.debug("Finds the root logger every module logger feeds")
    root = logging.getLogger()
    # log.debug("Stops when this module already set the root logger up")
    if any(handler.get_name() == HANDLER_NAME for handler in root.handlers):
        # log.debug("Returns the file without adding handlers twice")
        return path
    # log.debug("Creates the log folder")
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    # log.debug("Reads the configured level as a number")
    level = logging.getLevelNamesMapping()[settings.log_level]
    # log.debug("Adds a JSON handler for the file and one for stderr")
    for handler in (
        logging.FileHandler(path, encoding=ENCODING),
        logging.StreamHandler(sys.stderr),
    ):
        # log.debug("Names the handler so a second setup can find it")
        handler.set_name(HANDLER_NAME)
        # log.debug("Sets the handler to the configured level")
        handler.setLevel(level)
        # log.debug("Gives it the JSON format")
        handler.setFormatter(JsonFormatter())
        # log.debug("Attaches it to the root logger")
        root.addHandler(handler)
    # log.debug("Lets the root logger pass the configured level")
    root.setLevel(level)
    # log.debug("Adds the trace lines when the settings ask for them")
    if settings.log_trace:
        # log.debug("Prints debug lines as HH:MM:SS - what happened")
        trace = trace_to_stderr()
        # log.debug("Keeps the trace to debug lines; JSON shows the rest")
        trace.addFilter(lambda record: record.levelno == logging.DEBUG)
    # log.debug("Returns the log file's path")
    return path


# log.debug("Defines the logger lookup services use")
def get_logger(name: str | None = None) -> logging.Logger:
    """Returns the named logger; `setup_logging` sets where it goes.

    Args:
        name: The logger's name, usually the module's __name__.
            Required.

    Returns:
        The standard library's logger of that name.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Returns the standard library's logger for the name")
    return logging.getLogger(name)


# log.debug("Defines how a structured event is logged")
def log_event(
    logger: logging.Logger | None = None,
    kind: str | None = None,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Logs an event and its fields; fields are redacted unless off.

    Args:
        logger: The module's logger. Required.
        kind: A dotted event name, such as "llm.call". Required.
        level: The level to log at.
        **fields: The event's data; strings in it are redacted.
    """
    # log.debug("Takes the logger, which the caller must give")
    logger = required(logger=logger)
    # log.debug("Takes the kind, which the caller must give")
    kind = required(kind=kind)
    # log.debug("Puts the event's name first among its fields")
    data = {"kind": kind, **fields}
    # log.debug("Redacts personal data unless the settings turn it off")
    if get_settings().log_redact:
        # log.debug("Replaces emails, phone numbers and the like")
        data = redact_obj(data)
    # log.debug("Logs the event with its fields attached")
    logger.log(level, kind, extra={EVENT: data})
