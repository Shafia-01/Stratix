import streamlit as st
import os
import time
import random
from datetime import datetime
from dotenv import load_dotenv

def lazy_imports():
    """Import heavy modules only when needed."""
    import google.generativeai as genai
    import pandas as pd
    import json
    import plotly.express as px
    import plotly.graph_objects as go
    return genai, pd, json, px, go
genai, pd, json, px, go = lazy_imports()

load_dotenv()

st.set_page_config(page_title="GemKey AI", page_icon="🔑", layout="wide", initial_sidebar_state="expanded")

@st.cache_data(ttl=3600)
def initialize_session_state():
    """Initialize session state variables."""
    return {
        "current_page": "home",
        "keyword_results": [],
        "competitor_results": None,
        "cluster_results": None,
        "trend_results": None,
        "serp_results": None,
        "search_history": [],
        "daily_requests": 0,
        "total_keywords": 0,
        "opportunities": 0
    }

session_defaults = initialize_session_state()
for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODELS = ["gemini-2.0-flash", "gemini-flash-latest", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "learnlm-2.0-flash-experimental"]
@st.cache_data(ttl=1800)
def cached_run_lightweight_agent(keyword, limit):
    from src.lightweight_agent import run_lightweight_agent
    return run_lightweight_agent(keyword, limit)
@st.cache_data(ttl=3600)
def cached_run_agent(keyword, limit):
    from src.agent import run_agent
    return run_agent(keyword, limit)
@st.cache_data(ttl=1800)
def cached_analyze_competitor_gap(keyword):
    from src.competitor_gap_analyzer import analyze_competitor_keyword_gap
    return analyze_competitor_keyword_gap(keyword)
@st.cache_data(ttl=1800)
def cached_analyze_serp_opportunities(keyword):
    from src.serp_analyzer import analyze_serp_opportunities
    return analyze_serp_opportunities(keyword)
@st.cache_data(ttl=1800)
def cached_cluster_keywords_semantically(keywords):
    from src.topic_clusterer import cluster_keywords_semantically
    return cluster_keywords_semantically(keywords)
@st.cache_data(ttl=1800)
def cached_analyze_trend_forecasting(keywords):
    from src.trend_forecaster import analyze_trend_forecasting
    return analyze_trend_forecasting(keywords)

@st.cache_data(ttl=3600)
def safe_gemini_call(prompt, temperature=0.7):
    """Try multiple Gemini models until one succeeds."""
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            result = model.generate_content(prompt)
            if hasattr(result, "text"):
                print(f"✅ Using {model_name}")
                return result.text.strip()
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"⚠️ {model_name} quota hit. Trying next...")
                time.sleep(random.uniform(1, 3))
                continue
            else:
                print(f"❌ {model_name} failed: {e}")
                continue
    return "⚠️ All Gemini models are currently unavailable. Try again later."

@st.cache_data(ttl=300)
def cached_fetch_past_results(limit=50):
    """Cached version of fetch_past_results for better performance."""
    from src.db_client import fetch_past_results
    return fetch_past_results(limit)
@st.cache_data(ttl=1800)
def cached_verify_database_schema():
    """Cached version of database schema verification."""
    from src.db_client import verify_database_schema
    return verify_database_schema()
@st.cache_data(ttl=300)
def cached_check_api_status():
    """Cached version of API status check."""
    return check_api_status()
@st.cache_data(ttl=300)
def cached_save_to_db(data):
    """Cached version of save_to_db function."""
    from src.db_client import save_to_db
    return save_to_db(data)
@st.cache_data(ttl=3600)
def get_performance_stats():
    """Get performance statistics for monitoring."""
    return {
        "cache_hits": st.session_state.get("cache_hits", 0),
        "page_loads": st.session_state.get("page_loads", 0),
        "last_optimization": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
def get_color_theme():
    """Get light theme colors."""
    return {
        "primary": "#051B4A",          
        "primary_hover": "#CADEFF",    
        "primary_light": "#B5D1FF",    
        "secondary": "#6EE7B7",        
        "secondary_hover": "#34D399",  
        "bg_main": "#FFF7ED",          
        "bg_card": "#FFFFFF",          
        "bg_sidebar": "#FFC7CF",       
        "text_primary": "#000000",     
        "text_secondary": "#232527",   
        "text_white": "#FFFFFF",
        "border_light": "#000000",
        "border_dark": "#051B4A",
        "success": "#4ADE80",          
        "warning": "#FACC15",          
        "error": "#F87171",            
        "info": "#60A5FA"              
    }

def get_optimized_css():
    """Get optimized CSS with light theme colors."""
    colors = get_color_theme()
    return f"""
    <style>
    /* Import Cambria font and Material Icons */
    @import url('https://fonts.googleapis.com/css2?family=Cambria:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');   
    /* Global Styles */
    .main {{
        background-color: {colors['bg_main']} !important;
        font-family: 'Cambria', serif !important;
    }}
    
    /* Force theme colors on main containers */
    .stApp {{
        background-color: {colors['bg_main']} !important;
    }}
    
    div[data-testid="stAppViewContainer"] {{
        background-color: {colors['bg_main']} !important;
    }}    
    /* Apply Cambria only to specific text elements, NOT buttons or icons */
    body, p, div.stMarkdown, div.stText, h1, h2, h3, h4, h5, h6, 
    label, input, textarea, select, option {{
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
    }}    
    /* DO NOT apply Cambria to buttons, icons, or navigation */
    button, [data-testid="stSidebarNav"], [data-testid="stSidebarNav"] * {{
        font-family: inherit !important;
    }}   
    /* Apply Cambria only to text content, NOT interactive elements */
    .stMarkdown, .stText, .stTitle, .stHeader, .stSubheader {{
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
    }} 
    /* DO NOT override buttons, inputs, or interactive elements */
    .stButton, .stButton > button, .stSelectbox, .stTextInput, .stTextArea {{
        font-family: inherit !important;
    }}
    /* Apply Cambria only to text content in sidebar */
    .stSidebar .stMarkdown, .stSidebar .stText {{
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
    }}
    /* Sidebar Styling */
    .css-1d391kg {{
        background-color: {colors['bg_sidebar']} !important;
        border-right: 2px solid {colors['border_light']};
    }}
    
    /* Force sidebar background */
    section[data-testid="stSidebar"] {{
        background-color: {colors['bg_sidebar']} !important;
    }}
    
    div[data-testid="stSidebar"] {{
        background-color: {colors['bg_sidebar']} !important;
    }}    
    .css-1d391kg .css-1v0mbdj {{
        color: {colors['text_primary']};
        font-family: 'Cambria', serif;
        font-weight: bold;
    }}    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {colors['bg_card']};
        border-radius: 8px;
        padding: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}    
    .stTabs [data-baseweb="tab"] {{
        background-color: {colors['bg_main']};
        border-radius: 6px;
        padding: 8px 16px;
        font-family: 'Cambria', serif;
        font-weight: 500;
        color: {colors['text_secondary']};
        transition: all 0.3s ease;
    }}    
    .stTabs [aria-selected="true"] {{
        background-color: {colors['primary']};
        color: {colors['text_white']};
        box-shadow: 0 2px 8px {colors['primary']}30;
    }}    
    /* Card Styling */
    .metric-card {{
        background-color: {colors['bg_card']};
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid {colors['border_light']};
        margin: 10px 0;
    }}    
    .metric-title {{
        font-family: 'Cambria', serif;
        font-size: 14px;
        font-weight: 500;
        color: {colors['text_secondary']};
        margin-bottom: 8px;
    }}    
    .metric-value {{
        font-family: 'Cambria', serif;
        font-size: 24px;
        font-weight: 600;
        color: {colors['primary']};
    }}
    /* Chat Styling */
    .chat-container {{
        background-color: {colors['bg_card']};
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid {colors['border_light']};
        margin: 10px 0;
    }}    
    .chat-message {{
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
        font-family: 'Cambria', serif;
    }}    
    .chat-user {{
        background-color: {colors['primary']};
        color: {colors['text_white']};
        margin-left: 20%;
    }}    
    .chat-assistant {{
        background-color: {colors['bg_main']};
        color: {colors['text_primary']};
        margin-right: 20%;
    }}    
    /* Button Styling */
    .stButton > button {{
        background-color: {colors['primary']};
        color: {colors['text_white']};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-family: 'Cambria', serif;
        font-weight: 500;
        transition: all 0.3s ease;
    }}    
    .stButton > button:hover {{
        background-color: {colors['primary_hover']};
        box-shadow: 0 4px 8px {colors['primary']}30;
    }}    
    /* Chart Styling */
    .plotly-chart {{
        background-color: {colors['bg_card']};
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid {colors['border_light']};
    }}    
    /* Table Styling */
    .stDataFrame {{
        background-color: {colors['bg_card']};
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid {colors['border_light']};
    }}    
    /* Header Styling */
    .main-header {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['primary_hover']} 100%);
        color: {colors['text_white']};
        padding: 30px;
        border-radius: 16px;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 8px 16px {colors['primary']}30;
    }}    
    .main-header h1 {{
        font-family: 'Cambria', serif;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}    
    .main-header p {{
        font-family: 'Cambria', serif;
        font-size: 1.1rem;
        margin: 10px 0 0 0;
        opacity: 0.9;
    }}    
    /* Sidebar Header */
    .sidebar-header {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['primary_hover']} 100%);
        color: {colors['text_white']};
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
    }}    
    .sidebar-header h2 {{
        font-family: 'Cambria', serif;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }}    
    /* Success/Error Messages */
    .stSuccess {{
        background-color: #D1FAE5;
        border: 1px solid #10B981;
        color: #065F46;
        border-radius: 8px;
    }}    
    .stError {{
        background-color: #FEE2E2;
        border: 1px solid #EF4444;
        color: #991B1B;
        border-radius: 8px;
    }}    
    .stWarning {{
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        color: #92400E;
        border-radius: 8px;
    }}    
    /* Loading Spinner */
    .stSpinner {{
        color: #2563EB;
    }}    
    /* Download Button */
    .download-btn {{
        background-color: #FFC7CF;
        color: #000000;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
    }}    
    .download-btn:hover {{
        background-color: #FFB3C1;
        box-shadow: 0 4px 8px rgba(255, 199, 207, 0.3);
    }}
    /* Streamlit Download Button Styling */
    .stDownloadButton button {{
        background-color: #FFC7CF !important;
        color: #000000 !important;
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }}
    .stDownloadButton button:hover {{
        background-color: #B5D1FF !important;
        box-shadow: 0 4px 8px rgba(255, 199, 207, 0.3) !important;
    }}
    .stDownloadButton button:active {{
        background-color: #FFC7CF !important;
        border: 2px solid #051B4A !important;
    }}
    /* All Streamlit Buttons Border Styling */
    .stButton button {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }}
    
    /* Sidebar Buttons */
    .stSidebar .stButton button {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
    }}
    /* Primary Buttons */
    .stButton > button:first-child {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
    }}
    /* Secondary Buttons */
    .stButton > button:nth-child(2) {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
    }}    
    /* Floating Panel Styles */
    .floating-panel {{
        position: fixed;
        top: 20px;
        right: -400px;
        width: 380px;
        height: calc(100vh - 40px);
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        border-radius: 16px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
        border: 1px solid #E5E7EB;
        transition: right 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 1000;
        overflow-y: auto;
        padding: 20px;
    }}    
    .floating-panel.open {{
        right: 20px;
    }}    
    .floating-toggle {{
        position: fixed;
        top: 50%;
        right: 20px;
        transform: translateY(-50%);
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border: none;
        border-radius: 50px 0 0 50px;
        padding: 15px 20px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
        transition: all 0.3s ease;
        z-index: 1001;
        writing-mode: vertical-rl;
        text-orientation: mixed;
    }}    
    .floating-toggle:hover {{
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
        box-shadow: 0 12px 24px rgba(37, 99, 235, 0.4);
    }}    
    .floating-toggle.open {{
        right: 400px;
        border-radius: 0 50px 50px 0;
    }}    
    /* Home Overview Styles */
    .home-container {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }}    
    .welcome-section {{
        text-align: center;
        margin: 0 0 10px 0;
    }}    
    .app-logo {{
        font-size: 4rem;
        margin: 0 0 0 0;
    }}    
    .app-title {{
        font-family: 'Cambria', serif;
        font-size: 6rem;
        font-weight: 700;
        color: #1F2937;
        margin: 0;
        line-height: 0.8;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}    
    .app-subtitle {{
        font-family: 'Cambria', serif;
        font-size: 1.8rem;
        color: #6B7280;
        margin: 0;
        line-height: 1;
    }}   
    .quick-buttons {{
        display: flex;
        gap: 15px;
        justify-content: center;
        flex-wrap: wrap;
        margin-bottom: 40px;
    }}    
    .quick-btn {{
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-family: 'Cambria', serif;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.2);
    }}    
    .quick-btn:hover {{
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
        box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
        transform: translateY(-2px);
    }}    
    .summary-cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 40px;
    }}    
    .summary-card {{
        background: #FFC7CF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid #051B4A;
        text-align: center;
        transition: all 0.3s ease;
        height: 300px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}    
    .summary-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
    }}    
    .summary-card-icon {{
        font-size: 2.5rem;
        margin-bottom: 12px;
        flex-shrink: 0;
    }}    
    .summary-card-title {{
        font-family: 'Cambria', serif;
        font-size: 1.1rem;
        font-weight: bold;
        color: #232527;
        margin-bottom: 8px;
        flex-shrink: 0;
    }}    
    .summary-card-value {{
        font-family: 'Cambria', serif;
        font-size: 2rem;
        font-weight: 700;
        color: #2563EB;
        margin-bottom: 8px;
        flex-shrink: 0;
    }}    
    .summary-card-desc {{
        font-family: 'Cambria', serif;
        font-size: 0.9rem;
        font-weight: bold;
        color: #232527;
        flex-grow: 1;
        display: flex;
        align-items: flex-end;
    }}    
    /* System Status Styles */
    .system-status {{
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border: 1.5px solid #000000;
    }}    
    .status-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1.5px solid #FFC7CF;
    }}    
    .status-item:last-child {{
        border-bottom: none;
    }}    
    .status-label {{
        font-family: 'Cambria', serif;
        font-size: 0.9rem;
        font-weight: bold;
        color: #232527;
    }}    
    .status-value {{
        font-family: 'Cambria', serif;
        font-size: 0.9rem;
        font-weight: bold;
    }}    
    .status-online {{
        color: #10B981;
    }}    
    .status-offline {{
        color: #EF4444;
    }}   
    .status-warning {{
        color: #F59E0B;
    }}    
    /* Let sidebar navigation use default fonts - no overrides */
    [data-testid="stSidebarNav"] {{
        font-family: inherit !important;
    }}    
    [data-testid="stSidebarNav"] * {{
        font-family: inherit !important;
    }}
    
    /* Make sidebar dividers bold */
    .stSidebar hr {{
        border: none !important;
        height: 2px !important;
        background: {colors['primary']} !important;
        margin: 15px 0 !important;
        border-radius: 1.5px !important;
    }}
    </style>
    <script>
    function fixBackButton() {{
        // Simple text replacement
        const elements = document.querySelectorAll('*');
        elements.forEach(element => {{
            if (element.textContent && element.textContent.includes('keyboard_double_arrow_right')) {{
                element.innerHTML = element.innerHTML.replace(/keyboard_double_arrow_right/g, '>>');
            }}
        }});
    }}
    // Run multiple times to catch dynamic content
    fixBackButton();
    setTimeout(fixBackButton, 500);
    setTimeout(fixBackButton, 1000);
    </script>
    
    """

def load_custom_css():
    """Load optimized CSS with light theme."""
    st.markdown(get_optimized_css(), unsafe_allow_html=True)

load_custom_css()

@st.cache_data(ttl=300)
def get_system_status():
    """Get cached system status to avoid repeated calls."""
    api_status = cached_check_api_status()
    api_test = test_api_quick()
    return api_status, api_test

def render_sidebar():
    st.sidebar.markdown("""
    <div class="sidebar-header">
        <h2>The Gemini-Powered SEO Keyword Agent</h2>
    </div>
    """, unsafe_allow_html=True)    
    st.sidebar.markdown("### 🔧 System Status")
    api_status, api_test = get_system_status()    
    st.sidebar.markdown("""
    <div class="system-status">
        <div class="status-item">
            <span class="status-label">Gemini API</span>
            <span class="status-value {}">{}</span>
        </div>
        <div class="status-item">
            <span class="status-label">SerpApi</span>
            <span class="status-value {}">{}</span>
        </div>
    </div>
    """.format(
        "status-online" if api_test["gemini"] else "status-offline",
        "✅ Online" if api_test["gemini"] else "❌ Offline",
        "status-online" if api_test["serpapi"] else "status-offline", 
        "✅ Online" if api_test["serpapi"] else "❌ Offline"
    ), unsafe_allow_html=True)    
    # Model Status
    st.sidebar.markdown("### 🤖 Model Status")
    st.sidebar.markdown("""
    <div class="system-status">
        <div class="status-item">
            <span class="status-label">Model Type</span>
            <span class="status-value">Gemini 2.5 Flash</span>
        </div>
        <div class="status-item">
            <span class="status-label">Active Models</span>
            <span class="status-value">{}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Requests Today</span>
            <span class="status-value">{}</span>
        </div>
    </div>
    """.format(len(GEMINI_MODELS), st.session_state.get("daily_requests", 0)), unsafe_allow_html=True)    
    # Database Status (simplified)
    st.sidebar.markdown("### 💾 Database")    
    # Use a placeholder that doesn't make heavy DB calls on every render
    if st.sidebar.button("🔍 Check Database Status", use_container_width=True):
        with st.sidebar:
            with st.spinner("Checking database..."):
                try:
                    schema_ok = cached_verify_database_schema()
                    df_test = cached_fetch_past_results(limit=1)
                    if schema_ok and not df_test.empty:
                        st.success(f"✅ Connected ({len(df_test)} records)")
                    elif schema_ok:
                        st.success("✅ Connected (0 records)")
                    else:
                        st.warning("⚠️ Schema issues detected")
                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)[:30]}...")
    st.sidebar.markdown("---")    
    # Database History
    st.sidebar.markdown("### 📂 Database History")
    if st.sidebar.button("📊 Show History", use_container_width=True):
        st.session_state.current_page = "search_history"
        st.rerun()    
    # Recent Searches (optimized)
    st.sidebar.markdown("### 🔍 Recent Searches")    
    # Display recent searches from session state only
    if st.session_state.search_history:
        for i, search in enumerate(st.session_state.search_history[-3:]):
            if st.sidebar.button(f"🔍 {search[:25]}...", key=f"history_{i}", use_container_width=True):
                st.session_state.selected_keyword = search
                st.session_state.current_page = "keyword_discovery"
                st.rerun()
    else:
        st.sidebar.info("No recent searches")
    
def render_home_overview():
    # Welcome section
    st.markdown("""
    <div class="home-container">
        <div class="welcome-section">
            <div class="app-logo">💎</div>
            <h1 class="app-title">GemKey AI</h1>
            <p class="app-subtitle">Advanced SEO Research & Analysis Platform</p>
        </div>
    </div>
    """, unsafe_allow_html=True)   
    # Quick buttons using Streamlit buttons
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔍 Keyword Discovery", use_container_width=True):
            st.session_state.current_page = "keyword_discovery"
            st.rerun()
    with col2:
        if st.button("🧩 Competitor Gap", use_container_width=True):
            st.session_state.current_page = "competitor_gap"
            st.rerun()
    with col3:
        if st.button("📈 Trend Forecasting", use_container_width=True):
            st.session_state.current_page = "trend_forecasting"
            st.rerun()
    with col4:
        if st.button("🧩 Full Strategy", use_container_width=True):
            st.session_state.current_page = "full_strategy"
            st.rerun()
    # Summary cards
    st.markdown("### 📊 Global Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="summary-card">
            <div class="summary-card-icon">🔍</div>
            <div class="summary-card-title">Keywords Analyzed</div>
            <div class="summary-card-value">{}</div>
            <div class="summary-card-desc">Total keywords processed</div>
        </div>
        """.format(st.session_state.get("total_keywords", 0)), unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="summary-card">
            <div class="summary-card-icon">📊</div>
            <div class="summary-card-title">Avg Volume</div>
            <div class="summary-card-value">{}</div>
            <div class="summary-card-desc">Average search volume</div>
        </div>
        """.format(f"{st.session_state.get('avg_volume', 0):.0f}"), unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="summary-card">
            <div class="summary-card-icon">🎯</div>
            <div class="summary-card-title">Opportunities</div>
            <div class="summary-card-value">{}</div>
            <div class="summary-card-desc">High-potential keywords</div>
        </div>
        """.format(st.session_state.get("opportunities", 0)), unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="summary-card">
            <div class="summary-card-icon">📈</div>
            <div class="summary-card-title">Trend Score</div>
            <div class="summary-card-value">{}</div>
            <div class="summary-card-desc">Overall trend strength</div>
        </div>
        """.format(f"{st.session_state.get('trend_score', 0):.1f}"), unsafe_allow_html=True)

def render_floating_panel():
    """Render the floating features panel"""
    if st.session_state.get("panel_open", False):
        st.markdown("### 🚀 All Features")
        # Feature buttons in columns
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Keyword Discovery", key="fp_kd", use_container_width=True):
                st.session_state.current_page = "keyword_discovery"
                st.rerun()
            if st.button("🧩 Competitor Gap", key="fp_cg", use_container_width=True):
                st.session_state.current_page = "competitor_gap"
                st.rerun()
            if st.button("🎯 Search Intent", key="fp_si", use_container_width=True):
                st.session_state.current_page = "search_intent"
                st.rerun()
            if st.button("🧠 Topic Clustering", key="fp_tc", use_container_width=True):
                st.session_state.current_page = "topic_clustering"
                st.rerun()
            if st.button("📈 Trend Forecasting", key="fp_tf", use_container_width=True):
                st.session_state.current_page = "trend_forecasting"
                st.rerun()        
        with col2:
            if st.button("📰 SERP Analysis", key="fp_sa", use_container_width=True):
                st.session_state.current_page = "serp_analysis"
                st.rerun()
            if st.button("🧾 Content Optimization", key="fp_co", use_container_width=True):
                st.session_state.current_page = "content_optimization"
                st.rerun()
            if st.button("💰 Conversion Mapping", key="fp_cm", use_container_width=True):
                st.session_state.current_page = "conversion_mapping"
                st.rerun()
            if st.button("🌐 Industry Focus", key="fp_if", use_container_width=True):
                st.session_state.current_page = "industry_focus"
                st.rerun()
            if st.button("🧩 Full Strategy", key="fp_fs", use_container_width=True):
                st.session_state.current_page = "full_strategy"
                st.rerun()

def update_global_metrics(keyword_results):
    """Update global metrics based on keyword analysis results"""
    if keyword_results:
        df = pd.DataFrame(keyword_results) if isinstance(keyword_results, list) else keyword_results        
        # Update total keywords
        current_total = st.session_state.get("total_keywords", 0)
        st.session_state.total_keywords = current_total + len(df)
        # Update average volume
        if 'volume' in df.columns:
            current_avg = st.session_state.get("avg_volume", 0)
            new_avg = df['volume'].mean()
            # Calculate weighted average
            total_count = st.session_state.total_keywords
            if total_count > 0:
                st.session_state.avg_volume = (current_avg * (total_count - len(df)) + new_avg * len(df)) / total_count        
        # Update opportunities (keywords with high scores)
        if 'score' in df.columns:
            high_score_keywords = len(df[df['score'] > 7.0])  # Assuming score > 7 is high opportunity
            current_opps = st.session_state.get("opportunities", 0)
            st.session_state.opportunities = current_opps + high_score_keywords        
        # Update trend score
        if 'score' in df.columns:
            current_trend = st.session_state.get("trend_score", 0)
            new_trend = df['score'].mean()
            # Calculate weighted average
            total_count = st.session_state.total_keywords
            if total_count > 0:
                st.session_state.trend_score = (current_trend * (total_count - len(df)) + new_trend * len(df)) / total_count

def render_keyword_discovery():
    """🔍 Keyword Discovery: Find, rank, and score keywords"""
    st.markdown("### 🔍 Keyword Discovery")
    st.markdown("Find, rank, and score keywords with comprehensive metrics and trend analysis.")
    # Input bar
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        keyword_input = st.text_input(
            "Enter a seed keyword or topic:",
            placeholder="e.g., 'AI tools', 'fitness apps', 'digital marketing'",
            key="keyword_discovery_input"
        )
    with col2:
        analysis_mode = st.selectbox(
            "Mode:",
            ["Quick (5)", "Standard (15)", "Full (30)", "Comprehensive (50)"],
            key="discovery_mode"
        )
    with col3:
        if st.button("🚀 Analyze", type="primary", use_container_width=True):
            if keyword_input:
                keyword_limit = {
                    "Quick (5)": 5, 
                    "Standard (15)": 15, 
                    "Full (30)": 30,
                    "Comprehensive (50)": 50
                }[analysis_mode]
                with st.spinner(f"Analyzing {keyword_limit} keywords..."):
                    try:
                        if keyword_limit <= 5:
                            results = cached_run_lightweight_agent(keyword_input, keyword_limit)
                        else:
                            results = cached_run_agent(keyword_input, keyword_limit)
                        if results and len(results) > 0:
                            st.session_state.keyword_results = results[:keyword_limit]
                            st.session_state.selected_keyword = keyword_input
                            # Update global metrics
                            update_global_metrics(results[:keyword_limit])
                            st.success(f"✅ Analyzed {len(results[:keyword_limit])} keywords!")
                        else:
                            st.error("❌ No keywords found. Please try a different term.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")   
    # Display results
    if "keyword_results" in st.session_state and st.session_state.keyword_results:
        results = st.session_state.keyword_results
        df = pd.DataFrame(results) if isinstance(results, list) else results
        # Metrics table
        st.markdown("#### 📊 Metrics Table")
        st.dataframe(df, use_container_width=True, hide_index=True)
        # Trend graph
        if 'volume' in df.columns and 'score' in df.columns:
            st.markdown("#### 📈 Trend Graph")
            fig = px.scatter(
                df.head(20), 
                x='volume', 
                y='score',
                hover_data=['keyword', 'difficulty'],
                title="Volume vs Score Analysis",
                color='score',
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family="Inter", size=12)
            )
            st.plotly_chart(fig, use_container_width=True)

def render_competitor_gap():
    """🧩 Competitor Gap: Compare your keywords vs. competitors"""
    st.markdown("### 🧩 Competitor Gap Analysis")
    st.markdown("Compare your keywords against competitors to find missing opportunities.")
    col1, col2 = st.columns([2, 1])
    with col1:
        your_keyword = st.text_input(
            "Your keyword:",
            placeholder="e.g., 'project management software'",
            key="your_keyword"
        )
    with col2:
        competitor_keyword = st.text_input(
            "Competitor keyword:",
            placeholder="e.g., 'task management tools'",
            key="competitor_keyword"
        )
    if st.button("🔍 Analyze Gap", type="primary"):
        if your_keyword and competitor_keyword:
            with st.spinner("Analyzing competitor gaps..."):
                try:
                    results = cached_analyze_competitor_gap(your_keyword)
                    if results and "error" not in results:
                        st.session_state.competitor_results = results
                        st.success("✅ Competitor analysis complete!")
                    else:
                        st.warning("⚠️ Analysis completed but no competitor data found.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please enter both keywords.")   
    # Display results
    if "competitor_results" in st.session_state and st.session_state.competitor_results:
        results = st.session_state.competitor_results
        if "opportunities" in results and results["opportunities"]:
            st.markdown("#### 🎯 Missing Keyword List")
            for i, opp in enumerate(results["opportunities"][:10]):
                with st.expander(f"#{i+1} {opp['keyword']} (Score: {opp['gap_score']})"):
                    st.markdown(f"**Opportunity Type:** {opp['opportunity_type']}")
                    st.markdown(f"**Traffic Potential:** {opp['traffic_potential']}")
                    st.markdown(f"**Reasoning:** {opp['reasoning']}")        
        # Bar chart
        if "opportunities" in results and results["opportunities"]:
            st.markdown("#### 📊 Gap Analysis Chart")
            gap_data = []
            for opp in results["opportunities"][:10]:
                gap_data.append({
                    "Keyword": opp['keyword'][:20] + "...",
                    "Gap Score": opp['gap_score'],
                    "Traffic Potential": opp['traffic_potential']
                })
            if gap_data:
                df_gap = pd.DataFrame(gap_data)
                fig = px.bar(
                    df_gap,
                    x="Keyword",
                    y="Gap Score",
                    title="Top Keyword Gaps",
                    color="Gap Score",
                    color_continuous_scale="Reds"
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)

def render_search_intent():
    """🎯 Search Intent: Identify intent behind queries"""
    st.markdown("### 🎯 Search Intent Analysis")
    st.markdown("Identify the intent behind search queries to optimize content strategy.")
    # Keyword list input
    keywords_text = st.text_area(
        "Enter keywords (one per line):",
        placeholder="AI tools\nbest project management software\nhow to use AI\nproject management tips",
        height=150,
        key="intent_keywords"
    )
    if st.button("🎯 Analyze Intent", type="primary"):
        if keywords_text:
            keywords = [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]
            if keywords:
                with st.spinner("Analyzing search intent..."):
                    try:
                        # Use AI to analyze intent
                        intent_results = []
                        for keyword in keywords[:10]:  # Limit to 10 for performance
                            prompt = f"Analyze the search intent for the keyword '{keyword}'. Return the intent type (informational, navigational, transactional, commercial) and a short reasoning (max 50 words)."
                            response = safe_gemini_call(prompt)
                            # Parse response
                            intent_type = "informational"  # default
                            reasoning = response
                            if "transactional" in response.lower():
                                intent_type = "transactional"
                            elif "navigational" in response.lower():
                                intent_type = "navigational"
                            elif "commercial" in response.lower():
                                intent_type = "commercial"   
                            intent_results.append({
                                "keyword": keyword,
                                "intent_type": intent_type,
                                "reasoning": reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
                            })
                        st.session_state.intent_results = intent_results
                        st.success(f"✅ Analyzed intent for {len(intent_results)} keywords!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter at least one keyword.")
        else:
            st.warning("⚠️ Please enter keywords to analyze.")
    
    # Display results
    if "intent_results" in st.session_state and st.session_state.intent_results:
        results = st.session_state.intent_results
        st.markdown("#### 🎯 Intent Analysis Results")
        for result in results:
            intent_color = {
                "informational": "🔵",
                "navigational": "🟢", 
                "transactional": "🔴",
                "commercial": "🟡"
            }.get(result["intent_type"], "⚪")
            st.markdown(f"""
            **{intent_color} {result['keyword']}**
            - **Intent Type:** {result['intent_type'].title()}
            - **Reasoning:** {result['reasoning']}
            """)
            st.divider()

def render_topic_clustering():
    """🧠 Topic Clustering: Group related keywords"""
    st.markdown("### 🧠 Topic Clustering")
    st.markdown("Group related keywords into semantic clusters for better content strategy.")
    col1, col2 = st.columns([2, 1])
    with col1:
        cluster_keyword = st.text_input(
            "Enter seed keyword for clustering:",
            placeholder="e.g., 'AI tools', 'fitness apps'",
            key="cluster_keyword_new"
        )
    with col2:
        if st.button("🧠 Cluster Topics", type="primary", use_container_width=True):
            if cluster_keyword:
                with st.spinner("Clustering topics..."):
                    try:
                        keywords = cached_run_lightweight_agent(cluster_keyword, 15)
                        if keywords and len(keywords) > 0:
                            results = cached_cluster_keywords_semantically(keywords)
                            if results and "clusters" in results and len(results["clusters"]) > 0:
                                st.session_state.cluster_results = results
                                st.success(f"✅ Found {len(results['clusters'])} topic clusters!")
                            else:
                                st.warning("⚠️ No clusters found. Try a different keyword.")
                        else:
                            st.error("❌ No keywords found for clustering.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
    # Display results
    if "cluster_results" in st.session_state and st.session_state.cluster_results:
        results = st.session_state.cluster_results
        if "clusters" in results and results["clusters"]:
            st.markdown("#### 🎯 Topic Clusters")
            # Cluster visualization
            cluster_data = []
            for i, cluster in enumerate(results["clusters"]):
                cluster_data.append({
                    "Cluster": f"Cluster {i+1}",
                    "Keywords": cluster['keyword_count'],
                    "Opportunity Score": cluster['opportunity_score']
                })
            if cluster_data:
                df_clusters = pd.DataFrame(cluster_data)
                fig = px.bar(
                    df_clusters,
                    x="Cluster",
                    y="Opportunity Score",
                    title="Cluster Opportunity Scores",
                    color="Opportunity Score",
                    color_continuous_scale="Viridis"
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
            # Grouped tables
            for i, cluster in enumerate(results["clusters"]):
                with st.expander(f"#{i+1} {cluster['cluster_name']} ({cluster['keyword_count']} keywords)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Description:** {cluster['description']}")
                        st.markdown(f"**Intent:** {cluster['primary_intent']}")
                        st.markdown(f"**Industry:** {cluster['industry_focus']}")
                    with col2:
                        st.markdown("**Keywords:**")
                        for kw in cluster['keywords'][:8]:
                            st.markdown(f"- {kw}")

def render_trend_forecasting():
    """📈 Trend Forecasting: Predict keyword trends"""
    st.markdown("### 📈 Trend Forecasting")
    st.markdown("Predict keyword trends with 6-month forecasts and seasonal analysis.")
    col1, col2 = st.columns([2, 1])
    with col1:
        trend_keyword = st.text_input(
            "Enter keyword for trend analysis:",
            placeholder="e.g., 'AI tools', 'remote work'",
            key="trend_keyword_new"
        )
    with col2:
        if st.button("📈 Forecast Trends", type="primary", use_container_width=True):
            if trend_keyword:
                with st.spinner("Analyzing trends..."):
                    try:
                        keywords = cached_run_lightweight_agent(trend_keyword, 8)
                        if keywords:
                            results = cached_analyze_trend_forecasting(keywords)
                            st.session_state.trend_results = results
                            st.success("✅ Trend analysis complete!")
                        else:
                            st.error("❌ No keywords found for trend analysis.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
    
    # Display results
    if "trend_results" in st.session_state and st.session_state.trend_results:
        results = st.session_state.trend_results
        # Line graph
        if "forecasts" in results and results["forecasts"]:
            st.markdown("#### 📊 Trend Forecasts")
            for keyword, forecast in list(results["forecasts"].items())[:3]:
                with st.expander(f"📈 {keyword} - {forecast['trend_direction']}"):
                    st.markdown(f"**Predicted Growth:** {forecast['predicted_growth']}%")
                    st.markdown(f"**Recommendation:** {forecast['recommendation']}")
                    # Forecast chart
                    if "forecast_scores" in forecast:
                        forecast_df = pd.DataFrame(forecast["forecast_scores"])
                        fig = px.line(
                            forecast_df,
                            x="month",
                            y="score",
                            title=f"6-Month Forecast: {keyword}",
                            markers=True
                        )
                        fig.update_layout(
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            font=dict(family="Inter", size=12)
                        )
                        st.plotly_chart(fig, use_container_width=True)
        # Seasonal peaks
        if "seasonal_analysis" in results and results["seasonal_analysis"]:
            st.markdown("#### 🗓️ Seasonal Peaks")
            for keyword, analysis in list(results["seasonal_analysis"].items())[:3]:
                st.markdown(f"""
                **{keyword}**
                - Peak Season: Month {analysis['peak_season']}
                - Low Season: Month {analysis['low_season']}
                - Growth %: {analysis.get('growth_rate', 'N/A')}%
                - Recommendation: {analysis['recommendation']}
                """)
                st.divider()

def render_serp_analysis():
    """📰 SERP Analysis: Show snippets & top-ranking pages"""
    st.markdown("### 📰 SERP Analysis")
    st.markdown("Analyze search engine results pages for optimization opportunities.")
    col1, col2 = st.columns([2, 1])
    with col1:
        serp_keyword = st.text_input(
            "Enter keyword for SERP analysis:",
            placeholder="e.g., 'best project management tools'",
            key="serp_keyword_new"
        )
    with col2:
        if st.button("📊 Analyze SERP", type="primary", use_container_width=True):
            if serp_keyword:
                with st.spinner("Analyzing SERP opportunities..."):
                    try:
                        results = cached_analyze_serp_opportunities(serp_keyword)
                        if results and "error" not in results:
                            st.session_state.serp_results = results
                            st.success("✅ SERP analysis complete!")
                        else:
                            st.warning("⚠️ Analysis completed but limited data available.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
    # Display results
    if "serp_results" in st.session_state and st.session_state.serp_results:
        results = st.session_state.serp_results
        # SERP preview cards
        if "serp_data" in results and results["serp_data"]:
            st.markdown("#### 🔍 Top-Ranking Pages")
            for i, result in enumerate(results["serp_data"][:5]):
                with st.expander(f"#{i+1} {result.get('title', 'No title')[:50]}..."):
                    st.markdown(f"**URL:** {result.get('link', 'No URL')}")
                    st.markdown(f"**Snippet:** {result.get('snippet', 'No snippet')[:200]}...")
                    st.markdown(f"**Domain:** {result.get('domain', 'Unknown')}")
        # Featured snippets
        if "featured_snippets" in results and results["featured_snippets"]:
            st.markdown("#### ⭐ Featured Snippets")
            for snippet in results["featured_snippets"][:3]:
                st.markdown(f"""
                **{snippet.get('title', 'Featured Snippet')}**
                {snippet.get('content', 'No content available')}
                """)
                st.divider()
        # PAA questions
        if "paa_questions" in results and results["paa_questions"]:
            paa = results["paa_questions"]
            if paa.get("questions"):
                st.markdown("#### ❓ People Also Ask Questions")
                for q in paa["questions"][:5]:
                    st.markdown(f"**Q:** {q['question']}")
                    st.markdown(f"**A:** {q['snippet'][:150]}...")
                    st.markdown(f"**Content Idea:** {q['content_idea']}")
                    st.divider()

def render_content_optimization():
    """🧾 Content Optimization: Suggest meta tags, missing topics"""
    st.markdown("### 🧾 Content Optimization")
    st.markdown("Get AI-powered suggestions for meta tags and missing content topics.")
    # Text area for content
    content_text = st.text_area(
        "Enter your content or topic:",
        placeholder="Paste your article content or describe your topic here...",
        height=200,
        key="content_optimization_input"
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        content_type = st.selectbox(
            "Content Type:",
            ["Blog Post", "Product Page", "Landing Page", "Article", "Guide"],
            key="content_type"
        )
    with col2:
        if st.button("🧾 Optimize Content", type="primary", use_container_width=True):
            if content_text:
                with st.spinner("Generating optimization suggestions..."):
                    try:
                        prompt = f"""
                        Analyze this {content_type.lower()} content and provide optimization suggestions:
                        Content: {content_text[:1000]}...
                        Please provide:
                        1. Meta title suggestions (3 options)
                        2. Meta description suggestions (3 options)
                        3. Missing topics to cover
                        4. Keyword optimization tips
                        5. Content structure improvements
                        Format as a structured response.
                        """
                        response = safe_gemini_call(prompt)
                        st.session_state.optimization_results = response
                        st.success("✅ Content optimization complete!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter content to optimize.")
    # Display results
    if "optimization_results" in st.session_state and st.session_state.optimization_results:
        results = st.session_state.optimization_results
        st.markdown("#### 🎯 AI Suggestions")
        st.markdown(results)

def render_conversion_mapping():
    """💰 Conversion Mapping: Rank by CPC, buyer intent"""
    st.markdown("### 💰 Conversion Mapping")
    st.markdown("Rank keywords by CPC and buyer intent for maximum ROI.")
    # Get keyword data
    if "keyword_results" in st.session_state and st.session_state.keyword_results:
        df = pd.DataFrame(st.session_state.keyword_results)
        if 'cpc' in df.columns and 'score' in df.columns:
            # Calculate ROI potential
            df['roi_potential'] = df['score'] / (df['cpc'] + 0.01)  # Avoid division by zero
            # Sort by ROI potential
            df_sorted = df.sort_values('roi_potential', ascending=False)
            st.markdown("#### 📊 ROI Potential Ranking")
            # Table sorted by ROI potential
            st.dataframe(
                df_sorted[['keyword', 'volume', 'cpc', 'score', 'roi_potential']].head(20),
                use_container_width=True,
                hide_index=True
            )
            # ROI chart
            fig = px.bar(
                df_sorted.head(15),
                x="keyword",
                y="roi_potential",
                title="Top Keywords by ROI Potential",
                color="roi_potential",
                color_continuous_scale="Greens"
            )
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family="Inter", size=12),
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ CPC data not available. Run keyword analysis first.")
    else:
        st.info("💡 Run keyword analysis first to see conversion mapping data.")
        # Quick keyword input for conversion analysis
        quick_keyword = st.text_input(
            "Enter keyword for quick conversion analysis:",
            placeholder="e.g., 'buy project management software'",
            key="conversion_keyword"
        )
        if st.button("💰 Analyze Conversion", type="primary"):
            if quick_keyword:
                with st.spinner("Analyzing conversion potential..."):
                    try:
                        keywords = cached_run_lightweight_agent(quick_keyword, 10)
                        if keywords:
                            df = pd.DataFrame(keywords)
                            if 'cpc' in df.columns:
                                df['roi_potential'] = df['score'] / (df['cpc'] + 0.01)
                                df_sorted = df.sort_values('roi_potential', ascending=False)
                                st.markdown("#### 📊 Conversion Analysis Results")
                                st.dataframe(
                                    df_sorted[['keyword', 'volume', 'cpc', 'score', 'roi_potential']],
                                    use_container_width=True,
                                    hide_index=True
                                )
                            else:
                                st.warning("⚠️ CPC data not available for this keyword.")
                        else:
                            st.error("❌ No keywords found.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

def render_industry_focus():
    """🌐 Industry Focus: Select industry → get tailored keyword set"""
    st.markdown("### 🌐 Industry Focus")
    st.markdown("Get tailored keyword sets and insights for your specific industry.")
    # Industry dropdown
    industry = st.selectbox(
        "Select Industry:",
        [
            "Technology", "Healthcare", "Finance", "Education", "E-commerce",
            "Marketing", "Real Estate", "Travel", "Food & Beverage", "Fashion",
            "Automotive", "Sports", "Entertainment", "Legal", "Consulting"
        ],
        key="industry_selection"
    )
    if st.button("🌐 Get Industry Insights", type="primary"):
        with st.spinner(f"Generating {industry} keyword insights..."):
            try:
                # Generate industry-specific keywords
                prompt = f"""
                Generate 20 high-value keywords for the {industry} industry. 
                Include a mix of informational, commercial, and transactional keywords.
                Focus on current trends and opportunities in {industry}.
                """
                response = safe_gemini_call(prompt)
                # Parse and structure the response
                keywords = []
                lines = response.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('#') and not line.startswith('*'):
                        keyword = line.strip().replace('-', '').replace('•', '').strip()
                        if keyword and len(keyword) > 3:
                            keywords.append(keyword)
                if keywords:
                    st.session_state.industry_keywords = keywords[:15]
                    st.success(f"✅ Generated {len(keywords[:15])} {industry} keywords!")
                else:
                    st.warning("⚠️ Could not parse keywords from response.")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    # Display results
    if "industry_keywords" in st.session_state and st.session_state.industry_keywords:
        keywords = st.session_state.industry_keywords
        st.markdown(f"#### 🎯 {industry} Keywords")
        # Insights cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="summary-card">
                <div class="summary-card-icon">🎯</div>
                <div class="summary-card-title">Target Keywords</div>
                <div class="summary-card-value">{}</div>
                <div class="summary-card-desc">Industry-specific</div>
            </div>
            """.format(len(keywords)), unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="summary-card">
                <div class="summary-card-icon">📈</div>
                <div class="summary-card-title">Growth Potential</div>
                <div class="summary-card-value">High</div>
                <div class="summary-card-desc">Trending in {}</div>
            </div>
            """.format(industry), unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="summary-card">
                <div class="summary-card-icon">💰</div>
                <div class="summary-card-title">ROI Potential</div>
                <div class="summary-card-value">Strong</div>
                <div class="summary-card-desc">Industry-focused</div>
    </div>
    """, unsafe_allow_html=True)
        # Keyword list
        st.markdown("#### 📋 Recommended Keywords")
        for i, keyword in enumerate(keywords, 1):
            st.markdown(f"{i}. **{keyword}**")
        # Industry insights
        st.markdown("#### 💡 Industry Insights")
        st.info(f"""
        **{industry} Industry Focus:**
        - These keywords are specifically tailored for the {industry} sector
        - Focus on industry-specific terminology and trends
        - Consider seasonal patterns and industry events
        - Monitor competitor activity in this space
        """)

def render_full_strategy():
    """🧩 Full Strategy: Run all modules together"""
    st.markdown("### 🧩 Full Strategy Analysis")
    st.markdown("Run all modules together for comprehensive SEO strategy.")
    col1, col2 = st.columns([2, 1])
    with col1:
        strategy_keyword = st.text_input(
            "Enter main keyword for full strategy:",
            placeholder="e.g., 'project management software'",
            key="strategy_keyword"
        )
    with col2:
        if st.button("🧩 Run Full Strategy", type="primary", use_container_width=True):
            if strategy_keyword:
                with st.spinner("Running comprehensive analysis..."):
                    try:
                        # Run multiple analyses
                        progress_bar = st.progress(0)
                        # 1. Keyword Discovery
                        st.info("🔍 Running Keyword Discovery...")
                        keywords = cached_run_lightweight_agent(strategy_keyword, 20)
                        progress_bar.progress(20)                       
                        # 2. Competitor Analysis
                        st.info("🧩 Running Competitor Gap Analysis...")
                        competitor_results = cached_analyze_competitor_gap(strategy_keyword)
                        progress_bar.progress(40)                       
                        # 3. Topic Clustering
                        st.info("🧠 Running Topic Clustering...")
                        cluster_results = cached_cluster_keywords_semantically(keywords) if keywords else None
                        progress_bar.progress(60)                       
                        # 4. Trend Forecasting
                        st.info("📈 Running Trend Forecasting...")
                        trend_results = cached_analyze_trend_forecasting(keywords) if keywords else None
                        progress_bar.progress(80)                       
                        # 5. SERP Analysis
                        st.info("📰 Running SERP Analysis...")
                        serp_results = cached_analyze_serp_opportunities(strategy_keyword)
                        progress_bar.progress(100)
                        # Store results
                        st.session_state.strategy_results = {
                            "keyword": strategy_keyword,
                            "keywords": keywords,
                            "competitor": competitor_results,
                            "clusters": cluster_results,
                            "trends": trend_results,
                            "serp": serp_results
                        }
                        st.success("✅ Full strategy analysis complete!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
    # Display results
    if "strategy_results" in st.session_state and st.session_state.strategy_results:
        results = st.session_state.strategy_results
        # Multi-output dashboard with expandable sections
        st.markdown("#### 📊 Comprehensive Strategy Dashboard")
        # Summary
        with st.expander("📋 Executive Summary", expanded=True):
            st.markdown(f"""
            **Keyword:** {results['keyword']}
            **Total Keywords Found:** {len(results['keywords']) if results['keywords'] else 0}
            **Competitor Opportunities:** {len(results['competitor'].get('opportunities', [])) if results['competitor'] and 'opportunities' in results['competitor'] else 0}
            **Topic Clusters:** {len(results['clusters'].get('clusters', [])) if results['clusters'] and 'clusters' in results['clusters'] else 0}
            **Trend Analysis:** {'✅ Complete' if results['trends'] else '❌ Failed'}
            **SERP Analysis:** {'✅ Complete' if results['serp'] else '❌ Failed'}
            """)
        # Keyword Discovery Results
        if results['keywords']:
            with st.expander("🔍 Keyword Discovery Results"):
                df = pd.DataFrame(results['keywords'])
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)
        # Competitor Gap Results
        if results['competitor'] and 'opportunities' in results['competitor']:
            with st.expander("🧩 Competitor Gap Opportunities"):
                for i, opp in enumerate(results['competitor']['opportunities'][:5]):
                    st.markdown(f"**{i+1}. {opp['keyword']}** - Score: {opp['gap_score']}")
        # Topic Clusters
        if results['clusters'] and 'clusters' in results['clusters']:
            with st.expander("🧠 Topic Clusters"):
                for i, cluster in enumerate(results['clusters']['clusters'][:3]):
                    st.markdown(f"**{i+1}. {cluster['cluster_name']}** ({cluster['keyword_count']} keywords)")
        # Trend Analysis
        if results['trends'] and 'forecasts' in results['trends']:
            with st.expander("📈 Trend Forecasts"):
                for keyword, forecast in list(results['trends']['forecasts'].items())[:3]:
                    st.markdown(f"**{keyword}:** {forecast['trend_direction']} ({forecast['predicted_growth']}%)")
        # SERP Analysis
        if results['serp'] and 'serp_data' in results['serp']:
            with st.expander("📰 SERP Analysis"):
                st.markdown(f"**Top Results:** {len(results['serp']['serp_data'])} pages analyzed")
                if results['serp']['serp_data']:
                    st.markdown(f"**Top Result:** {results['serp']['serp_data'][0].get('title', 'No title')}")

def render_chat_interface():
    st.markdown("### 💬 Conversational SEO Assistant")
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    # Chat input
    if prompt := st.chat_input("Ask me anything about SEO, keywords, or trends..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Add to search history
        if prompt not in st.session_state.search_history:
            st.session_state.search_history.append(prompt)
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = generate_chat_response(prompt)
                st.markdown(response)
        # Add assistant message
        st.session_state.messages.append({"role": "assistant", "content": response})

def generate_chat_response(user_input):
    """Generate AI response based on user input."""
    try:
        # Enhanced intent detection with more specific responses
        user_lower = user_input.lower()
        if any(word in user_lower for word in ["keyword", "keywords", "search", "analyze"]):
            return f"🔍 **Keyword Analysis Ready!**\n\nI can help you analyze keywords for '{user_input}'. Here's what I can do:\n\n• **Generate related keywords** with search volume and competition data\n• **Analyze keyword difficulty** and scoring\n• **Find trending keywords** in your niche\n• **Suggest content ideas** based on keyword research\n\n💡 **Quick Start:** Use the 'Keyword Analysis' tab or ask me to 'find keywords for [your topic]'"        
        elif any(word in user_lower for word in ["trend", "trends", "forecast", "seasonal"]):
            return f"📈 **Trend Analysis Available!**\n\nI can help you understand trends for '{user_input}'. My capabilities include:\n\n• **6-month trend forecasts** with confidence scores\n• **Seasonal pattern analysis** to optimize content timing\n• **Growth rate calculations** and trend direction\n• **Market opportunity identification**\n\n💡 **Quick Start:** Use the 'Trend Forecasting' tab or ask me to 'analyze trends for [your topic]'"
        elif any(word in user_lower for word in ["competitor", "competitors", "gap", "opportunity"]):
            return f"🕵️ **Competitor Analysis Ready!**\n\nI can help you analyze competitors for '{user_input}'. Here's what I offer:\n\n• **Keyword gap analysis** to find missed opportunities\n• **Competitor ranking insights** and domain analysis\n• **Traffic potential scoring** for each opportunity\n• **Strategic recommendations** for outranking competitors\n\n💡 **Quick Start:** Use the 'Competitor Analysis' tab or ask me to 'find competitor gaps for [your keyword]'"
        elif any(word in user_lower for word in ["serp", "snippet", "optimization", "people also ask", "paa"]):
            return f"📊 **SERP Analysis Available!**\n\nI can help you optimize SERP performance for '{user_input}'. My features include:\n\n• **Snippet optimization opportunities** and recommendations\n• **People Also Ask (PAA) questions** extraction\n• **Title tag optimization** suggestions\n• **Content gap identification** in search results\n\n💡 **Quick Start:** Use the 'SERP Analysis' tab or ask me to 'analyze SERP for [your keyword]'"
        elif any(word in user_lower for word in ["cluster", "group", "topic", "semantic"]):
            return f"🧩 **Topic Clustering Ready!**\n\nI can help you cluster topics for '{user_input}'. Here's what I can do:\n\n• **Semantic keyword clustering** into meaningful groups\n• **Topic opportunity scoring** and prioritization\n• **Content strategy recommendations** by cluster\n• **Keyword relationship mapping** and insights\n\n💡 **Quick Start:** Use the 'Topic Clustering' tab or ask me to 'cluster topics for [your keyword]'"
        else:
            return f"💎 **Welcome to GemKey AI!**\n\nI understand you're asking about '{user_input}'. I'm your comprehensive SEO research assistant with these powerful features:\n\n🔍 **Keyword Analysis** - Find and analyze keywords with metrics\n🕵️ **Competitor Analysis** - Discover keyword gaps and opportunities\n📊 **SERP Analysis** - Optimize snippets and find PAA questions\n🧩 **Topic Clustering** - Group keywords semantically\n📈 **Trend Forecasting** - Predict trends and seasonal patterns\n\n💡 **How to get started:**\n• Use the tabs above for detailed analysis\n• Ask me specific questions like 'find keywords for [topic]'\n• Try 'analyze competitors for [keyword]' for gap analysis\n• Use 'show trends for [keyword]' for forecasting\n\nWhat would you like to explore first?"
    except Exception as e:
        return f"⚠️ **I encountered an error:** {str(e)}\n\nPlease try again or use the specific tabs for detailed analysis. If the issue persists, check your API keys and internet connection."

def render_keyword_analysis():
    st.markdown("### 🔍 Keyword Analysis")
    # Add performance options
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        keyword_input = st.text_input(
            "Enter a seed keyword or topic:",
            placeholder="e.g., 'AI tools', 'fitness apps', 'digital marketing'",
            key="keyword_input"
        )    
    with col2:
        analysis_mode = st.selectbox(
            "Analysis Mode:",
            ["Quick (5 keywords)", "Standard (15 keywords)", "Full (30 keywords)", "Comprehensive (50 keywords)"],
            key="analysis_mode"
        )    
    with col3:
        if st.button("🚀 Analyze Keywords", type="primary", use_container_width=True):
            if keyword_input:
                # Determine keyword limit based on mode
                keyword_limit = {
                    "Quick (5 keywords)": 5, 
                    "Standard (15 keywords)": 15, 
                    "Full (30 keywords)": 30,
                    "Comprehensive (50 keywords)": 50
                }[analysis_mode]                
                with st.spinner(f"Analyzing {keyword_limit} keywords..."):
                    try:
                        # Use cached results if available
                        cache_key = f"keywords_{keyword_input}_{keyword_limit}"
                        if cache_key in st.session_state:
                            st.session_state.keyword_results = st.session_state[cache_key]
                            st.session_state.selected_keyword = keyword_input
                            st.success(f"✅ Loaded {len(st.session_state[cache_key])} cached keywords!")
                        else:
                            # Use lightweight agent for smaller sets, full agent for larger sets
                            if keyword_limit <= 5:
                                results = cached_run_lightweight_agent(keyword_input, keyword_limit)
                            elif keyword_limit <= 30:
                                results = cached_run_agent(keyword_input, keyword_limit)
                            else:  # 50 keywords
                                results = cached_run_agent(keyword_input, keyword_limit)                            
                            if results and len(results) > 0:
                                # Limit results based on mode
                                limited_results = results[:keyword_limit]
                                st.session_state.keyword_results = limited_results
                                st.session_state[cache_key] = limited_results  # Cache results
                                st.session_state.selected_keyword = keyword_input                                
                                # Save to database
                                try:
                                    cached_save_to_db(limited_results)
                                    st.success(f"✅ Analyzed {len(limited_results)} keywords and saved to database!")
                                except Exception as db_error:
                                    st.success(f"✅ Analyzed {len(limited_results)} keywords!")
                                    st.warning(f"⚠️ Database save failed: {db_error}")
                            else:
                                st.error("❌ No keywords found. Please try a different term.")
                    except Exception as e:
                        error_msg = str(e)
                        if "timeout" in error_msg.lower():
                            st.error("❌ Analysis timed out. Try 'Quick' mode or check your internet connection.")
                        elif "api" in error_msg.lower() or "key" in error_msg.lower():
                            st.error("❌ API error. Please check your GEMINI_API_KEY in the .env file.")
                        else:
                            st.error(f"❌ Error: {error_msg}")
            else:
                st.warning("⚠️ Please enter a keyword first.")    
    # Display results
    if "keyword_results" in st.session_state and st.session_state.keyword_results:
        results = st.session_state.keyword_results       
        # Convert to DataFrame if needed
        if isinstance(results, list):
            df = pd.DataFrame(results)
        else:
            df = results
        # Metrics Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Total Keywords</div>
                <div class="metric-value">{}</div>
            </div>
            """.format(len(df)), unsafe_allow_html=True)
        with col2:
            avg_volume = df['volume'].mean() if 'volume' in df.columns else 0
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Avg Volume</div>
                <div class="metric-value">{}</div>
            </div>
            """.format(f"{avg_volume:.0f}"), unsafe_allow_html=True)       
        with col3:
            avg_score = df['score'].mean() if 'score' in df.columns else 0
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Avg Score</div>
                <div class="metric-value">{}</div>
            </div>
            """.format(f"{avg_score:.2f}"), unsafe_allow_html=True)
        with col4:
            easy_keywords = len(df[df['difficulty'].str.contains('Easy', na=False)]) if 'difficulty' in df.columns else 0
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Easy Keywords</div>
                <div class="metric-value">{}</div>
            </div>
            """.format(easy_keywords), unsafe_allow_html=True)
        # Charts
        col1, col2 = st.columns(2)
        with col1:
            # Volume vs Score scatter plot
            if 'volume' in df.columns and 'score' in df.columns:
                fig = px.scatter(
                    df.head(20), 
                    x='volume', 
                    y='score',
                    hover_data=['keyword', 'difficulty'],
                    title="Volume vs Score Analysis",
                    color='score',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Difficulty distribution
            if 'difficulty' in df.columns:
                difficulty_counts = df['difficulty'].value_counts()
                fig = px.pie(
                    values=difficulty_counts.values,
                    names=difficulty_counts.index,
                    title="Difficulty Distribution",
                    color_discrete_sequence=['#10B981', '#F59E0B', '#EF4444']
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
        # Data Table
        st.markdown("### 📊 Keyword Results")
        # Style the dataframe
        styled_df = df.style.map(
            lambda x: 'background-color: #D1FAE5' if 'Easy' in str(x) else 
                     'background-color: #FEF3C7' if 'Medium' in str(x) else 
                     'background-color: #FEE2E2' if 'Hard' in str(x) else '',
            subset=['difficulty']
        )
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        ) 
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"keywords_{st.session_state.selected_keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def render_competitor_analysis():
    st.markdown("### 🕵️ Competitor Gap Analysis")
    col1, col2 = st.columns([2, 1])
    with col1:
        competitor_keyword = st.text_input(
            "Enter keyword for competitor analysis:",
            placeholder="e.g., 'project management software'",
            key="competitor_keyword"
        )
    with col2:
        if st.button("🔍 Analyze Competitors", type="primary", use_container_width=True):
            if competitor_keyword:
                with st.spinner("Analyzing competitor gaps..."):
                    try:
                        # Add timeout and better error handling
                        results = cached_analyze_competitor_gap(competitor_keyword)
                        if results and "error" not in results:
                            st.session_state.competitor_results = results
                            st.success("✅ Competitor analysis complete!")
                        elif results and "error" in results:
                            st.warning(f"⚠️ Analysis completed but no competitor data found: {results['error']}")
                        else:
                            st.error("❌ Competitor analysis failed. Please check your API keys and try again.")
                    except Exception as e:
                        error_msg = str(e)
                        if "timeout" in error_msg.lower():
                            st.error("❌ Analysis timed out. Please try with a simpler keyword or check your internet connection.")
                        elif "api" in error_msg.lower() or "key" in error_msg.lower():
                            st.error("❌ API error. Please check your SERPAPI_KEY in the .env file.")
                        else:
                            st.error(f"❌ Error: {error_msg}")
            else:
                st.warning("⚠️ Please enter a keyword first.")   
    # Display results
    if "competitor_results" in st.session_state and st.session_state.competitor_results:
        results = st.session_state.competitor_results       
        if "error" in results:
            st.error(f"❌ {results['error']}")
            return       
        # Summary
        st.markdown("### 📋 Analysis Summary")
        st.info(results.get("summary", "No summary available"))       
        # Opportunities
        if "opportunities" in results and results["opportunities"]:
            st.markdown("### 🎯 Top Opportunities")           
            for i, opp in enumerate(results["opportunities"][:5]):
                with st.expander(f"#{i+1} {opp['keyword']} (Score: {opp['gap_score']})"):
                    col1, col2 = st.columns(2)  
                    with col1:
                        st.markdown(f"**Opportunity Type:** {opp['opportunity_type']}")
                        st.markdown(f"**Traffic Potential:** {opp['traffic_potential']}")
                        st.markdown(f"**Gap Score:** {opp['gap_score']}") 
                    with col2:
                        st.markdown(f"**Reasoning:** {opp['reasoning']}")       
        # Competitors
        if "competitors" in results and results["competitors"]:
            st.markdown("### 🏢 Top Competitors")           
            for comp in results["competitors"][:5]:
                st.markdown(f"""
                **{comp['rank']}. [{comp['title']}]({comp['link']})**
                - 🌐 Domain: {comp['domain']}
                - 📝 Snippet: {comp['snippet'][:100]}...
                """)

def render_serp_analysis_tab():
    st.markdown("### 🔍 SERP Analysis & Optimization")    
    col1, col2 = st.columns([2, 1])   
    with col1:
        serp_keyword = st.text_input(
            "Enter keyword for SERP analysis:",
            placeholder="e.g., 'best project management tools'",
            key="serp_keyword"
        )    
    with col2:
        if st.button("📊 Analyze SERP", type="primary", use_container_width=True):
            if serp_keyword:
                with st.spinner("Analyzing SERP opportunities..."):
                    try:
                        st.info("🔄 Fetching SERP data...")
                        # Add timeout and better error handling
                        results = cached_analyze_serp_opportunities(serp_keyword)
                        if results and "error" not in results:
                            st.session_state.serp_results = results
                            st.success("✅ SERP analysis complete!")
                        elif results and "error" in results:
                            st.warning(f"⚠️ Analysis completed but limited data: {results['error']}")
                            st.info("💡 This might be due to API quota limits or network issues.")
                        else:
                            st.error("❌ SERP analysis failed. Please check your API keys and try again.")
                            st.info("💡 Make sure your SERPAPI_KEY is valid and has available credits.")
                    except Exception as e:
                        error_msg = str(e)
                        if "timeout" in error_msg.lower():
                            st.error("❌ Analysis timed out. Please try with a simpler keyword or check your internet connection.")
                        elif "api" in error_msg.lower() or "key" in error_msg.lower():
                            st.error("❌ API error. Please check your SERPAPI_KEY in the .env file.")
                        elif "quota" in error_msg.lower():
                            st.error("❌ API quota exceeded. Please add credits to your SerpApi account.")
                        else:
                            st.error(f"❌ Error: {error_msg}")
                            st.info("💡 Try using a different keyword or check your internet connection.")
            else:
                st.warning("⚠️ Please enter a keyword first.")   
    # Display results
    if "serp_results" in st.session_state and st.session_state.serp_results:
        results = st.session_state.serp_results        
        if "error" in results:
            st.error(f"❌ {results['error']}")
            return        
        # Summary
        st.markdown("### 📋 SERP Summary")
        st.info(results.get("summary", "No summary available"))       
        # Snippet Opportunities
        if "snippet_analysis" in results and results["snippet_analysis"]:
            snippet_analysis = results["snippet_analysis"]            
            if snippet_analysis["snippet_opportunities"]:
                st.markdown("### 💡 Snippet Opportunities")                
                for opp in snippet_analysis["snippet_opportunities"]:
                    with st.expander(f"{opp['type'].title()} - {opp['opportunity']}"):
                        st.markdown(f"**Recommendation:** {opp['recommendation']}")
                        st.markdown(f"**Priority:** {opp['priority']}")        
        # PAA Questions
        if "paa_questions" in results and results["paa_questions"]:
            paa = results["paa_questions"]            
            if paa["questions"]:
                st.markdown("### ❓ People Also Ask Questions")                
                for q in paa["questions"][:5]:
                    st.markdown(f"**Q:** {q['question']}")
                    st.markdown(f"**A:** {q['snippet'][:150]}...")
                    st.markdown(f"**Content Idea:** {q['content_idea']}")
                    st.divider()        
        # Optimization Suggestions
        if "optimization_suggestions" in results and results["optimization_suggestions"]:
            st.markdown("### 🎯 Optimization Suggestions")            
            for suggestion in results["optimization_suggestions"][:10]:
                priority_color = {
                    "high": "🔴",
                    "medium": "🟡", 
                    "low": "🟢"
                }.get(suggestion.get("priority", "low"), "🟢")   
                st.markdown(f"""
                {priority_color} **{suggestion['type'].replace('_', ' ').title()}**
                - {suggestion['opportunity']}
                - {suggestion['recommendation']}
                """)

def render_topic_clustering_tab():
    st.markdown("### 🧩 Topic Clustering")    
    col1, col2 = st.columns([2, 1])    
    with col1:
        cluster_keyword = st.text_input(
            "Enter seed keyword for clustering:",
            placeholder="e.g., 'AI tools', 'fitness apps'",
            key="cluster_keyword"
        )   
    with col2:
        if st.button("🧩 Cluster Topics", type="primary", use_container_width=True):
            if cluster_keyword:
                with st.spinner("Clustering topics..."):
                    try:
                        # Use lightweight agent for faster clustering
                        st.info("🔄 Generating keywords for clustering...")
                        keywords = cached_run_lightweight_agent(cluster_keyword, 10)                        
                        if keywords and len(keywords) > 0:
                            st.info(f"✅ Generated {len(keywords)} keywords. Now clustering...")                           
                            # Save keywords to database first
                            try:
                                cached_save_to_db(keywords)
                                st.info("💾 Keywords saved to database")
                            except Exception as db_error:
                                st.warning(f"⚠️ Database save failed: {db_error}")                            
                            # Then cluster them with error handling
                            results = cached_cluster_keywords_semantically(keywords)
                            if results and "clusters" in results and len(results["clusters"]) > 0:
                                st.session_state.cluster_results = results
                                st.success(f"✅ Topic clustering complete! Found {len(results['clusters'])} clusters.")
                            else:
                                st.warning("⚠️ Clustering completed but no clusters found. Try a different keyword.")
                                # Show debug info
                                st.info(f"Debug: Results keys: {list(results.keys()) if results else 'No results'}")
                        else:
                            st.error("❌ No keywords found for clustering. Please try a different seed keyword.")
                            st.info("💡 Make sure your GEMINI_API_KEY is working properly.")
                    except Exception as e:
                        error_msg = str(e)
                        if "max() iterable argument is empty" in error_msg:
                            st.error("❌ Clustering failed: No data to cluster. Please try a different keyword or check your API connections.")
                        elif "api" in error_msg.lower() or "key" in error_msg.lower():
                            st.error("❌ API error. Please check your GEMINI_API_KEY in the .env file.")
                        else:
                            st.error(f"❌ Error: {error_msg}")
                            st.info("💡 Try using a simpler keyword or check your internet connection.")
            else:
                st.warning("⚠️ Please enter a keyword first.")    
    # Display results
    if "cluster_results" in st.session_state and st.session_state.cluster_results:
        results = st.session_state.cluster_results        
        # Summary
        st.markdown("### 📋 Clustering Summary")
        st.info(results.get("summary", "No summary available"))        
        # Clusters
        if "clusters" in results and results["clusters"]:
            st.markdown("### 🎯 Topic Clusters")            
            for i, cluster in enumerate(results["clusters"]):
                with st.expander(f"#{i+1} {cluster['cluster_name']} ({cluster['keyword_count']} keywords)"):
                    col1, col2 = st.columns(2)                   
                    with col1:
                        st.markdown(f"**Description:** {cluster['description']}")
                        st.markdown(f"**Intent:** {cluster['primary_intent']}")
                        st.markdown(f"**Industry:** {cluster['industry_focus']}")
                        st.markdown(f"**Opportunity Score:** {cluster['opportunity_score']}")                   
                    with col2:
                        st.markdown("**Keywords:**")
                        for kw in cluster['keywords'][:10]:
                            st.markdown(f"- {kw}")
                    # Metrics
                    if "metrics" in cluster:
                        metrics = cluster["metrics"]
                        st.markdown("**Cluster Metrics:**")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Avg Volume", f"{metrics['avg_volume']:.0f}")
                        with col2:
                            st.metric("Avg Competition", f"{metrics['avg_competition']:.2f}")
                        with col3:
                            st.metric("Avg CPC", f"${metrics['avg_cpc']:.2f}")
                        with col4:
                            st.metric("Total Volume", f"{metrics['total_volume']:,}")
        # Insights
        if "insights" in results and results["insights"]:
            st.markdown("### 💡 Cluster Insights")
            for insight in results["insights"]:
                st.markdown(f"**{insight['title']}**")
                st.markdown(insight['description'])
                st.markdown(f"*Recommendation:* {insight['recommendation']}")
                st.divider()

def render_trend_forecasting_tab():
    st.markdown("### 📈 Trend Forecasting")
    col1, col2 = st.columns([2, 1])
    with col1:
        trend_keyword = st.text_input(
            "Enter keyword for trend analysis:",
            placeholder="e.g., 'AI tools', 'remote work'",
            key="trend_keyword"
        )
    with col2:
        if st.button("📈 Forecast Trends", type="primary", use_container_width=True):
            if trend_keyword:
                with st.spinner("Analyzing trends..."):
                    try:
                        # Use lightweight agent for faster trend analysis
                        keywords = cached_run_lightweight_agent(trend_keyword, 8)
                        if keywords:
                            # Then analyze trends
                            results = cached_analyze_trend_forecasting(keywords)
                            st.session_state.trend_results = results
                            st.success("✅ Trend analysis complete!")
                        else:
                            st.error("❌ No keywords found for trend analysis.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
    # Display results
    if "trend_results" in st.session_state and st.session_state.trend_results:
        results = st.session_state.trend_results
        # Summary
        st.markdown("### 📋 Trend Summary")
        st.info(results.get("summary", "No summary available"))
        # Trend Analysis
        if "trend_analysis" in results and results["trend_analysis"]:
            st.markdown("### 📊 Trend Analysis")
            # Create trend chart
            trend_data = []
            for keyword, analysis in results["trend_analysis"].items():
                trend_data.append({
                    "Keyword": keyword,
                    "Direction": analysis["direction"],
                    "Growth Rate": analysis["growth_rate"],
                    "Volatility": analysis["volatility"]
                })
            if trend_data:
                df_trends = pd.DataFrame(trend_data)
                # Trend direction chart
                fig = px.bar(
                    df_trends.head(10),
                    x="Keyword",
                    y="Growth Rate",
                    color="Direction",
                    title="Keyword Growth Rates",
                    color_discrete_map={
                        "strong_growth": "#10B981",
                        "moderate_growth": "#3B82F6",
                        "stable": "#6B7280",
                        "moderate_decline": "#F59E0B",
                        "strong_decline": "#EF4444"
                    }
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
        # Forecasts
        if "forecasts" in results and results["forecasts"]:
            st.markdown("### 🔮 6-Month Forecasts")
            for keyword, forecast in list(results["forecasts"].items())[:5]:
                with st.expander(f"📈 {keyword} - {forecast['trend_direction']}"):
                    st.markdown(f"**Predicted Growth:** {forecast['predicted_growth']}%")
                    st.markdown(f"**Recommendation:** {forecast['recommendation']}")
                    # Forecast chart
                    if "forecast_scores" in forecast:
                        forecast_df = pd.DataFrame(forecast["forecast_scores"])
                        fig = px.line(
                            forecast_df,
                            x="month",
                            y="score",
                            title=f"6-Month Forecast: {keyword}",
                            markers=True
                        )
                        fig.update_layout(
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            font=dict(family="Inter", size=12)
                        )
                        st.plotly_chart(fig, use_container_width=True)
        # Seasonal Analysis
        if "seasonal_analysis" in results and results["seasonal_analysis"]:
            st.markdown("### 🗓️ Seasonal Patterns")
            for keyword, analysis in list(results["seasonal_analysis"].items())[:3]:
                with st.expander(f"📅 {keyword} - Seasonality: {analysis['seasonality_strength']}"):
                    st.markdown(f"**Peak Season:** Month {analysis['peak_season']}")
                    st.markdown(f"**Low Season:** Month {analysis['low_season']}")
                    st.markdown(f"**Recommendation:** {analysis['recommendation']}")
        # Insights
        if "insights" in results and results["insights"]:
            st.markdown("### 💡 Trend Insights")
            for insight in results["insights"]:
                st.markdown(f"**{insight['title']}**")
                st.markdown(insight['description'])
                st.markdown(f"*Recommendation:* {insight['recommendation']}")
                st.divider()

def render_search_history():
    st.markdown("### 📂 Search History")
    # Fetch from database (cached)
    with st.spinner("Loading search history..."):
        try:
            df_history = cached_fetch_past_results(limit=100)
            if not df_history.empty:
                st.success(f"✅ Loaded {len(df_history)} records from database")
                # Filters
                col1, col2, col3 = st.columns(3)
                with col1:
                    seed_filter = st.selectbox(
                        "Filter by Seed Keyword:",
                        ["All"] + list(df_history['seed'].unique())
                    )
                with col2:
                    difficulty_filter = st.selectbox(
                        "Filter by Difficulty:",
                        ["All", "Easy", "Medium", "Hard"]
                    )
                with col3:
                    volume_filter = st.slider(
                        "Minimum Volume:",
                        min_value=0,
                        max_value=int(df_history['volume'].max()) if 'volume' in df_history.columns else 1000,
                        value=0
                    )
                # Apply filters
                filtered_df = df_history.copy()
                if seed_filter != "All":
                    filtered_df = filtered_df[filtered_df['seed'] == seed_filter]
                if difficulty_filter != "All":
                    filtered_df = filtered_df[filtered_df['difficulty'].str.contains(difficulty_filter, na=False)]
                if 'volume' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['volume'] >= volume_filter]
                st.info(f"Showing {len(filtered_df)} filtered results")
                # Display filtered results
                if not filtered_df.empty:
                    # Style the dataframe
                    styled_df = filtered_df.style.map(
                        lambda x: 'background-color: #D1FAE5' if 'Easy' in str(x) else 
                                 'background-color: #FEF3C7' if 'Medium' in str(x) else 
                                 'background-color: #FEE2E2' if 'Hard' in str(x) else '',
                        subset=['difficulty']
                    )
                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        hide_index=True
                    )
                    # Download button
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Filtered Results",
                        data=csv,
                        file_name=f"search_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No results match your filters")
            else:
                st.warning("No search history found. Try running some keyword analyses first.")
        except Exception as e:
            st.error(f"❌ Error loading history: {str(e)}")
            st.info("💡 Make sure your MySQL database is running and properly configured")

def check_api_status():
    """Check API keys status."""
    # Check API keys
    api_status = {
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "SERPAPI_KEY": bool(os.getenv("SERPAPI_KEY")),
    }
    return api_status

def test_api_quick():
    """Quick API test to show current status."""
    results = {"gemini": False, "serpapi": False}
    
    # Test Gemini with multiple models
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            for model_name in GEMINI_MODELS:
                try:
                    model = genai.GenerativeModel(model_name)
                    result = model.generate_content("Hello")
                    if hasattr(result, "text") and result.text:
                        results["gemini"] = True
                        break
                except Exception as e:
                    print(f"Gemini model {model_name} failed: {e}")
                    continue
        except Exception as e:
            print(f"Gemini test failed: {e}")
    
    # Test SerpApi
    serpapi_key = os.getenv("SERPAPI_KEY")
    if serpapi_key:
        try:
            import requests
            url = "https://serpapi.com/search.json"
            params = {"q": "test", "api_key": serpapi_key, "engine": "google", "num": "1"}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results["serpapi"] = "search_information" in data or "error" not in data
            else:
                print(f"SerpApi HTTP error: {response.status_code}")
        except Exception as e:
            print(f"SerpApi test failed: {e}")
    
    return results

def handle_api_errors():
    """Display API status."""
    api_status = check_api_status()
    if not api_status["GEMINI_API_KEY"]:
        st.error("⚠️ **GEMINI_API_KEY not found!** Please add it to your .env file.")
    if not api_status["SERPAPI_KEY"]:
        st.warning("⚠️ **SERPAPI_KEY not found!** Some features may not work properly.")

def main():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"
    if "daily_requests" not in st.session_state:
        st.session_state.daily_requests = 0
    api_status = check_api_status()
    api_test = test_api_quick()
    if not api_status["GEMINI_API_KEY"] or not api_status["SERPAPI_KEY"]:
        with st.expander("⚠️ API Configuration Issues", expanded=True):
            handle_api_errors()
    elif not api_test["gemini"] or not api_test["serpapi"]:
        with st.expander("⚠️ API Connection Issues", expanded=True):
            st.error("API keys found but connections are failing!")
            
            if not api_test["gemini"]:
                st.error("🔴 **Gemini API Failed**")
                st.info("💡 **Possible fixes:**")
                st.info("• Check if your API key is valid")
                st.info("• Verify internet connection")
                st.info("• Try refreshing the page")
                st.info("• Check Google AI Studio for service status")
            
            if not api_test["serpapi"]:
                st.error("🔴 **SerpApi Failed**")
                st.info("💡 **Possible fixes:**")
                st.info("• Check if your API key is valid")
                st.info("• Verify you have remaining searches in your account")
                st.info("• Check SerpApi service status")
                st.info("• Try refreshing the page")
            
            if api_test["gemini"] and not api_test["serpapi"]:
                st.success("✅ **Working Features:** Keyword Analysis, Topic Clustering, Trend Forecasting, Chat Assistant")
                st.warning("⚠️ **Limited Features:** SERP Analysis and Competitor Gap Analysis may not work")
            
            if st.button("🔄 Retest APIs", type="secondary"):
                st.rerun()
    render_sidebar()
    col1, col2, col3, col4, col5 = st.columns(5)
    with col5:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()
        toggle_text = "Hide Features" if st.session_state.get("panel_open", False) else "Show Features"
        if st.button(toggle_text, use_container_width=True):
            st.session_state.panel_open = not st.session_state.get("panel_open", False)
            st.rerun()
    render_floating_panel()
    current_page = st.session_state.current_page
    if current_page == "home":
        render_home_overview()
    elif current_page == "keyword_discovery":
        render_keyword_discovery()
    elif current_page == "competitor_gap":
        render_competitor_gap()
    elif current_page == "search_intent":
        render_search_intent()
    elif current_page == "topic_clustering":
        render_topic_clustering()
    elif current_page == "trend_forecasting":
        render_trend_forecasting()
    elif current_page == "serp_analysis":
        render_serp_analysis()
    elif current_page == "content_optimization":
        render_content_optimization()
    elif current_page == "conversion_mapping":
        render_conversion_mapping()
    elif current_page == "industry_focus":
        render_industry_focus()
    elif current_page == "full_strategy":
        render_full_strategy()
    elif current_page == "chat":
        render_chat_interface()
    elif current_page == "search_history":
        render_search_history()
    else:
        render_home_overview()

if __name__ == "__main__":
    main()
