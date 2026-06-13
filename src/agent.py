import os
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.keyword_api_client import get_enhanced_keywords, get_keyword_metrics_enhanced
from src.intent_classifier import classify_intent
from src.trends_client import get_trend_score
from src.competitor_client import get_competitor_data
from src.db_client import save_to_db 
from src.data_quality import DataSource 
from src.scoring import compute_score, classify_difficulty
from src.logger_config import get_logger

logger = get_logger(__name__)

from pydantic import ValidationError
from src.schemas import KeywordFinding, CompetitorEntry

# MAIN AGENT
def run_agent(seed_keyword, max_keywords=50):
    logger.info(f"Running Keylytics for: {seed_keyword}")
    
    # Use enhanced keyword research (DataForSEO + Gemini fallback)
    keywords = get_enhanced_keywords(seed_keyword, max_keywords)
    
    if not keywords or len(keywords) == 0:
        logger.warning(f"Enhanced keyword research failed for '{seed_keyword}'. Using emergency fallback...")
        time.sleep(1)
        keywords = [{"rank": 1, "keyword": f"{seed_keyword} ideas"}, 
                   {"rank": 2, "keyword": f"{seed_keyword} tools"}, 
                   {"rank": 3, "keyword": f"best {seed_keyword} resources"}]
    
    logger.info(f"Enhanced keyword research returned {len(keywords)} optimized keywords.")
    
    # Keywords are already formatted and sorted by opportunity score
    sorted_keywords = keywords
    
    # Limit to requested number of keywords
    if max_keywords < len(sorted_keywords):
        sorted_keywords = sorted_keywords[:max_keywords]
    
    # For larger keyword sets, do more full analysis
    if max_keywords <= 15:
        full_analysis_count = max_keywords
    elif max_keywords <= 30:
        full_analysis_count = 15
    else:
        full_analysis_count = 20
    full_analysis_keywords = sorted_keywords[:full_analysis_count]
    quick_keywords = sorted_keywords[full_analysis_count:]
    results = []

    # FULL ANALYSIS
    logger.info(f"Running full analysis (metrics + trends + competitors) on top {full_analysis_count} keywords...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_keyword, kw, seed_keyword) for kw in full_analysis_keywords]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                # Auto-save progress every 5 results
                if len(results) % 5 == 0:
                    pd.DataFrame([r.model_dump() for r in results]).to_csv(f"cache/{seed_keyword.replace(' ', '_')}_temp.csv", index=False)

    # QUICK ANALYSIS (OTHERS)
    if quick_keywords:
        logger.info(f"Running quick analysis (metrics only) for remaining {len(quick_keywords)} keywords...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_keyword_quick, kw, seed_keyword) for kw in quick_keywords]
            for future in as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)

    # FINALIZE
    results = sorted(results, key=lambda x: x.score, reverse=True)
    os.makedirs("cache", exist_ok=True)
    pd.DataFrame([r.model_dump() for r in results]).to_csv(f"cache/{seed_keyword.replace(' ', '_')}_results.csv", index=False)

    # Save to DB (SQLAlchemy)
    try:
        save_to_db(results)
    except Exception as e:
        logger.error(f"Database Save Error: {e}", exc_info=True)
    logger.info(f"{len(results)} keywords saved successfully!")
    return results

# FULL PROCESS (TOP 15)
def process_keyword(kw_item, seed_keyword):
    kw = kw_item["keyword"]
    try:
        # Use metrics from kw_item if available (from DataForSEO batch), otherwise fetch
        if "volume" in kw_item and "competition" in kw_item and "cpc" in kw_item:
            metrics = {
                "volume": kw_item.get("volume", 0),
                "competition": kw_item.get("competition", 0.5),
                "cpc": kw_item.get("cpc", 0.0)
            }
        else:
            metrics = get_keyword_metrics_enhanced(kw)
            if not metrics:
                return None
        opportunity = compute_score(metrics)
        score = opportunity.score
        difficulty = classify_difficulty(opportunity)
        intent = classify_intent(kw)

        # Trend data
        try:
            trend_score = get_trend_score(kw)
        except Exception:
            trend_score = None
        
        competitors_raw = get_competitor_data(kw)
        competitors = [
            CompetitorEntry(
                domain=c.get("domain", ""),
                rank=c.get("rank", 0),
                title=c.get("title"),
                url=c.get("link")
            )
            for c in competitors_raw
        ]
        
        final_score = round((0.8 * score + 0.2 * (trend_score if trend_score is not None else score)), 3)
        
        return KeywordFinding(
            seed=seed_keyword,
            keyword=kw,
            volume=float(metrics.get("volume", 0)),
            competition=metrics.get("competition"),
            cpc=metrics.get("cpc"),
            trend=trend_score,
            score=final_score,
            difficulty=difficulty,
            intent=intent,
            competitors=competitors,
            data_source=metrics.get("data_source", DataSource.UNAVAILABLE.value),
            trend_data_source=DataSource.LIVE.value if trend_score is not None else DataSource.UNAVAILABLE.value
        )
    except ValidationError as ve:
        logger.warning(f"Validation failed for keyword '{kw}': {ve}")
        return None
    except Exception as e:
        logger.error(f"Error processing '{kw}': {e}", exc_info=True)
        return None

# QUICK PROCESS (OTHERS)
def process_keyword_quick(kw_item, seed_keyword):
    kw = kw_item["keyword"]
    try:
        # Use metrics from kw_item if available (from DataForSEO batch), otherwise fetch
        if "volume" in kw_item and "competition" in kw_item and "cpc" in kw_item:
            metrics = {
                "volume": kw_item.get("volume", 0),
                "competition": kw_item.get("competition"),
                "cpc": kw_item.get("cpc"),
                "data_source": kw_item.get("data_source", DataSource.LIVE.value)
            }
        else:
            metrics = get_keyword_metrics_enhanced(kw)
            if not metrics:
                return None
        opportunity = compute_score(metrics)
        score = opportunity.score
        difficulty = classify_difficulty(opportunity)
        intent = classify_intent(kw)
        
        return KeywordFinding(
            seed=seed_keyword,
            keyword=kw,
            volume=float(metrics.get("volume", 0)),
            competition=metrics.get("competition"),
            cpc=metrics.get("cpc"),
            trend=None,
            score=score,
            difficulty=difficulty,
            intent=intent,
            competitors=[],
            data_source=metrics.get("data_source", DataSource.UNAVAILABLE.value),
            trend_data_source=DataSource.UNAVAILABLE.value
        )
    except ValidationError as ve:
        logger.warning(f"Validation failed (quick) for keyword '{kw}': {ve}")
        return None
    except Exception as e:
        logger.error(f"Error (quick) for '{kw}': {e}", exc_info=True)
        return None
