"""
scoring.py
----------
Turns a candidate's raw answer text into a weighted score out of 10.

This is the rule-based / semantic-similarity baseline described in the
project brief (AI_PROVIDER=local). It intentionally does NOT compare the
answer to a single "correct" sentence — it blends five independent
signals so two differently-worded but correct answers can both score
well:

    Relevance     25%  - semantic similarity to the ideal answer
    Technical     30%  - coverage of the question's keyword/concepts
    Completeness  20%  - answer covers enough ground (length + concept count)
    Clarity       15%  - structural heuristics (sentence count, filler words)
    Keywords      10%  - same keyword list, weighted differently as a
                          lightweight "did they even mention the topic" check

If SentenceTransformer isn't available (e.g. no internet on first run),
`use_semantic=False` falls back to a pure keyword/heuristic score so the
app never crashes because of a missing model.
"""

from typing import List, Dict
import re

WEIGHTS = {
    "relevance": 0.25,
    "technical": 0.30,
    "completeness": 0.20,
    "clarity": 0.15,
    "keyword_score": 0.10,
}

FILLER_WORDS = {"basically", "like", "um", "uh", "actually", "stuff", "things", "etc"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _keyword_coverage(answer: str, keywords: List[str]) -> float:
    """Fraction (0-1) of the question's keywords mentioned in the answer."""
    if not keywords:
        return 0.5  # neutral score when no keyword list exists for this question
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return hits / len(keywords)


def _completeness_score(answer: str, ideal_answer: str) -> float:
    """
    Heuristic: compares answer length to the ideal answer's length (capped),
    plus rewards multi-sentence, structured answers over one-liners.
    """
    word_count = len(answer.split())
    ideal_word_count = max(len(ideal_answer.split()), 15)

    length_ratio = min(word_count / ideal_word_count, 1.2) / 1.2  # cap the reward
    sentence_count = len(re.split(r"[.!?]+", answer.strip())) if answer.strip() else 0
    structure_bonus = min(sentence_count / 3, 1.0)  # reward >=3 sentences

    return round(0.7 * length_ratio + 0.3 * structure_bonus, 3)


def _clarity_score(answer: str) -> float:
    """Heuristic: penalizes filler words and extremely short/run-on answers."""
    if not answer.strip():
        return 0.0

    words = answer.lower().split()
    filler_ratio = sum(1 for w in words if w.strip(",.") in FILLER_WORDS) / max(len(words), 1)
    filler_penalty = min(filler_ratio * 3, 0.5)

    sentences = [s for s in re.split(r"[.!?]+", answer) if s.strip()]
    avg_sentence_len = (len(words) / len(sentences)) if sentences else len(words)
    # Very short (<4 words) or very long (>40 words) average sentence length hurts clarity
    if avg_sentence_len < 4:
        length_penalty = 0.3
    elif avg_sentence_len > 40:
        length_penalty = 0.2
    else:
        length_penalty = 0.0

    base = 1.0
    return round(max(base - filler_penalty - length_penalty, 0.0), 3)


def evaluate_answer(
    answer: str,
    ideal_answer: str,
    keywords: List[str],
    embed_fn=None,
) -> Dict:
    """
    Returns a full score breakdown dict:
        relevance, technical, completeness, clarity, keyword_score (all 0-10)
        final_score (0-10, weighted)
        positives / improvements (lists of short strings for feedback)

    embed_fn: optional callable(list[str]) -> embeddings, used for semantic
    relevance. Pass None to skip semantic scoring (keyword-only fallback).
    """
    answer = _clean(answer)

    if not answer:
        zero = {k: 0.0 for k in ["relevance", "technical", "completeness", "clarity", "keyword_score"]}
        zero["final_score"] = 0.0
        zero["positives"] = []
        zero["improvements"] = ["No answer was submitted."]
        return zero

    # --- Relevance (semantic similarity 0-1, scaled to 0-10) ---
    relevance_0_1 = 0.5
    if embed_fn is not None and ideal_answer:
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            emb = embed_fn([answer, ideal_answer])
            relevance_0_1 = float(cosine_similarity([emb[0]], [emb[1]])[0][0])
            relevance_0_1 = max(0.0, min(relevance_0_1, 1.0))
        except Exception:
            relevance_0_1 = _keyword_coverage(answer, keywords)  # graceful fallback
    else:
        relevance_0_1 = _keyword_coverage(answer, keywords)

    technical_0_1 = _keyword_coverage(answer, keywords)
    completeness_0_1 = _completeness_score(answer, ideal_answer)
    clarity_0_1 = _clarity_score(answer)
    keyword_0_1 = _keyword_coverage(answer, keywords)

    scores_0_1 = {
        "relevance": relevance_0_1,
        "technical": technical_0_1,
        "completeness": completeness_0_1,
        "clarity": clarity_0_1,
        "keyword_score": keyword_0_1,
    }

    final_0_1 = sum(scores_0_1[k] * WEIGHTS[k] for k in WEIGHTS)
    result = {k: round(v * 10, 2) for k, v in scores_0_1.items()}
    result["final_score"] = round(final_0_1 * 10, 2)
    result["positives"], result["improvements"] = _build_feedback_notes(scores_0_1, keywords, answer)
    return result


def _build_feedback_notes(scores_0_1: Dict[str, float], keywords: List[str], answer: str):
    positives, improvements = [], []

    if scores_0_1["relevance"] >= 0.7:
        positives.append("Your answer is closely aligned with what the question is asking.")
    if scores_0_1["technical"] >= 0.6:
        positives.append("Good coverage of the key technical concepts.")
    if scores_0_1["completeness"] >= 0.7:
        positives.append("The answer is appropriately detailed and well structured.")
    if scores_0_1["clarity"] >= 0.8:
        positives.append("Clear, well-organized explanation.")
    if not positives:
        positives.append("You attempted the core idea of the question.")

    if scores_0_1["technical"] < 0.5:
        missing = [kw for kw in keywords if kw.lower() not in answer.lower()][:3]
        if missing:
            improvements.append(f"Try mentioning: {', '.join(missing)}.")
        else:
            improvements.append("Add more of the key technical terms this question expects.")
    if scores_0_1["completeness"] < 0.5:
        improvements.append("Expand your answer with a concrete example or more detail.")
    if scores_0_1["clarity"] < 0.6:
        improvements.append("Tighten the explanation — shorter sentences, fewer filler words.")
    if scores_0_1["relevance"] < 0.5:
        improvements.append("Focus more directly on what the question is actually asking.")
    if not improvements:
        improvements.append("Consider mentioning a real-world example or edge case for extra depth.")

    return positives[:3], improvements[:3]


def performance_label(score_out_of_10: float) -> str:
    if score_out_of_10 >= 8:
        return "Strong Candidate"
    if score_out_of_10 >= 6.5:
        return "Good Candidate"
    if score_out_of_10 >= 4.5:
        return "Needs Improvement"
    return "Weak — More Practice Needed"
