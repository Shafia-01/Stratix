from pytrends.request import TrendReq
import pandas as pd
import time

def get_trend_score(keyword):
    """
    Returns the average Google Trends interest for a keyword (0-100 scaled).
    """
    try:
        pytrends = TrendReq(hl='en-US', tz=330)
        pytrends.build_payload([keyword], timeframe='today 3-m', geo='', gprop='')
        data = pytrends.interest_over_time()
        if data.empty:
            return 0
        avg_interest = data[keyword].mean()
        time.sleep(0.5)
        return round(avg_interest / 100, 3)  # Normalize to 0–1 scale
    except Exception as e:
        print(f"⚠️ Trend error for '{keyword}': {e}")
        return 0
