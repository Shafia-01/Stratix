import os
from src.security_utils import redact_api_keys

def test_redact_api_keys(monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "secret_serp_key_123")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "supersecretpwd")
    
    # Text containing secrets
    log_msg = "Error contacting API: key = secret_serp_key_123, user = some_user, pass = supersecretpwd"
    redacted = redact_api_keys(log_msg)
    
    assert "secret_serp_key_123" not in redacted
    assert "supersecretpwd" not in redacted
    assert redacted == "Error contacting API: key = ***REDACTED***, user = some_user, pass = ***REDACTED***"

def test_redact_api_keys_none_or_empty(monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    assert redact_api_keys("No secrets here") == "No secrets here"
