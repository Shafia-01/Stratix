import random
import time
from dotenv import load_dotenv
from src.gemini_client import safe_gemini_call
from src.seo_api_client import get_keyword_metrics

load_dotenv()

def run_lightweight_agent(seed_keyword, max_keywords=5):
    """
    Lightweight version of the agent for faster performance.
    Generates fewer keywords and uses cached data when possible.
    """
    print(f"\nRunning Lightweight GemKey AI for: {seed_keyword}")
    try:
        keywords = generate_keywords_lightweight(seed_keyword, max_keywords)
        if not keywords or len(keywords) == 0:
            print(f"Gemini failed, using fallback keywords...")
            keywords = [f"{seed_keyword} tools", f"{seed_keyword} guide", f"best {seed_keyword}"]
        print(f"Generated {len(keywords)} keywords.")
        results = []
        
        # Process keywords with lightweight analysis
        for i, kw in enumerate(keywords[:max_keywords]):
            try:
                # Get basic metrics
                metrics = get_keyword_metrics(kw)
                if not metrics:
                    continue
                
                # Calculate simple score
                score = compute_lightweight_score(metrics)
                difficulty = classify_difficulty_lightweight(score)
                result = {
                    "seed": seed_keyword,
                    "keyword": kw,
                    "volume": metrics.get("volume", 0),
                    "competition": metrics.get("competition", 0.0),
                    "cpc": metrics.get("cpc", 0.0),
                    "trend": random.randint(20, 80),  # Simulated trend
                    "score": score,
                    "difficulty": difficulty,
                    "intent": "informational",  # Default intent
                    "competitors": []  # Empty for lightweight version
                }
                results.append(result)
                
                # Small delay to avoid rate limits
                time.sleep(0.2)
            except Exception as e:
                print(f"Error processing '{kw}': {e}")
                continue
        print(f"\n{len(results)} keywords processed successfully!")
        return results
    except Exception as e:
        print(f"Lightweight agent error: {e}")
        return []

def generate_keywords_lightweight(seed_keyword, max_keywords=5):
    """Generate keywords using Gemini with lightweight prompt."""
    prompt = f"""
    Generate {max_keywords} related keywords for "{seed_keyword}".
    Focus on high-value, searchable terms.
    Return as a simple list, one keyword per line.
    Do not use numbers, bullets, or special characters.
    """
    try:
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
        print(f"Keyword generation failed: {e}")
    
    # Fallback keywords
    return [
        f"{seed_keyword} tools",
        f"{seed_keyword} guide", 
        f"best {seed_keyword}",
        f"{seed_keyword} tips",
        f"{seed_keyword} software"
    ]

def compute_lightweight_score(metrics):
    """Compute a simple score for lightweight analysis."""
    volume = metrics.get("volume", 0)
    cpc = metrics.get("cpc", 0)
    competition = metrics.get("competition", 0)
    
    # Simple scoring formula
    score = (volume * 0.4 + cpc * 50 * 0.3 + (1 - competition) * 50 * 0.3) / 100
    return round(score, 2)

def classify_difficulty_lightweight(score):
    """Classify difficulty for lightweight analysis."""
    if score >= 0.7:
        return "Easy"
    elif score >= 0.4:
        return "Medium"
    else:
        return "Hard"
