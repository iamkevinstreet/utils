########################################################################
#                                                                      #
#                        tests/test_template.py                        #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-09

Tests the project template by rendering it as `copier copy` renders a
new project, from copier.yml and template/ alone, then committing the
result as its first commit. The project must meet the code standard,
pass ruff with its own settings and pass its own tests, run in its own
folder against this repository's packages, as its pins install them.
Its pins must name the commit given and admit this release, and a bad
answer must be refused before anything is written.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Final

# Third-party
import copier
import pytest
from packaging.specifiers import SpecifierSet

# Local
from kds.args import required
from kds.standards.cli import main as standards

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
# log.debug("Points at the repository root, where copier.yml is")
ROOT: Final = Path(__file__).resolve().parents[1]
# log.debug("Sets the answers a new project gives, its pin one no repository has")
ANSWERS: Final = {
    "project_name": "Sample charges",
    "repo": "sample-charges",
    "description": "A sample project, rendered by the template's test.",
    "industry": "legal",
    "utils_commit": "0" * 40,
}
# log.debug("Lists the package folders the project's tests import, as its pins install them")
IMPORTED: Final = ("args", "settings", "logs", "pipelines")
# log.debug("Sets git with an identity of its own, for the throwaway first commit")
GIT: Final = ("git", "-c", "user.name=Template test", "-c", "user.email=test@example.com")
# log.debug("Sets what the code standard prints when it finds nothing")
CLEAN: Final = "kds-standards: no findings"


########################################################################
#                                                                      #
#                            Template tests                            #
#                                                                      #
########################################################################
# log.debug("Defines one run of a command in the rendered project")
def _run(
    folder: Path | None = None, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Runs a command in the folder and returns how it ended.

    Args:
        folder: The rendered project. Required.
        *args: The command and its arguments.
        env: The command's whole environment; this process's when None.

    Returns:
        The finished process, with what it printed.
    """
    # log.debug("Takes the folder, which the caller must give")
    folder = required(folder=folder)
    # log.debug("Runs the command there without a shell")
    return subprocess.run(  # noqa: S603 - fixed arguments, no shell
        args, cwd=folder, env=env, capture_output=True, text=True, check=False
    )


# log.debug("Defines the template as a clone holds it, copied once")
@pytest.fixture(scope="module")
def source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copies copier.yml and template/ alone, leaving out caches.

    A plain folder, not this repository: copier would clone that, and
    warn that its working tree is dirty while a change is being made.

    Args:
        tmp_path_factory: pytest's maker of temporary folders.

    Returns:
        The folder copier renders from.
    """
    # log.debug("Makes the folder")
    folder = tmp_path_factory.mktemp("source")
    # log.debug("Copies the questions")
    shutil.copy2(ROOT / "copier.yml", folder)
    # log.debug("Copies the template, leaving out caches")
    shutil.copytree(
        ROOT / "template",
        folder / "template",
        ignore=shutil.ignore_patterns("__pycache__", ".*_cache"),
    )
    # log.debug("Returns the folder")
    return folder


# log.debug("Defines the project the tests share, rendered once")
@pytest.fixture(scope="module")
def project(source: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Renders the template and commits it as a project's first commit.

    Args:
        source: The template, as a clone holds it.
        tmp_path_factory: pytest's maker of temporary folders.

    Returns:
        The rendered project's folder.
    """
    # log.debug("Renders it with the answers, asking nothing")
    target = tmp_path_factory.mktemp("project")
    # log.debug("Runs copier")
    copier.run_copy(str(source), target, data=dict(ANSWERS), defaults=True, quiet=True)
    # log.debug("Starts the project's repository")
    _run(target, *GIT, "init", "-q", "-b", "main").check_returncode()
    # log.debug("Lists the files the first commit will hold")
    files = _run(target, "git", "ls-files", "--others", "--exclude-standard").stdout.split()
    # log.debug("Stamps their headers with today's dates, from the project's folder")
    with pytest.MonkeyPatch.context() as patch:
        # log.debug("Moves to the project, which stamp reads as the root")
        patch.chdir(target)
        # log.debug("Checks the stamp ran")
        assert standards(["stamp", *files]) == 0
    # log.debug("Adds every file")
    _run(target, *GIT, "add", "-A").check_returncode()
    # log.debug("Makes the first commit")
    _run(target, *GIT, "commit", "-q", "--no-gpg-sign", "-m", "Start").check_returncode()
    # log.debug("Returns the project")
    return target


# log.debug("Defines the test that the project meets the code standard")
def test_the_rendered_project_meets_the_code_standard(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """kds-standards check finds nothing in the first commit.

    Args:
        project: The rendered project.
        monkeypatch: pytest's helper for patching the environment.
        capsys: pytest's capture of what the check prints.
    """
    # log.debug("Moves to the project, which check reads as the root")
    monkeypatch.chdir(project)
    # log.debug("Checks the check passed and said so")
    assert (standards(["check", "."]), capsys.readouterr().out.strip()) == (0, CLEAN)


# log.debug("Defines the test that ruff passes with the project's own settings")
def test_ruff_passes_on_the_rendered_project(project: Path) -> None:
    """Lint and format, as the project's `make check` runs them.

    Args:
        project: The rendered project.
    """
    # log.debug("Lints the project")
    lint = _run(project, sys.executable, "-m", "ruff", "check", ".")
    # log.debug("Checks its formatting")
    form = _run(project, sys.executable, "-m", "ruff", "format", "--check", ".")
    # log.debug("Checks both passed")
    assert (lint.returncode, form.returncode) == (0, 0), lint.stdout + form.stdout


# log.debug("Defines the test that the project's own tests pass")
def test_the_rendered_projects_own_tests_pass(project: Path) -> None:
    """Its tests pass in its folder, with nothing of this repository's.

    The environment holds only PATH, HOME and the packages' folders, so
    none of this repository's own test settings reach the project.

    Args:
        project: The rendered project.
    """
    # log.debug("Puts this repository's packages where the project's pins would")
    path = os.pathsep.join(str(ROOT / folder) for folder in IMPORTED)
    # log.debug("Builds the project's environment")
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", ""), "PYTHONPATH": path}
    # log.debug("Runs the project's tests")
    done = _run(project, sys.executable, "-m", "pytest", "-p", "no:cacheprovider", env=env)
    # log.debug("Checks they passed")
    assert (done.returncode, "passed" in done.stdout) == (0, True), done.stdout + done.stderr


# log.debug("Defines the test of the project's pins")
def test_the_project_pins_every_package_at_the_commit(project: Path) -> None:
    """Each package installs from the commit given, at this release.

    Args:
        project: The rendered project.
    """
    # log.debug("Reads the project's pyproject.toml")
    pyproject: dict[str, Any] = tomllib.loads((project / "pyproject.toml").read_text("utf-8"))
    # log.debug("Reads where each of this repository's packages installs from")
    sources = pyproject["tool"]["uv"]["sources"]
    # log.debug("Reads this release's version, which every package shares")
    release = tomllib.loads((ROOT / "pipelines" / "pyproject.toml").read_text("utf-8"))["project"]
    # log.debug("Lists the project's requirements on this repository's packages")
    kds = [
        r
        for r in [*pyproject["project"]["dependencies"], *pyproject["dependency-groups"]["dev"]]
        if r.startswith("kds-")
    ]
    # log.debug("Splits each into its package and its range")
    ranges = {r[: r.index(">=")]: SpecifierSet(r[r.index(">=") :]) for r in kds}
    # log.debug("Checks each package installs from the commit given, and only those do")
    assert (set(ranges), {s["rev"] for s in sources.values()}) == (
        set(sources),
        {ANSWERS["utils_commit"]},
    )
    # log.debug("Checks this release is in every range")
    assert all(release["version"] in spec for spec in ranges.values()), ranges


# log.debug("Defines the test that bad answers are refused")
@pytest.mark.parametrize(
    "answer",
    [
        {"repo": "Sample Charges"},
        {"utils_commit": "main"},
        {"utils_commit": "c6f4659"},
        {"description": 'Says "hello"'},
        {"project_name": " "},
    ],
)
def test_a_bad_answer_is_refused_before_anything_is_written(
    answer: dict[str, str], source: Path, tmp_path: Path
) -> None:
    """A name GitHub would change, a moving pin, or broken TOML.

    Args:
        answer: The one answer changed from the good set.
        source: The template, as a clone holds it.
        tmp_path: A temporary folder pytest makes for this test.
    """
    # log.debug("Checks copier refuses the answers")
    with pytest.raises(ValueError, match="Validation error"):
        # log.debug("Renders with the bad answer")
        copier.run_copy(
            str(source), tmp_path / "out", data=ANSWERS | answer, defaults=True, quiet=True
        )
    # log.debug("Checks nothing was written")
    assert not (tmp_path / "out").exists()
