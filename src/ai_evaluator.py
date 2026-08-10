"""
ai_evaluator.py
---------------
Thin wrapper around scoring.py that owns the SentenceTransformer model
(cached so it loads once per server process) and decides which follow-up
question to ask next based on how strong the last answer was.

If sentence-transformers/the model download fails (no internet, first
run in an offline environment, etc.) the app falls back to the
keyword-only scorer in scoring.py instead of crashing.
"""

import streamlit as st
from .scoring import evaluate_answer, performance_label  # noqa: F401 (re-exported)

MODEL_NAME = "all-MiniLM-L6-v2"


@st.cache_resource(show_spinner="Loading AI evaluation model...")
def load_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(MODEL_NAME)
    except Exception as e:  # model download / import failure
        st.session_state["_model_load_error"] = str(e)
        return None


def get_embed_fn():
    """Returns an embed_fn(list[str]) usable by scoring.evaluate_answer, or None."""
    model = load_model()
    if model is None:
        return None

    def _embed(texts):
        return model.encode(texts)

    return _embed


def score_answer(answer_text: str, question: dict) -> dict:
    """Convenience wrapper: scores one answer against one question dict."""
    return evaluate_answer(
        answer=answer_text,
        ideal_answer=question.get("ideal_answer", ""),
        keywords=question.get("keywords", []),
        embed_fn=get_embed_fn(),
    )


def pick_follow_up(question: dict, final_score: float) -> str:
    """
    Returns a follow-up question string based on answer strength.
    Strong answer (>=7/10) -> deeper follow-up.
    Weak answer (<5/10)    -> simpler follow-up.
    Otherwise              -> no follow-up (None).
    """
    if final_score >= 7 and question.get("follow_up_strong"):
        return question["follow_up_strong"]
    if final_score < 5 and question.get("follow_up_weak"):
        return question["follow_up_weak"]
    return None
