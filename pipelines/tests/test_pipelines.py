########################################################################
#                                                                      #
#                  pipelines/tests/test_pipelines.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-09
Last modified on:  2026-11-10

Tests the shared pipeline parts offline: Databricks refused when half
set up, the variables dbt reads, dbt's command line, a real dlt load
into a DuckDB file of the test's own that a second run leaves as it
was, and the command's load and dbt subcommands.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# Third-party
import dlt
import duckdb
import pytest
from pydantic import ValidationError

# Local
from kds.args import required
from kds.logs import get_logger
from kds.pipelines import PipelineSettings, dbt_env, load, run_command, transform
from kds.pipelines import command as command_module

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = get_logger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the rows the test source yields")
ROWS = [{"id": 1, "name": "first"}, {"id": 2, "name": "second"}]


########################################################################
#                                                                      #
#                                Tests                                 #
#                                                                      #
########################################################################
# log.debug("Defines settings that write only under the test's folder")
def _settings(tmp_path: Path | None = None, **values: Any) -> PipelineSettings:
    """Returns settings whose warehouse and state are the test's own.

    Args:
        tmp_path: The test's temporary folder. Required.
        **values: Any other settings to set.

    Returns:
        The settings.
    """
    # log.debug("Takes the folder, which the caller must give")
    tmp_path = required(tmp_path=tmp_path)
    # log.debug("Returns them")
    return PipelineSettings(
        warehouse_path=tmp_path / "warehouse.duckdb",
        warehouse_state=tmp_path / "dlt",
        log_dir=tmp_path / "logs",
        **values,
    )


# log.debug("Defines the source the load test runs")
@dlt.source
def _people() -> Any:
    """Returns one resource of two rows, merged on their id.

    Returns:
        The resource.
    """

    # log.debug("Defines the resource")
    @dlt.resource(name="people", write_disposition="merge", primary_key="id")
    def people() -> Iterator[dict[str, Any]]:
        """Yields the rows.

        Yields:
            Each row.
        """
        # log.debug("Yields the rows")
        yield from ROWS

    # log.debug("Returns the resource")
    return people


# log.debug("Defines the test that Databricks needs its whole connection")
def test_databricks_needs_its_host_path_and_token(tmp_path: Path) -> None:
    """Half a connection is refused; a pasted host is taken bare.

    Args:
        tmp_path: The test's temporary folder.
    """
    # log.debug("Checks a destination without its connection is refused")
    with pytest.raises(ValidationError, match="DATABRICKS_HOST"):
        # log.debug("Builds settings with Databricks half set up")
        _settings(tmp_path, warehouse_destination="databricks")
    # log.debug("Builds the whole connection, with the host as a browser shows it")
    whole = _settings(
        tmp_path,
        warehouse_destination="databricks",
        databricks_host="https://dbc-1.cloud.databricks.com/",
        databricks_http_path="/sql/1.0/warehouses/1",
        databricks_token="not-a-real-token",  # noqa: S106 - a placeholder, not a credential
    )
    # log.debug("Checks the host is bare")
    assert whole.databricks_host == "dbc-1.cloud.databricks.com"


# log.debug("Defines the test of the variables dbt reads")
def test_dbt_reads_the_warehouse_and_only_what_is_set(tmp_path: Path) -> None:
    """DuckDB's path always; the others' values only when set.

    Args:
        tmp_path: The test's temporary folder.
    """
    # log.debug("Reads the variables for a DuckDB warehouse")
    env = dbt_env(_settings(tmp_path))
    # log.debug("Checks the names and the path, and that no token was asked for")
    assert (set(env), env["WAREHOUSE_PATH"]) == (
        {"WAREHOUSE_PATH", "DATABRICKS_CATALOG", "SNOWFLAKE_DATABASE"},
        str((tmp_path / "warehouse.duckdb").resolve()),
    )


# log.debug("Defines the test of dbt's command line")
def test_dbt_runs_the_settings_project_with_the_warehouse_folder_made(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The command names the settings' project; DuckDB gets its folder.

    Args:
        tmp_path: The test's temporary folder.
        monkeypatch: pytest's helper for patching objects.
    """
    # log.debug("Builds settings whose warehouse folder does not exist yet")
    settings = _settings(tmp_path / "new", dbt_threads=2)
    # log.debug("Keeps a record of each command, without running dbt")
    commands: list[list[str]] = []

    # log.debug("Defines a process that records its command and succeeds")
    def succeeding(
        command: list[str] | None = None, **options: Any
    ) -> subprocess.CompletedProcess[str]:
        """Records the command line and reports success.

        Args:
            command: The command line. Required.
            **options: The rest of subprocess.run's arguments.

        Returns:
            A finished process with status 0.
        """
        # log.debug("Records the command, which the caller must give")
        commands.append(required(command=command))
        # log.debug("Returns success")
        return subprocess.CompletedProcess(commands[-1], 0, "", str(sorted(options)))

    # log.debug("Puts the recording process in subprocess's place")
    monkeypatch.setattr(transform.subprocess, "run", succeeding)
    # log.debug("Checks dbt succeeded, the folder exists and dbt got the settings")
    assert (
        transform.run_dbt(settings, ["build"]),
        settings.warehouse_path.parent.is_dir(),
        " ".join(commands[0][1:]),
    ) == (True, True, "build --project-dir dbt --profiles-dir dbt --target dev --threads 2")


# log.debug("Defines the test of a real load")
def test_a_load_lands_in_duckdb_and_a_second_changes_nothing(tmp_path: Path) -> None:
    """The rows load once, and loading them again merges on the key.

    Args:
        tmp_path: The test's temporary folder.
    """
    # log.debug("Builds the settings")
    settings = _settings(tmp_path)
    # log.debug("Loads the source twice")
    for _ in range(2):
        # log.debug("Loads it")
        load(settings, name="people", dataset="raw_people", source=_people())
    # log.debug("Reads the table back")
    with duckdb.connect(str(settings.warehouse_path)) as db:
        # log.debug("Counts its rows")
        rows = db.execute("select count(*) from raw_people.people").fetchone()
    # log.debug("Checks two rows, not four")
    assert rows == (2,)


# log.debug("Defines the test of the command's two subcommands")
def test_the_command_runs_a_named_load_and_reports_dbt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A load runs by its name; a failed dbt fails the command.

    Args:
        tmp_path: The test's temporary folder.
        monkeypatch: pytest's helper for patching objects.
    """
    # log.debug("Builds the settings")
    settings = _settings(tmp_path)
    # log.debug("Keeps a record of the loads run")
    ran: list[str] = []
    # log.debug("Names one load that records its run")
    loads = {"people": lambda s: ran.append(type(s).__name__)}
    # log.debug("Runs the load by its name")
    status = run_command(loads, lambda: settings, ["load", "people"])
    # log.debug("Makes dbt fail, without running it")
    monkeypatch.setattr(command_module, "run_dbt", lambda s, a: False)
    # log.debug("Checks the load ran, and a failed dbt fails the command")
    assert (status, ran, run_command(loads, lambda: settings, ["dbt", "build"])) == (
        0,
        ["PipelineSettings"],
        1,
    )
    # log.debug("Checks a load the project does not have is refused")
    with pytest.raises(SystemExit):
        # log.debug("Runs a load by a name it does not have")
        run_command(loads, lambda: settings, ["load", "nobody"])
