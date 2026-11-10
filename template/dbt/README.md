# dbt

One dbt project, built in DuckDB (`dev`, CI), Databricks (`prod`) or Snowflake (`snowflake`). Run
it through `python -m pipelines dbt <command>`, which points `profiles.yml` at the warehouse the
loaders used; `make build` and `make docs` do.

| Folder | Layer | Built as |
| --- | --- | --- |
| `models/staging/` | One view per raw table, `stg_<source>__<table>`: renamed and cast, nothing joined | Views in `staging` |
| `models/intermediate/` | The sources lined up to one grain, `int_<domain>__<what>` | Views in `intermediate` |
| `models/<domain>/` | A published mart per domain: `dim_`, `fct_` and `rpt_` tables, each with an enforced contract, in the domain's group, public | Tables in `<domain>` |
| `seeds/` | Reference tables, small and reviewed by hand | Tables in `reference` |
| `macros/` | The schema names, a surrogate key every warehouse computes alike, and two generic tests: a unique combination of columns, and a value between two bounds | |
| `tests/` | Singular tests: a query that returns the rows that break a rule | |

The repository's code standard allows three folders below the root, so the published marts sit in
a folder per domain directly under `models/`, beside the staging and intermediate layers.

Each source's raw tables are declared in `models/staging/_<source>__sources.yml`, with a freshness
limit, so `make freshness` reports how long ago each was loaded. Every mart's YAML gives its grain
and its columns with their types, which the contract enforces; unit tests check logic on
hand-written rows. Anonymous usage reporting and the version check are off in `dbt_project.yml`.
