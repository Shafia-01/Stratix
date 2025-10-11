# topic_clusterer.py
import re
from collections import defaultdict
from dotenv import load_dotenv
from src.gemini_client import safe_gemini_call

load_dotenv()

def cluster_keywords_semantically(keywords_data):
    """
    Group keywords into meaningful semantic clusters.
    
    Expected Output: Groups like "Content Generation," "Ad Targeting," "Customer Support AI," etc.
    """
    print(f"[CLUSTERING] Clustering {len(keywords_data)} keywords semantically...")
    
    # Extract keywords from data
    keywords = [item["keyword"] if isinstance(item, dict) else str(item) for item in keywords_data]
    
    # Step 1: Use Gemini for semantic clustering
    clusters = perform_semantic_clustering(keywords)
    
    # Step 2: Enhance clusters with additional analysis
    enhanced_clusters = enhance_clusters_with_metrics(clusters, keywords_data)
    
    # Step 3: Generate cluster insights
    cluster_insights = generate_cluster_insights(enhanced_clusters)
    
    return {
        "total_keywords": len(keywords),
        "total_clusters": len(enhanced_clusters),
        "clusters": enhanced_clusters,
        "insights": cluster_insights,
        "summary": generate_clustering_summary(enhanced_clusters)
    }

def perform_semantic_clustering(keywords):
    """Use Gemini AI to perform semantic clustering of keywords."""
    # Limit to 50 keywords for better clustering
    keywords_sample = keywords[:50]
    
    prompt = f"""
    Analyze these keywords and group them into 3-8 semantic clusters based on meaning and intent:
    
    {chr(10).join(keywords_sample)}
    
    Return a JSON response with this structure:
    {{
        "clusters": [
            {{
                "cluster_name": "Descriptive cluster name",
                "description": "Brief description of what this cluster represents",
                "keywords": ["keyword1", "keyword2", "keyword3"],
                "primary_intent": "commercial|informational|transactional|navigational",
                "industry_focus": "main industry or use case"
            }}
        ]
    }}
    
    Make cluster names specific and actionable (e.g., "AI Content Generation Tools", "Fitness App Features", "SEO Analytics Software").
    """
    
    try:
        response = safe_gemini_call(prompt, temperature=0.3)
        if response:
            # Try to parse JSON response
            import json
            try:
                data = json.loads(response)
                return data.get("clusters", [])
            except json.JSONDecodeError:
                # Fallback: parse as text and create clusters
                return parse_text_clusters(response, keywords_sample)
    except Exception as e:
        print(f"[ERROR] Semantic clustering failed: {e}")
        # Suppress Unicode errors for Windows console
        import warnings
        warnings.filterwarnings("ignore", category=UnicodeWarning)
    
    # Fallback: rule-based clustering
    return rule_based_clustering(keywords_sample)

def parse_text_clusters(response, keywords):
    """Parse text response into cluster structure."""
    clusters = []
    lines = response.split('\n')
    current_cluster = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('Cluster:') or line.startswith('Group:'):
            if current_cluster:
                clusters.append(current_cluster)
            current_cluster = {
                "cluster_name": line.replace('Cluster:', '').replace('Group:', '').strip(),
                "description": "",
                "keywords": [],
                "primary_intent": "informational",
                "industry_focus": "general"
            }
        elif line.startswith('Keywords:') and current_cluster:
            keywords_text = line.replace('Keywords:', '').strip()
            current_cluster["keywords"] = [kw.strip() for kw in keywords_text.split(',')]
    
    if current_cluster:
        clusters.append(current_cluster)
    
    return clusters

def rule_based_clustering(keywords):
    """Fallback rule-based clustering."""
    clusters = defaultdict(list)
    
    # Define cluster patterns
    cluster_patterns = {
        "AI Tools & Software": ["ai tool", "software", "app", "platform", "system"],
        "Content & Marketing": ["content", "marketing", "seo", "blog", "social"],
        "Analytics & Data": ["analytics", "data", "report", "metric", "track"],
        "Business & Sales": ["business", "sales", "customer", "lead", "revenue"],
        "Technical & Development": ["api", "integration", "development", "code", "technical"],
        "User Experience": ["user", "interface", "design", "experience", "usability"]
    }
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        assigned = False
        
        for cluster_name, patterns in cluster_patterns.items():
            if any(pattern in keyword_lower for pattern in patterns):
                clusters[cluster_name].append(keyword)
                assigned = True
                break
        
        if not assigned:
            clusters["General"].append(keyword)
    
    # Convert to expected format
    result_clusters = []
    for cluster_name, keywords_list in clusters.items():
        if keywords_list:  # Only include non-empty clusters
            result_clusters.append({
                "cluster_name": cluster_name,
                "description": f"Keywords related to {cluster_name.lower()}",
                "keywords": keywords_list,
                "primary_intent": "informational",
                "industry_focus": "general"
            })
    
    return result_clusters

def enhance_clusters_with_metrics(clusters, keywords_data):
    """Enhance clusters with keyword metrics and insights."""
    enhanced_clusters = []
    
    for cluster in clusters:
        cluster_keywords = cluster["keywords"]
        
        # Find matching keywords in the original data
        matching_keywords = []
        for keyword in cluster_keywords:
            for data_item in keywords_data:
                if isinstance(data_item, dict) and data_item.get("keyword") == keyword:
                    matching_keywords.append(data_item)
                    break
        
        # Calculate cluster metrics
        metrics = calculate_cluster_metrics(matching_keywords)
        
        enhanced_cluster = {
            **cluster,
            "keyword_count": len(matching_keywords),
            "metrics": metrics,
            "top_keywords": get_top_keywords_by_score(matching_keywords, 3),
            "opportunity_score": calculate_opportunity_score(matching_keywords)
        }
        
        enhanced_clusters.append(enhanced_cluster)
    
    return enhanced_clusters

def calculate_cluster_metrics(keywords_data):
    """Calculate aggregated metrics for a cluster."""
    if not keywords_data:
        return {
            "avg_volume": 0,
            "avg_competition": 0,
            "avg_cpc": 0,
            "avg_score": 0,
            "total_volume": 0
        }
    
    total_volume = sum(kw.get("volume", 0) for kw in keywords_data)
    avg_volume = total_volume / len(keywords_data)
    avg_competition = sum(kw.get("competition", 0) for kw in keywords_data) / len(keywords_data)
    avg_cpc = sum(kw.get("cpc", 0) for kw in keywords_data) / len(keywords_data)
    avg_score = sum(kw.get("score", 0) for kw in keywords_data) / len(keywords_data)
    
    return {
        "avg_volume": round(avg_volume, 1),
        "avg_competition": round(avg_competition, 2),
        "avg_cpc": round(avg_cpc, 2),
        "avg_score": round(avg_score, 2),
        "total_volume": total_volume
    }

def get_top_keywords_by_score(keywords_data, limit=3):
    """Get top keywords by score within a cluster."""
    sorted_keywords = sorted(keywords_data, key=lambda x: x.get("score", 0), reverse=True)
    return [
        {
            "keyword": kw["keyword"],
            "score": kw.get("score", 0),
            "volume": kw.get("volume", 0)
        }
        for kw in sorted_keywords[:limit]
    ]

def calculate_opportunity_score(keywords_data):
    """Calculate opportunity score for a cluster."""
    if not keywords_data:
        return 0
    
    # Factors: high volume, low competition, good scores
    scores = []
    for kw in keywords_data:
        volume = kw.get("volume", 0)
        competition = kw.get("competition", 1)
        score = kw.get("score", 0)
        
        # Opportunity formula: volume * (1 - competition) * score
        opportunity = volume * (1 - competition) * score
        scores.append(opportunity)
    
    return round(sum(scores) / len(scores), 2)

def generate_cluster_insights(clusters):
    """Generate insights about the clusters."""
    insights = []
    
    # Sort clusters by opportunity score
    sorted_clusters = sorted(clusters, key=lambda x: x["opportunity_score"], reverse=True)
    
    # Top opportunity cluster
    if sorted_clusters:
        top_cluster = sorted_clusters[0]
        insights.append({
            "type": "top_opportunity",
            "title": f"Best Opportunity: {top_cluster['cluster_name']}",
            "description": f"This cluster has the highest opportunity score ({top_cluster['opportunity_score']}) with {top_cluster['keyword_count']} keywords averaging {top_cluster['metrics']['avg_volume']} monthly searches.",
            "recommendation": f"Focus content strategy on {top_cluster['cluster_name'].lower()} topics for maximum impact."
        })
    
    # High volume cluster
    high_volume_cluster = max(clusters, key=lambda x: x["metrics"]["total_volume"])
    if high_volume_cluster["metrics"]["total_volume"] > 0:
        insights.append({
            "type": "high_volume",
            "title": f"Highest Volume: {high_volume_cluster['cluster_name']}",
            "description": f"This cluster has the highest total search volume ({high_volume_cluster['metrics']['total_volume']:,}) across {high_volume_cluster['keyword_count']} keywords.",
            "recommendation": "Consider creating comprehensive content hubs for this high-volume topic cluster."
        })
    
    # Low competition opportunity
    low_comp_clusters = [c for c in clusters if c["metrics"]["avg_competition"] < 0.4]
    if low_comp_clusters:
        best_low_comp = max(low_comp_clusters, key=lambda x: x["metrics"]["avg_volume"])
        insights.append({
            "type": "low_competition",
            "title": f"Low Competition Opportunity: {best_low_comp['cluster_name']}",
            "description": f"This cluster has low competition ({best_low_comp['metrics']['avg_competition']:.2f}) with decent volume ({best_low_comp['metrics']['avg_volume']:.0f} avg searches).",
            "recommendation": "Easier to rank for these keywords - prioritize for quick wins."
        })
    
    return insights

def generate_clustering_summary(clusters):
    """Generate a summary of the clustering results."""
    total_keywords = sum(c["keyword_count"] for c in clusters)
    total_volume = sum(c["metrics"]["total_volume"] for c in clusters)
    
    summary = f"Clustered {total_keywords} keywords into {len(clusters)} semantic groups:\n"
    summary += f"Total search volume: {total_volume:,} monthly searches\n\n"
    
    # Top 3 clusters by opportunity
    top_clusters = sorted(clusters, key=lambda x: x["opportunity_score"], reverse=True)[:3]
    summary += "Top 3 opportunities:\n"
    
    for i, cluster in enumerate(top_clusters, 1):
        summary += f"{i}. {cluster['cluster_name']} (Score: {cluster['opportunity_score']}, Volume: {cluster['metrics']['total_volume']:,})\n"
    
    return summary

def get_semantic_keyword_variations(seed_keyword):
    """Get semantic variations of a keyword for clustering."""
    prompt = f"""
    Generate 20 semantic variations of "{seed_keyword}" including:
    - Synonyms and related terms
    - Long-tail versions
    - Question-based queries
    - Industry-specific terminology
    - User intent variations
    
    Return as a simple list, one keyword per line.
    """
    
    try:
        response = safe_gemini_call(prompt, temperature=0.7)
        if response:
            variations = [kw.strip() for kw in response.split('\n') if kw.strip()]
            return variations[:20]
    except Exception as e:
        print(f"[ERROR] Failed to generate semantic variations: {e}")
    
    return []
