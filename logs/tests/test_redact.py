########################################################################
#                      logs/tests/test_redact.py                       #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests that redaction removes each identifier,    #
#                     named terms and nested values, and nothing else. #
########################################################################
"""Tests for kds.logs.redact."""

from __future__ import annotations

import logging

from kds.logs.redact import redact, redact_obj

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets a made-up sentence holding one of each identifier")
SENTENCE = (
    "Call 404-555-0133 or mail kevin@example.com. SSN 123-45-6789, "
    "card 4111 1111 1111 1111, DOB 04/12/1990."
)


# log.debug("Defines the test that each identifier is replaced")
def test_redacts_common_identifiers() -> None:
    """Phone, email, SSN, card and birth date each become a label."""
    # log.debug("Redacts the sentence")
    out = redact(SENTENCE)
    # log.debug("Checks every label appears")
    assert all(label in out for label in ("[PHONE]", "[EMAIL]", "[SSN]", "[CARD]", "[DOB]"))
    # log.debug("Checks the original values are gone")
    assert "404-555" not in out and "example.com" not in out


# log.debug("Defines the test for named terms in nested values")
def test_extra_terms_and_nested_objects() -> None:
    """Names are replaced in any case, deep inside dicts and lists."""
    # log.debug("Builds a structure with a name in two places")
    obj = {"note": "Spoke with Avery Bennett", "items": ["avery bennett called", 42, None]}
    # log.debug("Redacts it with the name as an extra term")
    out = redact_obj(obj, extra_terms=["Avery Bennett"])
    # log.debug("Checks the name in the dict value is replaced")
    assert out["note"] == "Spoke with [NAME]"
    # log.debug("Checks the lower-case name in the list is replaced")
    assert out["items"][0] == "[NAME] called"
    # log.debug("Checks the number and None pass through")
    assert out["items"][1:] == [42, None]


# log.debug("Defines the test that plain text is left alone")
def test_plain_text_untouched() -> None:
    """Text without identifiers comes back exactly as it went in."""
    # log.debug("Checks plain words are unchanged")
    assert redact("no identifiers here") == "no identifiers here"
