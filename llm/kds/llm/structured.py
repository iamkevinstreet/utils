########################################################################
#                      llm/kds/llm/structured.py                       #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Finds the JSON object in a model's answer and validates it against a
pydantic schema.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import json
import logging
import re

# Third-party
from pydantic import BaseModel

# Local
from kds.args import required
from kds.llm.errors import StructuredOutputError

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Matches a fenced code block, with or without a json tag")
JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
# log.debug("Sets the line the schema follows in the system prompt")
SCHEMA_INTRO = "\n\nReturn only a JSON object that validates against this schema:\n"


########################################################################
#                          Structured output                           #
########################################################################
# log.debug("Defines the system prompt that asks for the schema")
def schema_prompt(system: str | None = None, schema: type[BaseModel] | None = None) -> str:
    """Returns the system prompt plus the schema the answer must fit.

    Args:
        system: The caller's system prompt, if any.
        schema: The pydantic model the answer must match. Required.

    Returns:
        The system prompt, then the request for JSON and the schema.
    """
    # log.debug("Takes the schema, which the caller must give")
    schema = required(schema=schema)
    # log.debug("Writes the schema as compact JSON")
    schema_text = json.dumps(schema.model_json_schema(), indent=0)
    # log.debug("Returns the caller's prompt, then the schema request")
    return ((system or "") + SCHEMA_INTRO + schema_text).strip()


# log.debug("Defines how the JSON object is cut out of an answer")
def json_object(text: str | None = None) -> str:
    """Returns the JSON object in `text`, unwrapping a code fence.

    Args:
        text: The model's answer. Required.

    Returns:
        The JSON object's text, cut out of the answer.

    Raises:
        StructuredOutputError: The text holds no JSON object.
    """
    # log.debug("Takes the text, which the caller must give")
    text = required(text=text)
    # log.debug("Trims the answer")
    raw = text.strip()
    # log.debug("Looks for a fenced code block")
    fenced = JSON_FENCE.search(raw)
    # log.debug("Uses the fenced block's contents when there is one")
    if fenced:
        # log.debug("Takes the inside of the fence")
        raw = fenced.group(1).strip()
    # log.debug("Returns the text when it already starts as an object")
    if raw.startswith("{"):
        # log.debug("Returns it")
        return raw
    # log.debug("Finds the first opening and last closing brace")
    start, end = raw.find("{"), raw.rfind("}")
    # log.debug("Stops when there is no object at all")
    if start == -1 or end == -1:
        # log.debug("Raises with the reason")
        raise StructuredOutputError("no JSON object in the response")
    # log.debug("Returns the text between the braces")
    return raw[start : end + 1]


# log.debug("Defines parsing an answer into the schema")
def parse[T: BaseModel](schema: type[T] | None = None, text: str | None = None) -> T:
    """Returns `text`'s JSON object validated as `schema`.

    Args:
        schema: The pydantic model the object must match. Required.
        text: The model's answer. Required.

    Returns:
        The validated object.

    Raises:
        StructuredOutputError: The text holds no JSON object.
        pydantic.ValidationError: The object does not match the schema.
    """
    # log.debug("Takes the schema, which the caller must give")
    schema = required(schema=schema)
    # log.debug("Takes the text, which the caller must give")
    text = required(text=text)
    # log.debug("Validates the extracted object against the schema")
    return schema.model_validate_json(json_object(text))
