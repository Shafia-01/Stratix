from src.gemini_client import generate_keywords
from src.seo_api_client import get_metrics
from src.scoring import compute_score
from src.db import save_keywords

def run_agent(seed_keyword):
    print(f"Running GemKey AI for: {seed_keyword}")
    keywords = generate_keywords(seed_keyword)
    results = []
    for kw in keywords[:50]:
        m = get_metrics(kw)
        score = compute_score(m["volume"], m["competition"], m["cpc"])
        results.append((seed_keyword, kw, m["volume"], m["competition"], m["cpc"], score))
    save_keywords(results)
    print(f"✅ {len(results)} keywords saved successfully!")
    return results
