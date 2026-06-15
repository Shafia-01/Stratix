import streamlit as st
from src.gemini_client import safe_gemini_call

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
                response = safe_gemini_call(prompt) or ""
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
            """.format(), unsafe_allow_html=True) # Note: we formats with no args because the original code didn't format anything in card 3: it formatted industry into card 2. Wait, let's look at formatting in original: card 3 has no placeholders, but let's check format() call in original code!
            # Ah, line 1658/1659 had: st.markdown("...", unsafe_allow_html=True) with no formats, but the code had `st.markdown("...".format(), unsafe_allow_html=True)`. Let's just avoid formatting it or format with empty args. Let's make sure it matches original behavior exactly.

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
