# db_client.py
import pandas as pd
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ----------------- LOAD ENVIRONMENT VARIABLES -----------------
load_dotenv()

# Default database configuration (fallback values)
DEFAULT_DB_CONFIG = {
    'MYSQL_HOST': '127.0.0.1',
    'MYSQL_USER': 'root', 
    'MYSQL_PASSWORD': '',
    'MYSQL_DATABASE': 'gemkey_ai',
    'MYSQL_PORT': '3306'
}

def get_db_config():
    """Get database configuration with fallbacks."""
    config = {}
    for key, default in DEFAULT_DB_CONFIG.items():
        value = os.getenv(key, default)
        if not value and key != 'MYSQL_PASSWORD':  # Allow empty password
            print(f"Warning: {key} not set, using default: {default}")
        config[key] = value
    return config

print("MYSQL_HOST from env:", os.getenv("MYSQL_HOST", "127.0.0.1 (default)"))

# ----------------- CONNECT TO MYSQL (SQLAlchemy) -----------------
def connect_db():
    """Create and return a SQLAlchemy engine."""
    import urllib.parse
    
    config = get_db_config()
    
    # Validate host format
    host = config['MYSQL_HOST']
    if not host or len(host.split('.')) != 4:
        print(f"Invalid MySQL host '{host}', using localhost")
        host = '127.0.0.1'
    
    # URL encode the password to handle special characters like @
    encoded_password = urllib.parse.quote_plus(config['MYSQL_PASSWORD'])
    
    db_url = (
        f"mysql+mysqlconnector://{config['MYSQL_USER']}:{encoded_password}"
        f"@{host}:{config['MYSQL_PORT']}/{config['MYSQL_DATABASE']}"
    )
    print(f"Connecting to MySQL: {config['MYSQL_USER']}@{host}:{config['MYSQL_PORT']}/{config['MYSQL_DATABASE']}")
    
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database connection successful")
        return engine
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Please check your MySQL server is running and credentials are correct")
        print("You can create a .env file with your database settings:")
        print("   MYSQL_HOST=127.0.0.1")
        print("   MYSQL_USER=root")
        print("   MYSQL_PASSWORD=your_password")
        print("   MYSQL_DATABASE=gemkey_ai")
        raise e
# ----------------- SAVE FULL KEYWORD RESULTS -----------------
def save_to_db(data):
    """Save keyword data with all computed fields."""
    try:
        engine = connect_db()
        df = pd.DataFrame(data)
        
        # Convert competitors list to JSON string for MySQL storage
        if 'competitors' in df.columns:
            import json
            df['competitors'] = df['competitors'].apply(lambda x: json.dumps(x) if isinstance(x, list) else json.dumps([]))
        
        df.to_sql("keywords", con=engine, if_exists="append", index=False)
        print(f"[OK] {len(df)} keywords saved successfully!")
    except Exception as e:
        print("[WARNING] Database Save Error:", e)
        print("[INFO] Data will be saved to cache files instead")
        # Fallback: save to CSV cache
        try:
            cache_file = f"cache/keywords_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df = pd.DataFrame(data)
            df.to_csv(cache_file, index=False)
            print(f"[OK] Saved to cache file: {cache_file}")
        except Exception as cache_e:
            print(f"[ERROR] Cache save also failed: {cache_e}")

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
        print("📂 Trying to load from cache files instead...")
        # Fallback: load from cache files
        try:
            import glob
            cache_files = glob.glob("cache/*.csv")
            if cache_files:
                latest_file = max(cache_files, key=os.path.getctime)
                df = pd.read_csv(latest_file)
                return df.tail(limit)
            return pd.DataFrame()
        except Exception as cache_e:
            print(f"⚠️ Cache load also failed: {cache_e}")
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
        # Database unavailable, continue without cache
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
        # Database unavailable, continue without caching
        print("ℹ️ Continuing without intent caching")
