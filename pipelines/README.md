# kds.pipelines

What every project's data layers run on, so each project writes only its own sources and models:
the settings for the warehouse, dlt's state and dbt; a load of any dlt source into one DuckDB file or
Databricks; dbt runs over the same warehouse; and `python -m pipelines`, the one command a
project's Makefile, CI and Airflow DAGs call.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)).

```sh
pip install "kds-pipelines @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=pipelines" \
  "kds-logs @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=logs" \
  "kds-settings @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=settings" \
  "kds-args @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=args"
```

dbt runs as a process from the project's own environment, so the project pins `dbt-core` and its
adapters (`dbt-duckdb`, `dbt-databricks`); dlt's destination extras (`dlt[duckdb]`,
`dlt[databricks]`) likewise.

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
python -m pipelines load charges   # one load, into DuckDB or Databricks as the settings say
python -m pipelines dbt build      # dbt over the same warehouse
```

## Settings

| Setting | Default | What it does |
| --- | --- | --- |
| `warehouse_destination` | `duckdb` | Where loads go: `duckdb` or `databricks` |
| `warehouse_path` | `data/generated/warehouse.duckdb` | The DuckDB file |
| `warehouse_state` | `data/generated/dlt` | Where dlt keeps each pipeline's state |
| `dbt_project`, `dbt_target`, `dbt_threads` | `dbt`, `dev`, `4` | The dbt project (which holds `profiles.yml`), its target and threads |
| `databricks_catalog`, `databricks_host`, `databricks_http_path` | `kds`, unset, unset | The Unity Catalog catalog and the SQL warehouse |
| `databricks_token` | unset | A secret, from `config/.env` or the environment only |
| `files_encoding` | `utf-8` | Every file read or written |

Databricks is refused as the destination unless its host, HTTP path and token are all set, and a
host pasted with `https://` is taken bare. dbt's `profiles.yml` reads `WAREHOUSE_PATH` and the
`DATABRICKS_*` variables, which `run_dbt` sets from these settings, so the loads and the build
always point at the same warehouse. `run_dbt` makes the DuckDB file's folder first, so a build
before any load starts clean.
