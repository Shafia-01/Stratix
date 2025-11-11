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

def generate_keywords(seed_keyword, max_keywords=50):
    """Generate SEO keywords using Gemini with automatic fallback."""
    prompt = f"""
    Generate {max_keywords} high-quality SEO keywords that are DIRECTLY RELATED to: '{seed_keyword}'.
    
    IMPORTANT: All keywords MUST be relevant to '{seed_keyword}'. Do not generate random or unrelated keywords.
    
    Include a mix of:
    - Short-tail keywords (1-2 words) related to '{seed_keyword}'
    - Long-tail keywords (3-5 words) related to '{seed_keyword}'
    - Question-based keywords about '{seed_keyword}'
    - Commercial intent keywords for '{seed_keyword}'
    - Informational keywords about '{seed_keyword}'
    
    Return only keywords, one per line or comma-separated. Avoid duplicates.
    Make sure ALL keywords are relevant to '{seed_keyword}' and generate at least {max_keywords} keywords.
    """
    response = safe_gemini_call(prompt)
    if not response:
        print("Gemini failed to return keywords.")
        return []
    
    # Parse keywords - handle both comma-separated and newline-separated
    keywords = []
    for line in response.split("\n"):
        if "," in line:
            keywords.extend([kw.strip() for kw in line.split(",") if kw.strip()])
        else:
            if line.strip() and not line.strip().startswith("#"):
                keywords.append(line.strip())
    
    # Also try comma-separated if newline didn't work well
    if len(keywords) < max_keywords:
        keywords_comma = [kw.strip() for kw in response.split(",") if kw.strip()]
        if len(keywords_comma) > len(keywords):
            keywords = keywords_comma
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw and kw.lower() not in seen:
            seen.add(kw.lower())
            unique_keywords.append(kw)
    
    # If we still don't have enough, generate variations
    if len(unique_keywords) < max_keywords:
        variations = [
            f"{seed_keyword} guide", f"{seed_keyword} tips", f"best {seed_keyword}",
            f"{seed_keyword} tutorial", f"how to {seed_keyword}", f"{seed_keyword} review",
            f"{seed_keyword} comparison", f"{seed_keyword} tools", f"{seed_keyword} software",
            f"{seed_keyword} services", f"buy {seed_keyword}", f"{seed_keyword} price",
            f"{seed_keyword} examples", f"{seed_keyword} benefits", f"{seed_keyword} features",
            f"{seed_keyword} alternatives", f"{seed_keyword} vs", f"free {seed_keyword}",
            f"{seed_keyword} online", f"{seed_keyword} 2024", f"{seed_keyword} 2025"
        ]
        for var in variations:
            if var.lower() not in seen and len(unique_keywords) < max_keywords:
                seen.add(var.lower())
                unique_keywords.append(var)
    
    print(f"Gemini returned {len(unique_keywords)} keywords (requested {max_keywords}).")
    return unique_keywords[:max_keywords]
