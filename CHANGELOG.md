# Changelog

Each release names the commit projects pin; nothing installs from `main`. The v0.2 releases were
folded into v0.3.0 when this repository's history was rewritten on Oct 29, 2026, so they have no
commit of their own: pin v0.3.0 or later.

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
