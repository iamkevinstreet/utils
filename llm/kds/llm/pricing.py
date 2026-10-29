########################################################################
#                        llm/kds/llm/pricing.py                        #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Prices each call at list price from a dated table, so every report says
which prices it used. The table, pricing.json, ships inside this
package and gives USD per million tokens.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging
from functools import lru_cache
from importlib import resources
from typing import Any

# Local
from kds.args import required
from kds.llm.types import Usage

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Names the price table shipped inside this package")
TABLE = "pricing.json"
# log.debug("Sets the tokens each listed price is for")
PER_TOKENS = 1_000_000
# log.debug("Sets the decimal places a cost is rounded to")
COST_PLACES = 6


########################################################################
#                             Call pricing                             #
########################################################################
# log.debug("Defines the one read of the price table")
@lru_cache(maxsize=1)
def load_table() -> dict[str, Any]:
    """Returns the price table, read once per process.

    Returns:
        The table: its as_of date and each model's prices.
    """
    # log.debug("Reads the table's text from the package")
    text = resources.files("kds.llm").joinpath(TABLE).read_text(encoding="utf-8")
    # log.debug("Parses it")
    table: dict[str, Any] = json.loads(text)
    # log.debug("Returns the table")
    return table


# log.debug("Defines the date the prices were checked")
def prices_as_of() -> str:
    """Returns the table's as_of date, which every report prints.

    Returns:
        The date, or "unknown" when the table has none.
    """
    # log.debug("Returns the date, or unknown if the table lacks one")
    return str(load_table().get("as_of", "unknown"))


# log.debug("Defines how a model name finds its prices")
def prices_for(model: str | None = None) -> dict[str, float] | None:
    """Returns the model's prices; a dated name matches its base name.

    "claude-sonnet-4-5-20250929" is priced as "claude-sonnet-4-5", and
    the longest base name wins, so "gpt-4.1-mini-x" is not "gpt-4.1".

    Args:
        model: The model's name, as the provider gives it. Required.

    Returns:
        The model's input and output prices per million tokens, or
        None when no name in the table matches.
    """
    # log.debug("Takes the model, which the caller must give")
    model = required(model=model)
    # log.debug("Reads the per-model prices")
    models: dict[str, dict[str, float]] = load_table()["models"]
    # log.debug("Returns an exact match first")
    if model in models:
        # log.debug("Returns the exact entry")
        return models[model]
    # log.debug("Finds the longest base name the model starts with")
    base = max((name for name in models if model.startswith(name)), key=len, default=None)
    # log.debug("Returns that base name's prices, or None if none matched")
    return models[base] if base else None


# log.debug("Defines the cost of one call")
def estimate_cost(model: str | None = None, usage: Usage | None = None) -> float | None:
    """Returns the call's cost in USD, or None for an unpriced model.

    Args:
        model: The model's name, as the provider gives it. Required.
        usage: The tokens the call read and wrote. Required.

    Returns:
        The cost in USD, rounded, or None for an unpriced model.
    """
    # log.debug("Takes the model, which the caller must give")
    model = required(model=model)
    # log.debug("Takes the usage, which the caller must give")
    usage = required(usage=usage)
    # log.debug("Finds the model's prices")
    prices = prices_for(model)
    # log.debug("Returns None so the caller can log an unpriced model")
    if prices is None:
        # log.debug("Returns no cost")
        return None
    # log.debug("Prices the tokens read and written")
    cost = usage.input_tokens * prices["input"] + usage.output_tokens * prices["output"]
    # log.debug("Returns the cost per token, rounded")
    return round(cost / PER_TOKENS, COST_PLACES)
