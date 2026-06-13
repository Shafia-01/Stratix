"""
Retry and rate-limit utilities for Keylytics.

with_retries()
    Tenacity-backed exponential back-off decorator.
    Only retries on explicitly listed exception types — never on bare Exception.
    This prevents masking programming errors (ValueError, AttributeError, etc.)
    under retry loops.

with_rate_limit_delay()
    Simple sleep-before / sleep-after decorator for rate-limited APIs.

    Parameters
    ----------
    pre_delay  : float
        Seconds to sleep BEFORE the call.  Use this when an API requires
        a warm-up gap between consecutive requests (e.g., pytrends).
        Default 0.0 — no pre-delay unless explicitly needed.
    post_delay : float
        Seconds to sleep AFTER the call.  Use this when an API has a
        cool-down window after each response (rare in practice).
        Default 0.0 — no post-delay unless explicitly needed.

    Per-call-site guidance
    ----------------------
    pytrends / trends_client  — use pre_delay=1.0 (Google Trends enforces
        ~1 req/s; a pre-delay avoids 429s on consecutive keyword fetches).
    DataForSEO / seo_api_client — no delay needed; API is stateless and
        credits-based, not rate-limited by time window.
    Gemini / gemini_client — no delay needed; tenacity retry handles 429s.
"""

import functools
import time
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    retry_if_exception_type,
)
from src.exceptions import KeylyticsAPIError
from src.logger_config import get_logger

logger = get_logger(__name__)


def log_retry(retry_state):
    """Callback for tenacity to log each retry attempt."""
    exc = retry_state.outcome.exception()
    exc_message = str(exc) if exc else "Unknown error"
    logger.warning(
        f"Retry attempt {retry_state.attempt_number} failed. Exception: {exc_message}"
    )


def with_retries(
    max_attempts=3,
    base_delay=1.0,
    retry_on=(KeylyticsAPIError, requests.exceptions.RequestException),
    backoff_factor=2.0,
    jitter=True,
):
    """
    Decorator for retrying API/network calls using tenacity.

    Only retries on the exception types listed in retry_on.
    Never retries on bare Exception — programming errors should surface immediately.

    Default retry_on covers:
        - KeylyticsAPIError  : our own upstream-failure sentinel
        - requests.exceptions.RequestException : any requests-level network error
    """
    wait_strategy = wait_exponential(multiplier=base_delay, exp_base=backoff_factor)
    if jitter:
        # Add random jitter to exponential backoff to avoid thundering-herd
        wait_strategy = wait_strategy + wait_random(0, 1)

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(retry_on),
        before_sleep=log_retry,
        reraise=True,
    )


def with_rate_limit_delay(pre_delay: float = 0.0, post_delay: float = 0.0):
    """
    Decorator that sleeps before and/or after the wrapped call.

    Both defaults are 0.0 so existing call-sites that pass a positional
    ``seconds`` argument now need to be explicit.  Call-sites that relied on
    the old single-argument form (with_rate_limit_delay(1.0)) should be
    updated to with_rate_limit_delay(pre_delay=1.0).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if pre_delay > 0:
                time.sleep(pre_delay)
            try:
                return func(*args, **kwargs)
            finally:
                if post_delay > 0:
                    time.sleep(post_delay)
        return wrapper
    return decorator
