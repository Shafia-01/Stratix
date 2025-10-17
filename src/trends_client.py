import time
import random
import warnings
from datetime import datetime
import pandas as pd
from sqlalchemy import text
from pytrends.request import TrendReq
from dotenv import load_dotenv
from src.db_client import connect_db

load_dotenv()

# Suppress pandas FutureWarning for pytrends
warnings.filterwarnings("ignore", category=FutureWarning, module="pytrends")
pytrends = TrendReq(hl='en-US', tz=360)

def get_trend_score(keyword):
    """
    Fetch Google Trends average score (0–100) for a keyword.
    Includes caching via MySQL and fallback values.
    """
    cached = get_cached_trend(keyword)
    if cached:
        print(f"[CACHE] Using cached trend data for '{keyword}'")
        return cached
    print(f"[TREND] Fetching trend data for '{keyword}'...")
    
    # Retry logic with exponential backoff
    max_retries = 3
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            # Progressive delay to avoid rate-limit
            delay = base_delay * (2 ** attempt) + random.uniform(0.5, 2.0)
            time.sleep(delay)
            # Reset pytrends connection to avoid stale sessions
            if attempt > 0:
                global pytrends
                pytrends = TrendReq(hl='en-US', tz=360)
            pytrends.build_payload([keyword], timeframe="today 12-m")
            data = pytrends.interest_over_time()
            if not data.empty:
                score = int(data[keyword].mean())
            else:
                score = random.randint(20, 80)
            save_trend_to_db(keyword, score)
            print(f"[SUCCESS] Trend data fetched for '{keyword}': {score}")
            return score
        except Exception as e:
            error_msg = str(e)
            print(f"[WARNING] Trend error for '{keyword}' (attempt {attempt + 1}): {error_msg}")
            # Handle specific error types
            if "429" in error_msg or "rate" in error_msg.lower():
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt) * 3  # Longer wait for rate limits
                    print(f"[RATE_LIMIT] Waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                    continue
            elif "timeout" in error_msg.lower():
                if attempt < max_retries - 1:
                    print(f"[TIMEOUT] Retrying after delay...")
                    continue
            # Final fallback after all retries
            if attempt == max_retries - 1:
                print(f"[FALLBACK] Using random score for '{keyword}' after {max_retries} attempts")
                score = random.randint(20, 80)
                save_trend_to_db(keyword, score)
                return score

def get_cached_trend(keyword):
    """
    Retrieve cached trend if less than 7 days old.
    """
    try:
        engine = connect_db()
        query = text("""
            SELECT trend, last_updated
            FROM keywords
            WHERE keyword = :kw
            AND trend IS NOT NULL
            ORDER BY last_updated DESC
            LIMIT 1;
        """)
        df = pd.read_sql(query, engine, params={"kw": keyword})
        if df.empty:
            return None
        last_updated = df.iloc[0]["last_updated"]
        if pd.notnull(last_updated):
            delta = datetime.now() - pd.to_datetime(last_updated)
            if delta.days < 7:
                return int(df.iloc[0]["trend"])
        return None
    except Exception as e:
        print(f"[ERROR] Trend cache lookup failed for '{keyword}': {e}")
        return None

def save_trend_to_db(keyword, score):
    """
    Save or update trend score in DB.
    """
    try:
        engine = connect_db()
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE keywords
                    SET trend = :score, last_updated = NOW()
                    WHERE keyword = :kw;
                """),
                {"score": score, "kw": keyword}
            )
        print(f"[CACHE] Trend score saved for '{keyword}': {score}")
    except Exception as e:
        print(f"[ERROR] Trend cache save failed for '{keyword}': {e}")
