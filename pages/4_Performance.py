"""
4_📈_Performance.py
--------------------
Skill Gap Analysis: shows a progress-bar breakdown per skill and
recommends which skills to prioritize, based on average scores stored
in the `skills` table across all completed interviews.
"""

import sys
import os
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import init_db, get_skill_scores
from src import analytics

st.set_page_config(page_title="Performance", page_icon="📈", layout="wide")
init_db()

st.title("📈 Skill Gap Analysis")

skills_df = get_skill_scores()

if skills_df.empty:
    st.info("Complete an interview first — skill-level scores will appear here.")
    st.stop()

table = analytics.skill_gap_table(skills_df)

st.subheader("📊 Skill Gap Breakdown")
for _, row in table.iterrows():
    pct = max(min(row["avg_score"] / 10, 1.0), 0.0)
    st.write(f"**{row['skill_name']}** — {row['avg_score']}/10")
    st.progress(pct)

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

st.subheader("🎯 Priority Skills to Improve")
weakest = analytics.priority_skills(skills_df, top_n=3)
if weakest:
    for i, skill in enumerate(weakest, start=1):
        st.markdown(f"{i}. **{skill}**")

    st.markdown("#### Suggested Focus")
    recs = {
        "SQL": "Practice window functions, CTEs, and multi-table joins on a site like LeetCode/StrataScratch.",
        "Python": "Work through Pandas groupby/merge exercises on real messy datasets.",
        "Statistics": "Review hypothesis testing, p-values, and confidence intervals with worked examples.",
        "Power BI": "Build a small end-to-end dashboard: Power Query cleaning -> data model -> DAX measures.",
        "Excel": "Practice INDEX-MATCH, pivot tables, and SUMIFS/COUNTIFS on a sample sales dataset.",
        "Data Cleaning": "Practice handling missing values, duplicates, and inconsistent categories in Pandas or Excel.",
        "Case Study": "Practice structuring business problems: clarify scope -> segment -> hypothesize -> validate.",
    }
    for skill in weakest:
        if skill in recs:
            st.markdown(f"- **{skill}:** {recs[skill]}")
else:
    st.caption("Not enough data yet to recommend priority skills.")
