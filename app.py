# app.py
import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import time
import random
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.agent import run_agent
from src.db_client import fetch_past_results, save_to_db
from src.trends_client import get_trend_score
from src.competitor_client import get_competitor_data
from src.competitor_gap_analyzer import analyze_competitor_keyword_gap
from src.serp_analyzer import analyze_serp_opportunities
from src.topic_clusterer import cluster_keywords_semantically
from src.trend_forecaster import analyze_trend_forecasting

# ------------------------- SETUP -------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ✅ Multi-model fallback list
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "learnlm-2.0-flash-experimental"
]

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

# ------------------------- CUSTOM CSS STYLING -------------------------
def load_custom_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Montserrat:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&family=Lato:wght@300;400;700&family=Cambria:wght@400;700&display=swap');
    
    /* Global Styles */
    .main {
        background-color: #F3F4F6;
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background-color: #FFFFFF;
        border-right: 2px solid #E5E7EB;
    }
    
    .css-1d391kg .css-1v0mbdj {
        color: #111827;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #F3F4F6;
        border-radius: 6px;
        padding: 8px 16px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: #64748B;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2563EB;
        color: #FFFFFF;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
    }
    
    /* Card Styling */
    .metric-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #E5E7EB;
        margin: 10px 0;
    }
    
    .metric-title {
        font-family: 'Poppins', sans-serif;
        font-size: 14px;
        font-weight: 500;
        color: #64748B;
        margin-bottom: 8px;
    }
    
    .metric-value {
        font-family: 'Montserrat', sans-serif;
        font-size: 24px;
        font-weight: 600;
        color: #2563EB;
    }
    
    /* Chat Styling */
    .chat-container {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #E5E7EB;
        margin: 10px 0;
    }
    
    .chat-message {
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
        font-family: 'Cambria', serif;
    }
    
    .chat-user {
        background-color: #2563EB;
        color: #FFFFFF;
        margin-left: 20%;
    }
    
    .chat-assistant {
        background-color: #F3F4F6;
        color: #111827;
        margin-right: 20%;
    }
    
    /* Button Styling */
    .stButton > button {
        background-color: #2563EB;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background-color: #1D4ED8;
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
    }
    
    /* Chart Styling */
    .plotly-chart {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #E5E7EB;
    }
    
    /* Table Styling */
    .stDataFrame {
        background-color: #FFFFFF;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #E5E7EB;
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: #FFFFFF;
        padding: 30px;
        border-radius: 16px;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
    }
    
    .main-header h1 {
        font-family: 'Poppins', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .main-header p {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        margin: 10px 0 0 0;
        opacity: 0.9;
    }
    
    /* Sidebar Header */
    .sidebar-header {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .sidebar-header h2 {
        font-family: 'Poppins', sans-serif;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }
    
    /* Success/Error Messages */
    .stSuccess {
        background-color: #D1FAE5;
        border: 1px solid #10B981;
        color: #065F46;
        border-radius: 8px;
    }
    
    .stError {
        background-color: #FEE2E2;
        border: 1px solid #EF4444;
        color: #991B1B;
        border-radius: 8px;
    }
    
    .stWarning {
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        color: #92400E;
        border-radius: 8px;
    }
    
    /* Loading Spinner */
    .stSpinner {
        color: #2563EB;
    }
    
    /* Download Button */
    .download-btn {
        background-color: #10B981;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .download-btn:hover {
        background-color: #059669;
        box-shadow: 0 4px 8px rgba(16, 185, 129, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------- PAGE CONFIG -------------------------
st.set_page_config(
    page_title="GemKey AI - SEO Research Assistant",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
load_custom_css()

# ------------------------- SIDEBAR -------------------------
def render_sidebar():
    st.sidebar.markdown("""
    <div class="sidebar-header">
        <h2>💎 GemKey AI</h2>
        <p>SEO Research Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Actions
    st.sidebar.markdown("### 🚀 Quick Actions")
    
    if st.sidebar.button("🔍 New Keyword Analysis", use_container_width=True):
        st.session_state.current_tab = "Keyword Analysis"
        st.rerun()
    
    if st.sidebar.button("📊 View Search History", use_container_width=True):
        st.session_state.current_tab = "Search History"
        st.rerun()
    
    if st.sidebar.button("📈 Trend Analysis", use_container_width=True):
        st.session_state.current_tab = "Trend Forecasting"
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Search History Panel
    st.sidebar.markdown("### 📂 Recent Searches")
    
    if "search_history" not in st.session_state:
        st.session_state.search_history = []
    
    # Display recent searches
    if st.session_state.search_history:
        for i, search in enumerate(st.session_state.search_history[-5:]):
            if st.sidebar.button(f"🔍 {search[:30]}...", key=f"history_{i}", use_container_width=True):
                st.session_state.selected_keyword = search
                st.session_state.current_tab = "Keyword Analysis"
                st.rerun()
    else:
        st.sidebar.info("No recent searches")
    
    st.sidebar.markdown("---")
    
    # Database Status
    st.sidebar.markdown("### 💾 Database Status")
    try:
        df_test = fetch_past_results(limit=1)
        if not df_test.empty:
            st.sidebar.success("✅ Connected")
        else:
            st.sidebar.warning("⚠️ No data")
    except:
        st.sidebar.error("❌ Disconnected")

# ------------------------- MAIN HEADER -------------------------
def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>💎 GemKey AI</h1>
        <p>Advanced SEO Research & Analysis Platform</p>
    </div>
    """, unsafe_allow_html=True)

# ------------------------- CHAT INTERFACE -------------------------
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
        # Simple intent detection
        if any(word in user_input.lower() for word in ["keyword", "keywords", "search"]):
            return "I can help you analyze keywords! Use the 'Keyword Analysis' tab to get detailed insights, or try asking me to 'analyze keywords for [your topic]'."
        elif any(word in user_input.lower() for word in ["trend", "trends", "forecast"]):
            return "I can help with trend analysis! Use the 'Trend Forecasting' tab to see predictions and seasonal patterns."
        elif any(word in user_input.lower() for word in ["competitor", "competitors", "gap"]):
            return "I can analyze competitor gaps! Use the 'Competitor Analysis' tab to find keyword opportunities."
        elif any(word in user_input.lower() for word in ["serp", "snippet", "optimization"]):
            return "I can help with SERP analysis! Use the 'SERP Analysis' tab to optimize your snippets and titles."
        else:
            return f"I understand you're asking about '{user_input}'. I can help with keyword research, trend analysis, competitor insights, and SERP optimization. Which area would you like to explore?"
    except Exception as e:
        return f"I encountered an error: {str(e)}. Please try again or use the specific tabs for detailed analysis."

# ------------------------- KEYWORD ANALYSIS TAB -------------------------
def render_keyword_analysis():
    st.markdown("### 🔍 Keyword Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        keyword_input = st.text_input(
            "Enter a seed keyword or topic:",
            placeholder="e.g., 'AI tools', 'fitness apps', 'digital marketing'",
            key="keyword_input"
        )
    
    with col2:
        if st.button("🚀 Analyze Keywords", type="primary", use_container_width=True):
            if keyword_input:
                with st.spinner("Analyzing keywords..."):
                    try:
                        results = run_agent(keyword_input)
                        if results:
                            st.session_state.keyword_results = results
                            st.session_state.selected_keyword = keyword_input
                            st.success(f"✅ Analyzed {len(results)} keywords!")
                        else:
                            st.error("❌ No keywords found. Please try a different term.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
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

# ------------------------- COMPETITOR ANALYSIS TAB -------------------------
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
                        results = analyze_competitor_keyword_gap(competitor_keyword)
                        st.session_state.competitor_results = results
                        st.success("✅ Competitor analysis complete!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
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

# ------------------------- SERP ANALYSIS TAB -------------------------
def render_serp_analysis():
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
                        results = analyze_serp_opportunities(serp_keyword)
                        st.session_state.serp_results = results
                        st.success("✅ SERP analysis complete!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
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

# ------------------------- TOPIC CLUSTERING TAB -------------------------
def render_topic_clustering():
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
                        # First get keywords
                        keywords = run_agent(cluster_keyword)
                        if keywords:
                            # Then cluster them
                            results = cluster_keywords_semantically(keywords)
                            st.session_state.cluster_results = results
                            st.success("✅ Topic clustering complete!")
                        else:
                            st.error("❌ No keywords found for clustering.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
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

# ------------------------- TREND FORECASTING TAB -------------------------
def render_trend_forecasting():
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
                        # First get keywords
                        keywords = run_agent(trend_keyword)
                        if keywords:
                            # Then analyze trends
                            results = analyze_trend_forecasting(keywords)
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

# ------------------------- SEARCH HISTORY TAB -------------------------
def render_search_history():
    st.markdown("### 📂 Search History")
    
    # Fetch from database
    with st.spinner("Loading search history..."):
        try:
            df_history = fetch_past_results(limit=100)
            
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

# ------------------------- MAIN APP -------------------------
def main():
    # Initialize session state
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = "Chat Assistant"
    
    # Render sidebar
    render_sidebar()
    
    # Render header
    render_header()
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "💬 Chat Assistant",
        "🔍 Keyword Analysis", 
        "🕵️ Competitor Analysis",
        "📊 SERP Analysis",
        "🧩 Topic Clustering",
        "📈 Trend Forecasting",
        "📂 Search History"
    ])
    
    with tab1:
        render_chat_interface()
    
    with tab2:
        render_keyword_analysis()
    
    with tab3:
        render_competitor_analysis()
    
    with tab4:
        render_serp_analysis()
    
    with tab5:
        render_topic_clustering()
    
    with tab6:
        render_trend_forecasting()
    
    with tab7:
        render_search_history()

if __name__ == "__main__":
    main()
