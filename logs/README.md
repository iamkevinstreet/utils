# kds.logs

One JSON object per line, a request id on every record, and redaction of emails, phone numbers, SSN-like and card-like numbers before anything is written. Fields are plain keyword arguments.

## Install

```toml
# in a project's pyproject.toml
dependencies = ["kds-logs @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=logs"]
```

```sh
# or directly
pip install "kds-logs @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=logs"
```

## Use

```python
from kds.logs import get_logger, log_event, new_request_id

log = get_logger("intake")
with new_request_id():
    log_event(log, "intake.start", email="person@example.com")  # written as "[EMAIL]"
```

## Develop

```sh
# from the repository root
pytest logs/tests
```

Apache License 2.0. See the repository `LICENSE` and `NOTICE`.
