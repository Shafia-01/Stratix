import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def get_competitor_data(keyword, num_results=5):
    """
    Fetch top-ranking competitors for a given keyword using SerpApi.
    Returns a list of dicts with domain, title, snippet, and position.
    """
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "q": keyword,
            "api_key": SERPAPI_KEY,
            "engine": "google",
            "num": num_results,
        }
        res = requests.get(url, params=params, timeout=15).json()
        organic_results = res.get("organic_results", [])
        competitors = []
        for i, result in enumerate(organic_results[:num_results], start=1):
            competitors.append({
                "rank": i,
                "title": result.get("title"),
                "link": result.get("link"),
                "domain": extract_domain(result.get("link")),
                "snippet": result.get("snippet", "No description available.")
            })
        time.sleep(1)
        return competitors
    except Exception as e:
        print(f"⚠️ Competitor fetch error for '{keyword}': {e}")
        return []

def extract_domain(url):
    """Simple domain parser from URL."""
    try:
        if not url:
            return ""
        domain = url.split("/")[2]
        return domain.replace("www.", "")
    except Exception:
        return ""
