import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_keywords(seed_keyword: str):
    """Generate up to 50 keyword ideas using the Gemini 2.5 Flash model."""
    try:
        # use a model you actually have access to
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        prompt = (
            f"You are an SEO specialist. "
            f"Generate 50 keyword ideas related to '{seed_keyword}' "
            f"that have high search volume and low competition. "
            f"Return only a comma-separated list of keywords."
        )

        resp = model.generate_content(prompt)
        text = getattr(resp, "text", "")
        if not text:
            print("⚠️ No text output from Gemini.")
            return []

        keywords = [k.strip() for k in text.split(",") if k.strip()]
        print(f"✅ Gemini returned {len(keywords)} keywords.")
        return keywords[:50]

    except Exception as e:
        print("❌ Gemini API error:", e)
        return []
