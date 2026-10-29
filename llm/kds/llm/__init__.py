########################################################################
#                       llm/kds/llm/__init__.py                        #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

One model adapter for Anthropic, OpenAI and Azure OpenAI, with an
offline stand-in.

Usage:
    adapter = ModelAdapter()          # provider and model from settings
    record, completion = adapter.complete_json("Extract: ...", Record)
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Local
from kds.llm.adapter import ModelAdapter, get_adapter
from kds.llm.errors import BudgetExceededError, StructuredOutputError, TransientError
from kds.llm.types import Completion, Message, ToolCall, ToolSpec, Usage

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists what the package exports")
__all__ = [
    "BudgetExceededError",
    "Completion",
    "Message",
    "ModelAdapter",
    "StructuredOutputError",
    "ToolCall",
    "ToolSpec",
    "TransientError",
    "Usage",
    "get_adapter",
]
