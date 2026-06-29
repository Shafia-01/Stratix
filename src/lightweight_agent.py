import time
from dotenv import load_dotenv
from src.gemini_client import safe_gemini_call
from src.seo_api_client import get_keyword_metrics
from src.data_quality import DataSource
from src.scoring import compute_score, classify_difficulty
from src.logger_config import get_logger

load_dotenv()
logger = get_logger(__name__)

from pydantic import ValidationError
from src.schemas import KeywordFinding

def run_lightweight_agent(seed_keyword, max_keywords=5):
    """
    Lightweight version of the agent for faster performance.
    Generates fewer keywords and uses cached data when possible.
    """
    logger.info(f"Running Lightweight Keylytics for: {seed_keyword}")
    try:
        keywords = generate_keywords_lightweight(seed_keyword, max_keywords)
        if not keywords or len(keywords) == 0:
            logger.warning("Gemini failed, using fallback keywords...")
            keywords = [f"{seed_keyword} tools", f"{seed_keyword} guide", f"best {seed_keyword}"]
        logger.info(f"Generated {len(keywords)} keywords.")
        results = []

        # Process keywords with lightweight analysis
        for i, kw in enumerate(keywords[:max_keywords]):
            try:
                # Get basic metrics
                metrics = get_keyword_metrics(kw)
                if not metrics:
                    continue

                # Calculate simple score using unified scoring module
                opportunity = compute_score(metrics, mode="lightweight")
                score = opportunity.score
                difficulty = classify_difficulty(opportunity, mode="lightweight")
                try:
                    result = KeywordFinding(
                        seed=seed_keyword,
                        keyword=kw,
                        volume=float(metrics.get("volume", 0)),
                        competition=metrics.get("competition"),
                        cpc=metrics.get("cpc"),
                        trend=None,
                        score=score,
                        difficulty=difficulty,
                        intent="informational",  # Default intent
                        competitors=[],  # Empty for lightweight version
                        data_source=metrics.get("data_source", DataSource.UNAVAILABLE.value),
                        trend_data_source=DataSource.UNAVAILABLE.value
                    )
                    results.append(result)
                except ValidationError as ve:
                    logger.warning(f"Validation failed (lightweight) for keyword '{kw}': {ve}")
                    continue

                # Small delay to avoid rate limits
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Error processing '{kw}': {e}")
                continue
        logger.info(f"{len(results)} keywords processed successfully!")
        return results
    except Exception:
        logger.exception("Lightweight agent error occurred")
        return []

from src.prompt_safety import build_safe_prompt, cap_text_length

def generate_keywords_lightweight(seed_keyword, max_keywords=5):
    """Generate keywords using Gemini with lightweight prompt."""
    seed_keyword = cap_text_length(seed_keyword, 100)
    prompt_template = """
    Generate {max_keywords} related keywords for "{seed_keyword}".
    Focus on high-value, searchable terms.
    Return as a simple list, one keyword per line.
    Do not use numbers, bullets, or special characters.
    """
    try:
        # Use safe_gemini_call
        prompt = build_safe_prompt(prompt_template, max_keywords=max_keywords, seed_keyword=seed_keyword)
        response = safe_gemini_call(prompt, temperature=0.7)
        if response:
            # Clean the response to remove numbers, bullets, and special characters
            keywords = []
            for line in response.split('\n'):
                line = line.strip()
                if line:
                    # Remove common prefixes and clean the line
                    for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '-', '*', '•']:
                        if line.startswith(prefix):
                            line = line[len(prefix):].strip()
                            break
                    # Only add if it looks like a keyword (not empty and reasonable length)
                    if line and len(line) > 2 and len(line) < 100:
                        keywords.append(line)
            return keywords[:max_keywords]
    except Exception as e:
        logger.error(f"Keyword generation failed: {e}")

    # Fallback keywords
    return [
        f"{seed_keyword} tools",
        f"{seed_keyword} guide",
        f"best {seed_keyword}",
        f"{seed_keyword} tips",
        f"{seed_keyword} software"
    ]
