import streamlit as st
from src.services.serp_service import cached_analyze_serp_opportunities
from src.services.metrics_service import increment_daily_requests, add_recent_search

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
                            add_recent_search(serp_keyword)
                            increment_daily_requests()
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
            serp_data = results["serp_data"]
            organic_results = serp_data.get("organic_results", [])
            if organic_results:
                st.markdown("#### 🔍 Top-Ranking Pages")
                for i, result in enumerate(organic_results[:5]):
                    with st.expander(f"#{i+1} {result.get('title', 'No title')[:50]}..."):
                        st.markdown(f"**URL:** {result.get('link', 'No URL')}")
                        st.markdown(f"**Snippet:** {result.get('snippet', 'No snippet')[:200]}...")
                        st.markdown(f"**Domain:** {result.get('displayed_link', result.get('domain', 'Unknown'))}")
            else:
                st.info("No organic results returned for this query.")
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
                        results = cached_analyze_serp_opportunities(serp_keyword)
                        if results and "error" not in results:
                            st.session_state.serp_results = results
                            st.success("✅ SERP analysis complete!")
                        elif results and "error" in results:
                            st.warning(f"⚠️ Analysis completed but limited data: {results['error']}")
                        else:
                            st.error("❌ SERP analysis failed. Please check your API keys and try again.")
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
            else:
                st.warning("⚠️ Please enter a keyword first.")   
    # Display results
    if "serp_results" in st.session_state and st.session_state.serp_results:
        results = st.session_state.serp_results        
        if "error" in results:
            st.error(f"❌ {results['error']}")
            return        
        st.markdown("### 📋 SERP Summary")
        st.info(results.get("summary", "No summary available"))       
        if "snippet_analysis" in results and results["snippet_analysis"]:
            snippet_analysis = results["snippet_analysis"]            
            if snippet_analysis["snippet_opportunities"]:
                st.markdown("### 💡 Snippet Opportunities")                
                for opp in snippet_analysis["snippet_opportunities"]:
                    with st.expander(f"{opp['type'].title()} - {opp['opportunity']}"):
                        st.markdown(f"**Recommendation:** {opp['recommendation']}")
                        st.markdown(f"**Priority:** {opp['priority']}")        
        if "paa_questions" in results and results["paa_questions"]:
            paa = results["paa_questions"]            
            if paa["questions"]:
                st.markdown("### ❓ People Also Ask Questions")                
                for q in paa["questions"][:5]:
                    st.markdown(f"**Q:** {q['question']}")
                    st.markdown(f"**A:** {q['snippet'][:150]}...")
                    st.markdown(f"**Content Idea:** {q['content_idea']}")
                    st.divider()        
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
