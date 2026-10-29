# utils

[![ci](https://github.com/iamkevinstreet/utils/actions/workflows/ci.yml/badge.svg)](https://github.com/iamkevinstreet/utils/actions/workflows/ci.yml) [![codeql](https://github.com/iamkevinstreet/utils/actions/workflows/codeql.yml/badge.svg)](https://github.com/iamkevinstreet/utils/actions/workflows/codeql.yml) [![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Small, separately installable Python packages that my AI prototypes share: settings, logging, one
model adapter, evaluation, test data, and the tools that hold every repository to one standard.

## Status

Release **v0.3.0**. All seven packages are in use by the three prototypes below; 78 tests
pass offline in CI, with strict mypy and no kds-standards findings. Next: a second embeddings
provider, and a warning when the price table is more than a month old.

## Quick start

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/). No API key: the offline fake provider is the
default.

```sh
git clone https://github.com/iamkevinstreet/utils.git && cd utils
make install          # .venv from the hashed lockfile
make check test       # lint, strict types, the code standard, then every test
```

## Installing a package

A project installs only the packages it uses, each from git at one commit SHA, so nothing changes
underneath it. List every kds package the ones you use depend on (`kds-llm` needs `kds-settings` and
`kds-logs`), all at the same commit. With uv, in the project's `pyproject.toml`:

```toml
[project]
dependencies = ["kds-settings", "kds-logs", "kds-llm"]

[tool.uv.sources]
kds-settings = { git = "https://github.com/iamkevinstreet/utils", subdirectory = "settings", rev = "<commit>" }
kds-logs = { git = "https://github.com/iamkevinstreet/utils", subdirectory = "logs", rev = "<commit>" }
kds-llm = { git = "https://github.com/iamkevinstreet/utils", subdirectory = "llm", rev = "<commit>" }
```

None of these packages is on PyPI. A kds name left to the default index could resolve to a
stranger's package, so `uv.lock` must show every kds package coming from this repository. The
commits behind each release are in [CHANGELOG.md](CHANGELOG.md).

## Architecture at a glance

![utils at a glance: four runtime packages, test data, developer tools, and the one path to a model provider](docs/architecture.svg)

| Package | Import | What it does | Depends on |
| --- | --- | --- | --- |
| [settings](settings/) | `kds.settings` | typed, frozen settings from `config/settings.toml` and `.env` | pydantic |
| [logs](logs/) | `kds.logs` | JSON-lines logs, request ids, redaction, trace lines | settings |
| [llm](llm/) | `kds.llm` | one adapter for Anthropic, OpenAI, Azure and an offline fake | settings, logs |
| [evals](evals/) | `kds.evals` | cases, metrics, a runner, reports, a judge | llm, logs |
| [synthetic](synthetic/) | `kds.synthetic` | made-up names, near duplicates, PDFs that record page text | reportlab, pypdf |
| [standards](standards/) | `kds.standards` | `kds-standards`: holds a repository to one code standard | none |
| [diagrams](diagrams/) | `kds.diagrams` | `kds-diagrams`: draws these diagrams from TOML | none |

## How it works

![How a model call works: settings, request id, budget, provider call, validation, pricing](docs/flow.svg)

1. **Load settings.** `kds.settings` reads `config/settings.toml`, then secrets from `.env`;
   environment variables override both. It validates everything once and freezes it.
2. **Open a request id.** `kds.logs.new_request_id()` tags every log line in the block; the
   evaluation runner opens one per case.
3. **Check the budget.** The adapter refuses to call once the run's spend passes `eval_budget_usd`.
4. **Call the provider.** Failures that can succeed later (connection errors, 408, 409, 429, 5xx)
   are retried with capped, jittered backoff; anything else fails at once with a clear message.
5. **Validate the JSON.** `complete_json` parses the answer into a pydantic model and, if it does not
   fit, shows the model its answer and the error once.
6. **Price and log.** Each call is priced from a dated table and logged with its tokens, latency and
   cost; the evaluation runner sums them per case and per run.

## Design

- **Context.** Three prototypes each call a model, log, and measure themselves. Separate copies of
  that plumbing would drift, and their numbers would stop being comparable.
- **Requirements.** Any provider behind one interface; bounded spending; schema-checked answers;
  traceable runs; no secrets in config or logs; offline, deterministic tests; install only what is
  used.
- **Options considered.** Copying the code into each project; one large package; a framework such as
  LangChain; small packages in one namespace. The last was chosen: each project pulls only its
  dependencies, and a fix lands once.
- **Test plan.** Every package's tests run offline in CI with warnings as errors; the retry, repair
  and budget paths are tested with failing fakes.
- **Rollout.** Each release is a changelog entry naming the commit projects pin; a project moves to
  a new release in its own pull request.

## Results

This repository has no model evaluation of its own; its packages produce the results tables in each
project:

| Prototype | Repository |
| --- | --- |
| EEOC charge intake: extraction with source spans and human review | [eeoc-charge-intake](https://github.com/iamkevinstreet/eeoc-charge-intake) |
| Grounded Q&A over approved sources, with abstention | [grounded-qa](https://github.com/iamkevinstreet/grounded-qa) |
| New-matter intake agent with scoped tools and approval gates | [intake-conflicts-agent](https://github.com/iamkevinstreet/intake-conflicts-agent) |

Case studies with the evaluation plans and results: https://kevindstreet.com/projects/

## Configuration

Every shared setting, with its default, is in [config/settings.toml](config/settings.toml); a test
fails if that file and the defaults in code drift apart. Secrets are only ever in `.env` (names in
[.env.example](.env.example)).

| Setting | Default | What it does |
| --- | --- | --- |
| `[llm] provider` | `fake` | `anthropic`, `openai`, `azure`, or `fake` (offline, no key) |
| `[llm] model` | `claude-sonnet-5-5` | the model that does the work |
| `[llm] judge_model` | `claude-sonnet-5-5` | the model that grades answers in evaluations |
| `[llm] embedding_model` | `text-embedding-3-small` | the model that turns text into vectors |
| `[llm] max_tokens` | `2048` | the most tokens one answer may use |
| `[llm] temperature` | `0.0` | sampling temperature, where the SDK accepts one |
| `[llm] max_retries` | `3` | retries for failures that can succeed later |
| `[llm] timeout_s` | `60.0` | how long one call may take |
| `[azure_openai] endpoint`, `api_version` | unset, `2024-10-21` | the Azure OpenAI resource |
| `[eval] budget_usd` | `5.0` | the spend at which a run stops |
| `[log] dir`, `level` | `logs`, `INFO` | where JSON logs go and the lowest level written |
| `[log] redact` | `true` | remove emails, phone numbers and ID-like numbers |
| `[log] trace` | `false` | print logger lines as `HH:MM:SS - what happened` |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY` | in `.env` only | provider keys |

## Operating it

- **Logs.** A service calls `setup_logging()` once at startup. Every event is one JSON line in
  `<log dir>/YYYY-MM-DD.jsonl` and on stderr, with a timestamp, level, logger, request id and the
  event's fields, redacted by default.
- **Following one request.** Every line carries a request id; filter on it to see one request or one
  evaluation case from start to finish.
- **Tracing a run.** `kds-standards trace on <path>` turns the logger lines on; with
  `[log] trace = true` they print as `00:00:02 - Splits the question into search terms`.
  `kds-standards trace off <path>` turns them off again before you commit.
- **Cost.** Every `llm.call` line carries its tokens, latency and cost, and the running spend of the
  run.

There is no service to run here, so there is no runbook; each prototype has its own.

## Testing

```sh
make test     # 78 tests, offline, warnings as errors
make check    # ruff, strict mypy and kds-standards
make audit    # pip-audit over every locked dependency
```

The tests are deterministic: the fake provider answers from a script, names and PDFs come from
fixed seeds, retries use a no-op sleep, every file goes to a temporary folder, and the root
`conftest.py` gives every test the offline provider and an empty settings file.

## Security

Secrets live only in `.env`, and the settings loader refuses one in `settings.toml`. Logs redact
personal data by default. Dependencies are locked with hashes and audited in CI; Actions are pinned
to commit SHAs; gitleaks scans every commit and the whole history; CodeQL scans the code. To report a
vulnerability, see [SECURITY.md](SECURITY.md).

## Project layout

```
utils/
├── settings/      kds.settings: settings.toml and .env, typed and frozen
├── logs/          kds.logs: JSON lines, request ids, redaction, traces
├── llm/           kds.llm: the model adapter, providers, pricing
├── evals/         kds.evals: cases, metrics, runner, reports, judge
├── synthetic/     kds.synthetic: made-up names and PDFs
├── standards/     kds.standards: the kds-standards checker
├── diagrams/      kds.diagrams: the kds-diagrams renderer
├── config/        settings.toml: every shared setting at its default
├── docs/          diagrams.toml and the two SVGs it draws
└── .github/       CI, CodeQL, Dependabot, CODEOWNERS
```

Each package folder holds its own `pyproject.toml`, `README.md`, `kds/<name>/` and `tests/`. All of
them share the `kds` namespace, so a project imports `from kds.llm import ModelAdapter` whichever
packages it installed. Tests run from the root, where `pyproject.toml` puts every package on the
path.

## Changelog and license

Releases are listed in [CHANGELOG.md](CHANGELOG.md). Every file follows one code standard, which
`kds-standards` checks in pre-commit and CI.

Parts of this repository were drafted with AI coding assistants. Every change was read, run and
tested before it was kept.

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
