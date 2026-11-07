########################################################################
#                                                                      #
#                        logs/kds/logs/steps.py                        #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Steps: the spans a project's code opens around its own work, and the
file an evaluation run keeps them in.

step() runs a block as one span, nested under whatever span is open,
and records the error type if the block fails, but never the error's
message, which can hold the data being worked on. Text set on a span is
redacted as log lines are. While spans are off, a step costs nothing.
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
import threading
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# Third-party
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.trace import Span, SpanKind, Status, StatusCode
from opentelemetry.util.types import AttributeValue

# Local
from kds.args import required
from kds.logs.config import ENCODING, ERROR_TYPE
from kds.logs.redact import redact_obj
from kds.settings import get_settings

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
# log.debug("Names the code a project's own steps are recorded under")
SCOPE = "kds.logs"
# log.debug("Sets the most spans one run keeps in memory for its file")
MAX_KEPT = 100_000
# log.debug("Lists the value types a span attribute holds as they are")
PLAIN = (bool, int, float, str)


########################################################################
#                                                                      #
#                                Steps                                 #
#                                                                      #
########################################################################
# log.debug("Defines the block that runs as one span")
@contextmanager
def step(
    name: str | None = None,
    attributes: Mapping[str, Any] | None = None,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    scope: str = SCOPE,
    **fields: Any,
) -> Iterator[Span]:
    """Runs the block as one span named `name`, under any open span.

    A failure is recorded by its type alone, and the span is marked as
    failed; the error goes on to the caller unchanged.

    Args:
        name: The step's name, short and the same for every call, such
            as "verify". Required.
        attributes: Attributes whose names have dots, such as
            "gen_ai.operation.name".
        kind: INTERNAL for the project's own work, CLIENT for a call to
            another service.
        scope: The code the span is recorded under.
        **fields: More attributes, named as plain words.

    Yields:
        The span, to set what the step found on it.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Finds the tracer for the code the step belongs to")
    tracer = trace.get_tracer(scope)
    # log.debug("Puts the dotted attributes and the plain ones together")
    given = {**(attributes or {}), **fields}
    # log.debug("Opens the span; errors are recorded here, not by the library")
    with tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=values(given),
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        # log.debug("Runs the block inside the span")
        try:
            # log.debug("Hands the span to the block")
            yield span
        except Exception as error:
            # log.debug("Records the error's type, never its message")
            span.set_attribute(ERROR_TYPE, type(error).__name__)
            # log.debug("Marks the span as failed")
            span.set_status(Status(StatusCode.ERROR, type(error).__name__))
            # log.debug("Passes the error on unchanged")
            raise


# log.debug("Defines how values become span attributes")
def values(fields: Mapping[str, Any] | None = None) -> dict[str, AttributeValue]:
    """Returns the fields as span attributes, redacted like log lines.

    None is left out; a number, string or yes/no stays as it is; a list
    of those stays a list; anything else becomes JSON text.

    Args:
        fields: The attributes by name. Required.

    Returns:
        The attributes a span can hold, with personal data redacted
        unless the settings turn redaction off.
    """
    # log.debug("Takes the fields, which the caller must give")
    fields = required(fields=fields)
    # log.debug("Converts each value the span cannot hold as it is")
    converted = {key: _value(value) for key, value in fields.items() if value is not None}
    # log.debug("Returns them redacted unless the settings turn that off")
    return redact_obj(converted) if get_settings().log_redact else converted


# log.debug("Defines how one value becomes something a span can hold")
def _value(value: Any = None) -> AttributeValue:
    """Returns the value as a span attribute value.

    Args:
        value: The value to set. Required.

    Returns:
        The value itself, a list of plain values, JSON text for a table
        or a mixed list, or the text of anything else.
    """
    # log.debug("Takes the value, which the caller must give")
    value = required(value=value)
    # log.debug("Keeps a number, string or yes/no as it is")
    if isinstance(value, PLAIN):
        # log.debug("Returns it unchanged")
        return value
    # log.debug("Keeps a list of plain values of one type as a list")
    if isinstance(value, list | tuple) and _plain_list(value):
        # log.debug("Returns the list")
        return list(value)
    # log.debug("Writes a table or a mixed list as JSON")
    if isinstance(value, dict | list | tuple):
        # log.debug("Returns the JSON, odd types inside it as their text")
        return json.dumps(value, default=str, ensure_ascii=False)
    # log.debug("Writes anything else, such as a path, as its text")
    return str(value)


# log.debug("Defines the check for a list a span can hold")
def _plain_list(items: Sequence[Any] | None = None) -> bool:
    """Returns whether every item is plain and of one type.

    Args:
        items: The list to check. Required.

    Returns:
        True when the items are all strings, all numbers or all yes/no.
    """
    # log.debug("Takes the items, which the caller must give")
    items = required(items=items)
    # log.debug("Returns whether there is one plain type among them")
    return len({type(item) for item in items}) == 1 and isinstance(items[0], PLAIN)


# log.debug("Defines how a step records what it found")
def set_values(span: Span | None = None, fields: Mapping[str, Any] | None = None) -> None:
    """Sets the fields on the span as attributes, redacted.

    Args:
        span: The span to set them on. Required.
        fields: The attributes by name. Required.
    """
    # log.debug("Takes the span, which the caller must give")
    span = required(span=span)
    # log.debug("Takes the fields, which the caller must give")
    fields = required(fields=fields)
    # log.debug("Sets the converted, redacted attributes")
    span.set_attributes(values(fields))


# log.debug("Defines the processor that keeps a run's spans")
class Keeper(SpanProcessor):
    """Keeps every span that ends while a run is collecting them."""

    # log.debug("Defines the constructor")
    def __init__(self) -> None:
        """Starts with nothing to keep."""
        # log.debug("Guards the list against spans ending on other threads")
        self._lock = threading.Lock()
        # log.debug("Holds the spans kept so far, or None while not collecting")
        self._kept: list[ReadableSpan] | None = None

    # log.debug("Defines what happens as each span ends")
    def on_end(self, span: ReadableSpan) -> None:  # fixed: SpanProcessor's signature
        """Keeps the span while a run is collecting, up to the limit.

        Args:
            span: The span that just ended.
        """
        # log.debug("Works under the lock")
        with self._lock:
            # log.debug("Keeps the span when collecting and under the limit")
            if self._kept is not None and len(self._kept) < MAX_KEPT:
                # log.debug("Adds it to the run's spans")
                self._kept.append(span)

    # log.debug("Defines the start of collecting")
    def start(self) -> list[ReadableSpan]:
        """Starts keeping spans; returns the list they are kept in.

        Returns:
            The list, which fills as spans end.
        """
        # log.debug("Works under the lock")
        with self._lock:
            # log.debug("Starts an empty list unless one is filling already")
            self._kept = [] if self._kept is None else self._kept
            # log.debug("Returns the list")
            return self._kept

    # log.debug("Defines the end of collecting")
    def stop(self) -> None:
        """Stops keeping spans; a list already returned stays as is."""
        # log.debug("Works under the lock")
        with self._lock:
            # log.debug("Lets go of the list")
            self._kept = None


# log.debug("Holds the one keeper setup_spans adds when runs keep spans")
KEEPER = Keeper()


# log.debug("Defines the block whose spans a run keeps")
@contextmanager
def collect() -> Iterator[list[ReadableSpan]]:
    """Keeps every span that ends inside the block.

    Spans are kept only when setup_spans added the keeper, which it does
    when spans_keep is on; otherwise the list stays empty.

    Yields:
        The list the spans are kept in, which fills as spans end.
    """
    # log.debug("Starts keeping spans")
    kept = KEEPER.start()
    # log.debug("Runs the block, stopping however it ends")
    try:
        # log.debug("Hands the list to the block")
        yield kept
    finally:
        # log.debug("Stops keeping spans")
        KEEPER.stop()


# log.debug("Defines how a run's spans are written to a file")
def write_spans(spans: Sequence[ReadableSpan] | None = None, path: Path | None = None) -> Path:
    """Writes the spans to `path`, one JSON object per line.

    Each line is the span as OpenTelemetry writes it: its name, ids,
    parent, kind, start and end times, status, attributes and events.

    Args:
        spans: The spans to write, in the order they ended. Required.
        path: The file to write. Required.

    Returns:
        The path written.
    """
    # log.debug("Takes the spans, which the caller must give")
    spans = required(spans=spans)
    # log.debug("Takes the path, which the caller must give")
    path = required(path=path)
    # log.debug("Writes each span as one line of compact JSON")
    lines = [json.dumps(json.loads(span.to_json()), separators=(",", ":")) for span in spans]
    # log.debug("Writes the lines, ending with a newline")
    path.write_text("".join(f"{line}\n" for line in lines), encoding=ENCODING)
    # log.debug("Returns the path")
    return path
