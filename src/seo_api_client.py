import os
import requests
import time
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from src.db_client import connect_db
from src.data_quality import DataSource
from sqlalchemy.orm import Session
from src.models import Keyword
from src.logger_config import get_logger

logger = get_logger(__name__)
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def get_keyword_metrics(keyword):
    """
    Fetch SEO metrics (volume, CPC, competition) from cache or SerpApi.
    - Uses cached data if updated < 7 days ago
    - Otherwise refreshes via SerpApi and updates DB
    """
    cached = check_cache(keyword)
    if cached is not None:
        last_updated = cached.get("last_updated")
        if last_updated and (datetime.now() - pd.to_datetime(last_updated)) < timedelta(days=7):
            logger.info(f"Using cached data for '{keyword}' (updated {last_updated})")
            return cached
        else:
            logger.info(f"Cache expired for '{keyword}', refreshing...")
    try:
        logger.info(f"Fetching fresh data from SerpApi for '{keyword}'...")
        url = "https://serpapi.com/search.json"
        params = {"q": keyword, "api_key": SERPAPI_KEY, "engine": "google", "num": "1"}
        res = requests.get(url, params=params, timeout=15).json()
        info = res.get("search_information", {})
        total_results = info.get("total_results", 0)
        volume = min(int(total_results / 1000), 10000) or 0
        competition = None
        cpc = None
        time.sleep(0.5)
        metrics = {
            "volume": volume,
            "competition": competition,
            "cpc": cpc,
            "data_source": DataSource.ESTIMATED.value
        }
        save_to_cache(keyword, metrics)
        return metrics
    except Exception as e:
        logger.error(f"SerpApi Error for '{keyword}': {e}", exc_info=True)
        return {
            "volume": 0,
            "competition": None,
            "cpc": None,
            "data_source": DataSource.UNAVAILABLE.value
        }

def check_cache(keyword):
    """Check if keyword already exists in DB and return metrics + timestamp."""
    try:
        engine = connect_db()
        with Session(engine) as session:
            row = (session.query(Keyword)
                   .filter(Keyword.keyword == keyword)
                   .order_by(Keyword.last_updated.desc())
                   .first())
            if row and row.volume is not None:
                return {
                    "volume": int(row.volume),
                    "competition": row.competition,
                    "cpc": row.cpc,
                    "last_updated": row.last_updated,
                    "seed": row.seed,
                    "data_source": DataSource.CACHED.value
                }
        return None
    except Exception as e:
        logger.error(f"Cache check failed for '{keyword}': {e}", exc_info=True)
        return None

def save_to_cache(keyword, metrics):
    """Insert or update metrics + refresh timestamp without overwriting complete data."""
    try:
        engine = connect_db()
        with Session(engine) as session:
            row = session.query(Keyword).filter(Keyword.keyword == keyword).first()
            if not row:
                row = Keyword(
                    keyword=keyword,
                    volume=metrics["volume"],
                    competition=metrics.get("competition"),
                    cpc=metrics.get("cpc")
                )
                session.add(row)
            else:
                if not row.seed or row.seed == 'Unknown':
                    row.volume = metrics["volume"]
                    row.competition = metrics.get("competition")
                    row.cpc = metrics.get("cpc")
            session.commit()
        logger.info(f"Metrics cached for '{keyword}' (preserving complete data)")
    except Exception as e:
        logger.error(f"Cache save failed for '{keyword}': {e}", exc_info=True)
