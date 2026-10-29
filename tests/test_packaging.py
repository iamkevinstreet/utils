########################################################################
#                       tests/test_packaging.py                        #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Tests that every package ships a py.typed marker, so mypy checks its
callers, and that all the packages share one version.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import tomllib
from pathlib import Path

# Third-party
import pytest

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Points at the repository root, above this tests folder")
ROOT = Path(__file__).resolve().parents[1]
# log.debug("Lists every package folder in the repository")
PACKAGES = ("args", "settings", "logs", "llm", "evals", "synthetic", "standards", "diagrams")


########################################################################
#                           Packaging tests                            #
########################################################################
# log.debug("Defines the test that each package is marked as typed")
@pytest.mark.parametrize("name", PACKAGES)
def test_package_ships_py_typed(name: str) -> None:
    """Each package has py.typed (PEP 561) and packages it.

    Args:
        name: The package's folder name; pytest runs the test once for
            each name in PACKAGES.
    """
    # log.debug("Checks the marker file exists in the package")
    assert (ROOT / name / "kds" / name / "py.typed").is_file()
    # log.debug("Reads the package's pyproject.toml")
    project = tomllib.loads((ROOT / name / "pyproject.toml").read_text(encoding="utf-8"))
    # log.debug("Checks the marker is listed as package data")
    assert "py.typed" in project["tool"]["setuptools"]["package-data"][f"kds.{name}"]


# log.debug("Defines the test that every package has one version")
def test_packages_share_one_version() -> None:
    """All packages are released together, at the same version."""
    # log.debug("Reads each package's version")
    versions = {
        tomllib.loads((ROOT / n / "pyproject.toml").read_text(encoding="utf-8"))["project"][
            "version"
        ]
        for n in PACKAGES
    }
    # log.debug("Checks there is exactly one")
    assert len(versions) == 1
