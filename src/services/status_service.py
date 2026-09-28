import os
import streamlit as st
from google import genai
from src.logger_config import get_logger

logger = get_logger(__name__)

# All models suitable for this project's text-generation tasks.
# Primary workhorse: gemini-3.8-flash (reasoning, agent execution, structured outputs)
# Fast fallback: gemini-3.5-flash-lite (high throughput, auxiliary tasks)
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
]

def check_api_status():
    """Check API keys status."""
    api_status = {
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "SERPAPI_KEY": bool(os.getenv("SERPAPI_KEY")),
    }
    return api_status

def test_api_quick():
    """Quick API availability check — uses non-generative model metadata fetch
    to avoid consuming LLM generation quota on every Streamlit rerun."""
    results = {"gemini": False, "serpapi": False}

    # Test Gemini with a non-generative metadata fetch (no quota consumed)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            # Use models.get() — a metadata-only call, no generation quota consumed.
            # Try models in order until one succeeds (confirms key + model access).
            for model_name in GEMINI_MODELS:
                try:
                    client.models.get(model=model_name)
                    results["gemini"] = True
                    logger.info(f"Gemini API accessible via model metadata: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"Gemini model {model_name} metadata check failed: {e}. Trying next...")
                    continue
        except Exception:
            logger.exception("Gemini availability check failed")

    # Test SerpApi
    serpapi_key = os.getenv("SERPAPI_KEY")
    if serpapi_key:
        try:
            import requests
            url = "https://serpapi.com/search.json"
            params = {"q": "test", "api_key": serpapi_key, "engine": "google", "num": "1"}
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                results["serpapi"] = "search_information" in data or "error" not in data
            else:
                logger.error(f"SerpApi HTTP error: {response.status_code}")
        except requests.exceptions.Timeout as e:
            logger.warning(f"SerpApi test timed out: {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"SerpApi connection failed: {e}")
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
