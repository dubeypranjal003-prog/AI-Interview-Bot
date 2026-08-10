"""
2_📄_Resume_Analysis.py
------------------------
Upload a PDF resume -> extract text -> rule-based analysis (skills found/
missing, projects, resume score). Detected skills are stashed in
st.session_state["resume_skills"] so the Start Interview page can use
them to personalize the question set.
"""

import sys
import os
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import init_db, get_or_create_candidate, save_resume_analysis
from src.resume_parser import extract_text_from_pdf, analyze_resume

st.set_page_config(page_title="Resume Analysis", page_icon="📄", layout="wide")
init_db()

st.title("📄 Resume Analysis")
st.write("Upload a PDF resume to get a resume score and let interview questions be personalized to your actual skills.")

name = st.text_input("Your Name (used to save this analysis)", value=st.session_state.get("candidate_name", ""))
resume_file = st.file_uploader("Upload PDF Resume", type=["pdf"])

if resume_file:
    try:
        text = extract_text_from_pdf(resume_file)
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Unexpected error reading this PDF: {e}")
        st.stop()

    analysis = analyze_resume(text)
    st.session_state["resume_skills"] = analysis["skills_found"]

    st.success("Resume analyzed successfully.")

    score = analysis["resume_score"]
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Resume Score", f"{score}/100")
        st.progress(score / 100)
    with col2:
        contact = analysis["contact"]
        st.write(f"**Detected name:** {contact['name'] or '—'}")
        st.write(f"**Email:** {contact['email'] or '—'}")
        st.write(f"**Phone:** {contact['phone'] or '—'}")

    st.markdown("#### Skills Found")
    if analysis["skills_found"]:
        st.write(" · ".join(f"`{s}`" for s in analysis["skills_found"]))
    else:
        st.caption("No skills from our vocabulary were detected — try a text-based (not scanned) PDF.")

    st.markdown("#### Skills You Might Add")
    st.write(" · ".join(f"`{s}`" for s in analysis["skills_missing"]) or "—")

    st.markdown("#### Projects Found")
    if analysis["projects_found"]:
        for p in analysis["projects_found"]:
            st.markdown(f"- {p}")
    else:
        st.caption("No project section detected. Make sure your resume has a clear 'Projects' heading.")

    with st.expander("📄 Extracted Resume Text (first 2000 characters)"):
        st.text(analysis["raw_text_excerpt"])

    if name.strip():
        candidate_id = get_or_create_candidate(name)
        save_resume_analysis(
            candidate_id=candidate_id,
            resume_score=analysis["resume_score"],
            skills_found=analysis["skills_found"],
            skills_missing=analysis["skills_missing"],
            projects_found=analysis["projects_found"],
            raw_text_excerpt=analysis["raw_text_excerpt"],
        )
        st.caption("Saved to your resume analysis history.")
    else:
        st.caption("Enter your name above to save this analysis to your history.")

    st.info(
        f"✅ Detected skills will be prioritized next time you start an interview "
        f"(check 'Personalize questions using my resume' on the Start Interview page)."
    )
else:
    st.caption("No resume uploaded yet.")
