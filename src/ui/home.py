import streamlit as st
import base64

def load_base64_image(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def render_home_overview():
    try:
        logo_base64 = load_base64_image("assets/keylytics_icon.png")
    except Exception:
        logo_base64 = ""

    # Welcome section
    st.markdown(f"""
    <div style="width:100%; display:flex; justify-content:center;">
        <div class="home-container">
            <div class="welcome-section">
                <div class="app-logo" style="margin-bottom: -35px; margin-top: -150px;" >
                    <img src="data:image/png;base64,{logo_base64}" width="150" style="vertical-align:middle; margin:0; padding:0;" />
                </div>
                <h1 class="app-title">KeyLytics</h1>
                <p class="app-subtitle">Advanced SEO Research & Analysis Platform</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick buttons using Streamlit buttons
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3, col4, col5 = st.columns(5)
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
    with col5:
        if st.button("🤖 Agent Mode", use_container_width=True):
            st.session_state.current_page = "agent_mode"
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
            if st.button("🤖 Agent Mode", key="fp_am", use_container_width=True):
                st.session_state.current_page = "agent_mode"
                st.rerun()

