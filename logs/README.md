# kds.logs

One JSON object per line, a request id on every record, redaction of personal data before anything
is written, and trace lines that print what each line of code does, with the time since start. And
spans: the timed steps of the work, sent with OpenTelemetry to Langfuse or any other tracing tool.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)).

```sh
pip install "kds-logs @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=logs" \
  "kds-settings @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=settings"
```

`kds-logs` needs the other kds packages listed, from the same commit.

## Use

```python
from kds.logs import get_logger, log_event, new_request_id, setup_logging

setup_logging()  # once, when the service starts
log = get_logger(__name__)
with new_request_id():
    log_event(log, "intake.start", email="person@example.com")  # written as "[EMAIL]"
```

```json
{"ts": "2026-10-29T14:02:11.402+00:00", "level": "INFO", "logger": "intake", "request_id": "3f9c2a71b0de", "msg": "intake.start", "kind": "intake.start", "email": "[EMAIL]"}
```

## Trace lines

Every statement in our code has a commented logger line above it. Turn them on
with `kds-standards trace on <path>` and set `[log] trace = true`, and a run prints:

```text
00:00:02 - Splits the question into search terms
00:00:02 - Keeps passages above the relevance cut-off
```

## Spans

A span is one timed step of the work, nested under the step that called it. Spans stay off, at no
cost, until they have somewhere to go: Langfuse, when its two keys are in `config/.env` (an empty key
counts as unset, as CI sets a secret it does not have); any tool the standard
`OTEL_EXPORTER_OTLP_ENDPOINT` variable names; or an evaluation run's own file, with
`[spans] keep = true`.

```python
from kds.logs import setup_spans, step

setup_spans(service="grounded-qa", version=__version__)  # once, when the service or run starts
with step("verify", quotes=3) as span:  # a span named "verify", inside whatever span is open
    span.set_attribute("verify.dropped", 1)
```

- Every span carries the request id of its work, and every log line written inside a span carries
  the span's `trace_id` and `span_id`, so a line leads to its trace and back.
- A failing step records the error's type, never its message, which can hold the data being worked
  on. Text set on a span is redacted as log lines are.
- `session("run-1")` stamps every span inside it with one session id; Langfuse shows them as one
  session. `collect()` keeps the spans that end inside it, and `write_spans()` writes them one JSON
  object per line, as OpenTelemetry describes a span.
- [kds.llm](../llm/) opens the spans for model calls, agents, tools and searches, named as the
  OpenTelemetry GenAI conventions name them; [kds.evals](../evals/) runs each case in its own span.

## Conventions

- Libraries use `logging.getLogger(__name__)` and never configure logging; a service calls
  `setup_logging()` once.
- Redaction covers emails, phone numbers, SSNs, card numbers and dates of birth; pass real names as
  `extra_terms` to `redact()` if a dataset ever holds any.
- Settings live in [config/config.toml](../config/config.toml):

| Setting | Default | What it does |
| --- | --- | --- |
| `[log] dir` | `logs` | where the daily JSON log files go |
| `[log] level` | `INFO` | the lowest level written: `DEBUG`, `INFO`, `WARNING` or `ERROR` |
| `[log] redact` | `true` | removes emails, phone numbers and ID-like numbers before writing |
| `[log] trace` | `false` | prints the logger lines, once turned on, as `HH:MM:SS - what happened` |
| `[spans] keep` | `false` | writes each evaluation run's spans beside its results |
| `[spans] content` | `false` | puts prompts, answers and tool text on spans; for generated or public data |
| `[spans] public` | `false` | lets anyone with a trace's link open it in Langfuse |
| `[langfuse] base_url` | `https://cloud.langfuse.com` | Langfuse's address; `https://us.cloud.langfuse.com` for US data |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | unset | the project's keys, in `config/.env`; with both set, spans go to Langfuse |
