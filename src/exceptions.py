class KeylyticsError(Exception):
    """Base exception class for all Keylytics errors."""
    pass


class KeylyticsAPIError(KeylyticsError):
    """Exception raised for errors in external API calls (e.g. SerpApi, DataForSEO, Gemini, Pytrends)."""
    pass


class KeylyticsDataError(KeylyticsError):
    """Exception raised for data processing, validation, or consistency errors."""
    pass
