# kds.llm

One adapter for Anthropic, OpenAI and Azure OpenAI, plus an offline stand-in for tests and CI. It
checks the run's budget, retries only failures that can succeed later, validates structured output
against a pydantic model with one repair, prices every call from a dated table, and logs it.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)).

```sh
pip install "kds-llm @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=llm" \
  "kds-logs @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=logs" \
  "kds-settings @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=settings"
```

`kds-llm` needs the other kds packages listed, from the same commit.

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
```

Tests use the offline provider, which answers from a script:

```python
from kds.llm.fake import FakeProvider

adapter = ModelAdapter(FakeProvider(['{"charge_number": "1", "respondent": null}']))
```

## Conventions

- `providers.py` is the only place a concrete provider is chosen; everything else talks to the
  `Provider` interface in `base.py`.
- Retried: connection errors, timeouts, 408, 409, 429 and 5xx, with full-jitter backoff capped at
  eight seconds. The SDKs' own retries are off, so attempts never multiply.
- `pricing.json` holds list prices per million tokens and an `as_of` date that every report prints;
  a dated model name is priced by its longest matching base name.
- Settings: `[llm]`, `[azure_openai]` and `[eval] budget_usd` in
  [config/settings.toml](../config/settings.toml); keys in `.env`.
