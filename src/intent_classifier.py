import re
import os
import mysql.connector
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.gemini_client import generate_intent_gemini  # new helper (below)
load_dotenv()

# ---------- DATABASE HELPER ----------

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

# ---------- RULE-BASED INTENT CLASSIFIER ----------

def rule_based_intent(keyword: str) -> str:
    """
    Basic heuristic classifier for intent.
    """
    kw = keyword.lower().strip()

    transactional_keywords = [
        "buy", "apply", "book", "hire", "enroll", "download",
        "register", "get", "join", "subscribe", "pricing",
        "deal", "discount", "offer", "purchase", "shop"
    ]

    navigational_keywords = [
        "website", "linkedin", "indeed", "internshala", "glassdoor",
        "facebook", "instagram", "youtube", "portal", "account", "dashboard"
    ]

    informational_keywords = [
        "how", "what", "when", "where", "why", "guide", "tips", "examples",
        "ideas", "learn", "definition", "meaning", "benefits", "tutorial", "explained"
    ]

    if any(word in kw for word in transactional_keywords):
        return "💼 Transactional"
    elif any(word in kw for word in navigational_keywords):
        return "🧭 Navigational"
    elif any(word in kw for word in informational_keywords):
        return "📘 Informational"
    else:
        # uncertain
        return "🤔 Uncertain"


# ---------- HYBRID CLASSIFIER ----------

def classify_intent(keyword: str) -> str:
    """
    Hybrid intent classifier — rule-based first, Gemini backup if uncertain.
    """

    # Step 1: Check cache (MySQL)
    cached_intent = get_cached_intent(keyword)
    if cached_intent:
        return cached_intent

    # Step 2: Rule-based logic
    intent = rule_based_intent(keyword)

    # Step 3: If uncertain, use Gemini backup
    if intent == "🤔 Uncertain":
        print(f"🧠 Using Gemini for better intent understanding → '{keyword}'")
        gemini_intent = generate_intent_gemini(keyword)
        if gemini_intent:
            intent = gemini_intent

    # Step 4: Save result to DB
    save_intent_to_db(keyword, intent)
    return intent


# ---------- CACHE UTILITIES ----------

def get_cached_intent(keyword: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT intent, last_updated
            FROM keywords
            WHERE keyword = %s AND intent IS NOT NULL
            LIMIT 1;
        """, (keyword,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None
        updated_time = row.get("last_updated")
        if updated_time and (datetime.now() - updated_time) < timedelta(days=30):
            return row["intent"]
        return None
    except Exception:
        return None


def save_intent_to_db(keyword, intent):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
        UPDATE keywords
        SET intent = %s, last_updated = NOW()
        WHERE keyword = %s;
        """
        cursor.execute(query, (intent, keyword))
        conn.commit()
        conn.close()
    except Exception as e:
        print("⚠️ Intent cache save failed:", e)
