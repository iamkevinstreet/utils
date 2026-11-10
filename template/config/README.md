# config

[`config.toml`](config.toml) lists every setting the loaders, the build and the DAGs read, at its
default. It holds no secrets: those go in `config/.env` (copy [`.env.example`](.env.example), which
names each one), and the settings refuse a secret written in `config.toml`.

## How a value is chosen

Highest first: an environment variable, then `config/.env`, then `config.toml`, then the default in
code. Each key's environment name is its section and key joined by an underscore, in capitals:
`[warehouse] path` is `WAREHOUSE_PATH`. A test (`tests/test_config.py`) keeps `config.toml` equal to
the defaults in code.

dbt reads the same warehouse: `python -m pipelines dbt ...` sets `WAREHOUSE_PATH` and the Databricks
and Snowflake variables from these settings before it starts dbt, and `dbt/profiles.yml` reads them.
On Snowflake that includes a token made for this run: a GitHub job signs in as itself, with the
OIDC token GitHub gives a job allowed to ask for one (`permissions: id-token: write`), so no
password or key is stored for it.

## Every setting

| Setting | Default | What it does |
| --- | --- | --- |
| `[warehouse] destination` | `duckdb` | Where dlt loads: `duckdb`; `databricks`, with the three Databricks secrets; or `snowflake`, with `SNOWFLAKE_ACCOUNT` |
| `[warehouse] path` | `data/generated/warehouse.duckdb` | The DuckDB file dlt loads and dbt builds in |
| `[warehouse] state` | `data/generated/dlt` | dlt's pipeline state |
| `[dbt] project` | `dbt` | The dbt project, which also holds `profiles.yml` |
| `[dbt] target` | `dev` | `dev` builds in DuckDB, `prod` in Databricks, `snowflake` in Snowflake |
| `[dbt] threads` | `4` | Models dbt builds at once |
| `[databricks] catalog` | `kds` | The Unity Catalog catalog every schema lives in |
| `[snowflake] database` | `KDS` | The Snowflake database every schema lives in |
| `[files] encoding` | `utf-8` | Every file read or written |
| `[log] dir`, `level` | `logs`, `INFO` | Where `kds.logs` writes one JSON line per event, and from what level |

The secrets, in `config/.env` or the environment only: `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH`
and `DATABRICKS_TOKEN`; `SNOWFLAKE_ACCOUNT`, which names the account; and `SNOWFLAKE_TOKEN`, for a
run outside GitHub only.
