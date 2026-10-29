# kds.settings

Typed, read-only settings for every project. Values come from `config/config.toml`, secrets from
`config/.env`, and an environment variable overrides either. Settings are validated once, frozen, and
secrets are `SecretStr`: never in a repr, an error message or a log line.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)).

```sh
pip install "kds-settings @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=settings"
```

## Use

A project has one config module that subclasses `Settings` with its own fields:

```python
from functools import lru_cache

from kds.settings import Settings, describe


class AppSettings(Settings):
    answer_min_score: float = 0.35  # [answer] min_score in config.toml


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()


log_event(log, "settings.loaded", **describe(get_app_settings()))  # secrets show as ********
```

## Conventions

- A TOML key's name is its section and key joined: `[log] level` is `log_level`, and `LOG_LEVEL`
  overrides it.
- Priority, highest first: arguments, environment variables, `config/.env`, `config/config.toml`,
  defaults.
- A secret written into `config.toml` stops startup, naming the key but never printing its value.
- `SETTINGS_FILE` points the loader at another file; tests point it at one that does not exist.

Every shared setting and its default: [config/config.toml](../config/config.toml).

## Develop

```sh
make test   # from the repository root
```
