import time
import warnings
from datetime import datetime
import pandas as pd
from pytrends.request import TrendReq
from dotenv import load_dotenv
from src.db_client import connect_db
from src.logger_config import get_logger

logger = get_logger(__name__)

load_dotenv()

# Suppress pandas FutureWarning for pytrends
warnings.filterwarnings("ignore", category=FutureWarning, module="pytrends")
pytrends = TrendReq(hl='en-US', tz=360)

import requests
from src.exceptions import KeylyticsAPIError
from src.retry import with_retries

# Retry only on recoverable network/API errors — never on bare Exception.
# Programming errors (AttributeError, TypeError, etc.) should surface immediately.
# pytrends enforces ~1 req/s; the 2.0s base_delay + exponential backoff avoids 429s.
@with_retries(
    max_attempts=3,
    base_delay=2.0,
    retry_on=(
        KeylyticsAPIError,
        requests.exceptions.RequestException,
        ConnectionError,
        TimeoutError,
    ),
)
def _fetch_pytrends_dataframe(keyword):
    """
    Fetch raw interest over time DataFrame from Google Trends using pytrends.
    Reuses the retry and backoff logic. Returns None on failure.
    """
    global pytrends
    try:
        pytrends.build_payload([keyword], timeframe="today 12-m")
        data = pytrends.interest_over_time()
        if not data.empty:
            return data
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Trend error for '{keyword}': {error_msg}")
        
        # Reset pytrends connection to avoid stale sessions
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # PyTrends-specific 429/rate-limit detection logic
        if "429" in error_msg or "rate" in error_msg.lower():
            wait_time = 10.0  # Specific longer wait for rate limits
            logger.info(f"Rate limit detected. Waiting {wait_time}s before letting tenacity retry...")
            time.sleep(wait_time)
            
        raise e
    return None

def get_trend_score(keyword):
    """
    Fetch Google Trends average score (0–100) for a keyword.
    Includes caching via MySQL and fallback values.
    """
    cached = get_cached_trend(keyword)
    if cached is not None:
        logger.info(f"Using cached trend data for '{keyword}'")
        return cached
    logger.info(f"Fetching trend data for '{keyword}'...")
    
    data = _fetch_pytrends_dataframe(keyword)
    if data is not None and not data.empty and keyword in data.columns:
        score = int(data[keyword].mean())
        save_trend_to_db(keyword, score)
        logger.info(f"Trend data fetched for '{keyword}': {score}")
        return score
    
    logger.warning(f"Trend data fetch failed for '{keyword}' after retries")
    return None

def get_trend_history(keyword: str) -> list[dict] | None:
    """Fetch real 12-month Google Trends history. Returns None on failure."""
    logger.info(f"Fetching trend history for '{keyword}'...")
    data = _fetch_pytrends_dataframe(keyword)
    if data is not None and not data.empty and keyword in data.columns:
        try:
            # Resample to month end mean and round
            monthly_data = data[keyword].resample('ME').mean()
        except ValueError:
            # Fallback for older pandas versions where 'ME' is not supported
            monthly_data = data[keyword].resample('M').mean()
            
        history = []
        for date, val in monthly_data.items():
            history.append({
                "date": date.strftime("%Y-%m"),
                "score": int(round(val)) if pd.notnull(val) else 0
            })
        logger.info(f"Trend history fetched for '{keyword}': {len(history)} months")
        return history
    logger.warning(f"Trend history fetch failed for '{keyword}' after retries")
    return None

from sqlalchemy.orm import Session
from src.models import Keyword

def get_cached_trend(keyword):
    """
    Retrieve cached trend if less than 7 days old.
    """
    try:
        engine = connect_db()
        with Session(engine) as session:
            row = (session.query(Keyword)
                   .filter(Keyword.keyword == keyword)
                   .filter(Keyword.trend.isnot(None))
                   .order_by(Keyword.last_updated.desc())
                   .first())
            if not row:
                return None
            last_updated = row.last_updated
            if last_updated:
                delta = datetime.utcnow() - last_updated
                if delta.days < 7:
                    return int(row.trend)
            return None
    except Exception as e:
        logger.error(f"Trend cache lookup failed for '{keyword}': {e}", exc_info=True)
        return None

def save_trend_to_db(keyword, score):
    """
    Save or update trend score in DB.
    """
    if score is None:
        return
    try:
        engine = connect_db()
        with Session(engine) as session:
            row = session.query(Keyword).filter(Keyword.keyword == keyword).first()
            if not row:
                row = Keyword(keyword=keyword, trend=score)
                session.add(row)
            else:
                row.trend = score
            session.commit()
        logger.info(f"Trend score saved for '{keyword}': {score}")
    except Exception as e:
        logger.error(f"Trend cache save failed for '{keyword}': {e}", exc_info=True)
