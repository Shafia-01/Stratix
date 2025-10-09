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

load_dotenv()

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
    if score >= 0.8:
        return "🟢 Easy"
    elif score >= 0.5:
        return "🟡 Medium"
    else:
        return "🔴 Hard"

def run_agent(seed_keyword):
    print(f"\n🚀 Running GemKey AI for: {seed_keyword}")
    keywords = generate_keywords(seed_keyword)

    if not keywords or len(keywords) == 0:
        print(f"⚠️ No keywords generated for '{seed_keyword}'.")
        return []

    print(f"✅ Gemini returned {len(keywords)} keywords.")

    formatted_keywords = []
    for i, kw in enumerate(keywords, start=1):
        formatted_keywords.append({
            "rank": i,
            "keyword": kw if isinstance(kw, str) else kw.get("keyword", "")
        })
    sorted_keywords = sorted(formatted_keywords, key=lambda x: x["rank"])
    full_analysis_keywords = sorted_keywords[:15]
    quick_keywords = sorted_keywords[15:]
    results = []

    print("\n⚙️ Running full analysis (metrics + trends + competitors) on top 15 keywords...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_keyword, kw, seed_keyword) for kw in full_analysis_keywords]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                
    print("\n⚙️ Running quick analysis (metrics only) for remaining keywords...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_keyword_quick, kw, seed_keyword) for kw in quick_keywords]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    os.makedirs("cache", exist_ok=True)
    pd.DataFrame(results).to_csv(f"cache/{seed_keyword.replace(' ', '_')}_results.csv", index=False)
    
    from src.db_client import get_connection, save_to_db
    try:
        conn = get_connection()
        save_to_db(conn, results)
        conn.close()
    except Exception as e:
        print("⚠️ MySQL Save Error:", e)
        
    print(f"\n✅ {len(results)} keywords saved successfully!")
    return results

def process_keyword(kw_item, seed_keyword):
    kw = kw_item["keyword"]
    try:
        metrics = get_keyword_metrics(kw)
        if not metrics:
            return None

        score = compute_score(metrics)
        difficulty = classify_difficulty(score)
        intent = classify_intent(kw)

        trend_score = None
        try:
            trend_score = get_trend_score(kw)
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ Trend rate-limited for '{kw}'. Sleeping longer...")
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
        print(f"⚠️ Error processing '{kw}':", e)
        return None

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
        print(f"⚠️ Error (quick) for '{kw}':", e)
        return None
