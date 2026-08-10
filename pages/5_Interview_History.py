"""
5_📝_Interview_History.py
---------------------------
Browsable, filterable history of past interviews with a CSV export.
"""

import sys
import os
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import init_db, get_interview_history

st.set_page_config(page_title="Interview History", page_icon="📝", layout="wide")
init_db()

st.title("📝 Interview History")

df = get_interview_history()

if df.empty:
    st.info("No interviews recorded yet.")
    st.stop()

with st.expander("🔎 Filters", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        candidates = ["All"] + sorted(df["candidate"].unique().tolist())
        candidate_filter = st.selectbox("Candidate", candidates)
    with c2:
        roles = ["All"] + sorted(df["role"].unique().tolist())
        role_filter = st.selectbox("Role", roles)
    with c3:
        difficulties = ["All"] + sorted(df["difficulty"].unique().tolist())
        difficulty_filter = st.selectbox("Difficulty", difficulties)

filtered = df.copy()
if candidate_filter != "All":
    filtered = filtered[filtered["candidate"] == candidate_filter]
if role_filter != "All":
    filtered = filtered[filtered["role"] == role_filter]
if difficulty_filter != "All":
    filtered = filtered[filtered["difficulty"] == difficulty_filter]

st.dataframe(
    filtered[["interview_id", "candidate", "role", "difficulty", "interview_type",
              "num_questions", "overall_score", "status", "start_time"]],
    hide_index=True, use_container_width=True,
)

csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download Filtered History (CSV)", data=csv_bytes,
                    file_name="interview_history.csv", mime="text/csv")

completed = filtered[filtered["status"] == "completed"].sort_values("interview_id")
if len(completed) >= 2:
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.subheader("📈 Score Improvement")
    prev, curr = completed.iloc[-2], completed.iloc[-1]
    delta = round(curr["overall_score"] - prev["overall_score"], 2)
    st.metric(
        f"{curr['candidate']} — {curr['role']}",
        f"{curr['overall_score']}/10",
        delta=f"{delta:+.2f} vs previous ({prev['overall_score']}/10)",
    )
