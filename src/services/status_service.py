import os
import streamlit as st
from google import genai
from src.logger_config import get_logger

logger = get_logger(__name__)

GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

def check_api_status():
    """Check API keys status."""
    api_status = {
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "SERPAPI_KEY": bool(os.getenv("SERPAPI_KEY")),
    }
    return api_status

def test_api_quick():
    """Quick API test to show current status."""
    results = {"gemini": False, "serpapi": False}

    # Test Gemini with multiple models
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            for model_name in GEMINI_MODELS:
                try:
                    result = client.models.generate_content(
                        model=model_name,
                        contents="Hello"
                    )
                    if result.text:
                        results["gemini"] = True
                        break
                except Exception as e:
                    logger.warning(f"Gemini model {model_name} failed: {e}")
                    continue
        except Exception:
            logger.exception("Gemini test failed")

    # Test SerpApi
    serpapi_key = os.getenv("SERPAPI_KEY")
    if serpapi_key:
        try:
            import requests
            url = "https://serpapi.com/search.json"
            params = {"q": "test", "api_key": serpapi_key, "engine": "google", "num": "1"}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results["serpapi"] = "search_information" in data or "error" not in data
            else:
                logger.error(f"SerpApi HTTP error: {response.status_code}")
        except Exception:
            logger.exception("SerpApi test failed")

    return results

@st.cache_data(ttl=300)
def cached_check_api_status():
    """Cached version of API status check."""
    return check_api_status()

@st.cache_data(ttl=300)
def get_system_status():
    """Get cached system status to avoid repeated calls."""
    api_status = cached_check_api_status()
    api_test = test_api_quick()
    return api_status, api_test
