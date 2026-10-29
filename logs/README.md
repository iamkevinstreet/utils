# kds.logs

One JSON object per line, a request id on every record, redaction of personal data before anything
is written, and trace lines that print what each line of code does, with the time since start.

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
