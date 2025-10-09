# trends_client.py
import time
import random
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import text
from pytrends.request import TrendReq
from dotenv import load_dotenv
from src.db_client import connect_db  # ✅ reuse your SQLAlchemy connection

load_dotenv()

pytrends = TrendReq(hl='en-US', tz=360)

# ------------------ TREND FETCHER ------------------
def get_trend_score(keyword):
    """
    Fetch Google Trends average score (0–100) for a keyword.
    Includes caching via MySQL and fallback values.
    """
    cached = get_cached_trend(keyword)
    if cached:
        print(f"♻️ Using cached trend data for '{keyword}'")
        return cached

    print(f"📈 Fetching trend data for '{keyword}'...")
    try:
        # Small delay to avoid rate-limit
        time.sleep(random.uniform(1.5, 3.5))

        pytrends.build_payload([keyword], timeframe="today 12-m")
        data = pytrends.interest_over_time()

        if not data.empty:
            score = int(data[keyword].mean())
        else:
            score = random.randint(20, 80)

        save_trend_to_db(keyword, score)
        return score

    except Exception as e:
        print(f"⚠️ Trend error for '{keyword}': {e}")
        # fallback random score
        score = random.randint(20, 80)
        save_trend_to_db(keyword, score)
        return score


# ------------------ TREND CACHE ------------------
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
        print(f"⚠️ Trend cache lookup failed: {e}")
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
        print(f"💾 Trend score cached for '{keyword}' ({score})")
    except Exception as e:
        print(f"⚠️ Trend cache save failed: {e}")
