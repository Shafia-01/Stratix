from google import genai
import os
import time
import random
from dotenv import load_dotenv
from src.logger_config import get_logger

logger = get_logger(__name__)

load_dotenv()
client = genai.Client()

GEMINI_MODELS = [
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-2.5-flash"
]

def safe_gemini_call(prompt, temperature=0.7):
    """Try multiple Gemini models until one succeeds."""
    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": temperature}
            )
            if response.text:
                logger.info(f"Using {model_name}")
                return response.text.strip()
            else:
                logger.warning(f"No text response from {model_name}")
                continue
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                logger.warning(f"{model_name} quota hit. Trying next model...")
                time.sleep(random.uniform(2, 5))
                continue
            elif "safety" in error_str.lower() or "blocked" in error_str.lower():
                logger.warning(f"{model_name} blocked by safety filters. Trying next model...")
                time.sleep(random.uniform(1, 3))
                continue
            else:
                logger.error(f"{model_name} failed: {error_str}", exc_info=True)
                continue
    logger.error("All Gemini models failed or quota exceeded.")
    return None

from src.prompt_safety import build_safe_prompt, cap_text_length

def generate_keywords(seed_keyword, max_keywords=50):
    """Generate SEO keywords using Gemini with automatic fallback."""
    seed_keyword = cap_text_length(seed_keyword, 100)
    prompt_template = """
    Generate {max_keywords} high-quality SEO keywords that are DIRECTLY RELATED to: {seed_keyword}.

    IMPORTANT: All keywords MUST be relevant to the seed keyword. Do not generate random or unrelated keywords.

    Include a mix of:
    - Short-tail keywords (1-2 words) related to the seed keyword
    - Long-tail keywords (3-5 words) related to the seed keyword
    - Question-based keywords about the seed keyword
    - Commercial intent keywords for the seed keyword
    - Informational keywords about the seed keyword

    Return only keywords, one per line or comma-separated. Avoid duplicates.
    Make sure ALL keywords are relevant to the seed keyword and generate at least {max_keywords} keywords.
    """
    prompt = build_safe_prompt(prompt_template, max_keywords=max_keywords, seed_keyword=seed_keyword)
    response = safe_gemini_call(prompt)
    if not response:
        logger.warning("Gemini failed to return keywords.")
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

    logger.info(f"Gemini returned {len(unique_keywords)} keywords (requested {max_keywords}).")
    return unique_keywords[:max_keywords]
