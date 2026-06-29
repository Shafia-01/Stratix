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

