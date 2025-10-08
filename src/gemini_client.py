import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_keywords(seed_keyword: str):
    """
    Generate a list of SEO keywords using Gemini API.
    Compatible with google-generativeai >=0.8.5.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Generate 50 SEO-optimized keywords related to the topic "{seed_keyword}".
        Return only the keywords as a clean, comma-separated list without numbering.
        """

        # ✅ Correct call format (list input required)
        response = model.generate_content([prompt])

        # Validate and clean response
        if not hasattr(response, "text") or not response.text:
            print(f"⚠️ No response text for seed: {seed_keyword}")
            return []

        # Parse comma-separated keywords
        keywords = [kw.strip() for kw in response.text.split(",") if kw.strip()]
        print(f"✅ Gemini returned {len(keywords)} keywords.")
        return keywords

    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return []

def generate_intent_gemini(keyword: str) -> str:
    """
    Use Gemini to predict the search intent of a keyword.
    Returns one of: Informational, Navigational, Transactional
    """
    try:
        prompt = f"""
        Determine the search intent category of the keyword below.
        Choose one: Informational, Navigational, Transactional.

        Keyword: "{keyword}"

        Answer format: Just the intent name.
        """
        response = genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
        text = response.text.strip().lower()

        if "informational" in text:
            return "📘 Informational"
        elif "navigational" in text:
            return "🧭 Navigational"
        elif "transactional" in text:
            return "💼 Transactional"
        else:
            return "📘 Informational"
    except Exception as e:
        print(f"⚠️ Gemini intent error: {e}")
        return "📘 Informational"
