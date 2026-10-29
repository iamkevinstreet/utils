########################################################################
#                               Makefile                               #
########################################################################
# Author:            Kevin Street
# Created on:        2026-10-29
# Last modified on:  2026-10-29
#
# One command for each routine task; CI runs the same targets, so local
# and CI checks match.
#
# The Python to run tools with: the project's .venv locally, `PY=python` in CI.

PY ?= .venv/bin/python
PACKAGES := -p kds.args -p kds.settings -p kds.logs -p kds.llm -p kds.evals -p kds.synthetic \
            -p kds.standards -p kds.diagrams

.PHONY: install check test audit diagrams

install:  ## Create .venv from the hashed lockfile
	uv venv --python 3.12
	uv pip install --require-hashes -r requirements-dev.txt

check:  ## Lint, format, strict types and the code standard
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
	$(PY) -m mypy $(PACKAGES)
	PYTHONPATH=standards:args $(PY) -m kds.standards.cli check .

test:  ## Every package's tests, offline, warnings as errors
	$(PY) -m pytest -W error

audit:  ## Known vulnerabilities in every locked dependency
	$(PY) -m pip_audit --strict -r requirements-dev.txt --require-hashes --disable-pip

diagrams:  ## Redraw docs/architecture.svg and docs/flow.svg
	PYTHONPATH=diagrams:args $(PY) -m kds.diagrams docs/diagrams.toml
