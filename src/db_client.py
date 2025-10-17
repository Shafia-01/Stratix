import pandas as pd
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

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
        if not value and key != 'MYSQL_PASSWORD': 
            print(f"Warning: {key} not set, using default: {default}")
        config[key] = value
    return config

print("MYSQL_HOST from env:", os.getenv("MYSQL_HOST", "127.0.0.1 (default)"))

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

def save_to_db(data):
    """Save keyword data with all computed fields."""
    try:
        engine = connect_db()
        df = pd.DataFrame(data)
        
        # Debug: Print sample data being saved
        if not df.empty:
            print(f"[DEBUG] Sample data being saved:")
            sample_row = df.iloc[0]
            print(f"  Seed: {sample_row.get('seed', 'MISSING')}")
            print(f"  Keyword: {sample_row.get('keyword', 'MISSING')}")
            print(f"  Score: {sample_row.get('score', 'MISSING')}")
            print(f"  Difficulty: {sample_row.get('difficulty', 'MISSING')}")
        
        # Convert competitors list to JSON string for MySQL storage
        if 'competitors' in df.columns:
            import json
            df['competitors'] = df['competitors'].apply(lambda x: json.dumps(x) if isinstance(x, list) else json.dumps([]))
        
        # Use INSERT ... ON DUPLICATE KEY UPDATE to handle existing keywords
        with engine.begin() as conn:
            for _, row in df.iterrows():
                # Ensure all required fields have proper values
                seed_value = row.get("seed") or "Unknown"
                keyword_value = row.get("keyword") or ""
                volume_value = float(row.get("volume") or 0)
                competition_value = float(row.get("competition") or 0.0)
                cpc_value = float(row.get("cpc") or 0.0)
                trend_value = row.get("trend") if pd.notnull(row.get("trend")) else 0
                score_value = float(row.get("score") or 0.0)
                difficulty_value = row.get("difficulty") or "Unknown"
                intent_value = row.get("intent") or "informational"
                competitors_value = row.get("competitors") or "[]"
                
                conn.execute(
                    text("""
                        INSERT INTO keywords (seed, keyword, volume, competition, cpc, trend, score, difficulty, intent, competitors)
                        VALUES (:seed, :keyword, :volume, :competition, :cpc, :trend, :score, :difficulty, :intent, :competitors)
                        ON DUPLICATE KEY UPDATE
                            seed = VALUES(seed),
                            volume = VALUES(volume),
                            competition = VALUES(competition),
                            cpc = VALUES(cpc),
                            trend = VALUES(trend),
                            score = VALUES(score),
                            difficulty = VALUES(difficulty),
                            intent = VALUES(intent),
                            competitors = VALUES(competitors),
                            last_updated = NOW();
                    """),
                    {
                        "seed": seed_value,
                        "keyword": keyword_value,
                        "volume": volume_value,
                        "competition": competition_value,
                        "cpc": cpc_value,
                        "trend": trend_value,
                        "score": score_value,
                        "difficulty": difficulty_value,
                        "intent": intent_value,
                        "competitors": competitors_value
                    }
                )
        
        print(f"[OK] {len(df)} keywords saved/updated successfully!")
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

def fetch_past_results(limit=50):
    """Fetch recent keyword entries."""
    try:
        engine = connect_db()
        query = text("""
            SELECT 
                COALESCE(seed, 'Unknown') as seed,
                keyword, 
                COALESCE(volume, 0) as volume, 
                COALESCE(competition, 0.0) as competition, 
                COALESCE(cpc, 0.0) as cpc, 
                COALESCE(score, 0.0) as score, 
                COALESCE(difficulty, 'Unknown') as difficulty
            FROM keywords
            WHERE keyword IS NOT NULL
            ORDER BY id DESC
            LIMIT :limit;
        """)
        df = pd.read_sql(query, engine, params={"limit": limit})
        
        # Debug: Print sample data being retrieved
        if not df.empty:
            print(f"[DEBUG] Sample data retrieved from database:")
            sample_row = df.iloc[0]
            print(f"  Seed: {sample_row.get('seed', 'MISSING')}")
            print(f"  Keyword: {sample_row.get('keyword', 'MISSING')}")
            print(f"  Score: {sample_row.get('score', 'MISSING')}")
            print(f"  Difficulty: {sample_row.get('difficulty', 'MISSING')}")
        
        # Ensure all required columns exist with proper defaults
        required_columns = ['seed', 'keyword', 'volume', 'competition', 'cpc', 'score', 'difficulty']
        for col in required_columns:
            if col not in df.columns:
                if col in ['volume', 'competition', 'cpc', 'score']:
                    df[col] = 0.0
                else:
                    df[col] = 'Unknown'
        
        # Fill any remaining NaN values
        df = df.fillna({
            'seed': 'Unknown',
            'keyword': 'Unknown',
            'volume': 0,
            'competition': 0.0,
            'cpc': 0.0,
            'score': 0.0,
            'difficulty': 'Unknown'
        })
        
        print(f"[DB] Fetched {len(df)} records from database")
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
                
                # Ensure required columns exist in cache data
                required_columns = ['seed', 'keyword', 'volume', 'competition', 'cpc', 'score', 'difficulty']
                for col in required_columns:
                    if col not in df.columns:
                        if col in ['volume', 'competition', 'cpc', 'score']:
                            df[col] = 0.0
                        else:
                            df[col] = 'Unknown'
                
                df = df.fillna({
                    'seed': 'Unknown',
                    'keyword': 'Unknown', 
                    'volume': 0,
                    'competition': 0.0,
                    'cpc': 0.0,
                    'score': 0.0,
                    'difficulty': 'Unknown'
                })
                
                print(f"[CACHE] Loaded {len(df)} records from cache file: {latest_file}")
                return df.tail(limit)
            return pd.DataFrame()
        except Exception as cache_e:
            print(f"⚠️ Cache load also failed: {cache_e}")
            return pd.DataFrame()

def verify_database_schema():
    """Verify that the keywords table has all required columns."""
    try:
        engine = connect_db()
        with engine.connect() as conn:
            # Check if table exists and get column info
            result = conn.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'keywords' AND TABLE_SCHEMA = DATABASE()
                ORDER BY ORDINAL_POSITION;
            """))
            
            columns = result.fetchall()
            if not columns:
                print("[ERROR] Keywords table does not exist!")
                return False
            
            required_columns = ['seed', 'keyword', 'volume', 'competition', 'cpc', 'score', 'difficulty', 'intent', 'trend', 'competitors']
            existing_columns = [col[0] for col in columns]
            
            print(f"[SCHEMA] Keywords table has {len(existing_columns)} columns: {existing_columns}")
            
            missing_columns = [col for col in required_columns if col not in existing_columns]
            if missing_columns:
                print(f"[WARNING] Missing required columns: {missing_columns}")
                return False
            
            print("[SCHEMA] All required columns are present!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Schema verification failed: {e}")
        return False

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
