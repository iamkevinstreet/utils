# utils

[![ci](https://github.com/iamkevinstreet/utils/actions/workflows/ci.yml/badge.svg)](https://github.com/iamkevinstreet/utils/actions/workflows/ci.yml) [![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Small, separately installable utilities that my AI prototypes share. Each folder is its own package with its
own README, tests and `pyproject.toml`; the repository is the tree they live in. Install only what a project
needs.

```
utils/
  settings/    kds.settings    typed settings from the environment, secrets never printed
  logs/        kds.logs        JSON-lines logging with request ids and redaction
  llm/         kds.llm         one model adapter (Anthropic, OpenAI, Azure, offline stand-in), cost and budget
  evals/       kds.evals       cases, metrics, results tables, model judge, run comparison
  synthetic/   kds.synthetic   made-up names with near duplicates, PDFs that record page text
```

All of them share the `kds` namespace, so a project imports `from kds.llm import ModelAdapter` whichever
folders it installed.

| Folder | Depends on |
| --- | --- |
| `settings` | pydantic |
| `logs` | settings |
| `llm` | settings, logs, the provider SDKs |
| `evals` | llm, logs |
| `synthetic` | reportlab, pypdf |

## Install a utility

```toml
dependencies = [
  "kds-llm @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=llm",
  "kds-evals @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=evals",
]
```

## Prototypes that use these

| Prototype | Repository |
| --- | --- |
| EEOC charge intake: extraction with source spans and human review | [eeoc-charge-intake](https://github.com/iamkevinstreet/eeoc-charge-intake) |
| Grounded Q&A over approved sources, with abstention | [grounded-qa](https://github.com/iamkevinstreet/grounded-qa) |
| New-matter intake agent with scoped tools and approval gates | [intake-conflicts-agent](https://github.com/iamkevinstreet/intake-conflicts-agent) |

Case studies with the evaluation plans and results: https://kevindstreet.com/projects/

## Develop

```sh
uv venv && source .venv/bin/activate
uv pip install pydantic pydantic-settings anthropic openai httpx reportlab pypdf pytest pytest-asyncio ruff
pytest                                  # runs every folder's tests; pyproject.toml puts the five folders on the path
ruff check . && ruff format --check .
```

Editable installs of several folders would fight over the shared `kds` namespace, which is why tests use the
path setting instead. Installs from GitHub (non-editable) merge the namespace correctly.

## Working with AI tools

Parts of this repository were drafted with AI coding assistants. Every generated change was read, run and
tested before it was kept. The commit history shows what changed and why.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
