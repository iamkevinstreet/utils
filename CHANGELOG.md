# Changelog

Each release names the commit projects pin; nothing installs from `main`. The v0.2 releases were
folded into v0.3.0 when this repository's history was rewritten on Oct 29, 2026, so they have no
commit of their own: pin v0.3.0 or later.

## Unreleased

- **Dependency updates land by themselves.** Dependabot groups each week's updates into one pull
  request per kind, and the new `dependency-updates` workflow lands them every weekday: it applies the
  oldest open one to `main` as an ordinary commit, refreshes the dates in the headers it changes, runs
  the whole of CI on that commit, and moves `main` to it only when every check passes. One whose checks
  fail is labelled "needs a person" and waits. CI can now be called for a given commit, which is how the
  workflow checks one before it lands.

## v0.6.0, Nov 7, 2026

Pin: named in the next commit

Spans: every project's work can now be traced with OpenTelemetry and read in Langfuse or any other
tracing tool. Spans stay off, at no cost, until they have somewhere to go.

- **logs:** `setup_spans()` turns spans on when Langfuse's keys are set (`LANGFUSE_PUBLIC_KEY` and
  `LANGFUSE_SECRET_KEY` in `config/.env`), when the standard `OTEL_EXPORTER_OTLP_ENDPOINT` names a
  tool, or when `[spans] keep` asks for a run's own file. `step()` runs a block as one span, records
  a failure by its type and never its message, and redacts text as log lines are. Each span carries
  its request id, and each log line written inside a span carries the span's `trace_id` and
  `span_id`. `session()`, `collect()` and `write_spans()` let a run share one session and keep its
  spans. The request id moves to `kds.logs.request`; `kds.logs` still exports it.
- **llm:** every model call runs in a `chat <model>` span and every embedding call in an
  `embeddings <model>` span, retries as events, with the provider, models, tokens, cost and stop
  reason named as the OpenTelemetry GenAI conventions name them (their repository's commit `e6658f1`,
  Nov 6, 2026; the names live in `config.py`). `agent()`, `tool()` and `retrieval()` open the spans a
  project's own agents, tools and searches need. Prompts, answers, tool text and queries are
  recorded only with `[spans] content`.
- **evals:** each case runs in its own `eval <case id>` span that records its scores, also as GenAI
  evaluation results; a run's cases share one session, and with `[spans] keep` the run writes
  `<name>-<time>.spans.jsonl` beside its results. A score is a number, a yes or no, or a word: a list
  or a table a scorer returns beside its scores is the case's detail, which the results file keeps
  and the span leaves off, since it may hold what the documents say.
- **settings:** `[spans] keep`, `content` and `public`, `[langfuse] base_url`, and the two Langfuse
  keys as secrets.
- **standards:** an MCP server's tools, resources and prompts keep parameters without defaults, as
  FastAPI's routes do, since a tool's signature is the schema its caller sees. A test covers it.
- **Dependencies:** `kds-logs` needs `opentelemetry-api`, `opentelemetry-sdk` and
  `opentelemetry-exporter-otlp-proto-http` 1.45 or later; `kds-llm` and `kds-evals` need the API.
  `requirements-dev.txt` is recompiled with uv, the command its header names.
- **All packages** move to 0.6.0 together and name each other as `>=0.6,<0.7`; a project moves its
  kds requirements to `>=0.6.0,<0.7` with the new pin. 150 tests.

## v0.5.2, Nov 5, 2026

Pin: `4cff45d3fb22d2359ee61de49c652b04cae1c246`

- **Dependencies:** `requirements-dev.txt`, the hashed lockfile every package is tested against,
  moves to pydantic 2.14.2 (with pydantic-core 2.50.2) and openai 3.42.1. Nothing had to change
  for them: the tests, strict mypy, the code standard and the audit pass as they were. The
  packages still ask a project for `pydantic>=2.8` and `openai>=1.50`, so no project has to move.
- **All packages** move to 0.5.2 together.

## v0.5.1, Nov 3, 2026

Pin: `e57de0e97d1c41616af1a98873f6beeecc74c99f`

- **standards:** the TypeScript logger-line rule now sees the statements inside a function whose
  signature wraps and ends `): Type {`, and inside a bare `catch {`; both read as values before.
  Two tests cover them.
- **All packages** move to 0.5.1 together.

## v0.5.0, Nov 3, 2026

Pin: `fcac0477e1caadccf1e2d7580ce648258c5a79fa`

The box every file opens with, and every section banner, is five lines tall now: a border, a blank
walled line, the title, another blank walled line, and a border. The old three-line box is no
longer accepted.

- **standards:** `kds-standards check` asks for the five-line box in the header and in every
  banner. `kds-standards stamp` brings a file's old three-line boxes to the new form, so one run
  over a repository migrates it. The header code is split in two: `header` draws, `parsing`
  reads and checks. The dotfiles that take `#` comments (`.editorconfig`, `.gitattributes`,
  `.gitignore`, `.gitleaksignore`, `.prettierignore`, `.dockerignore`) carry a header like a
  Makefile, and are checked and stamped like one.
- **standards:** a TypeScript import written over more than nine lines, one name per line as
  Prettier writes a long one, is read to its end, so its source is known: its label is checked and
  the names it takes from the config count as config values. Before, it was cut off after nine
  lines.
- **All packages** move to 0.5.0 together and name each other as `>=0.5,<0.6`. 127 tests.

## v0.4.2, Oct 29, 2026

Pin: `62a38c5a3ecf667e3e227b18412abd77759c38d5`

- **standards:** the `functions` rule now flags a Python function that runs more than 60 lines
  below its doc block, counting every line: logger lines, comments and blanks too. With no doc
  block, the count starts at the comments above the first statement. The README's table lists
  every rule the checker has. Two tests cover it; 124 tests in all.
- **All packages** move to 0.4.2 together.

## v0.4.1, Oct 29, 2026

Pin: `a8e96e31d30b98415cd842a5fa4bbc96f259bc07`

- **standards:** the `docs` rule treats Markdown under `src/content/`, where a site keeps the text of
  its pages, as data, the way it treats `data/`: it may stay, and its links are not checked. Four
  logger lines that named a parameter without saying what it holds now say it.
- **All packages** move to 0.4.1 together.

## v0.4.0, Oct 29, 2026

Pin: `74142bcad36446dd53b66f462b8e3a8b3bc3fe56`

Every package now follows the code standard's new file layout, and one package joins them.

- **The file layout.** Each file opens with a box that holds only its path, then a doc block (the
  module docstring in Python) with the author, the dates and a description. After it come the
  Imports (standard library, third-party and local, each under a label), the Global constants (the
  logger, then the values the file takes from its package's config), the Local constants, and one
  section for the file's own job, each under a banner. Values two modules of a package share live in
  that package's `config.py`.
- **Functions show their whole contract.** Every parameter has a type and a default, `None` where
  there is no natural one; a function that cannot work without a value takes it with `required()`
  (or, for a union type, a guard that raises `missing()`), and every function's doc block lists each
  argument and what comes back. Library overrides keep their library's signature.
- **New: `kds-args`.** `required()` and `missing()`: the arguments a function cannot do without,
  named in the error the way Python names a missing argument.
- **settings:** values come from `config/config.toml` and secrets from `config/.env`, so everything a
  project configures lives in one folder. `config/.env.example` lists the secret names.
- **standards:** `kds-standards check` enforces the new layout: the title box and doc block, the
  banners and their order, the import labels, every function's defaults and doc block (and that
  `Required.` in a doc block matches `required()` in the body), and constants that two files of one
  project share. `stamp` also recentres every banner and puts the import labels back in place after
  a sort. A TypeScript doc block may sit between a function and its logger line.
- **llm:** the first retry waits up to the 0.5 s the docs promise, not 1 s. A missing key's message
  points at `config/.env`.
- **Docs:** the README describes the repository as the workshop every project draws from: tools
  collected over time, of which each project takes what it needs. Its flow diagram shows how a
  project uses them. Everything specific to model calls (the steps of a call, its settings, its log
  lines and what is next) is in the llm package's README, and each package's README lists the
  settings it reads. Package docstrings say "project" where they said "prototype".
- **All packages** move to 0.4.0 together and name each other as `>=0.4,<0.5`. 122 tests.

## v0.3.0, Oct 29, 2026

Pin: `1b67de07d6de8006f4d6f0ee7ea5668277e411f7`

- **standards:** `kds-standards check` no longer asks each repository for a copy of the standard. A
  new `docs` rule checks what a repository publishes: README.md files, a root CHANGELOG.md and a root
  SECURITY.md, and no other Markdown outside `data/`. Every relative link or image in them must
  resolve to a file or folder the repository holds, so nothing a visitor reads points at a private
  or removed file. Five tests cover it.
- **All packages** move to 0.3.0 together and name each other as `>=0.3,<0.4`.

## v0.2.3, Oct 29, 2026

- **llm:** when a model calls several tools in one turn, the Anthropic provider now sends their
  results back in one user turn, as the Messages API asks, instead of one user turn per result.
  A test covers it.

## v0.2.2, Oct 29, 2026

- **standards:** the TypeScript logger-line rule no longer mistakes the lines of a union written one
  member per line (`| { kind: 'a' }`) for statements, or an object that opens on its own line inside
  a call or array for a code block. A callback's body inside a call is still checked. The rule now
  has its own tests (ten), which it lacked.

## v0.2.1, Oct 29, 2026

- **Typed for callers.** Every package ships a `py.typed` marker (PEP 561), so a project that runs
  mypy checks its calls into `kds` against the type hints instead of skipping them. A test keeps
  every package marked and all seven at one version.

## v0.2.0, Oct 29, 2026

Every package now follows one code standard, and two packages join them.

- **New: `kds-standards`.** `kds-standards check .` enforces the standard: the header box, a logger
  line above every statement, file length, folder depth, required files and ignore rules. `stamp`
  keeps header dates true to git; `trace on|off` switches the logger lines.
- **New: `kds-diagrams`.** Draws README architecture and flow diagrams as SVG in one house style, and
  refuses text that would overflow its box.
- **settings:** values come from `config/settings.toml` (grouped by section) as well as the
  environment; secrets are refused in that file; settings are frozen once built; `describe()`
  gives the startup summary with secrets masked. New settings: `llm_max_tokens`, `llm_temperature`,
  `llm_max_retries`, `llm_timeout_s`, `log_level`, `log_trace`. The Entra settings moved to the
  intake agent, the one project that uses them.
- **logs:** `setup_logging()` is called once at startup instead of on import; turned-on logger lines
  print as `HH:MM:SS - what happened`.
- **llm:** retries only failures that can succeed later (connection errors, 408, 409, 429, 5xx) with
  capped, jittered backoff, and the SDKs no longer retry underneath it; a dated model name is priced
  by its longest matching base name, so `gpt-4.1-mini-...` is no longer priced as `gpt-4.1`.
- **evals:** the summary and Markdown report moved to `summary.py`; `judge()` takes the case as one
  dict; `changelog_line()` takes the two runs as a pair.
- **Installing:** packages name each other by version range, and projects pin every kds package to
  one commit through `[tool.uv.sources]` and `uv.lock`, instead of following `main`.
- **Repository:** strict mypy, a hashed lockfile, `pip-audit`, CodeQL, Dependabot, Actions pinned to
  commit SHAs, a checksum-verified gitleaks, `SECURITY.md`, and README diagrams.

## v0.1.0, Oct 13, 2026

Five utilities: settings, logs, llm, evals, synthetic. 22 tests. CI installs each folder in dependency
order, runs its tests, lints the tree and scans history for secrets.
