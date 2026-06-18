class StratixAIError(Exception):
    """Base exception class for all Stratix AI errors."""
    pass


class StratixAIAPIError(StratixAIError):
    """Exception raised for errors in external API calls (e.g. SerpApi, DataForSEO, Gemini, Pytrends)."""
    pass


class StratixAIDataError(StratixAIError):
    """Exception raised for data processing, validation, or consistency errors."""
    pass


# Backward compatibility aliases
KeylyticsError = StratixAIError
KeylyticsAPIError = StratixAIAPIError
KeylyticsDataError = StratixAIDataError
