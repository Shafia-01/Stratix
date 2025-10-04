import os, requests
from dotenv import load_dotenv

load_dotenv()

def get_metrics(keyword):
    url = "https://serpapi.com/search.json"
    params = {"q": keyword, "api_key": os.getenv("SERPAPI_KEY"), "engine": "google"}
    res = requests.get(url, params=params).json()

    # Placeholder metrics (since free tier has limits)
    return {
        "volume": res.get("search_information", {}).get("total_results", 1000),
        "competition": 0.3,
        "cpc": 0.5
    }
