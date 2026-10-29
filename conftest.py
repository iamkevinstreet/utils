########################################################################
#                             conftest.py                              #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Keeps every test offline and isolated: the fake provider, a temporary
log folder, no cache.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

# Third-party
import pytest

# Local
from kds import settings as config

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                            Test isolation                            #
########################################################################
# log.debug("Defines the isolation every test in this folder gets")
@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fake provider, temporary logs, no settings file, no cache.

    Args:
        tmp_path: A temporary folder pytest makes for this test.
        monkeypatch: pytest's helper for patching the environment and
            objects.

    Yields:
        Nothing; the test runs while the fixture waits here.
    """
    # log.debug("Forces the offline provider so no test calls a model")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    # log.debug("Sends any log file to the test's own folder")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    # log.debug("Points the settings file at one that does not exist")
    monkeypatch.setenv("SETTINGS_FILE", str(tmp_path / "absent.toml"))
    # log.debug("Clears cached settings before the test")
    config.get_settings.cache_clear()
    # log.debug("Runs the test")
    yield
    # log.debug("Clears cached settings after the test")
    config.get_settings.cache_clear()
