# config

`settings.toml` lists every setting the shared packages read, at its default. It is the reference a
project copies from: a project's own `config/settings.toml` holds only the sections it changes, and its
config module subclasses `kds.settings.Settings` to add its own.

| Where a value comes from | Wins over |
| --- | --- |
| An argument in code (tests) | everything |
| An environment variable, such as `LLM_MODEL` | `.env` and `settings.toml` |
| `.env` (secrets only, never committed) | `settings.toml` |
| `config/settings.toml` | the defaults in code |

- A key's name is its section and key joined by an underscore: `[llm] model` is `llm_model`, and
  `LLM_MODEL` overrides it.
- Secrets never go in this file. `kds.settings` refuses to start if one does, and names the key without
  printing its value.
- `settings/tests/test_settings.py` fails if this file and the defaults in code drift apart.
- `SETTINGS_FILE=/path/to/other.toml` points the loader at a different file.
