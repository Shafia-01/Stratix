import time
import warnings
from datetime import datetime, timezone
import pandas as pd
from pytrends.request import TrendReq
from dotenv import load_dotenv
from src.db_client import connect_db
from src.logger_config import get_logger

logger = get_logger(__name__)

load_dotenv()

# Suppress pandas FutureWarning for pytrends
warnings.filterwarnings("ignore", category=FutureWarning, module="pytrends")

# ---------------------------------------------------------------------------
# FIX: pytrends must NEVER be constructed at module import time.
#
# TrendReq.__init__() calls GetGoogleCookie(), which makes a live HTTP request
# to https://trends.google.com the instant the object is created. Because this
# module is imported transitively by almost the entire agent pipeline
# (graph/nodes.py -> tools/langchain_adapters.py -> tools/registry.py ->
#  tools/trend_forecast_tool.py -> trend_forecaster.py -> trends_client.py),
# a DNS failure or network hiccup at import time used to raise an exception
# that propagated all the way up and crashed EVERY caller of
# src.graph.graph.get_compiled_graph() (Agent Mode, Executive Reports,
# Analytics, the FastAPI lifespan warm-up, and the monitoring Scheduler),
# even though none of those callers actually needed trend data.
#
# The client is now built lazily on first real use inside
# _fetch_pytrends_dataframe(), and reset to None on failure so the next
# attempt gets a fresh session instead of a possibly-broken one.
# ---------------------------------------------------------------------------
_pytrends_instance = None


def _get_pytrends_client():
    """Lazily construct the pytrends client on first real use."""
    global _pytrends_instance
    if _pytrends_instance is None:
        _pytrends_instance = TrendReq(hl='en-US', tz=360)
    return _pytrends_instance


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
    global _pytrends_instance
    try:
        client = _get_pytrends_client()
        client.build_payload([keyword], timeframe="today 12-m")
        data = client.interest_over_time()
        if not data.empty:
            return data
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Trend error for '{keyword}': {error_msg}")

        # Reset pytrends connection to avoid stale sessions.
        # Do NOT reconstruct here — just drop the reference so the next
        # call to _get_pytrends_client() builds a fresh one lazily.
        _pytrends_instance = None

        # PyTrends-specific 429/rate-limit detection logic
        if "429" in error_msg or "rate" in error_msg.lower():
            wait_time = 10.0  # Specific longer wait for rate limits
            logger.info(f"Rate limit detected. Waiting {wait_time}s before letting tenacity retry...")
            time.sleep(wait_time)

        raise e
    return None

_last_trend_source = {}

def get_trend_score_with_source(keyword):
    """
    Fetch Google Trends average score (0-100) and return (score, data_source).
    If cached, return (score, DataSource.CACHED.value).
    If live fetches successfully, return (score, DataSource.LIVE.value).
    If live fails, return (fallback_score, DataSource.ESTIMATED.value).
    """
    from src.data_quality import DataSource
    cached = get_cached_trend(keyword)
    if cached is not None:
        logger.info(f"Using cached trend data for '{keyword}'")
        _last_trend_source[keyword] = DataSource.CACHED.value
        return cached, DataSource.CACHED.value

    logger.info(f"Fetching trend data for '{keyword}'...")
    try:
        data = _fetch_pytrends_dataframe(keyword)
        if data is not None and not data.empty and keyword in data.columns:
            score = int(data[keyword].mean())
            save_trend_to_db(keyword, score)
            logger.info(f"Trend data fetched for '{keyword}': {score}")
            _last_trend_source[keyword] = DataSource.LIVE.value
            return score, DataSource.LIVE.value
    except Exception as e:
        logger.warning(f"Trend fetch exception for '{keyword}': {e}")

    logger.warning(f"Trend data fetch failed for '{keyword}' after retries")
    # Deterministic fallback trend score
    import hashlib
    h = int(hashlib.md5(keyword.encode('utf-8')).hexdigest(), 16)
    fallback_score = 15 + (h % 70)
    logger.info(f"Using fallback trend score for '{keyword}': {fallback_score}")
    _last_trend_source[keyword] = DataSource.ESTIMATED.value
    return fallback_score, DataSource.ESTIMATED.value

def get_trend_score(keyword):
    """
    Fetch Google Trends average score (0–100) for a keyword.
    Includes caching via MySQL and fallback values.
    """
    score, _ = get_trend_score_with_source(keyword)
    return score

def get_trend_history(keyword: str) -> tuple[list[dict], str]:
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
        return history, "live"
    logger.warning(f"Trend history fetch failed for '{keyword}' after retries — using estimated fallback")
    return _generate_estimated_trend_history(keyword), "estimated"


def _generate_estimated_trend_history(keyword: str) -> list[dict]:
    """Deterministic, hash-seeded 12-month estimated trend series used only
    when Google Trends is unavailable. Marked as estimated, never presented
    as live data."""
    import hashlib
    from datetime import datetime, timedelta
    h = int(hashlib.md5(keyword.encode("utf-8")).hexdigest(), 16)
    base = 20 + (h % 60)
    history = []
    today = datetime.now()
    for i in range(11, -1, -1):
        month_date = today - timedelta(days=30 * i)
        drift = ((h >> (i % 16)) % 21) - 10  # deterministic +/-10 wobble per month
        score = max(0, min(100, base + drift))
        history.append({"date": month_date.strftime("%Y-%m"), "score": score})
    return history

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
                delta = datetime.now(timezone.utc).replace(tzinfo=None) - last_updated
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
