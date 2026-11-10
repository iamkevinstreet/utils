########################################################################
#                                                                      #
#                   pipelines/kds/pipelines/oidc.py                    #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-10
Last modified on:  2026-11-10

A workload's own identity, for a warehouse that trusts the workflow
instead of a stored secret. Snowflake's workload identity federation
signs a service user in with a GitHub Actions job's OIDC token, so no
password or key exists for the job. GitHub gives a job a token only
when the job may ask for one (permissions: id-token: write), and makes
a fresh one each time, so each sign-in asks just before it connects.

The token's audience is the Snowflake account's own address, as the
service users in data-platform-aws-snowflake require. A token set in
SNOWFLAKE_TOKEN is used instead, as for a run outside GitHub.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Final

# Local
from kds.args import required
from kds.logs import get_logger, log_event
from kds.pipelines.config import SCHEME, SNOWFLAKE_DOMAIN
from kds.pipelines.settings import PipelineSettings

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
# log.debug("Names the variable that holds where a GitHub job asks for its token")
REQUEST_URL: Final = "ACTIONS_ID_TOKEN_REQUEST_URL"
# log.debug("Names the variable that holds what a GitHub job asks with")
REQUEST_BEARER: Final = "ACTIONS_ID_TOKEN_REQUEST_TOKEN"
# log.debug("Sets how long to wait for GitHub's answer, in seconds")
TIMEOUT: Final = 10


########################################################################
#                                                                      #
#                          Workload identity                           #
#                                                                      #
########################################################################
# log.debug("Defines a GitHub job's request for its own OIDC token")
def github_token(audience: str | None = None) -> str:
    """Asks GitHub Actions for this job's OIDC token, for one audience.

    Args:
        audience: Who the token is for, such as a Snowflake account's
            address. Required.

    Returns:
        The token, a signed JWT that names the repository and the job.

    Raises:
        RuntimeError: Outside a GitHub job allowed to ask for one.
    """
    # log.debug("Takes the audience, which the caller must give")
    audience = required(audience=audience)
    # log.debug("Reads where to ask")
    url = os.environ.get(REQUEST_URL, "")
    # log.debug("Reads what to ask with")
    bearer = os.environ.get(REQUEST_BEARER, "")
    # log.debug("Refuses outside a GitHub job that may ask")
    if not url.startswith(SCHEME) or not bearer:
        # log.debug("Raises, saying what is missing")
        raise RuntimeError(
            "no OIDC token: run in a GitHub job with id-token: write, or set SNOWFLAKE_TOKEN"
        )
    # log.debug("Builds the request, the audience joining the query GitHub's address has")
    request = urllib.request.Request(  # noqa: S310 - https, checked above
        f"{url}&audience={urllib.parse.quote(audience, safe='')}",
        headers={"Authorization": f"bearer {bearer}"},
    )
    # log.debug("Asks GitHub, at the https address its runner gave, as checked above")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
        # log.debug("Reads the token from the answer")
        token: str = json.load(response)["value"]
    # log.debug("Logs that a token was given, never the token nor the account it names")
    log_event(log, "oidc.token")
    # log.debug("Returns it")
    return token


# log.debug("Defines the audience a Snowflake account's service users accept")
def snowflake_audience(account: str | None = None) -> str:
    """Returns the account's address, the audience its tokens must name.

    Args:
        account: ORGNAME-ACCOUNTNAME. Required.

    Returns:
        https://orgname-accountname.snowflakecomputing.com.
    """
    # log.debug("Takes the account, which the caller must give")
    account = required(account=account)
    # log.debug("Returns its address in small letters, as the platform's script sets it")
    return f"{SCHEME}{account.lower()}{SNOWFLAKE_DOMAIN}"


# log.debug("Defines the token a Snowflake sign-in uses")
def snowflake_token(settings: PipelineSettings | None = None) -> str:
    """Returns SNOWFLAKE_TOKEN when set, else a fresh one from GitHub.

    Args:
        settings: The Snowflake account and any token set. Required.

    Returns:
        The token to sign in with.
    """
    # log.debug("Takes the settings, which the caller must give")
    settings = required(settings=settings)
    # log.debug("Uses a token set by hand, when there is one")
    if settings.snowflake_token:
        # log.debug("Returns it")
        return settings.snowflake_token.get_secret_value()
    # log.debug("Returns a fresh token from GitHub for this account")
    return github_token(snowflake_audience(settings.snowflake_account))
