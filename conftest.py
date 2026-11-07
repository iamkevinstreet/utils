########################################################################
#                                                                      #
#                             conftest.py                              #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-11-07

Keeps every test offline and isolated: the fake provider, a temporary
log folder, no cache, and spans recorded in memory, never sent.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

# Third-party
import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Local
from kds import settings as config
from kds.logs.spans import Stamp
from kds.logs.steps import KEEPER

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
# log.debug("Holds every span the tests open, in memory")
MEMORY = InMemorySpanExporter()


########################################################################
#                                                                      #
#                            Test isolation                            #
#                                                                      #
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


# log.debug("Defines the span recorder every test in the session shares")
@pytest.fixture(scope="session", autouse=True)
def recorded() -> Iterator[None]:
    """Records every span in memory, stamped and kept as in a service.

    Yields:
        Nothing; the session runs while the fixture waits here.
    """
    # log.debug("Creates the provider every test's spans go to")
    provider = TracerProvider()
    # log.debug("Stamps each span with its request id and session")
    provider.add_span_processor(Stamp())
    # log.debug("Records each span in memory as it ends")
    provider.add_span_processor(SimpleSpanProcessor(MEMORY))
    # log.debug("Lets evaluation runs keep their spans")
    provider.add_span_processor(KEEPER)
    # log.debug("Puts it in use for the session")
    trace.set_tracer_provider(provider)
    # log.debug("Runs the session")
    yield


# log.debug("Defines the spans one test records")
@pytest.fixture
def spans() -> InMemorySpanExporter:
    """Returns the span recorder, cleared of earlier tests' spans.

    Returns:
        The recorder; get_finished_spans() lists this test's spans.
    """
    # log.debug("Forgets the spans earlier tests recorded")
    MEMORY.clear()
    # log.debug("Returns the recorder")
    return MEMORY
