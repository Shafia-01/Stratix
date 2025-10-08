import time
import random
from datetime import datetime, timedelta
import mysql.connector
from pytrends.request import TrendReq
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize PyTrends once
pytrends = TrendReq(hl='en-US', tz=360)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

# ---------- Main Function ----------

def get_trend_score(keyword):
    """
    Fetches Google Trends interest score (0–100) for a keyword.
    Includes delay and caching in MySQL.
    """
    cached = get_cached_trend(keyword)
    if cached:
        print(f"♻️ Using cached trend data for '{keyword}'")
        return cached

    print(f"📈 Fetching trend data for '{keyword}'...")
    try:
        # Random delay to avoid rate limiting
        delay = random.uniform(5, 10)
        print(f"🕒 Sleeping for {delay:.1f}s to avoid 429...")
        time.sleep(delay)

        pytrends.build_payload([keyword], timeframe='today 12-m')
        data = pytrends.interest_over_time()

        if not data.empty:
            score = int(data[keyword].mean())  # average interest
        else:
            score = random.randint(20, 80)  # fallback

        save_trend_to_db(keyword, score)
        return score

    except Exception as e:
        print(f"⚠️ Trend error for '{keyword}':", e)
        return random.randint(20, 80)  # fallback score


# ---------- Cache Utils ----------

def get_cached_trend(keyword):
    """
    Retrieve cached trend score if less than 7 days old.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT trend_score, last_updated
            FROM keywords
            WHERE keyword = %s AND trend_score IS NOT NULL
            LIMIT 1;
        """, (keyword,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        updated_time = row.get("last_updated")
        if updated_time and (datetime.now() - updated_time) < timedelta(days=7):
            return row["trend_score"]
        return None
    except Exception as e:
        print("⚠️ Trend cache check failed:", e)
        return None


def save_trend_to_db(keyword, score):
    """
    Save trend score to MySQL.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
        UPDATE keywords
        SET trend_score = %s, last_updated = NOW()
        WHERE keyword = %s;
        """
        cursor.execute(query, (score, keyword))
        conn.commit()
        conn.close()
        print(f"💾 Trend score cached for '{keyword}' ({score})")
    except Exception as e:
        print("⚠️ Trend cache save failed:", e)
