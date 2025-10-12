# gemini_client.py
import google.generativeai as genai
import os
import time
import random
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "learnlm-2.0-flash-experimental"
]

def safe_gemini_call(prompt, temperature=0.7):
    """Try multiple Gemini models until one succeeds."""
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            result = model.generate_content(prompt)
            if hasattr(result, "text") and result.text:
                print(f"Using {model_name}")
                return result.text.strip()
            else:
                print(f"No text response from {model_name}")
                continue
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                print(f"{model_name} quota hit. Trying next model...")
                time.sleep(random.uniform(2, 5))
                continue
            elif "safety" in error_str.lower() or "blocked" in error_str.lower():
                print(f"{model_name} blocked by safety filters. Trying next model...")
                time.sleep(random.uniform(1, 3))
                continue
            else:
                print(f"{model_name} failed: {error_str}")
                continue
    print("All Gemini models failed or quota exceeded.")
    return None

def generate_keywords(seed_keyword):
    """Generate SEO keywords using Gemini with automatic fallback."""
    prompt = f"""
    Generate 50 high-quality SEO keywords related to: '{seed_keyword}'.
    Return only keywords, comma-separated. Avoid duplicates.
    """
    response = safe_gemini_call(prompt)
    if not response:
        print("Gemini failed to return keywords.")
        return []

    keywords = [kw.strip() for kw in response.split(",") if kw.strip()]
    print(f"Gemini returned {len(keywords)} keywords.")
    return keywords
