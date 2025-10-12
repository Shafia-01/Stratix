# GemKey AI Setup Guide

## Quick Answer to Your Question

**You can enter ANY natural language prompts!** The app is designed to understand:
- "AI healthcare applications"
- "List opportunities missed by Grammarly in AI writing"
- "Show People Also Ask questions for AI image generator"
- "Find competitor gaps for project management software"

**You don't need exact wordings** - just describe what you want to analyze.

## Common Errors and Quick Fixes

### 1. "No data to cluster" / "Clustering failed"
**Cause:** Missing or invalid API keys
**Fix:** Set up your `.env` file (see below)

### 2. "No competitor data found"
**Cause:** Missing SerpApi key or API limits
**Fix:** Get SerpApi key and add to `.env`

### 3. "All Gemini models unavailable"
**Cause:** Missing Gemini API key or quota exceeded
**Fix:** Get Gemini API key and add to `.env`

## Step-by-Step Setup

### 1. Create API Keys

**Gemini API Key (Required):**
1. Go to: https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy the key

**SerpApi Key (Required for SERP/Competitor analysis):**
1. Go to: https://serpapi.com/
2. Sign up for free account
3. Get your API key from dashboard

### 2. Create .env File

Create a file named `.env` in your project root with:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
SERPAPI_KEY=your_serpapi_key_here
```

### 3. Test Your Setup

Run the test script:
```bash
python test_api.py
```

This will show you exactly what's working and what's not.

### 4. Restart the App

After adding API keys:
```bash
streamlit run app.py
```

## Troubleshooting

### If you see "API Configuration Issues":
- Check your `.env` file exists
- Verify API keys are correct
- Restart the app after changes

### If you see "API Connection Issues":
- Check your internet connection
- Verify API keys are valid
- Check your API account credits

### If analysis is slow:
- Use "Quick (5 keywords)" mode
- Try simpler keywords like "tools" or "software"
- Check your internet speed

## Example Prompts That Work

**Keyword Analysis:**
- "AI tools for students"
- "fitness apps"
- "project management software"

**Competitor Analysis:**
- "competitor gaps for Grammarly"
- "missed opportunities by Canva"
- "keyword gaps in AI writing tools"

**SERP Analysis:**
- "People Also Ask for AI image generator"
- "snippet optimization for project management"
- "content gaps in fitness apps"

**Topic Clustering:**
- "AI healthcare applications"
- "digital marketing tools"
- "productivity software"

**Trend Forecasting:**
- "AI trends 2025"
- "remote work tools"
- "sustainability apps"

## Performance Tips

1. **Start with Quick Mode** for fastest results
2. **Use simple keywords** first (avoid complex phrases)
3. **One analysis at a time** to avoid API limits
4. **Check API credits** regularly

## Still Having Issues?

1. Run `python test_api.py` to diagnose problems
2. Check the browser console for detailed errors
3. Try the simplest possible keywords first
4. Restart the application after any changes

The app is designed to be flexible with natural language - the main issue is usually API configuration, not your prompts!
