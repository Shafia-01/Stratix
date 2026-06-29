class StratixError(Exception):
    """Base exception class for all Stratix errors."""
    pass


class StratixAPIError(StratixError):
    """Exception raised for errors in external API calls (e.g. SerpApi, DataForSEO, Gemini, Pytrends)."""
    pass


class StratixDataError(StratixError):
    """Exception raised for data processing, validation, or consistency errors."""
    pass


# Backward compatibility aliases
KeylyticsError = StratixError
KeylyticsAPIError = StratixAPIError
KeylyticsDataError = StratixDataError
StratixAIError = StratixError
StratixAIAPIError = StratixAPIError
StratixAIDataError = StratixDataError
