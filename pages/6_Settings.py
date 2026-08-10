"""
6_⚙️_Settings.py
------------------
Shows current AI provider config (read from .env, never hard-coded) and
basic app info. No secrets are ever displayed here.
"""

import sys
import os
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ai_provider = os.getenv("AI_PROVIDER", "local")

st.subheader("AI Evaluation Provider")
st.write(f"Current provider: **{ai_provider}**")
st.caption(
    "Set AI_PROVIDER in a local .env file (never committed) to switch providers. "
    "The default 'local' provider uses SentenceTransformer + keyword scoring and needs no API key."
)

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

st.subheader("About")
st.write(
    "AI Interview Bot evaluates answers with a blended relevance / technical / "
    "completeness / clarity / keyword rubric — see `src/scoring.py` for the exact weights."
)
st.write("Database file: `interview_bot.db` (SQLite, created automatically on first run).")

st.subheader("Reset Local Data")
st.caption("This deletes all locally stored interview history. It cannot be undone.")
if st.button("🗑 Delete interview_bot.db", type="secondary"):
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interview_bot.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        st.success("Database deleted. It will be recreated the next time you visit any page.")
    else:
        st.info("No database file found.")
