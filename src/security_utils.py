import os

def redact_api_keys(text: str) -> str:
    """
    Scans the input text and redacts any sensitive credentials that are
    defined in environment variables.
    Replaces credentials with ***REDACTED***.
    """
    if not isinstance(text, str):
        return text

    sensitive_env_vars = [
        "SERPAPI_KEY",
        "DATAFORSEO_USERNAME",
        "DATAFORSEO_PASSWORD",
        "GEMINI_API_KEY"
    ]

    redacted_text = text
    for var_name in sensitive_env_vars:
        val = os.getenv(var_name)
        if val and len(val.strip()) > 3:
            redacted_text = redacted_text.replace(val, "***REDACTED***")

    return redacted_text
