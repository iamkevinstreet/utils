import os

import pytest

# Tests never touch a real provider or a real log directory.
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("LLM_MODEL", "fake-model")
os.environ.setdefault("LLM_JUDGE_MODEL", "fake-model")


@pytest.fixture(autouse=True)
def _log_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    from kds import settings as config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()
