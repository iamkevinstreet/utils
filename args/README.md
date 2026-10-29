# kds.args

Takes a function's arguments the code standard's way. Every parameter has a default, `None` where
there is no natural one, so a function that cannot work without a value takes it with `required()`.

## Install

Pin a commit of this repository (see [installing](../README.md#installing-a-package)).

```sh
pip install "kds-args @ git+https://github.com/iamkevinstreet/utils@<commit>#subdirectory=args"
```

## Use

```python
from datetime import date, timedelta

from kds.args import required


def response_due(notice_date: date | None = None, days: int = 30) -> date:
    """Returns the day a position statement is due."""
    notice_date = required(notice_date=notice_date)
    return notice_date + timedelta(days=days)
```

`required()` takes exactly one argument, by name, and returns its value. When the value is `None`
it raises `TypeError: missing required argument: 'notice_date'`, the same error Python raises when
a caller leaves out an argument that has no default. Type checkers see the returned value without
`None`, so the rest of the function needs no further checks.

When `None` is a real choice for a parameter (read the settings from config, say), the function
handles it instead of calling `required()`.

## Conventions

- The argument is passed by name, so the error names it without a string that could drift.
- No dependencies, and no logging configuration: `kds.args` is a library.
