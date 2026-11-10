# kds.pipelines

What every project's data layers run on, so each project writes only its own sources and models:
the settings for the warehouse, dlt's state and dbt; a load of any dlt source into one DuckDB file,
Databricks or Snowflake; dbt runs over the same warehouse; and `python -m pipelines`, the one
command a project's Makefile, CI and Airflow DAGs call. On Snowflake a GitHub job signs in as
itself, so no password or key is stored for it.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)).

```sh
pip install "kds-pipelines @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=pipelines" \
  "kds-logs @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=logs" \
  "kds-settings @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=settings" \
  "kds-args @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=args"
```

dbt runs as a process from the project's own environment, so the project pins `dbt-core` and its
adapters (`dbt-duckdb`, `dbt-databricks`, `dbt-snowflake`); dlt's destination extras
(`dlt[duckdb]`, `dlt[databricks]`, `dlt[snowflake]`) likewise.

## Use

A project's settings add its own sources to the shared ones:

```python
from kds.pipelines import PipelineSettings


class AppSettings(PipelineSettings):
    charges_dataset: str = "raw_charges"
```

Its command names its loads:

```python
from kds.pipelines import load, run_command


def load_charges(settings: AppSettings) -> None:
    load(settings, name="charges", dataset=settings.charges_dataset, source=charges(settings))


raise SystemExit(run_command({"charges": load_charges}, get_app_settings))
```

```sh
python -m pipelines load charges   # one load, into the warehouse the settings name
python -m pipelines dbt build      # dbt over the same warehouse
```

## Settings

| Setting | Default | What it does |
| --- | --- | --- |
| `warehouse_destination` | `duckdb` | Where loads go: `duckdb`, `databricks` or `snowflake` |
| `warehouse_path` | `data/generated/warehouse.duckdb` | The DuckDB file |
| `warehouse_state` | `data/generated/dlt` | Where dlt keeps each pipeline's state |
| `dbt_project`, `dbt_target`, `dbt_threads` | `dbt`, `dev`, `4` | The dbt project (which holds `profiles.yml`), its target and threads |
| `databricks_catalog`, `databricks_host`, `databricks_http_path` | `kds`, unset, unset | The Unity Catalog catalog and the SQL warehouse |
| `databricks_token` | unset | A secret, from `config/.env` or the environment only |
| `snowflake_account`, `snowflake_database` | unset, `KDS` | The account, `ORGNAME-ACCOUNTNAME`, and the database |
| `snowflake_token` | unset | A token to sign in with, for a run outside GitHub only; a secret |
| `files_encoding` | `utf-8` | Every file read or written |

Databricks is refused as the destination unless its host, HTTP path and token are all set, and a
host pasted with `https://` is taken bare. Snowflake is refused without its account, and an account
pasted as its address, `https://orgname-accountname.snowflakecomputing.com`, is taken as
`ORGNAME-ACCOUNTNAME`. dbt's `profiles.yml` reads `WAREHOUSE_PATH` and the `DATABRICKS_*` and
`SNOWFLAKE_*` variables, which `run_dbt` sets from these settings, so the loads and the build
always point at the same warehouse. `run_dbt` makes the DuckDB file's folder first, so a build
before any load starts clean.

## Snowflake without a stored secret

Snowflake's workload identity federation signs a service user in with a GitHub Actions job's own
OIDC token, so nothing that could leak is stored for the job. GitHub gives a job a token only when
the workflow lets it ask (`permissions: id-token: write`), and the token names the repository and,
for a job that names one, its environment, which is how Snowflake finds the one service user that
trusts it. The platform repository,
[data-platform-aws-snowflake](https://github.com/iamkevinstreet/data-platform-aws-snowflake), makes
those users, each trusting one repository's job.

Each load and each dbt run asks GitHub for a fresh token just before it connects, made for the
account's own address (`snowflake_audience()`); `snowflake_token()` returns `SNOWFLAKE_TOKEN`
instead when it is set, as for a run outside GitHub. A GitHub token lasts about five minutes, so a
load or a dbt run must make its connections within five minutes of asking; one that would open a
new connection later needs a token per connection, which this does not do yet. A workflow's job
then needs only:

```yaml
permissions:
  contents: read
  id-token: write
environment: snowflake-load
env:
  WAREHOUSE_DESTINATION: snowflake
  DBT_TARGET: snowflake
  SNOWFLAKE_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}
```

The account is kept as a secret only because it names the account; it signs no one in.
