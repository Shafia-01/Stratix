import pandas as pd
import os
import json
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session
from src.models import Base, Keyword, IntentCache
from src.logger_config import get_logger

logger = get_logger(__name__)

DB_PATH = os.getenv("STRATIX_DB_PATH") or os.getenv("KEYLYTICS_DB_PATH", "keylytics.db")

_engine = None


from src.db_utils import apply_sqlite_pragmas

def _configure_sqlite_pragmas(dbapi_connection, connection_record):
    """
    Configure SQLite PRAGMAs required for concurrent agent tool calls.
    """
    apply_sqlite_pragmas(dbapi_connection)



def connect_db():
    """Create and return a SQLite SQLAlchemy engine and verify tables exist."""
    global _engine
    if _engine is None:
        logger.info(f"Connecting to SQLite database: {os.path.basename(DB_PATH)}")
        _engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
        # Register the PRAGMA listener BEFORE creating tables so every
        # connection (including the schema-creation one) uses WAL mode.
        event.listen(_engine, "connect", _configure_sqlite_pragmas)
        Base.metadata.create_all(_engine)
    return _engine


def save_to_db(data):
    """Save keyword data with all computed fields using SQLAlchemy ORM."""
    try:
        engine = connect_db()
        from pydantic import BaseModel
        processed_data = []
        for item in data:
            if isinstance(item, BaseModel):
                processed_data.append(item.model_dump())
            else:
                processed_data.append(item)
        df = pd.DataFrame(processed_data)

        if df.empty:
            return

        # Convert competitors list to JSON string for database storage
        if 'competitors' in df.columns:
            df['competitors'] = df['competitors'].apply(lambda x: json.dumps(x) if isinstance(x, list) else json.dumps([]))

        with Session(engine) as session:
            for _, row in df.iterrows():
                kw = row.get("keyword")
                if not kw:
                    continue

                # Fetch existing by unique keyword or merge
                db_row = session.query(Keyword).filter(Keyword.keyword == kw).first()
                if not db_row:
                    db_row = Keyword(keyword=kw)
                    session.add(db_row)

                db_row.seed = row.get("seed") or "Unknown"
                db_row.volume = float(row.get("volume")) if pd.notnull(row.get("volume")) else 0.0
                db_row.competition = float(row.get("competition")) if pd.notnull(row.get("competition")) else None
                db_row.cpc = float(row.get("cpc")) if pd.notnull(row.get("cpc")) else None
                db_row.trend = float(row.get("trend")) if pd.notnull(row.get("trend")) else None
                db_row.score = float(row.get("score")) if pd.notnull(row.get("score")) else 0.0
                db_row.difficulty = row.get("difficulty") or "Unknown"

                # Normalize intent
                intent_raw = row.get("intent") or "Informational"
                if "Intent" in intent_raw:
                    intent_value = intent_raw.split("Intent")[0].strip()
                elif len(intent_raw) > 50:
                    intent_value = intent_raw[:50]
                else:
                    intent_value = intent_raw
                db_row.intent = intent_value
                db_row.competitors = row.get("competitors") or "[]"

            session.commit()
        logger.info(f"{len(df)} keywords saved/updated successfully!")
    except Exception as e:
        logger.error(f"Database Save Error: {e}", exc_info=True)
        logger.info("Data will be saved to cache files instead")
        try:
            os.makedirs("cache", exist_ok=True)
            cache_file = f"cache/keywords_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df = pd.DataFrame(data)
            df.to_csv(cache_file, index=False)
            logger.info(f"Saved to cache file: {cache_file}")
        except Exception as cache_e:
            logger.error(f"Cache save also failed: {cache_e}", exc_info=True)

def fetch_past_results(limit=50):
    """Fetch recent keyword entries."""
    try:
        engine = connect_db()
        with Session(engine) as session:
            rows = session.query(Keyword).order_by(Keyword.id.desc()).limit(limit).all()

            # Convert to list of dicts and strip internal _sa_instance_state
            data = []
            for row in rows:
                d = {k: v for k, v in row.__dict__.items() if k != '_sa_instance_state'}
                data.append(d)

            df = pd.DataFrame(data)

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

        logger.info(f"Fetched {len(df)} records from database")
        return df
    except Exception as e:
        logger.error(f"DB Fetch Error: {e}", exc_info=True)
        logger.info("Trying to load from cache files instead...")
        try:
            import glob
            cache_files = glob.glob("cache/*.csv")
            if cache_files:
                latest_file = max(cache_files, key=os.path.getctime)
                df = pd.read_csv(latest_file)

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

                logger.info(f"Loaded {len(df)} records from cache file: {latest_file}")
                return df.tail(limit)
            return pd.DataFrame()
        except Exception as cache_e:
            logger.error(f"Cache load also failed: {cache_e}", exc_info=True)
            return pd.DataFrame()

def verify_database_schema():
    """Verify that the keywords table has all required columns."""
    try:
        engine = connect_db()
        inspector = inspect(engine)
        columns = inspector.get_columns("keywords")
        if not columns:
            logger.error("Keywords table does not exist!")
            return False

        existing_columns = [col["name"] for col in columns]
        required_columns = ['seed', 'keyword', 'volume', 'competition', 'cpc', 'score', 'difficulty', 'intent', 'trend', 'competitors']

        logger.info(f"Keywords table has {len(existing_columns)} columns: {existing_columns}")

        missing_columns = [col for col in required_columns if col not in existing_columns]
        if missing_columns:
            logger.warning(f"Missing required columns: {missing_columns}")
            return False

        logger.info("All required columns are present!")
        return True
    except Exception as e:
        logger.error(f"Schema verification failed: {e}", exc_info=True)
        return False

def get_cached_intent(keyword):
    """Fetch cached intent for a given keyword from 'intent_cache' table if available."""
    try:
        engine = connect_db()
        with Session(engine) as session:
            row = session.query(IntentCache).filter(IntentCache.keyword == keyword).first()
            if row:
                logger.info(f"Cached intent found for '{keyword}': {row.intent}")
                return row.intent
        return None
    except Exception as e:
        logger.error(f"Intent cache lookup error for '{keyword}': {e}", exc_info=True)
        return None

def save_intent_to_db(keyword, intent):
    """Save new intent into 'intent_cache' table."""
    try:
        engine = connect_db()
        with Session(engine) as session:
            row = session.query(IntentCache).filter(IntentCache.keyword == keyword).first()
            if not row:
                row = IntentCache(keyword=keyword)
                session.add(row)
            row.intent = intent
            session.commit()
        logger.info(f"Cached intent saved for '{keyword}': {intent}")
    except Exception as e:
        logger.error(f"Error saving intent to DB for '{keyword}': {e}", exc_info=True)
