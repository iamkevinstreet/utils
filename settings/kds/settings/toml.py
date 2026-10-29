########################################################################
#                    settings/kds/settings/toml.py                     #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-10-29

Reads config/config.toml as a settings source: its sections become
flat field names, and a secret written into it stops startup, naming
the key but never printing its value.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path
from typing import Any, get_args

# Third-party
from pydantic import SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

# Local
from kds.args import required

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Names the variable that points at another settings file")
FILE_VARIABLE = "SETTINGS_FILE"
# log.debug("Sets where the settings file lives, from the working folder")
DEFAULT_FILE = Path("config/config.toml")
# log.debug("Sets the encoding the settings file is read in")
ENCODING = "utf-8"


########################################################################
#                            Settings file                             #
########################################################################
# log.debug("Defines how the settings file is found")
def settings_path() -> Path:
    """Returns the settings file: SETTINGS_FILE if set, else default.

    Returns:
        The path SETTINGS_FILE names, or config/config.toml.
    """
    # log.debug("Returns the override or the default path")
    return Path(os.environ.get(FILE_VARIABLE) or DEFAULT_FILE)


# log.debug("Defines how a TOML table becomes flat field names")
def flatten(table: dict[str, Any] | None = None) -> dict[str, Any]:
    """Turns `[llm] provider = "fake"` into `{"llm_provider": "fake"}`.

    Sections group related settings in the file; the fields stay flat,
    so a value's TOML name and its environment variable name match:
    `[llm] provider` is `llm_provider` is `LLM_PROVIDER`.

    Args:
        table: The parsed TOML file, sections as nested tables.
            Required.

    Returns:
        One flat table, each section's keys named section_key.
    """
    # log.debug("Takes the table, which the caller must give")
    table = required(table=table)
    # log.debug("Starts an empty flat table")
    flat: dict[str, Any] = {}
    # log.debug("Walks each top-level key or section")
    for key, value in table.items():
        # log.debug("Prefixes each key in a section with the section name")
        if isinstance(value, dict):
            # log.debug("Adds the section's keys under section_key names")
            flat |= {f"{key}_{inner}": item for inner, item in value.items()}
        else:
            # log.debug("Keeps a top-level key as it is")
            flat[key] = value
    # log.debug("Returns the flat table")
    return flat


# log.debug("Defines the test for a field that holds a secret")
def is_secret(field: FieldInfo | None = None) -> bool:
    """Returns whether a field holds a secret, optional or not.

    Args:
        field: The settings field to test. Required.

    Returns:
        True when the field's type is SecretStr or includes it.
    """
    # log.debug("Takes the field, which the caller must give")
    field = required(field=field)
    # log.debug("Returns whether SecretStr is the type or one of its parts")
    return field.annotation is SecretStr or SecretStr in get_args(field.annotation)


# log.debug("Defines the source pydantic-settings reads the file through")
class TomlSource(PydanticBaseSettingsSource):
    """Settings from config/config.toml; a missing file means none."""

    # log.debug("Defines the constructor, which reads the file once")
    def __init__(self, settings_cls: type[BaseSettings] | None = None) -> None:
        """Reads and flattens the file, then refuses any secret in it.

        Args:
            settings_cls: The settings class the values are for, whose
                fields say which names are secrets. Required.

        Raises:
            ValueError: When the file holds a value for a secret field.
        """
        # log.debug("Takes the settings class, which the caller must give")
        settings_cls = required(settings_cls=settings_cls)
        # log.debug("Hands the settings class to the base source")
        super().__init__(settings_cls)
        # log.debug("Finds the settings file")
        path = settings_path()
        # log.debug("Reads it as flat values, or none when it is absent")
        self.values = (
            flatten(tomllib.loads(path.read_text(encoding=ENCODING))) if path.is_file() else {}
        )
        # log.debug("Finds each value that names a secret field")
        secrets = sorted(
            name
            for name in self.values
            if name in settings_cls.model_fields and is_secret(settings_cls.model_fields[name])
        )
        # log.debug("Stops when a secret was written into the file")
        if secrets:
            # log.debug("Words the error, naming the secrets but not their values")
            msg = f"{path} holds secrets {secrets}; secrets go in config/.env, never here"
            # log.debug("Raises it")
            raise ValueError(msg)

    # log.debug("Defines the per-field lookup the base class requires")
    def get_field_value(  # fixed: pydantic-settings' signature
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        """Returns one field's value from the file, with its key.

        Args:
            field: The field pydantic-settings is filling.
            field_name: The field's name, which is its key in the file.

        Returns:
            The value (None when the file lacks it), the key, and False:
            the value is never parsed again as JSON.
        """
        # log.debug("Returns the value, or None when the file lacks it")
        return self.values.get(field_name), field_name, False

    # log.debug("Defines what the source contributes to the settings")
    def __call__(self) -> dict[str, Any]:
        """Returns every value in the file, unknown names included.

        The settings class decides what unknown names mean: the shared
        base ignores them, a project's own class can forbid them.

        Returns:
            A copy of the file's flat values.
        """
        # log.debug("Returns a copy of the file's flat values")
        return dict(self.values)
