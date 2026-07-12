import os
import streamlit as st
from google import genai
from src.logger_config import get_logger

logger = get_logger(__name__)

# All models suitable for this project's text-generation tasks.
# NOT included: TTS, image-gen, video-gen, audio, live-API, embeddings,
#               robotics, Antigravity/Deep Research agent models.
GEMINI_MODELS = [
    # ── Gemini Flash (primary workhorses – low latency, strong reasoning) ──
    "gemini-2.5-flash",       # Gemini 2.5 Flash       | text-out
    "gemini-3.5-flash",       # Gemini 3.5 Flash       | text-out
    "gemini-3.1-flash-lite",  # Gemini 3.1 Flash Lite  | text-out
    "gemini-3-flash-preview", # Gemini 3 Flash         | text-out
    "gemini-2.5-flash-lite",  # Gemini 2.5 Flash Lite  | text-out
    # ── Gemini Pro (highest quality – slower, use when Flash fails) ──
    "gemini-2.5-pro",         # Gemini 2.5 Pro         | text-out
    "gemini-3.1-pro",         # Gemini 3.1 Pro         | text-out
    # ── Gemini 2.x (older generation – stable last-resort) ──
    "gemini-2.0-flash",       # Gemini 2 Flash         | text-out
    "gemini-2.0-flash-lite",  # Gemini 2 Flash Lite    | text-out
    # ── Gemma 4 (text-only – no tool/function calling) ──
    "gemma-4-31b-it",         # Gemma 4 31B            | other
    "gemma-4-26b-it",         # Gemma 4 26B            | other
]

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
                        logger.info(f"Gemini model {model_name} succeeded.")
                        break
                except Exception as e:
                    logger.warning(f"Gemini model {model_name} failed: {e}. Trying next fallback...")
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
