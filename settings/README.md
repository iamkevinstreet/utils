# kds.settings

Typed settings for every prototype, read from the environment or a `.env` file. Secrets are `SecretStr`, so they never appear in logs or error messages by accident.

## Install

```toml
# in a project's pyproject.toml
dependencies = ["kds-settings @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=settings"]
```

```sh
# or directly
pip install "kds-settings @ git+https://github.com/iamkevinstreet/utils.git@main#subdirectory=settings"
```

## Use

```python
from kds.settings import get_settings

s = get_settings()
s.llm_provider  # "anthropic" | "openai" | "azure" | "fake"
s.llm_model
s.eval_budget_usd  # the evaluation runner stops at this spend
s.entra_configured  # True when the three ENTRA_* values are set
```

## Develop

```sh
# from the repository root
pytest settings/tests
```

Apache License 2.0. See the repository `LICENSE` and `NOTICE`.
