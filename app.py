"""
app.py
------
Home / landing page. Streamlit auto-discovers everything in pages/ and
builds the sidebar navigation for us — this file only needs to render
the Home content and do one-time app bootstrap (DB init, CSS, session
defaults) that every page can rely on having already run.
"""

import os
import streamlit as st
from src.database import init_db, sync_questions_from_json

st.set_page_config(
    page_title="AI Interview Bot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# ONE-TIME APP BOOTSTRAP (runs on every page via st.session_state guard)
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
QUESTIONS_PATH = os.path.join(BASE_DIR, "data", "questions.json")


def load_css():
    css_path = os.path.join(BASE_DIR, "assets", "styles.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


if "_bootstrapped" not in st.session_state:
    try:
        init_db()
        sync_questions_from_json(QUESTIONS_PATH)
        st.session_state["_bootstrapped"] = True
        st.session_state["_bootstrap_error"] = None
    except Exception as e:
        st.session_state["_bootstrapped"] = True
        st.session_state["_bootstrap_error"] = str(e)

load_css()

if st.session_state.get("_bootstrap_error"):
    st.error(f"⚠️ Startup issue: {st.session_state['_bootstrap_error']}")

# ---------------------------------------------------------------------
# LANDING PAGE CONTENT
# ---------------------------------------------------------------------
st.title("🎯 AI-Powered Interview Assessment Platform")
st.markdown(
    "Practice interviews, receive AI-powered feedback, identify skill gaps, "
    "and track your improvement over time."
)

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

cols = st.columns(3)
features = [
    ("🤖", "AI Evaluation", "Answers are scored on relevance, technical accuracy, completeness, and clarity — not just similarity to one sample answer."),
    ("📄", "Resume Analysis", "Upload a PDF resume to get a resume score and interview questions personalized to your actual skills."),
    ("🎯", "Personalized Questions", "Choose a role, difficulty, and interview type — SQL, Excel, Python, Statistics, Power BI, and more for Data Analyst tracks."),
    ("📊", "Performance Analytics", "A dashboard tracks your average score, best/lowest score, and score trends across all your interviews."),
    ("📈", "Skill Gap Analysis", "See which skills need the most work, ranked by your average score on questions in that skill."),
    ("📥", "Interview Reports", "Every interview produces a downloadable CSV report with your questions, answers, scores, and feedback."),
]
for i, (icon, title, desc) in enumerate(features):
    with cols[i % 3]:
        st.markdown(
            f"<div class='feature-card'><h4>{icon} {title}</h4><p>{desc}</p></div>",
            unsafe_allow_html=True,
        )
        st.write("")

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

st.subheader("Ready to practice?")
st.write("Use the sidebar to go to **🎤 Start Interview**, or upload your resume first on **📄 Resume Analysis** for personalized questions.")

if st.button("🚀 Start Interview", type="primary"):
    st.info("Open **🎤 Start Interview** from the sidebar to begin.")

st.caption(
    "Note: this app uses a local sentence-similarity + keyword scoring engine by default "
    "(AI_PROVIDER=local in .env). It does not send your answers to an external LLM unless "
    "you configure one — see README.md."
)
