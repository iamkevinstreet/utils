########################################################################
#                                                                      #
#                        tests/test_template.py                        #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

Tests the project template by rendering it as `copier copy` renders a
new project, from copier.yml and template/ alone, then committing the
result as its first commit: once as a repository of its own, and once
into a folder of an app's repository, which keeps the root's files.
Each must meet the code standard, pass ruff with its own settings and
pass its own tests, run in its own folder against this repository's
packages, as its pins install them. Its pins must name the commit
given and admit this release, its dbt profile must read only what the
pipelines command sets for each warehouse, and a bad answer must be
refused before anything is written.
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
import re
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
from kds.pipelines import PipelineSettings, dbt_env
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
# log.debug("Sets the answers that put the data layers in a folder of an app's repository")
IN_FOLDER: Final = {"folder": "warehouse", "project_name": "Sample warehouse"}
# log.debug("Lists the files a folder leaves to the repository's root")
ROOT_ONLY: Final = (
    ".github",
    ".editorconfig",
    ".gitattributes",
    ".pre-commit-config.yaml",
    ".yamllint.yaml",
    "LICENSE",
    "NOTICE",
    "CHANGELOG.md",
    "SECURITY.md",
)
# log.debug("Sets the lines that mark the folder's generated files, as copier's message asks")
GENERATED: Final = (
    "warehouse/uv.lock linguist-generated\nwarehouse/.copier-answers.yml linguist-generated\n"
)


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


# log.debug("Defines a repository's first commit, as copier's message asks for it")
def _first_commit(repository: Path | None = None) -> None:
    """Starts git, stamps every new file's header, and commits them.

    Args:
        repository: The repository's root. Required.
    """
    # log.debug("Takes the root, which the caller must give")
    repository = required(repository=repository)
    # log.debug("Starts the repository")
    _run(repository, *GIT, "init", "-q", "-b", "main").check_returncode()
    # log.debug("Lists the files the first commit will hold")
    files = _run(repository, "git", "ls-files", "--others", "--exclude-standard").stdout.split()
    # log.debug("Stamps their headers with today's dates, from the root")
    with pytest.MonkeyPatch.context() as patch:
        # log.debug("Moves to the root, which stamp reads as the repository")
        patch.chdir(repository)
        # log.debug("Checks the stamp ran")
        assert standards(["stamp", *files]) == 0
    # log.debug("Adds every file")
    _run(repository, *GIT, "add", "-A").check_returncode()
    # log.debug("Makes the first commit")
    _run(repository, *GIT, "commit", "-q", "--no-gpg-sign", "-m", "Start").check_returncode()


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


# log.debug("Defines the project the tests share, rendered once as a repository of its own")
@pytest.fixture(scope="module")
def project(source: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Renders the template and commits it as a project's first commit.

    Args:
        source: The template, as a clone holds it.
        tmp_path_factory: pytest's maker of temporary folders.

    Returns:
        The rendered project's folder.
    """
    # log.debug("Makes the project's folder")
    target = tmp_path_factory.mktemp("project")
    # log.debug("Renders the template with the answers, asking nothing")
    copier.run_copy(str(source), target, data=dict(ANSWERS), defaults=True, quiet=True)
    # log.debug("Makes the first commit")
    _first_commit(target)
    # log.debug("Returns the project")
    return target


# log.debug("Defines an app's repository with the data layers in a folder, rendered once")
@pytest.fixture(scope="module")
def app(source: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Renders a repository's root, then the data layers into a folder.

    The root render stands in for an app's root files: its CI, license
    and changelog are what a folder leaves to the root.

    Args:
        source: The template, as a clone holds it.
        tmp_path_factory: pytest's maker of temporary folders.

    Returns:
        The repository's root.
    """
    # log.debug("Makes the repository's folder")
    root = tmp_path_factory.mktemp("app")
    # log.debug("Renders the root's files")
    copier.run_copy(str(source), root, data=dict(ANSWERS), defaults=True, quiet=True)
    # log.debug("Renders the data layers into their folder")
    copier.run_copy(
        str(source),
        root / IN_FOLDER["folder"],
        data=ANSWERS | IN_FOLDER,
        defaults=True,
        quiet=True,
    )
    # log.debug("Marks the folder's generated files, as copier's message asks")
    with (root / ".gitattributes").open("a", encoding="utf-8") as attributes:
        # log.debug("Adds the lines")
        attributes.write(GENERATED)
    # log.debug("Makes the first commit")
    _first_commit(root)
    # log.debug("Returns the root")
    return root


# log.debug("Defines the repository each standard test checks")
@pytest.fixture(params=["own repository", "app's repository"])
def repository(request: pytest.FixtureRequest) -> Path:
    """Returns a project's own repository, or the app's with a folder.

    Args:
        request: pytest's account of the parameter this run has.

    Returns:
        The repository's root.
    """
    # log.debug("Returns the root the parameter names")
    return Path(request.getfixturevalue("project" if request.param == "own repository" else "app"))


# log.debug("Defines the data layers each project test checks")
@pytest.fixture(params=["own repository", "folder"])
def layers(request: pytest.FixtureRequest) -> Path:
    """Returns the data layers: a repository of their own, or a folder.

    Args:
        request: pytest's account of the parameter this run has.

    Returns:
        The folder their Makefile and pyproject.toml are in.
    """
    # log.debug("Returns the project, or the folder in the app's repository")
    return (
        Path(request.getfixturevalue("project"))
        if request.param == "own repository"
        else Path(request.getfixturevalue("app")) / IN_FOLDER["folder"]
    )


# log.debug("Defines the test that each repository meets the code standard")
def test_the_rendered_repository_meets_the_code_standard(
    repository: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """kds-standards check finds nothing in the first commit.

    Args:
        repository: The repository's root.
        monkeypatch: pytest's helper for patching the environment.
        capsys: pytest's capture of what the check prints.
    """
    # log.debug("Moves to the root, which check reads as the repository")
    monkeypatch.chdir(repository)
    # log.debug("Checks the check passed and said so")
    assert (standards(["check", "."]), capsys.readouterr().out.strip()) == (0, CLEAN)


# log.debug("Defines the test that ruff passes with the project's own settings")
def test_ruff_passes_on_the_rendered_layers(layers: Path) -> None:
    """Lint and format, as the project's `make check` runs them.

    Args:
        layers: The rendered data layers.
    """
    # log.debug("Lints them")
    lint = _run(layers, sys.executable, "-m", "ruff", "check", ".")
    # log.debug("Checks their formatting")
    form = _run(layers, sys.executable, "-m", "ruff", "format", "--check", ".")
    # log.debug("Checks both passed")
    assert (lint.returncode, form.returncode) == (0, 0), lint.stdout + form.stdout


# log.debug("Defines the test that the layers' own tests pass")
def test_the_rendered_layers_own_tests_pass(layers: Path) -> None:
    """Their tests pass in their folder, with none of this repository's.

    The environment holds only PATH, HOME and the packages' folders, so
    none of this repository's own test settings reach the project.

    Args:
        layers: The rendered data layers.
    """
    # log.debug("Puts this repository's packages where the project's pins would")
    path = os.pathsep.join(str(ROOT / folder) for folder in IMPORTED)
    # log.debug("Builds the project's environment")
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", ""), "PYTHONPATH": path}
    # log.debug("Runs their tests")
    done = _run(layers, sys.executable, "-m", "pytest", "-p", "no:cacheprovider", env=env)
    # log.debug("Checks they passed")
    assert (done.returncode, "passed" in done.stdout) == (0, True), done.stdout + done.stderr


# log.debug("Defines the test that a folder leaves the root's files to the repository")
def test_a_folder_leaves_the_roots_files_and_the_standard_to_the_root(app: Path) -> None:
    """No CI, license or changelog of its own; the root checks the code.

    Args:
        app: The app's repository, with the data layers in a folder.
    """
    # log.debug("Points at the folder")
    folder = app / IN_FOLDER["folder"]
    # log.debug("Reads its Makefile")
    makefile = (folder / "Makefile").read_text(encoding="utf-8")
    # log.debug("Checks none of the root's files is there, and the standard is the root's")
    assert (
        [f for f in ROOT_ONLY if (folder / f).exists()],
        "$(UV) kds-standards" in makefile,
    ) == (
        [],
        False,
    )


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


# log.debug("Defines the test that dbt's profile reads only what the command sets")
def test_the_dbt_profile_reads_only_what_the_command_sets() -> None:
    """Each target reads only variables set for its warehouse."""
    # log.debug("Reads the template's dbt profile")
    text = (ROOT / "template" / "dbt" / "profiles.yml").read_text(encoding="utf-8")
    # log.debug("Splits it at each target, a name indented four spaces")
    parts = re.split(r"^    (\w+):\n", text, flags=re.MULTILINE)[1:]
    # log.debug("Lists the variables each target reads")
    reads = {
        target: set(re.findall(r"env_var\('(\w+)'\)", body))
        for target, body in zip(parts[::2], parts[1::2], strict=True)
    }
    # log.debug("Sets up each target's warehouse whole, with made-up values")
    warehouses: dict[str, dict[str, Any]] = {
        "dev": {},
        "prod": {
            "warehouse_destination": "databricks",
            "databricks_host": "example.cloud.databricks.com",
            "databricks_http_path": "/sql/1.0/warehouses/example",
            "databricks_token": "made-up",
        },
        "snowflake": {
            "warehouse_destination": "snowflake",
            "snowflake_account": "ORGNAME-ACCOUNTNAME",
            "snowflake_token": "made-up",
        },
    }
    # log.debug("Lists the variables the command sets for each")
    sets = {t: set(dbt_env(PipelineSettings(**values))) for t, values in warehouses.items()}
    # log.debug("Checks the targets are the three, each reading only what is set for it")
    assert (set(reads), {t: reads[t] - sets[t] for t in reads}) == (
        set(warehouses),
        {t: set() for t in warehouses},
    )


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
