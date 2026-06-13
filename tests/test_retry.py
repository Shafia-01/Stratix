import pytest
from src.retry import with_retries, with_rate_limit_delay
from src.exceptions import KeylyticsAPIError

def test_with_retries_success():
    call_count = 0
    
    @with_retries(max_attempts=3, base_delay=0.01, jitter=False)
    def dummy_func():
        nonlocal call_count
        call_count += 1
        return "success"
        
    res = dummy_func()
    assert res == "success"
    assert call_count == 1

def test_with_retries_fail_and_propagate():
    call_count = 0
    
    @with_retries(max_attempts=3, base_delay=0.01, jitter=False)
    def dummy_func():
        nonlocal call_count
        call_count += 1
        raise KeylyticsAPIError("API Error")
        
    with pytest.raises(KeylyticsAPIError):
        dummy_func()
        
    assert call_count == 3
