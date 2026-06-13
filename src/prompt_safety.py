"""
Prompt safety and input validation utilities to prevent prompt injection and handle untrusted input.
"""

import re
from typing import Any

# Common role markers or override instruction phrases to neutralize
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:all\s+)?previous\s+instructions",
    r"(?i)ignore\s+(?:all\s+)?instructions\s+above",
    r"(?i)ignore\s+(?:all\s+)?rules",
    r"(?i)system\s*:",
    r"(?i)user\s*:",
    r"(?i)assistant\s*:",
    r"(?i)role\s*:\s*system",
    r"(?i)role\s*:\s*assistant",
    r"(?i)role\s*:\s*user",
    r"(?i)you\s+are\s+now\s+a",
    r"(?i)instead\s+of\s+what\s+you\s+were\s+doing",
]

def sanitize_untrusted_text(text: str) -> str:
    """
    Sanitize text destined for an LLM prompt by removing/neutralizing
    suspected prompt injection sequences and excessive control characters.
    """
    if not isinstance(text, str):
        return ""

    # Replace newlines/tabs with standard spaces or clean them up, but keep basic structure
    # Let's replace carriage returns and limit consecutive newlines to maximum 2
    sanitized = text.replace("\r", "")
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)

    # Neutralize injection patterns by prepending a warning or sanitizing them out
    for pattern in INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "[REMOVED_INSTRUCTION_OVERRIDE]", sanitized)

    return sanitized.strip()

def cap_text_length(text: str, limit: int) -> str:
    """Capping function for text destined for a prompt."""
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit]

def build_safe_prompt(template: str, **untrusted_fields: Any) -> str:
    """
    Safely builds a prompt by sanitizing untrusted inputs, wrapping them in fenced blocks,
    and interpolating them into the template.
    """
    sanitized_fields = {}
    for key, value in untrusted_fields.items():
        if isinstance(value, str):
            # Apply safety steps: sanitize first, then wrap in delimiters
            clean_val = sanitize_untrusted_text(value)
            sanitized_fields[key] = f"\n[START UNTRUSTED DATA]\n{clean_val}\n[END UNTRUSTED DATA]\n"
        else:
            sanitized_fields[key] = value

    return template.format(**sanitized_fields)
