"""
Tests for src/retry.py.
Verifies with_retries only retries on specified exception types and
that with_rate_limit_delay correctly applies pre/post delays.
"""

import pytest
from unittest.mock import patch
from src.retry import with_retries, with_rate_limit_delay
from src.exceptions import KeylyticsAPIError


# ---------------------------------------------------------------------------
# with_retries
# ---------------------------------------------------------------------------
class TestWithRetries:
    def test_retries_on_keylytics_api_error(self):
        """Should retry on KeylyticsAPIError up to max_attempts, then re-raise."""
        call_count = 0

        @with_retries(max_attempts=3, base_delay=0.0, jitter=False)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise KeylyticsAPIError("upstream failed")

        with pytest.raises(KeylyticsAPIError):
            always_fails()

        assert call_count == 3

    def test_does_not_retry_on_value_error(self):
        """Programming errors like ValueError should NOT be retried."""
        call_count = 0

        @with_retries(max_attempts=3, base_delay=0.0, jitter=False)
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError):
            raises_value_error()

        # Must fail immediately, no retries
        assert call_count == 1

    def test_does_not_retry_on_type_error(self):
        """TypeErrors should NOT be retried — they indicate programming bugs."""
        call_count = 0

        @with_retries(max_attempts=3, base_delay=0.0, jitter=False)
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            raises_type_error()

        assert call_count == 1

    def test_succeeds_on_retry(self):
        """Should return successfully when a later attempt succeeds."""
        attempt = 0

        @with_retries(max_attempts=3, base_delay=0.0, jitter=False)
        def fails_twice_then_succeeds():
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise KeylyticsAPIError("not ready yet")
            return "success"

        result = fails_twice_then_succeeds()
        assert result == "success"
        assert attempt == 3

    def test_returns_value_on_first_success(self):
        @with_retries(max_attempts=3, base_delay=0.0, jitter=False)
        def always_works():
            return 42

        assert always_works() == 42


# ---------------------------------------------------------------------------
# with_rate_limit_delay
# ---------------------------------------------------------------------------
class TestWithRateLimitDelay:
    def test_pre_delay_applied(self):
        """pre_delay should sleep BEFORE calling the function."""
        sleep_calls = []

        @with_rate_limit_delay(pre_delay=0.1)
        def my_func():
            return "done"

        with patch("src.retry.time.sleep", side_effect=lambda s: sleep_calls.append(("pre", s))):
            result = my_func()

        assert result == "done"
        assert sleep_calls == [("pre", 0.1)]

    def test_post_delay_applied(self):
        """post_delay should sleep AFTER calling the function."""
        sleep_calls = []

        @with_rate_limit_delay(post_delay=0.2)
        def my_func():
            return "ok"

        with patch("src.retry.time.sleep", side_effect=lambda s: sleep_calls.append(("post", s))):
            result = my_func()

        assert result == "ok"
        assert sleep_calls == [("post", 0.2)]

    def test_no_delay_by_default(self):
        """With default values (0.0, 0.0), sleep should never be called."""
        @with_rate_limit_delay()
        def my_func():
            return "fast"

        with patch("src.retry.time.sleep") as mock_sleep:
            result = my_func()

        assert result == "fast"
        mock_sleep.assert_not_called()

    def test_both_delays_applied_in_order(self):
        """Both pre and post delays should fire in the correct order."""
        order = []

        @with_rate_limit_delay(pre_delay=0.05, post_delay=0.1)
        def my_func():
            order.append("call")
            return "result"

        with patch("src.retry.time.sleep", side_effect=lambda s: order.append(f"sleep({s})")):
            result = my_func()

        assert result == "result"
        assert order == ["sleep(0.05)", "call", "sleep(0.1)"]
