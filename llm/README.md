# kds.llm

One adapter for Anthropic, OpenAI and Azure OpenAI, plus an offline stand-in for tests. Retries transient failures, validates structured output against a pydantic model with one repair attempt, prices every call from a dated table, and stops when a run reaches its budget.

## Install

```toml
# in a project's pyproject.toml
dependencies = ["kds-llm @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=llm"]
```

```sh
# or directly
pip install "kds-llm @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=llm"
```

## Use

```python
from pydantic import BaseModel
from kds.llm import ModelAdapter


class Record(BaseModel):
    charge_number: str | None
    respondent: str | None


adapter = ModelAdapter()  # provider and model from settings
record, completion = adapter.complete_json("Extract: ...", Record)
completion.cost_usd, completion.latency_ms, adapter.spent_usd

# tests: no network
from kds.llm.fake import FakeProvider

adapter = ModelAdapter(FakeProvider(['{"charge_number": "1", "respondent": null}']), model="fake-model")
```

## Develop

```sh
# from the repository root
pytest llm/tests
```

Apache License 2.0. See the repository `LICENSE` and `NOTICE`.
