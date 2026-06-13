import streamlit as st
from src.gemini_client import safe_gemini_call

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
