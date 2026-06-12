import pytest
from src.exceptions import KeylyticsError, KeylyticsAPIError, KeylyticsDataError

def test_exceptions_inheritance():
    with pytest.raises(KeylyticsError):
        raise KeylyticsAPIError("API error occurred")

    with pytest.raises(KeylyticsError):
        raise KeylyticsDataError("Data error occurred")
