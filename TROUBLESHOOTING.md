# GemKey AI Troubleshooting Guide

## Common Issues and Solutions

### 1. Chat Assistant Not Working
**Symptoms:** Chat responses are generic or not helpful
**Solutions:**
- Check if `GEMINI_API_KEY` is set in `.env` file
- Verify your Gemini API key is valid and has credits
- Try simpler queries first

### 2. Competitor Analysis Errors
**Symptoms:** "No competitor data found" or timeout errors
**Solutions:**
- Ensure `SERPAPI_KEY` is configured in `.env` file
- Check your SerpApi account credits
- Try simpler keywords (avoid complex phrases)
- Use shorter keywords for faster processing

### 3. SERP Analysis Issues
**Symptoms:** Analysis fails or shows limited data
**Solutions:**
- Verify `SERPAPI_KEY` is valid and active
- Try different keywords (some may have limited SERP data)
- Check your internet connection
- Use "Quick" mode for faster results

### 4. Topic Clustering Errors
**Symptoms:** "max() iterable argument is empty" error
**Solutions:**
- Ensure keyword generation is working first
- Try different seed keywords
- Check `GEMINI_API_KEY` configuration
- Use simpler, more common keywords

### 5. Slow Performance
**Symptoms:** Analysis takes too long or times out
**Solutions:**
- Use "Quick (5 keywords)" mode for faster results
- Check your internet connection speed
- Ensure API keys are properly configured
- Try one analysis at a time
- Clear browser cache and restart the app

### 6. Database Connection Issues
**Symptoms:** "Database disconnected" or search history not loading
**Solutions:**
- MySQL is optional - the app works with cache files
- Check MySQL server is running
- Verify database credentials in `.env`
- The app will automatically use cache files if database fails

## Performance Optimization Tips

### Quick Mode Usage
- Use "Quick (5 keywords)" for fastest results
- Standard mode (15 keywords) for balanced performance
- Full mode (30 keywords) only when needed

### API Configuration
```bash
# Create .env file with:
GEMINI_API_KEY=your_gemini_api_key
SERPAPI_KEY=your_serpapi_key
```

### Best Practices
1. **Start Simple:** Use basic keywords first
2. **One at a Time:** Don't run multiple analyses simultaneously
3. **Cache Results:** Results are cached during your session
4. **Check Credits:** Monitor your API usage and credits

## Error Messages and Solutions

### "API error. Please check your GEMINI_API_KEY"
- Get API key from: https://makersuite.google.com/app/apikey
- Add to `.env` file: `GEMINI_API_KEY=your_key_here`
- Restart the application

### "API error. Please check your SERPAPI_KEY"
- Get API key from: https://serpapi.com/
- Add to `.env` file: `SERPAPI_KEY=your_key_here`
- Restart the application

### "Analysis timed out"
- Try "Quick" mode instead
- Use simpler keywords
- Check your internet connection
- Wait a few minutes and try again

### "No keywords found"
- Try different seed keywords
- Use more common terms
- Check if your Gemini API key is working
- Try the lightweight fallback keywords

## Getting Help

If you continue to experience issues:

1. **Check the browser console** for detailed error messages
2. **Verify your .env file** has all required API keys
3. **Test with simple keywords** like "tools" or "software"
4. **Restart the application** after making changes
5. **Check your API credits** and account status

## Performance Benchmarks

Expected performance with proper configuration:
- **Quick Mode:** 10-30 seconds
- **Standard Mode:** 30-60 seconds  
- **Full Mode:** 60-120 seconds
- **Chat Responses:** 2-5 seconds
- **Clustering:** 15-45 seconds
- **Trend Analysis:** 20-60 seconds

If your performance is significantly slower, check your internet connection and API key configuration.
