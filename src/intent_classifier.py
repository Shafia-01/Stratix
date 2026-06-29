from dotenv import load_dotenv
from src.db_client import get_cached_intent, save_intent_to_db
from src.gemini_client import safe_gemini_call
from src.prompt_safety import build_safe_prompt, cap_text_length
from src.logger_config import get_logger

logger = get_logger(__name__)

load_dotenv()

# SIMPLE RULE-BASED INTENT DETECTOR
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
    return "Uncertain"

# GEMINI BACKUP INTENT DETECTOR
def generate_intent_gemini(keyword: str) -> str:
    """
    Use Gemini (fallback) to refine uncertain intents with safe fallback system.
    """
    keyword = cap_text_length(keyword, 100)
    prompt_template = """
    You are an SEO assistant. Determine the **search intent** behind this keyword: "{keyword}".
    Classify into one of these EXACT labels (respond with ONLY the label, nothing else):
    - Informational
    - Navigational
    - Transactional
    - Commercial
    Respond with ONLY the label name, no descriptions or extra text.
    """
    prompt = build_safe_prompt(prompt_template, keyword=keyword)
    response = safe_gemini_call(prompt)
    if response:
        # Clean the response to extract just the intent type
        response_clean = response.strip()
        # Remove common prefixes/suffixes
        for intent_type in ["Informational", "Navigational", "Transactional", "Commercial"]:
            if intent_type in response_clean:
                return intent_type
        # If we got something else, try to extract
        if "Intent" in response_clean:
            return response_clean.split("Intent")[0].strip()
        return response_clean[:50]  # Truncate if too long
    # if all Gemini models fail
    return "Informational"

def classify_intent_with_source(keyword: str) -> tuple[str, str]:
    """
    Hybrid classifier → checks DB → rule-based → Gemini fallback → saves to cache.
    Returns a tuple (intent, source) indicating which path resolved it.
    """
    # 1️⃣ Check Cache
    cached_intent = get_cached_intent(keyword)
    if cached_intent:
        return cached_intent, "cache"

    # 2️⃣ Rule-based intent
    intent = rule_based_intent(keyword)
    if intent != "Uncertain":
        save_intent_to_db(keyword, intent)
        return intent, "rule"

    # 3️⃣ Gemini backup if uncertain
    logger.info(f"Using Gemini to refine intent for '{keyword}'...")
    gemini_intent = generate_intent_gemini(keyword)
    if gemini_intent:
        intent = gemini_intent
        save_intent_to_db(keyword, intent)
        return intent, "gemini"

    # 4️⃣ Fallback if Gemini failed
    intent = "Informational"
    save_intent_to_db(keyword, intent)
    return intent, "gemini"

def classify_intent(keyword: str) -> str:
    """
    Hybrid classifier → checks DB → rule-based → Gemini fallback → saves to cache.
    """
    intent, _ = classify_intent_with_source(keyword)
    return intent
