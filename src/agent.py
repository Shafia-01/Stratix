# src/agent.py

import pandas as pd
import google.generativeai as genai
import os
from src.gemini_client import generate_keywords
from src.seo_api_client import get_keyword_metrics
from src.db import save_keywords_to_db
from src.trend_client import get_trend_score
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ------------------ MAIN FUNCTION ------------------

def run_agent(seed_keyword):
    """
    Main AI agent for GemKey.
    1. Generate keywords via Gemini
    2. Fetch SEO metrics
    3. Compute SEO score
    4. Classify difficulty
    5. Classify search intent
    6. Save + return sorted DataFrame
    """

    print(f"🚀 Running GemKey AI for: {seed_keyword}")

    keywords = generate_keywords(seed_keyword)
    if not keywords:
        print("❌ No keywords generated.")
        return pd.DataFrame()

    print(f"✅ Gemini returned {len(keywords)} keywords.")

    results = []
    for kw in keywords:
        metrics = get_keyword_metrics(kw)
        if metrics:
            score = compute_score(metrics)
            difficulty = classify_difficulty(score)
            intent = classify_intent(kw)
            trend_score = get_trend_score(kw)

            # Combine both
            final_score = round((0.8 * score + 0.2 * trend_score), 3)

            results.append({
                "seed": seed_keyword,
                "keyword": kw,
                "volume": metrics.get("volume", 0),
                "competition": metrics.get("competition", 0.0),
                "cpc": metrics.get("cpc", 0.0),
                "trend": trend_score,
                "score": final_score,
                "difficulty": difficulty,
                "intent": intent
            })

    if not results:
        print("⚠️ No results fetched.")
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.sort_values(by="score", ascending=False).reset_index(drop=True)

    save_keywords_to_db(df)
    print(f"✅ {len(df)} keywords saved successfully!")

    return df


# ------------------ HELPERS ------------------

def compute_score(metrics):
    """Weighted SEO scoring model."""
    volume = metrics.get("volume", 0)
    competition = metrics.get("competition", 0)
    cpc = metrics.get("cpc", 0)

    vol_norm = min(volume / 10000, 1.0)
    comp_norm = 1 - min(competition, 1.0)
    cpc_norm = 1 - min(cpc / 10, 1.0)
    score = round((0.5 * vol_norm + 0.3 * comp_norm + 0.2 * cpc_norm), 3)
    return score


def classify_difficulty(score):
    """Label difficulty level."""
    if score >= 0.8:
        return "🟢 Easy"
    elif score >= 0.5:
        return "🟡 Medium"
    else:
        return "🔴 Hard"


def classify_intent(keyword):
    """
    Use Gemini to classify search intent:
    Informational | Navigational | Transactional
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""
        Classify the search intent for the keyword: '{keyword}'.
        Choose one of:
        - Informational: user seeks knowledge or learning
        - Navigational: user searches for a brand, website, or tool
        - Transactional: user wants to take action (buy, apply, hire, register)
        Return only one word: Informational, Navigational, or Transactional.
        """
        result = model.generate_content(prompt)
        intent = result.text.strip()
        if intent not in ["Informational", "Navigational", "Transactional"]:
            intent = "Informational"
        return intent
    except Exception as e:
        print(f"⚠️ Intent classification failed for '{keyword}': {e}")
        return "Informational"
