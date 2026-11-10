########################################################################
#                                                                      #
#                  pipelines/tests/test_snowflake.py                   #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-10
Last modified on:  2026-11-10

Tests Snowflake offline, with GitHub's token service stood in for:
Snowflake refused without its account, which is taken from an address
as a browser shows it; a GitHub job's token asked for with the account
as its audience and handed to dbt; no token outside a job that may ask
for one; and a token set by hand signing a load in as the workload,
without asking GitHub.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path
from typing import Any, Final

# Third-party
import pytest
from pydantic import ValidationError

# Local
from kds.args import required
from kds.logs import get_logger
from kds.pipelines import PipelineSettings, dbt_env, destination, github_token

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
# log.debug("Sets a made-up account, as Snowsight shows one")
ACCOUNT: Final = "MYORG-MYACCOUNT"
# log.debug("Sets the address a browser shows for it")
ADDRESS: Final = "https://myorg-myaccount.snowflakecomputing.com"
# log.debug("Sets where a made-up GitHub job asks for its token")
REQUEST_URL: Final = "https://token.example/request?api-version=2.0"
# log.debug("Sets a made-up token, three parts as a JWT has")
JWT: Final = "header.claims.signature"


########################################################################
#                                                                      #
#                                Tests                                 #
#                                                                      #
########################################################################
# log.debug("Defines settings that write only under the test's folder")
def _settings(tmp_path: Path | None = None, **values: Any) -> PipelineSettings:
    """Returns Snowflake settings whose state is the test's own.

    Args:
        tmp_path: The test's temporary folder. Required.
        **values: Any other settings to set.

    Returns:
        The settings.
    """
    # log.debug("Takes the folder, which the caller must give")
    tmp_path = required(tmp_path=tmp_path)
    # log.debug("Returns them, with Snowflake as the warehouse")
    return PipelineSettings(
        warehouse_destination="snowflake",
        warehouse_path=tmp_path / "warehouse.duckdb",
        warehouse_state=tmp_path / "dlt",
        log_dir=tmp_path / "logs",
        **values,
    )


# log.debug("Defines a stand-in for GitHub's token service")
class FakeGitHub:
    """Answers each token request with the made-up token, keeping it."""

    # log.debug("Defines the stand-in's start")
    def __init__(self) -> None:
        """Starts with no request kept."""
        # log.debug("Starts the requests kept")
        self.requests: list[urllib.request.Request] = []
        # log.debug("Starts how long each request would wait")
        self.waits: list[float] = []

    # log.debug("Defines its answer to a request")
    def __call__(
        self, request: urllib.request.Request | None = None, timeout: float = 0
    ) -> io.BytesIO:
        """Keeps the request and answers as GitHub does.

        Args:
            request: The request. Required.
            timeout: How long the caller would wait, in seconds.

        Returns:
            GitHub's answer: JSON whose value is the token.
        """
        # log.debug("Keeps the request, which the caller must give")
        self.requests.append(required(request=request))
        # log.debug("Keeps how long it would wait")
        self.waits.append(timeout)
        # log.debug("Answers with the made-up token")
        return io.BytesIO(json.dumps({"value": JWT}).encode())


# log.debug("Defines the test that Snowflake needs its account")
def test_snowflake_needs_its_account_and_takes_it_from_an_address(tmp_path: Path) -> None:
    """No account is refused; a browser's address is taken as one.

    Args:
        tmp_path: The test's temporary folder.
    """
    # log.debug("Checks Snowflake without its account is refused")
    with pytest.raises(ValidationError, match="SNOWFLAKE_ACCOUNT"):
        # log.debug("Builds settings with Snowflake and no account")
        _settings(tmp_path)
    # log.debug("Builds the settings with the account as a browser shows it")
    pasted = _settings(tmp_path, snowflake_account=f"{ADDRESS}/console/login")
    # log.debug("Checks the account is its identifier, in capitals")
    assert pasted.snowflake_account == ACCOUNT


# log.debug("Defines the test that a GitHub job asks for a token for the account")
def test_a_github_job_asks_for_a_token_for_the_account_and_dbt_gets_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The dbt run gets a fresh token, made for the account's address.

    Args:
        tmp_path: The test's temporary folder.
        monkeypatch: pytest's helper for patching the environment and
            objects.
    """
    # log.debug("Sets where the job asks, as a job with id-token: write has")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", REQUEST_URL)
    # log.debug("Sets what the job asks with")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "job-bearer")
    # log.debug("Makes the stand-in for GitHub")
    github = FakeGitHub()
    # log.debug("Puts it in the place of the request GitHub would answer")
    monkeypatch.setattr(urllib.request, "urlopen", github)
    # log.debug("Reads the variables dbt gets for Snowflake")
    env = dbt_env(_settings(tmp_path, snowflake_account=ACCOUNT))
    # log.debug("Checks dbt's token and account, and what GitHub was asked, and how")
    assert (
        env["SNOWFLAKE_TOKEN"],
        env["SNOWFLAKE_ACCOUNT"],
        github.requests[0].full_url,
        github.requests[0].get_header("Authorization"),
        github.waits,
    ) == (
        JWT,
        ACCOUNT,
        f"{REQUEST_URL}&audience=https%3A%2F%2Fmyorg-myaccount.snowflakecomputing.com",
        "bearer job-bearer",
        [10],
    )


# log.debug("Defines the test that only a GitHub job that may ask gets a token")
@pytest.mark.parametrize(
    ("url", "bearer"),
    [
        ("", "job-bearer"),
        (REQUEST_URL.replace("https://", "http://"), "job-bearer"),
        (REQUEST_URL, ""),
    ],
)
def test_outside_a_github_job_that_may_ask_there_is_no_token(
    url: str, bearer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No address, one that is not https, or nothing to ask with fails.

    Args:
        url: Where the job would ask.
        bearer: What it would ask with.
        monkeypatch: pytest's helper for patching the environment.
    """
    # log.debug("Sets where the job would ask")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_URL", url)
    # log.debug("Sets what it would ask with")
    monkeypatch.setenv("ACTIONS_ID_TOKEN_REQUEST_TOKEN", bearer)
    # log.debug("Checks the request is refused before anything is sent")
    with pytest.raises(RuntimeError, match="id-token: write"):
        # log.debug("Asks for a token")
        github_token(ADDRESS)


# log.debug("Defines the test that a token set by hand signs a load in")
def test_a_token_set_by_hand_signs_a_load_in_as_the_workload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A set SNOWFLAKE_TOKEN is used as it is; GitHub is not asked.

    Args:
        tmp_path: The test's temporary folder.
        monkeypatch: pytest's helper for patching the environment.
    """
    # log.debug("Removes where a job would ask, so asking GitHub would fail")
    monkeypatch.delenv("ACTIONS_ID_TOKEN_REQUEST_URL", raising=False)
    # log.debug("Builds the settings with a token set")
    settings = _settings(
        tmp_path,
        snowflake_account=ACCOUNT,
        snowflake_token=JWT,
    )
    # log.debug("Checks dlt signs in as the workload with that token")
    assert destination(settings).config_params["credentials"] == {
        "host": ACCOUNT,
        "database": "KDS",
        "authenticator": "WORKLOAD_IDENTITY",
        "workload_identity_provider": "OIDC",
        "token": JWT,
    }
