import streamlit as st
from src.agent import run_agent
import pandas as pd

st.title("🌟 GemKey AI — SEO Keyword Research Agent")
seed = st.text_input("Enter Seed Keyword:")
if st.button("Generate Keywords"):
    with st.spinner("Fetching keywords..."):
        data = run_agent(seed)
        df = pd.DataFrame(data, columns=["Seed", "Keyword", "Volume", "Competition", "CPC", "Score"])
        st.dataframe(df.sort_values(by="Score", ascending=False).head(50))
