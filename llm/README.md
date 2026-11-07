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
7. **Span.** Each call runs in a `chat <model>` span, retries included as events, recording the
   provider, the models, the tokens, the cost and why the answer stopped. An embedding call runs in
   an `embeddings <model>` span. See [spans](#spans).

## Spans

Once [kds.logs](../logs/#spans) has turned spans on, the adapter's calls are recorded with nothing
more to write. A project opens the other GenAI spans around its own work:

```python
from kds.llm.spans import agent, documents, retrieval, tool, tool_result

with agent("intake", model=adapter.model):  # invoke_agent intake
    with tool("search_clients", call_id=call.id, arguments=call.arguments) as span:
        tool_result(span, found)  # execute_tool search_clients
with retrieval(question, top_k=6, source="approved-sources") as span:
    documents(span, [(hit.id, hit.score) for hit in hits])  # each passage's id and score
```

- Names follow the OpenTelemetry GenAI conventions, which are still at Development stability and
  now live in their own repository; these follow its commit `e6658f1` of Nov 6, 2026. Every name is
  in `config.py`, so a rename is one edit. Langfuse reads them: a chat span is a generation, a tool
  call a tool, an agent's run an agent.
- Prompts, answers, tool arguments and results, and search queries can hold personal data. They
  are recorded only with `[spans] content = true`, meant for generated or public data, and redacted
  like log lines even then.
- The cost is set as `gen_ai.usage.cost`, which the conventions do not name but Langfuse reads.
- The Anthropic SDK's own spans are off. Since version 1.14 the SDK opens a span for every API
  call, which would repeat the chat span's call, tokens included, and add the account's
  organization and workspace ids. Its trace headers are off too, so no trace id leaves with a
  request.

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
