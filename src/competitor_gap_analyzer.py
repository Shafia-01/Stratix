import os
import requests
from dotenv import load_dotenv
from src.competitor_client import get_competitor_data
from src.gemini_client import safe_gemini_call

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def analyze_competitor_keyword_gap(seed_keyword, top_competitors=3):
    """
    Analyze competitor keyword gaps and opportunities.
    Expected Output: Missing keywords, traffic potential, competitor rank
    """
    print(f"[GAP_ANALYSIS] Analyzing keyword gaps for: {seed_keyword}")
    
    # Step 1: Get competitor domains for the seed keyword
    competitors_data = get_competitor_data(seed_keyword, num_results=top_competitors)
    if not competitors_data:
        return {"error": "No competitor data found"}
    competitor_domains = [comp["domain"] for comp in competitors_data]
    print(f"[GAP_ANALYSIS] Found competitors: {competitor_domains}")
    
    # Step 2: Generate related keywords for gap analysis
    related_keywords = generate_related_keywords_for_gap(seed_keyword)
    
    # Step 3: Analyze each competitor's ranking for related keywords
    gap_analysis = {}
    for keyword in related_keywords[:10]:
        keyword_gaps = analyze_keyword_ranking_gaps(keyword, competitor_domains)
        if keyword_gaps:
            gap_analysis[keyword] = keyword_gaps
    
    # Step 4: Identify opportunities
    opportunities = identify_keyword_opportunities(gap_analysis, seed_keyword)
    return {
        "seed_keyword": seed_keyword,
        "competitors": competitors_data,
        "gap_analysis": gap_analysis,
        "opportunities": opportunities,
        "summary": generate_gap_summary(opportunities)
    }

def generate_related_keywords_for_gap(seed_keyword):
    """Generate related keywords for gap analysis using Gemini."""
    prompt = f"""
    Generate 15 related keywords for "{seed_keyword}" that competitors might be targeting.
    Include variations like:
    - Long-tail versions
    - Question-based queries
    - Product/service variations
    - Industry-specific terms
    Return as a simple list, one keyword per line.
    """
    try:
        response = safe_gemini_call(prompt, temperature=0.7)
        if response:
            keywords = [kw.strip() for kw in response.split('\n') if kw.strip()]
            return keywords[:15]
    except Exception as e:
        print(f"[ERROR] Failed to generate related keywords: {e}")
    
    # Fallback keywords
    return [
        f"{seed_keyword} guide",
        f"{seed_keyword} tutorial", 
        f"{seed_keyword} review",
        f"{seed_keyword} comparison",
        f"{seed_keyword} best practices",
        f"{seed_keyword} tips",
        f"{seed_keyword} tools",
        f"{seed_keyword} software",
        f"{seed_keyword} solutions",
        f"{seed_keyword} services"
    ]

def analyze_keyword_ranking_gaps(keyword, competitor_domains):
    """Check where competitors rank for a specific keyword."""
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "q": keyword,
            "api_key": SERPAPI_KEY,
            "engine": "google",
            "num": "20"
        }
        response = requests.get(url, params=params, timeout=15)
        data = response.json()  
        organic_results = data.get("organic_results", [])
        competitor_rankings = {}
        for result in organic_results:
            domain = extract_domain_from_url(result.get("link", ""))
            if domain in competitor_domains:
                rank = organic_results.index(result) + 1
                competitor_rankings[domain] = {
                    "rank": rank,
                    "title": result.get("title"),
                    "url": result.get("link")
                }
        
        # If no competitors rank in top 20, it's a gap opportunity
        if not competitor_rankings:
            return {
                "opportunity_type": "keyword_gap",
                "competitor_rankings": {},
                "gap_score": 100,
                "traffic_potential": "high"
            }
        
        # Calculate gap score based on competitor performance
        avg_competitor_rank = sum(r["rank"] for r in competitor_rankings.values()) / len(competitor_rankings)
        gap_score = max(0, 100 - (avg_competitor_rank * 5))  # Lower rank = higher gap score
        return {
            "opportunity_type": "ranking_improvement",
            "competitor_rankings": competitor_rankings,
            "gap_score": round(gap_score, 1),
            "traffic_potential": "high" if gap_score > 70 else "medium" if gap_score > 40 else "low"
        }
    except Exception as e:
        print(f"[ERROR] Failed to analyze ranking gaps for '{keyword}': {e}")
        return None

def identify_keyword_opportunities(gap_analysis, seed_keyword):
    """Identify the best keyword opportunities based on gap analysis."""
    opportunities = []
    
    for keyword, analysis in gap_analysis.items():
        if analysis["gap_score"] > 60:  # High opportunity threshold
            opportunities.append({
                "keyword": keyword,
                "opportunity_type": analysis["opportunity_type"],
                "gap_score": analysis["gap_score"],
                "traffic_potential": analysis["traffic_potential"],
                "reasoning": generate_opportunity_reasoning(keyword, analysis)
            })
    
    # Sort by gap score (highest first)
    opportunities.sort(key=lambda x: x["gap_score"], reverse=True)
    return opportunities[:5]  # Top 5 opportunities

def generate_opportunity_reasoning(keyword, analysis):
    """Generate reasoning for why this keyword is an opportunity."""
    if analysis["opportunity_type"] == "keyword_gap":
        return f"No competitors currently rank in top 20 for '{keyword}' - clear opportunity to capture first-mover advantage."
    else:
        competitor_count = len(analysis["competitor_rankings"])
        avg_rank = sum(r["rank"] for r in analysis["competitor_rankings"].values()) / competitor_count
        return f"Competitors average rank {avg_rank:.1f} for '{keyword}' - opportunity to outrank them with better content."

def generate_gap_summary(opportunities):
    """Generate a summary of the gap analysis."""
    if not opportunities:
        return "No significant keyword gaps identified."
    high_potential = [opp for opp in opportunities if opp["traffic_potential"] == "high"]
    gap_opportunities = [opp for opp in opportunities if opp["opportunity_type"] == "keyword_gap"]
    summary = f"Found {len(opportunities)} keyword opportunities:\n"
    summary += f"- {len(high_potential)} high-traffic potential keywords\n"
    summary += f"- {len(gap_opportunities)} complete keyword gaps\n"
    if opportunities:
        summary += f"\nTop opportunity: '{opportunities[0]['keyword']}' (Gap Score: {opportunities[0]['gap_score']})"
    return summary

def extract_domain_from_url(url):
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return url

def get_missing_keywords_analysis(seed_keyword):
    """
    Get missing keywords that competitors are targeting but you're not.
    This is a simplified version focusing on semantic gaps.
    """
    prompt = f"""
    Analyze "{seed_keyword}" and identify 10 keywords that competitors might be targeting
    but are often overlooked. Focus on:
    - Semantic variations
    - Long-tail opportunities  
    - Question-based queries
    - Local variations
    - Industry jargon
    Return as a JSON list with each keyword having: keyword, opportunity_type, difficulty_estimate
    """
    try:
        response = safe_gemini_call(prompt, temperature=0.8)
        if response:
            # Try to parse JSON response
            import json
            try:
                keywords_data = json.loads(response)
                return keywords_data
            except:
                # Fallback: parse as text
                lines = response.split('\n')
                keywords = []
                for line in lines:
                    if line.strip() and not line.startswith('{') and not line.startswith('['):
                        keywords.append({"keyword": line.strip(), "opportunity_type": "semantic_gap", "difficulty_estimate": "medium"})
                return keywords[:10]
    except Exception as e:
        print(f"[ERROR] Failed to get missing keywords analysis: {e}")
    return []
