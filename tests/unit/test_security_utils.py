import pytest
from src.security_utils import redact_api_keys

@pytest.mark.unit
def test_redact_api_keys_happy_path(monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "secret_serp_key_123")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "supersecretpwd")
    
    # Text containing secrets
    log_msg = "Error contacting API: key = secret_serp_key_123, user = some_user, pass = supersecretpwd"
    redacted = redact_api_keys(log_msg)
    
    assert "secret_serp_key_123" not in redacted
    assert "supersecretpwd" not in redacted
    assert redacted == "Error contacting API: key = ***REDACTED***, user = some_user, pass = ***REDACTED***"


@pytest.mark.unit
def test_redact_api_keys_unset_env(monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    monkeypatch.delenv("DATAFORSEO_PASSWORD", raising=False)
    
    msg = "No secrets here and keys are unset"
    assert redact_api_keys(msg) == msg


@pytest.mark.unit
def test_redact_api_keys_non_string():
    # Verify no-op on non-string inputs
    assert redact_api_keys(None) is None
    assert redact_api_keys(12345) == 12345
    assert redact_api_keys({"key": "val"}) == {"key": "val"}
