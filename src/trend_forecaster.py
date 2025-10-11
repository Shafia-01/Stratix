# trend_forecaster.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
from dotenv import load_dotenv
from src.trends_client import get_trend_score
from src.gemini_client import safe_gemini_call

load_dotenv()
warnings.filterwarnings("ignore", category=FutureWarning)

def analyze_trend_forecasting(keywords_data):
    """
    Analyze and forecast keyword trends with seasonal patterns.
    
    Expected Output: Trend graphs, growth %, seasonality insights
    """
    print(f"[FORECASTING] Analyzing trends for {len(keywords_data)} keywords...")
    
    # Step 1: Get historical trend data
    historical_data = get_historical_trends(keywords_data)
    
    # Step 2: Perform trend analysis
    trend_analysis = perform_trend_analysis(historical_data)
    
    # Step 3: Generate forecasts
    forecasts = generate_trend_forecasts(trend_analysis)
    
    # Step 4: Identify seasonal patterns
    seasonal_analysis = analyze_seasonal_patterns(historical_data)
    
    # Step 5: Generate insights
    insights = generate_trend_insights(forecasts, seasonal_analysis)
    
    return {
        "historical_data": historical_data,
        "trend_analysis": trend_analysis,
        "forecasts": forecasts,
        "seasonal_analysis": seasonal_analysis,
        "insights": insights,
        "summary": generate_forecast_summary(forecasts, seasonal_analysis)
    }

def get_historical_trends(keywords_data):
    """Get historical trend data for keywords."""
    historical_data = {}
    
    for item in keywords_data:
        keyword = item["keyword"] if isinstance(item, dict) else str(item)
        
        # Get current trend score
        current_trend = get_trend_score(keyword)
        
        # Simulate historical data (in real implementation, you'd use Google Trends API with historical data)
        historical_scores = simulate_historical_trends(keyword, current_trend)
        
        historical_data[keyword] = {
            "current_trend": current_trend,
            "historical_scores": historical_scores,
            "volume": item.get("volume", 0) if isinstance(item, dict) else 0,
            "competition": item.get("competition", 0) if isinstance(item, dict) else 0
        }
    
    return historical_data

def simulate_historical_trends(keyword, current_trend):
    """Simulate historical trend data (replace with real Google Trends API calls)."""
    # Generate 12 months of historical data
    months = 12
    base_trend = current_trend or 50
    
    # Add some realistic variation and seasonality
    historical_scores = []
    for month in range(months):
        # Add seasonal variation based on keyword type
        seasonal_factor = get_seasonal_factor(keyword, month)
        
        # Add random variation
        random_variation = np.random.normal(0, 10)
        
        # Calculate trend score for this month
        trend_score = max(0, min(100, base_trend + seasonal_factor + random_variation))
        historical_scores.append({
            "month": month + 1,
            "score": round(trend_score, 1),
            "date": (datetime.now() - timedelta(days=30*(months-month))).strftime("%Y-%m")
        })
    
    return historical_scores

def get_seasonal_factor(keyword, month):
    """Get seasonal factor based on keyword type and month."""
    keyword_lower = keyword.lower()
    
    # Define seasonal patterns
    seasonal_patterns = {
        "fitness": [10, 15, 20, 15, 10, 5, -5, 0, 5, 10, 15, 20],  # Peak in summer/winter
        "christmas": [-20, -20, -20, -20, -20, -20, -20, -20, -20, -20, 30, 40],
        "back to school": [-20, -20, 40, 30, -20, -20, -20, -20, -20, -20, -20, -20],
        "tax": [-20, -20, -20, 40, 30, -20, -20, -20, -20, -20, -20, -20],
        "travel": [5, 10, 15, 20, 25, 30, 35, 30, 20, 10, 5, 0],
        "ai": [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22],  # Growing trend
        "software": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # Steady growth
    }
    
    # Find matching pattern
    for pattern_key, pattern_values in seasonal_patterns.items():
        if pattern_key in keyword_lower:
            return pattern_values[month % 12]
    
    # Default: slight growth trend
    return month * 1.5

def perform_trend_analysis(historical_data):
    """Analyze trends in the historical data."""
    trend_analysis = {}
    
    for keyword, data in historical_data.items():
        scores = [point["score"] for point in data["historical_scores"]]
        
        # Calculate trend metrics
        trend_metrics = calculate_trend_metrics(scores)
        
        # Determine trend direction
        trend_direction = determine_trend_direction(trend_metrics)
        
        trend_analysis[keyword] = {
            "metrics": trend_metrics,
            "direction": trend_direction,
            "volatility": calculate_volatility(scores),
            "peak_month": find_peak_month(data["historical_scores"]),
            "growth_rate": calculate_growth_rate(scores)
        }
    
    return trend_analysis

def calculate_trend_metrics(scores):
    """Calculate various trend metrics."""
    if len(scores) < 2:
        return {"slope": 0, "r_squared": 0, "avg_change": 0}
    
    # Linear regression to find slope
    x = np.arange(len(scores))
    y = np.array(scores)
    
    # Calculate slope (trend)
    slope = np.polyfit(x, y, 1)[0]
    
    # Calculate R-squared (trend strength)
    correlation_matrix = np.corrcoef(x, y)
    r_squared = correlation_matrix[0, 1] ** 2
    
    # Calculate average change
    changes = np.diff(scores)
    avg_change = np.mean(changes)
    
    return {
        "slope": round(slope, 3),
        "r_squared": round(r_squared, 3),
        "avg_change": round(avg_change, 3)
    }

def determine_trend_direction(metrics):
    """Determine the overall trend direction."""
    slope = metrics["slope"]
    r_squared = metrics["r_squared"]
    
    if r_squared > 0.7:  # Strong correlation
        if slope > 1:
            return "strong_growth"
        elif slope < -1:
            return "strong_decline"
        elif slope > 0.2:
            return "moderate_growth"
        elif slope < -0.2:
            return "moderate_decline"
    
    return "stable"

def calculate_volatility(scores):
    """Calculate volatility (standard deviation)."""
    return round(np.std(scores), 2)

def find_peak_month(historical_scores):
    """Find the month with the highest score."""
    peak_point = max(historical_scores, key=lambda x: x["score"])
    return peak_point["month"]

def calculate_growth_rate(scores):
    """Calculate compound growth rate."""
    if len(scores) < 2:
        return 0
    
    first_score = scores[0]
    last_score = scores[-1]
    
    if first_score == 0:
        return 0
    
    growth_rate = ((last_score - first_score) / first_score) * 100
    return round(growth_rate, 1)

def generate_trend_forecasts(trend_analysis):
    """Generate forecasts for the next 6 months."""
    forecasts = {}
    
    for keyword, analysis in trend_analysis.items():
        current_trend = analysis.get("current_trend", 50)
        slope = analysis["metrics"]["slope"]
        growth_rate = analysis["growth_rate"]
        
        # Generate 6-month forecast
        forecast_scores = []
        for month in range(1, 7):
            # Apply trend continuation with some uncertainty
            forecast_score = current_trend + (slope * month) + np.random.normal(0, 5)
            forecast_score = max(0, min(100, forecast_score))
            
            forecast_scores.append({
                "month": month,
                "score": round(forecast_score, 1),
                "confidence": calculate_forecast_confidence(analysis, month)
            })
        
        forecasts[keyword] = {
            "forecast_scores": forecast_scores,
            "predicted_growth": growth_rate,
            "trend_direction": analysis["direction"],
            "recommendation": generate_trend_recommendation(analysis)
        }
    
    return forecasts

def calculate_forecast_confidence(analysis, month):
    """Calculate confidence level for forecast."""
    r_squared = analysis["metrics"]["r_squared"]
    volatility = analysis["volatility"]
    
    # Higher R-squared and lower volatility = higher confidence
    base_confidence = r_squared * 100
    volatility_penalty = min(volatility * 5, 30)
    
    # Confidence decreases with time
    time_decay = month * 5
    
    confidence = max(10, base_confidence - volatility_penalty - time_decay)
    return round(confidence, 1)

def generate_trend_recommendation(analysis):
    """Generate recommendation based on trend analysis."""
    direction = analysis["direction"]
    growth_rate = analysis["growth_rate"]
    
    if direction == "strong_growth":
        return "High priority - strong upward trend indicates growing market interest"
    elif direction == "strong_decline":
        return "Low priority - declining trend suggests decreasing market interest"
    elif direction == "moderate_growth":
        return "Medium priority - steady growth indicates stable opportunity"
    elif growth_rate > 20:
        return "High priority - significant growth rate indicates emerging opportunity"
    elif growth_rate < -20:
        return "Low priority - declining growth rate suggests market saturation"
    else:
        return "Monitor - stable trend with moderate growth potential"

def analyze_seasonal_patterns(historical_data):
    """Analyze seasonal patterns in the data."""
    seasonal_analysis = {}
    
    for keyword, data in historical_data.items():
        scores = data["historical_scores"]
        
        # Calculate seasonal factors
        seasonal_factors = calculate_seasonal_factors(scores)
        
        # Identify peak and low seasons
        peak_season = max(seasonal_factors, key=lambda x: x["factor"])["month"]
        low_season = min(seasonal_factors, key=lambda x: x["factor"])["month"]
        
        seasonal_analysis[keyword] = {
            "seasonal_factors": seasonal_factors,
            "peak_season": peak_season,
            "low_season": low_season,
            "seasonality_strength": calculate_seasonality_strength(seasonal_factors),
            "recommendation": generate_seasonal_recommendation(peak_season, low_season)
        }
    
    return seasonal_analysis

def calculate_seasonal_factors(historical_scores):
    """Calculate seasonal factors for each month."""
    monthly_scores = {}
    
    # Group scores by month
    for point in historical_scores:
        month = point["month"]
        score = point["score"]
        
        if month not in monthly_scores:
            monthly_scores[month] = []
        monthly_scores[month].append(score)
    
    # Calculate average for each month
    seasonal_factors = []
    overall_avg = np.mean([point["score"] for point in historical_scores])
    
    for month in range(1, 13):
        if month in monthly_scores:
            month_avg = np.mean(monthly_scores[month])
            factor = month_avg - overall_avg
            seasonal_factors.append({
                "month": month,
                "factor": round(factor, 2),
                "avg_score": round(month_avg, 1)
            })
    
    return seasonal_factors

def calculate_seasonality_strength(seasonal_factors):
    """Calculate how strong the seasonality is."""
    if not seasonal_factors:
        return 0
    
    factors = [sf["factor"] for sf in seasonal_factors]
    return round(np.std(factors), 2)

def generate_seasonal_recommendation(peak_season, low_season):
    """Generate seasonal recommendation."""
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    peak_month = month_names.get(peak_season, f"Month {peak_season}")
    low_month = month_names.get(low_season, f"Month {low_season}")
    
    return f"Peak interest in {peak_month}, lowest in {low_month}. Plan content calendar accordingly."

def generate_trend_insights(forecasts, seasonal_analysis):
    """Generate insights from trend analysis."""
    insights = []
    
    # Find trending keywords
    trending_keywords = []
    declining_keywords = []
    
    for keyword, forecast in forecasts.items():
        if forecast["trend_direction"] in ["strong_growth", "moderate_growth"]:
            trending_keywords.append({
                "keyword": keyword,
                "growth": forecast["predicted_growth"],
                "direction": forecast["trend_direction"]
            })
        elif forecast["trend_direction"] in ["strong_decline", "moderate_decline"]:
            declining_keywords.append({
                "keyword": keyword,
                "growth": forecast["predicted_growth"],
                "direction": forecast["trend_direction"]
            })
    
    # Sort by growth rate
    trending_keywords.sort(key=lambda x: x["growth"], reverse=True)
    declining_keywords.sort(key=lambda x: x["growth"])
    
    if trending_keywords:
        insights.append({
            "type": "trending_up",
            "title": "Rising Trends",
            "keywords": trending_keywords[:3],
            "description": f"These keywords are showing upward trends with growth rates up to {trending_keywords[0]['growth']}%",
            "recommendation": "Prioritize content creation for trending keywords to capitalize on growing interest."
        })
    
    if declining_keywords:
        insights.append({
            "type": "trending_down",
            "title": "Declining Trends",
            "keywords": declining_keywords[:3],
            "description": f"These keywords are declining with growth rates as low as {declining_keywords[0]['growth']}%",
            "recommendation": "Consider reducing investment in declining keywords and reallocating resources to trending topics."
        })
    
    # Seasonal insights
    high_seasonality = []
    for keyword, analysis in seasonal_analysis.items():
        if analysis["seasonality_strength"] > 15:  # High seasonality threshold
            high_seasonality.append({
                "keyword": keyword,
                "peak_season": analysis["peak_season"],
                "seasonality_strength": analysis["seasonality_strength"]
            })
    
    if high_seasonality:
        insights.append({
            "type": "seasonal",
            "title": "High Seasonality Keywords",
            "keywords": high_seasonality[:3],
            "description": f"These keywords show strong seasonal patterns with variability up to {max(k['seasonality_strength'] for k in high_seasonality)}",
            "recommendation": "Plan content calendar around seasonal peaks for maximum impact."
        })
    
    return insights

def generate_forecast_summary(forecasts, seasonal_analysis):
    """Generate a summary of the forecasting analysis."""
    total_keywords = len(forecasts)
    
    # Count trend directions
    trend_counts = {}
    for forecast in forecasts.values():
        direction = forecast["trend_direction"]
        trend_counts[direction] = trend_counts.get(direction, 0) + 1
    
    # Count seasonal keywords
    seasonal_count = sum(1 for analysis in seasonal_analysis.values() 
                        if analysis["seasonality_strength"] > 15)
    
    summary = f"Trend Analysis Summary:\n"
    summary += f"Analyzed {total_keywords} keywords\n"
    summary += f"Seasonal keywords: {seasonal_count}\n\n"
    
    summary += "Trend Distribution:\n"
    for direction, count in trend_counts.items():
        percentage = (count / total_keywords) * 100
        summary += f"- {direction.replace('_', ' ').title()}: {count} ({percentage:.1f}%)\n"
    
    return summary

def get_trend_visualization_data(historical_data, forecasts):
    """Prepare data for trend visualization."""
    visualization_data = {}
    
    for keyword in historical_data.keys():
        # Historical data
        historical = historical_data[keyword]["historical_scores"]
        
        # Forecast data
        forecast = forecasts[keyword]["forecast_scores"]
        
        # Combine for visualization
        all_data = []
        
        # Add historical data
        for point in historical:
            all_data.append({
                "period": f"Historical-{point['month']}",
                "score": point["score"],
                "type": "historical"
            })
        
        # Add forecast data
        for point in forecast:
            all_data.append({
                "period": f"Forecast-{point['month']}",
                "score": point["score"],
                "type": "forecast",
                "confidence": point["confidence"]
            })
        
        visualization_data[keyword] = all_data
    
    return visualization_data
