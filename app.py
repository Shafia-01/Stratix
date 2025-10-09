import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import time
import random
from dotenv import load_dotenv
from src.agent import run_agent
from src.db_client import fetch_past_results
from src.trends_client import get_trend_score
from src.competitor_client import get_competitor_data

# ------------------------- SETUP -------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# List of fallback models
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
                print(f"⚠️ {model_name} quota hit, trying next...")
                time.sleep(random.uniform(1, 3))
                continue
            else:
                print(f"❌ {model_name} failed: {e}")
                continue
    return "⚠️ All Gemini models are currently unavailable. Try again later."

# ------------------------- UI CONFIG -------------------------
st.set_page_config(page_title="GemKey AI", page_icon="💎", layout="wide")
st.title("💎 GemKey AI — Conversational SEO Research Assistant")

st.markdown(
    "Welcome to **GemKey AI**, your AI-powered SEO assistant 🤖\n\n"
    "Type a keyword or ask in natural language — for example:\n"
    "- `global internship`\n"
    "- `find low competition keywords for AI careers`\n"
    "- `generate blog ideas for eco-friendly fashion`\n"
    "- `explain keyword difficulty`\n\n"
    "GemKey AI will automatically detect your intent and respond intelligently!"
)

# ------------------------- CHAT STATE -------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ------------------------- INTENT DETECTION -------------------------
def detect_intent(user_input: str) -> str:
    """Use Gemini (with fallback) to detect what the user wants."""
    intent_prompt = f"""
    You are GemKey AI, an SEO assistant.
    Determine what the user wants to do from this message: "{user_input}"
    Choose one of:
      1. Generate Keywords
      2. Show SEO Trends
      3. Generate Content Ideas
      4. Explain SEO Concept
    """
    return safe_gemini_call(intent_prompt).lower()

# ------------------------- STYLING -------------------------
def highlight_difficulty(val):
    if not isinstance(val, str):
        return ""
    if "Easy" in val:
        return "background-color: #C6F6D5"
    elif "Medium" in val:
        return "background-color: #FEF3C7"
    elif "Hard" in val:
        return "background-color: #FECACA"
    return ""

# ------------------------- INTENT HANDLER -------------------------
def handle_intent(user_input: str, intent: str):
    """Route request to correct function based on intent."""
    
    # 1️⃣ Keyword generation
    if "keyword" in intent or len(user_input.split()) <= 3:
        try:
            data = run_agent(user_input)
            if isinstance(data, pd.DataFrame) and not data.empty:
                st.markdown("### 📊 Keyword Performance Overview")
                top_data = data.head(15)
                for idx, row in top_data.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(
                            f"**{idx+1}. {row['keyword']}**  \n"
                            f"📈 Score: {row['score']} | 💰 CPC: {row['cpc']} | 🔍 Volume: {row['volume']}  \n"
                            f"{row['difficulty']} | {row['intent']} | 🔥 Trend: {row['trend']}"
                        )
                    with col2:
                        if st.button("View Competitors", key=f"comp_{idx}"):
                            competitors = get_competitor_data(row["keyword"])
                            if competitors:
                                st.markdown(f"#### 🕵️ Competitor Insights for: **{row['keyword']}**")
                                for comp in competitors:
                                    st.markdown(
                                        f"**{comp['rank']}. [{comp['title']}]({comp['link']})**  \n"
                                        f"🌐 {comp['domain']}  \n"
                                        f"📝 *{comp['snippet']}*"
                                    )
                            else:
                                st.warning(f"No competitor data found for '{row['keyword']}'.")
                    with col3:
                        st.write("")
                        st.divider()
                
                # Default competitor insights
                top_kw = data.iloc[0]["keyword"]
                st.markdown("---")
                st.subheader(f"🕵️ Competitor Insights for: **{top_kw}**")
                competitors = get_competitor_data(top_kw)
                if competitors:
                    for comp in competitors:
                        st.markdown(
                            f"**{comp['rank']}. [{comp['title']}]({comp['link']})**  \n"
                            f"🌐 {comp['domain']}  \n"
                            f"📝 *{comp['snippet']}*"
                        )
                else:
                    st.warning(f"No competitor data found for '{top_kw}'.")
            else:
                return f"⚠️ No keywords generated for '{user_input}'.", None
        except Exception as e:
            return f"❌ Error generating keywords: {e}", None

    # 2️⃣ Trends
    elif "trend" in intent:
        st.markdown(f"📈 Fetching Google Trends for top keywords related to '{user_input}'...")
        trend_df = get_trend_score([user_input])
        if not trend_df.empty:
            st.line_chart(trend_df.set_index("date"))
            return "✅ Trend chart generated below.", None
        else:
            return f"⚠️ No trend data available for '{user_input}'.", None

    # 3️⃣ Content ideas
    elif "content" in intent:
        prompt = f"Generate 3 catchy blog titles and 1 meta description for the topic '{user_input}'."
        try:
            result = safe_gemini_call(prompt)
            return f"🧠 Content Ideas:\n\n{result}", None
        except Exception as e:
            return f"Error generating content ideas: {e}", None

    # 4️⃣ SEO explanation
    else:
        explain_prompt = f"Explain briefly the SEO concept: '{user_input}'."
        try:
            result = safe_gemini_call(explain_prompt)
            return result, None
        except Exception as e:
            return f"Error explaining concept: {e}", None

# ------------------------- VIEW HISTORY -------------------------
st.markdown("---")
st.subheader("📂 View Past Keyword Searches")

if st.button("Show Previous Runs"):
    with st.spinner("Fetching past results..."):
        df_prev = fetch_past_results(limit=50)
        if not df_prev.empty:
            st.success(f"Showing the latest {len(df_prev)} results from database.")
            styled_prev = df_prev.style.map(highlight_difficulty, subset=["difficulty"])
            st.dataframe(styled_prev, use_container_width=True)
        else:
            st.warning("No previous data found yet. Try running a keyword search first.")

# ------------------------- MAIN CHAT -------------------------
prompt = st.chat_input("Type your query or keyword...")

if prompt:
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            intent = detect_intent(prompt)
            text_reply, styled_table = handle_intent(prompt, intent)
            st.markdown(text_reply)
            if styled_table is not None:
                st.dataframe(styled_table, use_container_width=True)

    st.session_state["messages"].append({"role": "assistant", "content": text_reply})
