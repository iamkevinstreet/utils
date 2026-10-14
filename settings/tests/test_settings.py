from kds.settings import Settings


def test_defaults_are_safe(monkeypatch):
    for k in ("LLM_PROVIDER", "LLM_MODEL", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    s = Settings(_env_file=None)
    assert s.llm_provider == "fake"
    assert s.log_redact is True
    assert s.eval_budget_usd > 0
    assert s.entra_configured is False


def test_secret_values_do_not_leak_in_repr(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-real-key")
    s = Settings(_env_file=None)
    assert "sk-test" not in repr(s)
    assert s.anthropic_api_key.get_secret_value() == "sk-test-not-a-real-key"
