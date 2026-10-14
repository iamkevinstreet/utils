"""Redaction for logs and audit records.

The patterns are deliberately simple and a little greedy. In a prototype it is better to redact a harmless
number than to leak a real one. Add names of real people to `extra_terms` if a dataset ever contains any.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("PHONE", re.compile(r"(?<!\w)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\w)")),
    ("DOB", re.compile(r"\b(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b")),
]


def redact(text: str, extra_terms: Iterable[str] = ()) -> str:
    """Replace emails, phone numbers, SSNs, card numbers, dates of birth and any extra terms."""
    out = text
    for label, pattern in _PATTERNS:
        out = pattern.sub(f"[{label}]", out)
    for term in extra_terms:
        if term:
            out = re.sub(re.escape(term), "[NAME]", out, flags=re.IGNORECASE)
    return out


def redact_obj(obj: Any, extra_terms: Iterable[str] = ()) -> Any:
    """Walk dicts, lists and strings and redact every string leaf. Other types pass through unchanged."""
    terms = tuple(extra_terms)
    if isinstance(obj, str):
        return redact(obj, terms)
    if isinstance(obj, dict):
        return {k: redact_obj(v, terms) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [redact_obj(v, terms) for v in obj]
    return obj
