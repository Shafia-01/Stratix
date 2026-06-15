import streamlit as st
import re
from src.gemini_client import safe_gemini_call
from src.services.metrics_service import increment_daily_requests, add_recent_search

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
                            response = safe_gemini_call(prompt) or ""
                            # Parse response
                            intent_type = "informational"  # default
                            reasoning = response
                            intent_match = re.search(r"intent(?:\s*type)?\s*:\s*([a-zA-Z ]+)", response, re.IGNORECASE)
                            if intent_match:
                                extracted_intent = intent_match.group(1).strip().lower()
                                for candidate in ["transactional", "commercial", "navigational", "informational"]:
                                    if candidate in extracted_intent:
                                        intent_type = candidate
                                        break
                            else:
                                response_lower = response.lower()
                                if "transactional" in response_lower:
                                    intent_type = "transactional"
                                elif "navigational" in response_lower:
                                    intent_type = "navigational"
                                elif "commercial" in response_lower:
                                    intent_type = "commercial"
                            reasoning = ""
                            reasoning_match = re.search(r"reasoning\s*:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
                            if reasoning_match:
                                reasoning = reasoning_match.group(1).strip()
                            if not reasoning:
                                reasoning = response.strip()
                            reasoning_lines = []
                            for line in reasoning.splitlines():
                                stripped = line.strip()
                                if not stripped:
                                    continue
                                lowered = stripped.lower()
                                if lowered.startswith("intent type") or lowered.startswith("intent:"):
                                    continue
                                reasoning_lines.append(stripped)
                            reasoning = " ".join(reasoning_lines).strip()
                            intent_results.append({
                                "keyword": keyword,
                                "intent_type": intent_type,
                                "reasoning": reasoning
                            })
                        st.session_state.intent_results = intent_results
                        add_recent_search(keywords[0])
                        increment_daily_requests()
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
            st.markdown(f"**{intent_color} {result['keyword']}**")
            st.markdown(f"**Intent Type:** {result['intent_type'].title()}")
            clean_reasoning = result['reasoning'].strip().strip('*').strip()
            st.markdown(f"**Reasoning:** {clean_reasoning}")
            st.divider()
