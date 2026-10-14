from kds.logs.redact import redact, redact_obj


def test_redacts_common_identifiers():
    text = "Call 404-555-0133 or mail kevin@example.com. SSN 123-45-6789, card 4111 1111 1111 1111, DOB 04/12/1990."
    out = redact(text)
    assert "[PHONE]" in out and "[EMAIL]" in out and "[SSN]" in out and "[CARD]" in out and "[DOB]" in out
    assert "404-555" not in out and "example.com" not in out


def test_extra_terms_and_nested_objects():
    obj = {"note": "Spoke with Avery Bennett", "items": ["avery bennett called", 42, None]}
    out = redact_obj(obj, extra_terms=["Avery Bennett"])
    assert out["note"] == "Spoke with [NAME]"
    assert out["items"][0] == "[NAME] called"
    assert out["items"][1] == 42 and out["items"][2] is None


def test_plain_text_untouched():
    assert redact("Charge number 510-2026-01234 is a charge id, not a phone") != ""
    assert redact("no identifiers here") == "no identifiers here"
