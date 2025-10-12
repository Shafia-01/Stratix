# intent_classifier.py
import re
import random
from dotenv import load_dotenv
from src.db_client import get_cached_intent, save_intent_to_db
from src.gemini_client import safe_gemini_call  # ✅ Use the unified Gemini fallback handler

load_dotenv()

# ---------- SIMPLE RULE-BASED INTENT DETECTOR ----------
def rule_based_intent(keyword: str) -> str:
    keyword_lower = keyword.lower()

    if any(w in keyword_lower for w in ["buy", "price", "deal", "shop", "discount", "best"]):
        return "Commercial Intent"

    elif any(w in keyword_lower for w in ["hire", "job", "internship", "career", "apply"]):
        return "Transactional Intent"

    elif any(w in keyword_lower for w in ["what is", "how to", "tutorial", "guide", "learn"]):
        return "Informational Intent"

    elif any(w in keyword_lower for w in ["review", "comparison", "vs", "alternative"]):
        return "Navigational Intent"

    elif any(w in keyword_lower for w in ["cheap", "affordable", "free", "budget"]):
        return "Low-Intent (Bargain)"

    # fallback
    return "Uncertain"

# ---------- GEMINI BACKUP INTENT DETECTOR ----------
def generate_intent_gemini(keyword: str) -> str:
    """
    Use Gemini (fallback) to refine uncertain intents with safe fallback system.
    """
    prompt = f"""
    You are an SEO assistant. Determine the **search intent** behind this keyword: "{keyword}".
    Classify into one of:
    - Informational Intent (learning or exploring)
    - Navigational Intent (finding specific brand or product)
    - Transactional Intent (taking action, buying or applying)
    - Commercial Intent (researching before purchase)
    Respond with the label only.
    """
    response = safe_gemini_call(prompt)  # ✅ auto-fallback logic
    if response:
        return response

    # if all Gemini models fail
    return random.choice([
        "Informational Intent",
        "Transactional Intent",
        "Commercial Intent",
        "Navigational Intent"
    ])

# ---------- HYBRID INTENT CLASSIFIER ----------
def classify_intent(keyword: str) -> str:
    """
    Hybrid classifier → checks DB → rule-based → Gemini fallback → saves to cache.
    """
    # 1️⃣ Check Cache
    cached_intent = get_cached_intent(keyword)
    if cached_intent:
        return cached_intent

    # 2️⃣ Rule-based intent
    intent = rule_based_intent(keyword)

    # 3️⃣ Gemini backup if uncertain
    if intent == "Uncertain":
        print(f"Using Gemini to refine intent for '{keyword}'...")
        gemini_intent = generate_intent_gemini(keyword)
        if gemini_intent:
            intent = gemini_intent

    # 4️⃣ Save to cache
    save_intent_to_db(keyword, intent)
    return intent
