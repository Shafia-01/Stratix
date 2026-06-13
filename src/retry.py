import functools
import time
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    retry_if_exception_type
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
    jitter=True
):
    """
    Decorator for retrying API/network calls using tenacity.
    """
    wait_strategy = wait_exponential(multiplier=base_delay, exp_base=backoff_factor)
    if jitter:
        # Add random jitter to exponential backoff
        wait_strategy = wait_strategy + wait_random(0, 1)

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(retry_on),
        before_sleep=log_retry,
        reraise=True
    )

def with_rate_limit_delay(seconds=1.0):
    """
    Decorator that sleeps before and after the wrapped call to avoid rate limits.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            time.sleep(seconds)
            try:
                return func(*args, **kwargs)
            finally:
                time.sleep(seconds)
        return wrapper
    return decorator
