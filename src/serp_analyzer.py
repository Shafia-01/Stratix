import os
import requests
import time
import re
from collections import defaultdict
from dotenv import load_dotenv
from src.gemini_client import safe_gemini_call

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def analyze_serp_opportunities(keyword, num_results=10):
    """
    Analyze SERP opportunities and snippet optimization chances.
    Expected Output: Snippet titles, PAA questions, top-ranking pages
    """
    print(f"[SERP_ANALYSIS] Analyzing SERP opportunities for: {keyword}")
    # Step 1: Get SERP data
    serp_data = get_serp_data(keyword, num_results)
    if not serp_data:
        return {"error": "Failed to fetch SERP data"}
    # Step 2: Analyze snippet opportunities
    snippet_analysis = analyze_snippet_opportunities(serp_data, keyword)
    # Step 3: Extract PAA (People Also Ask) questions
    paa_questions = extract_paa_questions(serp_data)
    # Step 4: Analyze top-ranking pages
    ranking_analysis = analyze_top_ranking_pages(serp_data)
    # Step 5: Identify content gaps
    content_gaps = identify_content_gaps(serp_data, keyword)
    # Step 6: Generate optimization suggestions
    optimization_suggestions = generate_optimization_suggestions(
        snippet_analysis, paa_questions, ranking_analysis, content_gaps
    )
    return {
        "keyword": keyword,
        "serp_data": serp_data,
        "snippet_analysis": snippet_analysis,
        "paa_questions": paa_questions,
        "ranking_analysis": ranking_analysis,
        "content_gaps": content_gaps,
        "optimization_suggestions": optimization_suggestions,
        "summary": generate_serp_summary(snippet_analysis, paa_questions, content_gaps)
    }

def get_serp_data(keyword, num_results=10):
    """Get comprehensive SERP data using SerpApi."""
    if not SERPAPI_KEY:
        print(f"[ERROR] SERPAPI_KEY not found. Please add it to your .env file.")
        return None
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "q": keyword,
            "api_key": SERPAPI_KEY,
            "engine": "google",
            "num": num_results,
            "gl": "us",  # Country
            "hl": "en"   # Language
        }
        print(f"[SERP_API] Fetching data for: {keyword}")
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"[ERROR] SERP API returned status {response.status_code}: {response.text}")
            return None
        data = response.json()
        # Check for API errors
        if "error" in data:
            print(f"[ERROR] SERP API error: {data['error']}")
            return None
        # Extract relevant SERP features
        serp_data = {
            "organic_results": data.get("organic_results", []),
            "people_also_ask": data.get("people_also_ask", []),
            "related_searches": data.get("related_searches", []),
            "search_information": data.get("search_information", {}),
            "ads": data.get("ads", []),
            "knowledge_graph": data.get("knowledge_graph", {}),
            "featured_snippet": data.get("featured_snippet", {})
        }
        print(f"[SERP_API] Successfully fetched {len(serp_data['organic_results'])} organic results")
        time.sleep(1)  # Rate limiting
        return serp_data
    except requests.exceptions.Timeout:
        print(f"[ERROR] SERP API timeout for '{keyword}'")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] SERP API request failed for '{keyword}': {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to fetch SERP data for '{keyword}': {e}")
        return None

def analyze_snippet_opportunities(serp_data, keyword=""):
    """Analyze snippet optimization opportunities."""
    organic_results = serp_data.get("organic_results", [])
    featured_snippet = serp_data.get("featured_snippet", {})
    snippet_analysis = {
        "has_featured_snippet": bool(featured_snippet),
        "snippet_opportunities": [],
        "title_optimization": [],
        "meta_description_analysis": []
    }
    
    # Analyze featured snippet opportunity
    if not featured_snippet:
        snippet_analysis["snippet_opportunities"].append({
            "type": "featured_snippet",
            "opportunity": "No featured snippet present",
            "recommendation": "Create content that directly answers the main question with a clear, concise answer",
            "priority": "high"
        })
    
    # Analyze title tags
    for i, result in enumerate(organic_results[:5]):
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        title_analysis = analyze_title_tag(title, keyword)
        meta_analysis = analyze_meta_description(snippet)
        snippet_analysis["title_optimization"].append({
            "rank": i + 1,
            "title": title,
            "analysis": title_analysis,
            "opportunity_score": calculate_title_opportunity_score(title_analysis)
        })
        snippet_analysis["meta_description_analysis"].append({
            "rank": i + 1,
            "snippet": snippet,
            "analysis": meta_analysis,
            "opportunity_score": calculate_meta_opportunity_score(meta_analysis)
        })
    return snippet_analysis

def analyze_title_tag(title, keyword):
    """Analyze title tag optimization."""
    title_lower = title.lower()
    keyword_lower = keyword.lower()
    analysis = {
        "length": len(title),
        "contains_keyword": keyword_lower in title_lower,
        "keyword_position": title_lower.find(keyword_lower) if keyword_lower in title_lower else -1,
        "has_power_words": analyze_power_words(title),
        "has_numbers": bool(re.search(r'\d+', title)),
        "has_emotional_triggers": analyze_emotional_triggers(title)
    }
    # Calculate optimization score
    score = 0
    if 30 <= analysis["length"] <= 60:
        score += 20  # Optimal length
    if analysis["contains_keyword"]:
        score += 25  # Contains keyword
    if analysis["keyword_position"] <= 30:
        score += 15  # Keyword in first 30 chars
    if analysis["has_power_words"]:
        score += 15  # Has power words
    if analysis["has_numbers"]:
        score += 10  # Has numbers
    if analysis["has_emotional_triggers"]:
        score += 15  # Has emotional triggers
    analysis["optimization_score"] = min(100, score)
    return analysis

def analyze_meta_description(snippet):
    """Analyze meta description optimization."""
    analysis = {
        "length": len(snippet),
        "contains_cta": analyze_cta_presence(snippet),
        "readability": analyze_readability(snippet),
        "has_benefits": analyze_benefits(snippet),
        "has_features": analyze_features(snippet)
    }
    # Calculate optimization score
    score = 0
    if 120 <= analysis["length"] <= 160:
        score += 25  # Optimal length
    if analysis["contains_cta"]:
        score += 20  # Has call-to-action
    if analysis["readability"] > 0.7:
        score += 20  # Good readability
    if analysis["has_benefits"]:
        score += 20  # Mentions benefits
    if analysis["has_features"]:
        score += 15  # Mentions features
    analysis["optimization_score"] = min(100, score)
    return analysis

def analyze_power_words(title):
    """Check for power words in title."""
    power_words = [
        "best", "ultimate", "complete", "guide", "secret", "proven", "expert",
        "free", "new", "exclusive", "limited", "guaranteed", "results", "tips"
    ]
    title_lower = title.lower()
    return any(word in title_lower for word in power_words)

def analyze_emotional_triggers(title):
    """Check for emotional triggers in title."""
    emotional_words = [
        "amazing", "incredible", "shocking", "surprising", "unbelievable",
        "essential", "critical", "important", "vital", "must-have"
    ]
    title_lower = title.lower()
    return any(word in title_lower for word in emotional_words)

def analyze_cta_presence(snippet):
    """Check for call-to-action in snippet."""
    cta_words = ["learn", "discover", "find out", "get", "download", "try", "start", "click"]
    snippet_lower = snippet.lower()
    return any(cta in snippet_lower for cta in cta_words)

def analyze_readability(snippet):
    """Simple readability analysis."""
    # Count sentences and words
    sentences = len(re.split(r'[.!?]+', snippet))
    words = len(snippet.split())
    if sentences == 0:
        return 0
    avg_words_per_sentence = words / sentences
    # Optimal is 15-20 words per sentence
    if 15 <= avg_words_per_sentence <= 20:
        return 1.0
    elif 10 <= avg_words_per_sentence <= 25:
        return 0.8
    else:
        return 0.6

def analyze_benefits(snippet):
    """Check if snippet mentions benefits."""
    benefit_words = ["benefit", "advantage", "improve", "increase", "save", "boost", "enhance"]
    snippet_lower = snippet.lower()
    return any(word in snippet_lower for word in benefit_words)

def analyze_features(snippet):
    """Check if snippet mentions features."""
    feature_words = ["feature", "include", "offer", "provide", "capability", "function"]
    snippet_lower = snippet.lower()
    return any(word in snippet_lower for word in feature_words)

def calculate_title_opportunity_score(analysis):
    """Calculate opportunity score for title optimization."""
    base_score = 100 - analysis["optimization_score"]
    # Bonus for high-ranking positions with poor optimization
    if analysis["optimization_score"] < 70:
        base_score += 20
    return min(100, base_score)

def calculate_meta_opportunity_score(analysis):
    """Calculate opportunity score for meta description optimization."""
    base_score = 100 - analysis["optimization_score"]
    # Bonus for poor optimization
    if analysis["optimization_score"] < 60:
        base_score += 15
    return min(100, base_score)

def extract_paa_questions(serp_data):
    """Extract People Also Ask questions."""
    paa_data = serp_data.get("people_also_ask", [])
    paa_analysis = {
        "questions": [],
        "opportunities": [],
        "content_ideas": []
    }
    for paa_item in paa_data:
        question = paa_item.get("question", "")
        snippet = paa_item.get("snippet", "")
        if question and snippet:
            paa_analysis["questions"].append({
                "question": question,
                "snippet": snippet,
                "word_count": len(snippet.split()),
                "opportunity_type": classify_paa_opportunity(snippet),
                "content_idea": generate_content_idea_from_paa(question, snippet)
            })
    # Identify opportunities
    paa_analysis["opportunities"] = identify_paa_opportunities(paa_analysis["questions"])
    paa_analysis["content_ideas"] = generate_content_ideas_from_paa(paa_analysis["questions"])
    return paa_analysis

def classify_paa_opportunity(snippet):
    """Classify the type of opportunity from PAA snippet."""
    snippet_lower = snippet.lower()
    if len(snippet.split()) < 50:
        return "quick_answer"
    elif any(word in snippet_lower for word in ["how to", "step", "guide", "tutorial"]):
        return "how_to_guide"
    elif any(word in snippet_lower for word in ["what is", "definition", "meaning"]):
        return "definition_content"
    elif any(word in snippet_lower for word in ["best", "top", "compare"]):
        return "comparison_content"
    else:
        return "informational_content"

def generate_content_idea_from_paa(question, snippet):
    """Generate content idea from PAA question and snippet."""
    prompt = f"""
    Based on this People Also Ask question and snippet, suggest a content idea:
    Question: {question}
    Snippet: {snippet}
    Suggest a specific content piece that could rank for this question.
    Return just the content idea title.
    """
    try:
        response = safe_gemini_call(prompt, temperature=0.7)
        if response:
            return response.strip()
    except Exception as e:
        print(f"[ERROR] Failed to generate content idea: {e}")
    # Fallback
    return f"Complete Guide to {question.replace('?', '').title()}"

def identify_paa_opportunities(questions):
    """Identify opportunities from PAA questions."""
    opportunities = []
    # Group by opportunity type
    opportunity_types = defaultdict(list)
    for q in questions:
        opportunity_types[q["opportunity_type"]].append(q)
    for opp_type, questions_list in opportunity_types.items():
        opportunities.append({
            "type": opp_type,
            "count": len(questions_list),
            "top_questions": [q["question"] for q in questions_list[:3]],
            "recommendation": generate_opportunity_recommendation(opp_type, len(questions_list))
        })
    return opportunities

def generate_opportunity_recommendation(opp_type, count):
    """Generate recommendation based on opportunity type and count."""
    recommendations = {
        "quick_answer": f"Create FAQ section with {count} quick answers to capture featured snippets",
        "how_to_guide": f"Develop comprehensive how-to guide covering {count} related questions",
        "definition_content": f"Create glossary or definition page covering {count} key terms",
        "comparison_content": f"Build comparison resource addressing {count} comparison questions",
        "informational_content": f"Develop informational hub with {count} detailed explanations"
    }
    return recommendations.get(opp_type, f"Create content addressing {count} related questions")

def generate_content_ideas_from_paa(questions):
    """Generate content ideas from PAA questions."""
    content_ideas = []
    # Group questions by topic similarity
    topic_groups = group_questions_by_topic(questions)
    for topic, questions_list in topic_groups.items():
        content_ideas.append({
            "topic": topic,
            "question_count": len(questions_list),
            "content_title": generate_content_title(topic, questions_list),
            "content_type": determine_content_type(questions_list),
            "priority": calculate_content_priority(questions_list)
        })
    # Sort by priority
    content_ideas.sort(key=lambda x: x["priority"], reverse=True)
    return content_ideas[:5]  # Top 5 content ideas

def group_questions_by_topic(questions):
    """Group questions by topic similarity."""
    topic_groups = defaultdict(list)
    for question in questions:
        # Simple keyword-based grouping
        question_lower = question["question"].lower()
        if any(word in question_lower for word in ["how to", "how do", "how can"]):
            topic_groups["How-to Guides"].append(question)
        elif any(word in question_lower for word in ["what is", "what are", "what does"]):
            topic_groups["Definitions & Explanations"].append(question)
        elif any(word in question_lower for word in ["best", "top", "compare"]):
            topic_groups["Comparisons & Reviews"].append(question)
        elif any(word in question_lower for word in ["why", "when", "where"]):
            topic_groups["Context & Background"].append(question)
        else:
            topic_groups["General Information"].append(question)
    return dict(topic_groups)

def generate_content_title(topic, questions_list):
    """Generate content title based on topic and questions."""
    if len(questions_list) == 1:
        return questions_list[0]["question"].replace("?", "").title()
    return f"Complete Guide to {topic}: Answering {len(questions_list)} Key Questions"

def determine_content_type(questions_list):
    """Determine the best content type for the questions."""
    question_text = " ".join([q["question"] for q in questions_list]).lower()
    if any(word in question_text for word in ["step", "how to", "process"]):
        return "Step-by-step Guide"
    elif any(word in question_text for word in ["compare", "vs", "difference"]):
        return "Comparison Article"
    elif any(word in question_text for word in ["best", "top", "recommend"]):
        return "Review/Ranking Article"
    else:
        return "Informational Article"

def calculate_content_priority(questions_list):
    """Calculate priority score for content ideas."""
    # Factors: number of questions, question complexity, opportunity types
    base_score = len(questions_list) * 10
    # Bonus for high-value opportunity types
    for question in questions_list:
        if question["opportunity_type"] in ["how_to_guide", "comparison_content"]:
            base_score += 5
        elif question["opportunity_type"] == "quick_answer":
            base_score += 3
    return base_score

def analyze_top_ranking_pages(serp_data):
    """Analyze top-ranking pages for insights."""
    organic_results = serp_data.get("organic_results", [])
    
    ranking_analysis = {
        "top_domains": [],
        "content_patterns": [],
        "ranking_factors": [],
        "competition_analysis": []
    }
    # Analyze top 5 results
    for i, result in enumerate(organic_results[:5]):
        domain = extract_domain_from_url(result.get("link", ""))
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        # Domain analysis
        ranking_analysis["top_domains"].append({
            "rank": i + 1,
            "domain": domain,
            "title": title,
            "domain_authority": estimate_domain_authority(domain),
            "title_analysis": analyze_title_tag(title, ""),
            "snippet_length": len(snippet)
        })
        # Content pattern analysis
        content_pattern = analyze_content_pattern(title, snippet)
        ranking_analysis["content_patterns"].append({
            "rank": i + 1,
            "pattern": content_pattern,
            "title_type": classify_title_type(title),
            "snippet_type": classify_snippet_type(snippet)
        })
    # Competition analysis
    ranking_analysis["competition_analysis"] = analyze_competition_level(ranking_analysis["top_domains"])
    return ranking_analysis

def extract_domain_from_url(url):
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return url

def estimate_domain_authority(domain):
    """Estimate domain authority (simplified)."""
    # This is a simplified estimation - in real implementation, you'd use actual DA data
    high_authority_domains = [
        "google.com", "youtube.com", "wikipedia.org", "amazon.com", "facebook.com",
        "twitter.com", "linkedin.com", "reddit.com", "stackoverflow.com", "github.com"
    ]
    if any(high_domain in domain for high_domain in high_authority_domains):
        return "high"
    elif len(domain.split('.')) == 2 and domain not in high_authority_domains:
        return "medium"
    else:
        return "low"

def analyze_content_pattern(title, snippet):
    """Analyze content pattern from title and snippet."""
    title_lower = title.lower()
    snippet_lower = snippet.lower()
    patterns = []
    if any(word in title_lower for word in ["guide", "tutorial", "how to"]):
        patterns.append("guide")
    if any(word in title_lower for word in ["review", "comparison", "vs"]):
        patterns.append("review")
    if any(word in title_lower for word in ["best", "top", "recommend"]):
        patterns.append("ranking")
    if any(word in snippet_lower for word in ["step", "process", "method"]):
        patterns.append("step-by-step")
    return patterns if patterns else ["informational"]

def classify_title_type(title):
    """Classify title type."""
    title_lower = title.lower()
    if any(word in title_lower for word in ["how to", "guide", "tutorial"]):
        return "how-to"
    elif any(word in title_lower for word in ["best", "top", "review"]):
        return "ranking"
    elif any(word in title_lower for word in ["what is", "definition"]):
        return "definition"
    else:
        return "informational"

def classify_snippet_type(snippet):
    """Classify snippet type."""
    snippet_lower = snippet.lower()
    if len(snippet.split()) < 50:
        return "brief"
    elif any(word in snippet_lower for word in ["step", "first", "then", "finally"]):
        return "step-by-step"
    elif any(word in snippet_lower for word in ["feature", "include", "offer"]):
        return "feature-list"
    else:
        return "descriptive"

def analyze_competition_level(top_domains):
    """Analyze competition level based on top domains."""
    high_authority_count = sum(1 for domain in top_domains if domain["domain_authority"] == "high")
    medium_authority_count = sum(1 for domain in top_domains if domain["domain_authority"] == "medium")
    if high_authority_count >= 3:
        return {
            "level": "high",
            "description": "High competition with established authority domains",
            "recommendation": "Focus on long-tail keywords and niche content"
        }
    elif medium_authority_count >= 3:
        return {
            "level": "medium",
            "description": "Medium competition with mixed domain authority",
            "recommendation": "Good opportunity with quality content and SEO optimization"
        }
    else:
        return {
            "level": "low",
            "description": "Low competition with mostly new or low-authority domains",
            "recommendation": "Excellent opportunity - easier to rank with good content"
        }

def identify_content_gaps(serp_data, keyword):
    """Identify content gaps in SERP results."""
    organic_results = serp_data.get("organic_results", [])
    featured_snippet = serp_data.get("featured_snippet", {})
    content_gaps = {
        "missing_content_types": [],
        "content_angle_opportunities": [],
        "format_opportunities": []
    }
    # Analyze content types present
    present_content_types = set()
    for result in organic_results:
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "")
        if any(word in title for word in ["guide", "tutorial"]):
            present_content_types.add("how-to")
        elif any(word in title for word in ["review", "comparison"]):
            present_content_types.add("review")
        elif any(word in title for word in ["best", "top"]):
            present_content_types.add("ranking")
        elif any(word in title for word in ["what is", "definition"]):
            present_content_types.add("definition")
        else:
            present_content_types.add("informational")
    # Identify missing content types
    all_content_types = {"how-to", "review", "ranking", "definition", "case-study", "infographic", "video"}
    missing_types = all_content_types - present_content_types
    content_gaps["missing_content_types"] = [
        {
            "type": content_type,
            "opportunity": f"No {content_type.replace('-', ' ')} content found in top results",
            "recommendation": f"Create {content_type.replace('-', ' ')} content to fill this gap"
        }
        for content_type in missing_types
    ]
    # Identify format opportunities
    if not featured_snippet:
        content_gaps["format_opportunities"].append({
            "format": "featured_snippet",
            "opportunity": "No featured snippet present",
            "recommendation": "Create content optimized for featured snippets"
        })
    # Check for video results
    has_video = any("youtube.com" in result.get("link", "") for result in organic_results)
    if not has_video:
        content_gaps["format_opportunities"].append({
            "format": "video",
            "opportunity": "No video content in top results",
            "recommendation": "Create video content for this keyword"
        })
    return content_gaps

def generate_optimization_suggestions(snippet_analysis, paa_questions, ranking_analysis, content_gaps):
    """Generate comprehensive optimization suggestions."""
    suggestions = []
    # Snippet optimization suggestions
    if snippet_analysis["snippet_opportunities"]:
        suggestions.extend(snippet_analysis["snippet_opportunities"])
    # Title optimization suggestions
    for title_opt in snippet_analysis["title_optimization"]:
        if title_opt["opportunity_score"] > 70:
            suggestions.append({
                "type": "title_optimization",
                "opportunity": f"Optimize title at rank {title_opt['rank']}",
                "recommendation": f"Current title: '{title_opt['title'][:50]}...' - Improve keyword placement and add power words",
                "priority": "medium"
            })
    # PAA optimization suggestions
    if paa_questions["opportunities"]:
        for opp in paa_questions["opportunities"]:
            suggestions.append({
                "type": "paa_optimization",
                "opportunity": f"Target {opp['type']} questions",
                "recommendation": opp["recommendation"],
                "priority": "high"
            })
    # Content gap suggestions
    for gap in content_gaps["missing_content_types"]:
        suggestions.append({
            "type": "content_gap",
            "opportunity": gap["opportunity"],
            "recommendation": gap["recommendation"],
            "priority": "medium"
        })
    # Sort by priority
    priority_order = {"high": 3, "medium": 2, "low": 1}
    suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 1), reverse=True)
    return suggestions[:10]  # Top 10 suggestions

def generate_serp_summary(snippet_analysis, paa_questions, content_gaps):
    """Generate summary of SERP analysis."""
    summary = f"SERP Analysis Summary:\n"
    # Snippet opportunities
    snippet_opps = len(snippet_analysis["snippet_opportunities"])
    summary += f"Snippet opportunities: {snippet_opps}\n"    
    # PAA questions
    paa_count = len(paa_questions["questions"])
    summary += f"PAA questions found: {paa_count}\n"    
    # Content gaps
    gap_count = len(content_gaps["missing_content_types"])
    summary += f"Content gaps identified: {gap_count}\n"   
    # Top opportunities
    if snippet_analysis["snippet_opportunities"]:
        top_opp = snippet_analysis["snippet_opportunities"][0]
        summary += f"\nTop opportunity: {top_opp['opportunity']}\n"
        summary += f"Recommendation: {top_opp['recommendation']}\n"  
    return summary
