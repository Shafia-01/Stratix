import os
import requests
import time
from dotenv import load_dotenv
from src.logger_config import get_logger

logger = get_logger(__name__)

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

from src.retry import with_retries, with_rate_limit_delay

@with_retries()
# SerpAPI rate limit: ~1 req/s per API key; pre_delay avoids 429s on rapid competitor lookups.
@with_rate_limit_delay(pre_delay=1.0)
def get_competitor_data(keyword, num_results=5):
    """
    Fetch top-ranking competitors for a given keyword using SerpApi.
    Returns a list of dicts with domain, title, snippet, and position.
    """
    url = "https://serpapi.com/search.json"
    params = {
        "q": keyword,
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "num": num_results,
    }
    res = requests.get(url, params=params, timeout=15)
    res.raise_for_status()
    res_json = res.json()
    organic_results = res_json.get("organic_results", [])
    competitors = []
    for i, result in enumerate(organic_results[:num_results], start=1):
        competitors.append({
            "rank": i,
            "title": result.get("title"),
            "link": result.get("link"),
            "domain": extract_domain(result.get("link")),
            "snippet": result.get("snippet", "No description available.")
        })
    return competitors

def extract_domain(url):
    """Simple domain parser from URL."""
    try:
        if not url:
            return ""
        domain = url.split("/")[2]
        return domain.replace("www.", "")
    except Exception as e:
        logger.debug(f"Failed to parse domain from URL '{url}'", exc_info=True)
        return ""
