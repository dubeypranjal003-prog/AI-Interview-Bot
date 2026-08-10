"""
3_📊_Dashboard.py
------------------
Analytics dashboard: summary metrics + charts built from the DB, using
src/analytics.py for the Pandas logic (keeps this file UI-only).
"""

import sys
import os
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import init_db, get_interview_history, get_skill_scores, get_all_scores
from src import analytics

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
init_db()

st.title("📊 Performance Analytics Dashboard")

history_df = get_interview_history()
skills_df = get_skill_scores()
scores_df = get_all_scores()

if history_df.empty:
    st.info("No interviews yet — complete one on the 🎤 Start Interview page to see analytics here.")
    st.stop()

metrics = analytics.summary_metrics(history_df)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Average Score", f"{metrics['avg_score']}/10")
c2.metric("Best Score", f"{metrics['best_score']}/10")
c3.metric("Lowest Score", f"{metrics['lowest_score']}/10")
c4.metric("Interviews Completed", metrics["num_interviews"])
c5.metric("Completion Rate", f"{metrics['completion_rate']}%")

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Average Score by Role")
    by_domain = analytics.score_by_domain(history_df)
    if not by_domain.empty:
        st.bar_chart(by_domain.set_index("role"))
    else:
        st.caption("Not enough completed interviews yet.")

with col2:
    st.subheader("Average Score by Difficulty")
    by_diff = analytics.score_by_difficulty(history_df)
    if not by_diff.empty:
        st.bar_chart(by_diff.set_index("difficulty"))
    else:
        st.caption("Not enough completed interviews yet.")

st.subheader("Score Trend Over Time")
trend = analytics.score_trend(history_df)
if not trend.empty:
    st.line_chart(trend.set_index("start_time"))
else:
    st.caption("Complete more interviews to see a trend.")

st.subheader("Skill-wise Performance")
skill_table = analytics.skill_gap_table(skills_df)
if not skill_table.empty:
    st.bar_chart(skill_table.set_index("skill_name"))
else:
    st.caption("No skill-level data yet.")

st.subheader("Toughest Questions (lowest average score)")
q_perf = analytics.question_performance(scores_df)
if not q_perf.empty:
    st.dataframe(q_perf.head(10), hide_index=True, use_container_width=True)
else:
    st.caption("No question-level data yet.")
