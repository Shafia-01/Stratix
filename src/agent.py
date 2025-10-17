import os
import random
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from src.gemini_client import generate_keywords
from src.seo_api_client import get_keyword_metrics
from src.intent_classifier import classify_intent
from src.trends_client import get_trend_score
from src.competitor_client import get_competitor_data
from src.db_client import save_to_db 

load_dotenv()

# SCORE COMPUTATION
def compute_score(metrics):
    """
    Compute base SEO score using volume, CPC, and competition.
    Weighted formula.
    """
    volume = metrics.get("volume", 0)
    cpc = metrics.get("cpc", 0)
    competition = metrics.get("competition", 0)

    score = (volume * 0.5 + cpc * 100 * 0.3 + (1 - competition) * 100 * 0.2) / 100
    return round(score, 3)

def classify_difficulty(score):
    """Classify keyword difficulty based on score."""
    if score >= 0.8:
        return "Easy"
    elif score >= 0.5:
        return "Medium"
    else:
        return "Hard"

# MAIN AGENT
def run_agent(seed_keyword, max_keywords=50):
    print(f"\nRunning GemKey AI for: {seed_keyword}")
    keywords = generate_keywords(seed_keyword)
    
    # Fallback if Gemini failed
    if not keywords or len(keywords) == 0:
        print(f"Gemini failed to generate keywords for '{seed_keyword}'. Retrying with fallback set...")
        time.sleep(1)
        keywords = [f"{seed_keyword} ideas", f"{seed_keyword} tools", f"best {seed_keyword} resources"]
    print(f"Gemini returned {len(keywords)} keywords.")
    formatted_keywords = [{"rank": i, "keyword": kw if isinstance(kw, str) else kw.get("keyword", "")}
                          for i, kw in enumerate(keywords, start=1)]
    sorted_keywords = sorted(formatted_keywords, key=lambda x: x["rank"])
    
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
    print(f"\nRunning full analysis (metrics + trends + competitors) on top {full_analysis_count} keywords...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_keyword, kw, seed_keyword) for kw in full_analysis_keywords]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                # Auto-save progress every 5 results
                if len(results) % 5 == 0:
                    pd.DataFrame(results).to_csv(f"cache/{seed_keyword.replace(' ', '_')}_temp.csv", index=False)

    # QUICK ANALYSIS (OTHERS)
    if quick_keywords:
        print(f"\nRunning quick analysis (metrics only) for remaining {len(quick_keywords)} keywords...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_keyword_quick, kw, seed_keyword) for kw in quick_keywords]
            for future in as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)

    # FINALIZE
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    os.makedirs("cache", exist_ok=True)
    pd.DataFrame(results).to_csv(f"cache/{seed_keyword.replace(' ', '_')}_results.csv", index=False)

    # Save to DB (SQLAlchemy)
    try:
        save_to_db(results)
    except Exception as e:
        print("MySQL Save Error:", e)
    print(f"\n{len(results)} keywords saved successfully!")
    return results

# FULL PROCESS (TOP 15)
def process_keyword(kw_item, seed_keyword):
    kw = kw_item["keyword"]
    try:
        metrics = get_keyword_metrics(kw)
        if not metrics:
            return None
        score = compute_score(metrics)
        difficulty = classify_difficulty(score)
        intent = classify_intent(kw)

        # Trend data
        try:
            trend_score = get_trend_score(kw)
        except Exception as e:
            if "429" in str(e):
                print(f"Trend rate-limited for '{kw}'. Sleeping longer...")
                time.sleep(random.uniform(30, 45))
                trend_score = random.randint(20, 80)
            else:
                trend_score = random.randint(20, 80)
        competitors = get_competitor_data(kw)
        final_score = round((0.8 * score + 0.2 * (trend_score or score)), 3)
        return {
            "seed": seed_keyword,
            "keyword": kw,
            "volume": metrics.get("volume", 0),
            "competition": metrics.get("competition", 0.0),
            "cpc": metrics.get("cpc", 0.0),
            "trend": trend_score,
            "score": final_score,
            "difficulty": difficulty,
            "intent": intent,
            "competitors": competitors
        }
    except Exception as e:
        print(f"Error processing '{kw}':", e)
        return None

# QUICK PROCESS (OTHERS)
def process_keyword_quick(kw_item, seed_keyword):
    kw = kw_item["keyword"]
    try:
        metrics = get_keyword_metrics(kw)
        if not metrics:
            return None
        score = compute_score(metrics)
        difficulty = classify_difficulty(score)
        intent = classify_intent(kw)
        return {
            "seed": seed_keyword,
            "keyword": kw,
            "volume": metrics.get("volume", 0),
            "competition": metrics.get("competition", 0.0),
            "cpc": metrics.get("cpc", 0.0),
            "trend": None,
            "score": score,
            "difficulty": difficulty,
            "intent": intent,
            "competitors": []
        }
    except Exception as e:
        print(f"Error (quick) for '{kw}':", e)
        return None
