"""Structured logging: one JSON object per line, a request id on every record, redaction on by default.

Usage:
    from kds.logs import get_logger, new_request_id, log_event
    log = get_logger("eeoc.extract")
    with new_request_id():
        log_event(log, "extract.start", doc="charge-0007.pdf")
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kds.logs.redact import redact_obj
from kds.settings import get_settings

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_configured = False


def current_request_id() -> str:
    return _request_id.get()


@contextmanager
def new_request_id(value: str | None = None) -> Iterator[str]:
    """Set a request id for everything logged inside the block."""
    rid = value or uuid.uuid4().hex[:12]
    token = _request_id.set(rid)
    try:
        yield rid
    finally:
        _request_id.reset(token)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": current_request_id(),
            "msg": record.getMessage(),
        }
        extra = getattr(record, "event", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> Path:
    """Configure the root logger once. Returns the log file path."""
    global _configured
    settings = get_settings()
    directory = Path(log_dir or settings.log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now(UTC):%Y-%m-%d}.jsonl"
    if _configured:
        return path
    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(_JsonFormatter())
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(_JsonFormatter())
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    _configured = True
    return path


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


def log_event(logger: logging.Logger, kind: str, level: int = logging.INFO, **fields: Any) -> None:
    """Log a structured event. Fields are redacted unless LOG_REDACT is false."""
    settings = get_settings()
    data = {"kind": kind, **fields}
    if settings.log_redact:
        data = redact_obj(data)
    logger.log(level, kind, extra={"event": data})
