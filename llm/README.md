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

## How a call works

1. **Settings.** The provider, model, retries, timeout and budget come from `kds.settings`; keys
   come from `config/.env` only.
2. **Request id.** Every log line inside `kds.logs.new_request_id()` carries the same id; the
   evaluation runner opens one per case.
3. **Budget.** The adapter refuses to call once the run's spend passes `eval_budget_usd`.
4. **Provider call.** Failures that can succeed later (connection errors, timeouts, 408, 409, 429,
   5xx) are retried with capped, jittered backoff; anything else fails at once with a clear message.
5. **Validation.** `complete_json` parses the answer into a pydantic model and, if it does not fit,
   shows the model its answer and the error once before giving up.
6. **Price and log.** Each call is priced from a dated table and logged with its tokens, latency
   and cost; the evaluation runner sums them per case and per run.

## Conventions

- `providers.py` is the only place a concrete provider is chosen; everything else talks to the
  `Provider` interface in `base.py`.
- Retried: connection errors, timeouts, 408, 409, 429 and 5xx, with full-jitter backoff capped at
  eight seconds. The SDKs' own retries are off, so attempts never multiply.
- `pricing.json` holds list prices per million tokens and an `as_of` date that every report prints;
  a dated model name is priced by its longest matching base name.
- Keys live only in `config/.env`; everything else in [config/config.toml](../config/config.toml).

## Settings

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
| `[eval] budget_usd` | `5.0` | the spend at which a run stops calling |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY` | in `config/.env` only | provider keys |

## Logs and cost

- `llm.call`: one call's model, tokens, latency and cost, and the running spend of the run.
- `llm.retry`: a failure that can succeed later, the attempt and the wait before the next.
- `llm.error`: a call that failed for good; the error's kind, never its text.
- `llm.unpriced_model`: a model missing from `pricing.json`, so its cost reads zero.

## Next

- A second embeddings provider, so retrieval does not depend on OpenAI.
- A warning when `pricing.json` is more than a month old.
