# db_client.py
import pandas as pd
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ----------------- LOAD ENVIRONMENT VARIABLES -----------------
load_dotenv()

# ----------------- CONNECT TO MYSQL (SQLAlchemy) -----------------
def connect_db():
    """Create and return a SQLAlchemy engine."""
    db_url = (
        f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
        f"@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}"
    )
    return create_engine(db_url, pool_pre_ping=True)

# ----------------- SAVE FULL KEYWORD RESULTS -----------------
def save_to_db(data):
    """Save keyword data with all computed fields."""
    engine = connect_db()
    try:
        df = pd.DataFrame(data)
        df.to_sql("keywords", con=engine, if_exists="append", index=False)
        print(f"✅ {len(df)} keywords saved successfully!")
    except Exception as e:
        print("⚠️ Database Save Error:", e)

# ----------------- FETCH PAST RESULTS -----------------
def fetch_past_results(limit=50):
    """Fetch recent keyword entries."""
    try:
        engine = connect_db()
        query = text("""
            SELECT seed, keyword, volume, competition, cpc, score, difficulty
            FROM keywords
            ORDER BY id DESC
            LIMIT :limit;
        """)
        df = pd.read_sql(query, engine, params={"limit": limit})
        return df
    except Exception as e:
        print(f"DB Fetch Error: {e}")
        return pd.DataFrame()

# ----------------- INTENT CACHE HELPERS -----------------
def get_cached_intent(keyword):
    """
    Fetch cached intent for a given keyword from 'intent_cache' table if available.
    """
    try:
        engine = connect_db()
        query = text("SELECT intent FROM intent_cache WHERE keyword = :kw LIMIT 1;")
        result = pd.read_sql(query, engine, params={"kw": keyword})
        if not result.empty:
            intent = result.iloc[0]["intent"]
            print(f"♻️ Cached intent found for '{keyword}': {intent}")
            return intent
        return None
    except Exception as e:
        print(f"⚠️ Intent cache lookup error for '{keyword}': {e}")
        return None

def save_intent_to_db(keyword, intent):
    """
    Save new intent into 'intent_cache' table.
    """
    try:
        engine = connect_db()
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO intent_cache (keyword, intent)
                    VALUES (:kw, :intent)
                    ON DUPLICATE KEY UPDATE intent = VALUES(intent);
                """),
                {"kw": keyword, "intent": intent}
            )
        print(f"💾 Cached intent saved for '{keyword}': {intent}")
    except Exception as e:
        print(f"⚠️ Error saving intent to DB for '{keyword}': {e}")
