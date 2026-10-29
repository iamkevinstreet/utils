########################################################################
#                       logs/kds/logs/redact.py                        #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Removes emails, phone numbers, SSNs, card numbers, birth dates and named
terms from text.

The patterns are simple and a little greedy on purpose: in logs it is
better to redact a harmless number than to leak a real one. Pass
the names of real people as `extra_terms` if a dataset ever has any.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import Any

# Local
from kds.args import required

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists each kind of identifier and the pattern that finds it")
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("PHONE", re.compile(r"(?<!\w)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\w)")),
    ("DOB", re.compile(r"\b(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b")),
)
# log.debug("Sets the placeholder a named term becomes")
NAME_LABEL = "[NAME]"


########################################################################
#                       Personal data redaction                        #
########################################################################
# log.debug("Defines redaction of one string")
def redact(text: str | None = None, extra_terms: Iterable[str] = ()) -> str:
    """Replaces identifiers and extra terms with labels like [EMAIL].

    Args:
        text: The text to clean. Required.
        extra_terms: Exact words to remove too, such as real names;
            matched without regard to case.

    Returns:
        The text with every match replaced by its label.
    """
    # log.debug("Takes the text, which the caller must give")
    text = required(text=text)
    # log.debug("Starts from the original text")
    out = text
    # log.debug("Applies each identifier pattern in turn")
    for label, pattern in PATTERNS:
        # log.debug("Replaces every match with the pattern's label")
        out = pattern.sub(f"[{label}]", out)
    # log.debug("Replaces each extra term that is not empty")
    for term in filter(None, extra_terms):
        # log.debug("Replaces the term wherever it appears, in any case")
        out = re.sub(re.escape(term), NAME_LABEL, out, flags=re.IGNORECASE)
    # log.debug("Returns the cleaned text")
    return out


# log.debug("Defines redaction of a whole structure")
def redact_obj(obj: Any = None, extra_terms: Iterable[str] = ()) -> Any:
    """Redacts every string inside dicts, lists and tuples.

    Other values (numbers, None, booleans) pass through unchanged.

    Args:
        obj: The value to clean, at any depth.
        extra_terms: Exact words to remove too, such as real names;
            matched without regard to case.

    Returns:
        The value with every string in it redacted and dict keys
        kept; a tuple comes back as a list.
    """
    # log.debug("Fixes the terms so a generator is read only once")
    terms = tuple(extra_terms)
    # log.debug("Redacts a string directly")
    if isinstance(obj, str):
        # log.debug("Returns the redacted string")
        return redact(obj, terms)
    # log.debug("Redacts each value of a dict, keeping its keys")
    if isinstance(obj, dict):
        # log.debug("Returns the dict with redacted values")
        return {key: redact_obj(value, terms) for key, value in obj.items()}
    # log.debug("Redacts each item of a list or tuple")
    if isinstance(obj, list | tuple):
        # log.debug("Returns the items as a redacted list")
        return [redact_obj(value, terms) for value in obj]
    # log.debug("Returns any other value as it was")
    return obj
