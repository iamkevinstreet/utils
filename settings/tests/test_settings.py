########################################################################
#                   settings/tests/test_settings.py                    #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests the defaults, the settings.toml source,    #
#                     source priority and that secrets never leak.     #
########################################################################
"""Tests for kds.settings."""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path

import pytest

from kds.settings import Settings, describe
from kds.settings.toml import flatten

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets a key that looks real enough to catch a leak")
FAKE_KEY = "sk-test-not-a-real-key"


# log.debug("Defines a helper that writes a settings file")
def _write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """Write `text` as the settings file; point SETTINGS_FILE at it."""
    # log.debug("Names the file inside the test's folder")
    path = tmp_path / "settings.toml"
    # log.debug("Writes the TOML text")
    path.write_text(text, encoding="utf-8")
    # log.debug("Points the settings loader at it")
    monkeypatch.setenv("SETTINGS_FILE", str(path))


# log.debug("Defines the test that the defaults are the safe ones")
def test_defaults_are_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """With nothing set: offline provider, redaction on, a budget."""
    # log.debug("Removes the provider the test setup chose")
    monkeypatch.delenv("LLM_PROVIDER")
    # log.debug("Builds settings without reading any .env file")
    s = Settings(_env_file=None)
    # log.debug("Checks the provider defaults to the offline one")
    assert s.llm_provider == "fake"
    # log.debug("Checks redaction defaults to on")
    assert s.log_redact is True
    # log.debug("Checks there is a spending limit")
    assert s.eval_budget_usd > 0


# log.debug("Defines the test that sections flatten into field names")
def test_flatten_joins_section_and_key() -> None:
    """`[llm] model` becomes `llm_model`; top-level keys stay."""
    # log.debug("Checks one section key and one top-level key")
    assert flatten({"llm": {"model": "m"}, "debug": True}) == {"llm_model": "m", "debug": True}


# log.debug("Defines the test that the file is read")
def test_settings_file_is_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Values in settings.toml reach the settings."""
    # log.debug("Writes a file that sets the model and the budget")
    _write(tmp_path, monkeypatch, '[llm]\nmodel = "from-file"\n[eval]\nbudget_usd = 1.5\n')
    # log.debug("Builds settings from it")
    s = Settings(_env_file=None)
    # log.debug("Checks the model came from the file")
    assert s.llm_model == "from-file"
    # log.debug("Checks the budget came from the file")
    assert s.eval_budget_usd == 1.5


# log.debug("Defines the test that the environment wins over the file")
def test_environment_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An environment variable beats the same setting in the file."""
    # log.debug("Writes a file that sets the model")
    _write(tmp_path, monkeypatch, '[llm]\nmodel = "from-file"\n')
    # log.debug("Sets the same setting in the environment")
    monkeypatch.setenv("LLM_MODEL", "from-env")
    # log.debug("Checks the environment's value won")
    assert Settings(_env_file=None).llm_model == "from-env"


# log.debug("Defines the test that a secret in the file is refused")
def test_secret_in_file_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A key in settings.toml stops startup, without echoing the key."""
    # log.debug("Writes a file that wrongly holds a key")
    _write(tmp_path, monkeypatch, f'[anthropic]\napi_key = "{FAKE_KEY}"\n')
    # log.debug("Expects startup to stop")
    with pytest.raises(ValueError, match=r"secrets go in \.env") as caught:
        # log.debug("Builds the settings, which should fail")
        Settings(_env_file=None)
    # log.debug("Checks the error does not repeat the key")
    assert FAKE_KEY not in str(caught.value)


# log.debug("Defines the test that secrets never show")
def test_secrets_do_not_leak(monkeypatch: pytest.MonkeyPatch) -> None:
    """A key is absent from the repr, masked in the startup summary."""
    # log.debug("Sets a key in the environment")
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    # log.debug("Builds settings that hold it")
    s = Settings(_env_file=None)
    # log.debug("Checks the repr does not show it")
    assert FAKE_KEY not in repr(s)
    # log.debug("Summarises the settings for the startup log")
    shown = describe(s)
    # log.debug("Checks the summary masks the set key")
    assert shown["anthropic_api_key"] == "********"
    # log.debug("Checks the summary marks a missing key as unset")
    assert shown["openai_api_key"] == "unset"


# log.debug("Defines the test that settings cannot change once built")
def test_settings_are_frozen() -> None:
    """Assigning to a setting after startup raises."""
    # log.debug("Builds settings")
    s = Settings(_env_file=None)
    # log.debug("Expects any assignment to fail")
    with pytest.raises(ValueError, match="frozen"):
        # log.debug("Tries to change the model")
        s.llm_model = "other"  # type: ignore[misc]


# log.debug("Defines the test that the reference file matches the code")
def test_reference_file_matches_defaults() -> None:
    """config/settings.toml lists each shared setting at its default."""
    # log.debug("Finds the reference file at the repository root")
    path = Path(__file__).resolve().parents[2] / "config" / "settings.toml"
    # log.debug("Reads it as flat setting names")
    listed = flatten(tomllib.loads(path.read_text(encoding="utf-8")))
    # log.debug("Reads each field's declared default from the class")
    defaults = {name: field.default for name, field in Settings.model_fields.items()}
    # log.debug("Checks every listed name is a real setting")
    assert set(listed) <= set(defaults)
    # log.debug("Checks every listed value equals its default")
    assert all(type(defaults[k])(v) == defaults[k] for k, v in listed.items())
