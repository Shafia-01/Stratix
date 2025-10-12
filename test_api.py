# test_api.py - Quick API Test Script
import os
from dotenv import load_dotenv

def test_api_keys():
    """Test if API keys are properly configured."""
    load_dotenv()
    
    print("Testing API Configuration...")
    print("=" * 50)
    
    # Test Gemini API Key
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print("OK GEMINI_API_KEY: Found")
        print(f"   Key starts with: {gemini_key[:10]}...")
    else:
        print("ERROR GEMINI_API_KEY: NOT FOUND")
        print("   Get from: https://makersuite.google.com/app/apikey")
    
    # Test SerpApi Key
    serpapi_key = os.getenv("SERPAPI_KEY")
    if serpapi_key:
        print("OK SERPAPI_KEY: Found")
        print(f"   Key starts with: {serpapi_key[:10]}...")
    else:
        print("ERROR SERPAPI_KEY: NOT FOUND")
        print("   Get from: https://serpapi.com/")
    
    print("=" * 50)
    
    if not gemini_key:
        print("CRITICAL: GEMINI_API_KEY is required for keyword generation")
        print("   Create a .env file with: GEMINI_API_KEY=your_key_here")
    
    if not serpapi_key:
        print("WARNING: SERPAPI_KEY is required for SERP and Competitor analysis")
        print("   Create a .env file with: SERPAPI_KEY=your_key_here")
    
    return bool(gemini_key and serpapi_key)

def test_gemini_connection():
    """Test Gemini API connection."""
    try:
        import google.generativeai as genai
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            print("ERROR Cannot test Gemini - no API key found")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        result = model.generate_content("Say 'Hello' if you can hear me.")
        
        if hasattr(result, "text"):
            print("OK Gemini API: Working")
            print(f"   Response: {result.text.strip()}")
            return True
        else:
            print("ERROR Gemini API: No response")
            return False
            
    except Exception as e:
        print(f"ERROR Gemini API: Error - {str(e)}")
        return False

def test_serpapi_connection():
    """Test SerpApi connection."""
    try:
        import requests
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv("SERPAPI_KEY")
        
        if not api_key:
            print("ERROR Cannot test SerpApi - no API key found")
            return False
        
        url = "https://serpapi.com/search.json"
        params = {
            "q": "test",
            "api_key": api_key,
            "engine": "google",
            "num": "1"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Check for specific error messages
        if "error" in data:
            error_msg = data["error"]
            print(f"ERROR SerpApi: API Error - {error_msg}")
            if "Invalid API key" in error_msg:
                print("   Solution: Check your SERPAPI_KEY in .env file")
            elif "quota" in error_msg.lower():
                print("   Solution: Check your SerpApi account credits")
            return False
        
        if "search_information" in data:
            print("OK SerpApi: Working")
            print(f"   Results: {data['search_information'].get('total_results', 'N/A')}")
            return True
        else:
            print("ERROR SerpApi: Invalid response format")
            print(f"   Response keys: {list(data.keys())}")
            return False
            
    except Exception as e:
        print(f"ERROR SerpApi: Error - {str(e)}")
        return False

if __name__ == "__main__":
    print("GemKey AI API Test")
    print("=" * 50)
    
    # Test configuration
    config_ok = test_api_keys()
    
    if config_ok:
        print("\nTesting API Connections...")
        print("=" * 50)
        
        # Test Gemini
        gemini_ok = test_gemini_connection()
        
        # Test SerpApi
        serpapi_ok = test_serpapi_connection()
        
        print("\nTest Summary:")
        print("=" * 50)
        print(f"Configuration: {'OK' if config_ok else 'Issues'}")
        print(f"Gemini API: {'OK' if gemini_ok else 'Issues'}")
        print(f"SerpApi: {'OK' if serpapi_ok else 'Issues'}")
        
        if gemini_ok and serpapi_ok:
            print("\nAll APIs working! Your app should work properly.")
        else:
            print("\nSome APIs have issues. Check the errors above.")
    else:
        print("\nPlease fix API configuration first!")
        print("   Create a .env file with your API keys")
