"""
1_🎤_Start_Interview.py
------------------------
The core interview flow: candidate setup -> question loop (answer, score,
feedback, optional follow-up) -> final report + save to DB.

Duplicate-save protection: finalize_interview() in src/database.py checks
the interview's status before writing, so a Streamlit rerun after
completion can never insert the same result twice.
"""

import sys
import os
import time
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import (
    init_db, get_or_create_candidate, create_interview,
    save_answer, finalize_interview, get_candidate_previous_score,
)
from src.question_engine import ALL_ROLES, DIFFICULTIES, INTERVIEW_TYPES, select_questions
from src.ai_evaluator import score_answer, pick_follow_up, performance_label

st.set_page_config(page_title="Start Interview", page_icon="🎤", layout="wide")
init_db()

st.title("🎤 Start Interview")

TIME_LIMIT_OPTIONS = {"30 seconds": 30, "1 minute": 60, "2 minutes": 120, "5 minutes": 300, "No limit": None}


# ---------------------------------------------------------------------
# SETUP FORM
# ---------------------------------------------------------------------
if "interview_active" not in st.session_state:
    st.session_state.interview_active = False

if not st.session_state.interview_active:

    with st.form("interview_setup"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Your Name *")
            role = st.selectbox("Job Role", ALL_ROLES)
            difficulty = st.selectbox("Difficulty", DIFFICULTIES, index=1)
        with col2:
            interview_type = st.selectbox("Interview Type", INTERVIEW_TYPES)
            num_questions = st.slider("Number of Questions", 2, 10, 5)
            time_choice = st.selectbox("Time per Question", list(TIME_LIMIT_OPTIONS.keys()), index=1)

        use_resume = st.checkbox(
            "Personalize questions using my uploaded resume skills (visit 📄 Resume Analysis first)",
            value=bool(st.session_state.get("resume_skills")),
        )

        submitted = st.form_submit_button("🚀 Start Interview", type="primary")

    if submitted:
        if not name.strip():
            st.error("Please enter your name before starting.")
        else:
            preferred_skills = st.session_state.get("resume_skills", []) if use_resume else []
            questions = select_questions(role, difficulty, interview_type, num_questions, preferred_skills)

            if not questions:
                st.error(
                    f"No questions found for **{role} / {difficulty} / {interview_type}**. "
                    "Try a different combination (e.g. Interview Type = Mixed)."
                )
            else:
                candidate_id = get_or_create_candidate(name)
                interview_id = create_interview(candidate_id, role, difficulty, interview_type, len(questions))

                st.session_state.interview_active = True
                st.session_state.candidate_name = name
                st.session_state.candidate_id = candidate_id
                st.session_state.interview_id = interview_id
                st.session_state.role = role
                st.session_state.difficulty = difficulty
                st.session_state.interview_type = interview_type
                st.session_state.time_limit = TIME_LIMIT_OPTIONS[time_choice]
                st.session_state.questions_queue = questions
                st.session_state.qno = 0
                st.session_state.total_score = 0.0
                st.session_state.skill_scores = {}
                st.session_state.report_rows = []
                st.session_state.pending_follow_up = None
                st.session_state.question_start_time = time.time()
                st.rerun()

    st.stop()


# ---------------------------------------------------------------------
# INTERVIEW LOOP
# ---------------------------------------------------------------------
questions_queue = st.session_state.questions_queue
qno = st.session_state.qno
total = len(questions_queue)

if qno < total:
    current_q = st.session_state.get("pending_follow_up") or questions_queue[qno]
    is_follow_up = st.session_state.get("pending_follow_up") is not None

    # Progress
    st.progress(qno / total, text=f"Question {qno + 1} of {total}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Answered", qno)
    m2.metric("Remaining", total - qno)
    m3.metric(
        "Current Avg",
        f"{round(st.session_state.total_score / qno, 2)}/10" if qno else "—",
    )

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

    label = "🔁 Follow-up Question" if is_follow_up else f"Question {qno + 1}"
    st.subheader(label)
    st.info(current_q["question"] if isinstance(current_q, dict) else current_q)
    st.caption(f"Skill: {current_q.get('skill', 'General')} · Type: {current_q.get('type', '')}")

    if st.session_state.time_limit:
        elapsed = time.time() - st.session_state.question_start_time
        remaining = max(0, int(st.session_state.time_limit - elapsed))
        mins, secs = divmod(remaining, 60)
        st.warning(f"⏱ Time Remaining (approx, updates on interaction): {mins:02d}:{secs:02d}")
        if remaining <= 0:
            st.caption("Time's up — submit your answer now, or it will be scored as-is on submit.")

    answer_key = f"answer_{qno}_{'fu' if is_follow_up else 'main'}"
    user_answer = st.text_area("Write Your Answer", key=answer_key, height=150)

    if st.button("Submit Answer", key=f"submit_{qno}_{'fu' if is_follow_up else 'main'}", type="primary"):
        time_taken = round(time.time() - st.session_state.question_start_time, 1)

        question_dict = current_q if isinstance(current_q, dict) else {"question": current_q, "keywords": [], "ideal_answer": ""}
        result = score_answer(user_answer, question_dict)

        save_answer(
            interview_id=st.session_state.interview_id,
            question_id=question_dict.get("id"),
            question_text=question_dict["question"],
            skill=question_dict.get("skill", "General"),
            answer_text=user_answer,
            time_taken_seconds=time_taken,
            score_breakdown=result,
        )

        skill = question_dict.get("skill", "General")
        st.session_state.skill_scores.setdefault(skill, []).append(result["final_score"])
        st.session_state.total_score += result["final_score"]
        st.session_state.report_rows.append({
            "question": question_dict["question"],
            "skill": skill,
            "answer": user_answer,
            "score": result["final_score"],
        })

        st.success(f"Score: {result['final_score']}/10")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Relevance", f"{result['relevance']}/10")
        c2.metric("Technical", f"{result['technical']}/10")
        c3.metric("Completeness", f"{result['completeness']}/10")
        c4.metric("Clarity", f"{result['clarity']}/10")

        st.markdown("**What you did well**")
        for p in result["positives"]:
            st.markdown(f"✔ {p}")
        st.markdown("**What you can improve**")
        for imp in result["improvements"]:
            st.markdown(f"⚠ {imp}")

        st.markdown("**Ideal Answer**")
        st.info(question_dict.get("ideal_answer", "No reference answer available for this question."))
        st.markdown("**Interview Tip**")
        st.caption("Structure answers as: definition -> how it works -> a concrete example. It signals depth fast.")

        # Decide follow-up vs advance
        follow_up_text = pick_follow_up(question_dict, result["final_score"]) if not is_follow_up else None
        if follow_up_text:
            st.session_state.pending_follow_up = {
                "question": follow_up_text, "skill": skill, "type": question_dict.get("type", "Technical"),
                "keywords": question_dict.get("keywords", []), "ideal_answer": "",
            }
        else:
            st.session_state.pending_follow_up = None
            st.session_state.qno += 1

        st.session_state.question_start_time = time.time()
        time.sleep(0.6)
        st.rerun()

else:
    # -------------------------------------------------------------
    # FINAL REPORT
    # -------------------------------------------------------------
    num_answered = len(st.session_state.report_rows)
    final_score = round(st.session_state.total_score / num_answered, 2) if num_answered else 0.0
    skill_avgs = {
        skill: round(sum(vals) / len(vals), 2)
        for skill, vals in st.session_state.skill_scores.items()
    }

    finalize_interview(st.session_state.interview_id, final_score, skill_avgs)

    st.balloons()
    st.success(f"🎉 Interview Completed: {st.session_state.candidate_name}")

    st.markdown("### 📄 AI Interview Performance Report")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Role", st.session_state.role)
    r2.metric("Difficulty", st.session_state.difficulty)
    r3.metric("Questions", num_answered)
    r4.metric("Overall Score", f"{final_score}/10")

    st.markdown(f"**Performance:** {performance_label(final_score)}")

    prev_score = get_candidate_previous_score(
        st.session_state.candidate_id, st.session_state.role, st.session_state.interview_id
    )
    if prev_score is not None:
        delta = round(final_score - prev_score, 2)
        st.metric("Compared to your previous attempt in this role", f"{final_score}/10", delta=delta)

    st.markdown("#### Skill-wise Performance")
    if skill_avgs:
        import pandas as pd
        skill_df = pd.DataFrame(list(skill_avgs.items()), columns=["Skill", "Avg Score (/10)"])
        st.dataframe(skill_df, hide_index=True, use_container_width=True)
    else:
        st.caption("No skill breakdown available.")

    st.markdown("#### Question-by-Question Detail")
    import pandas as pd
    detail_df = pd.DataFrame(st.session_state.report_rows)
    st.dataframe(detail_df, hide_index=True, use_container_width=True)

    csv_bytes = detail_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download CSV Report", data=csv_bytes,
        file_name=f"interview_report_{st.session_state.interview_id}.csv", mime="text/csv",
    )

    if st.button("🔄 Start a New Interview"):
        keep_resume_skills = st.session_state.get("resume_skills")
        st.session_state.clear()
        if keep_resume_skills:
            st.session_state["resume_skills"] = keep_resume_skills
        st.rerun()
