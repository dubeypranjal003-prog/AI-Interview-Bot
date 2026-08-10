"""
question_engine.py
-------------------
Loads the question bank from data/questions.json and selects a question
set for an interview, optionally personalized using skills detected in
the candidate's resume (see resume_parser.personalized_skill_focus).
"""

import json
import os
import random
from typing import List, Dict, Optional

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "questions.json")

ALL_ROLES = [
    "HR", "Data Analyst", "Data Scientist", "Python Developer",
    "SQL Developer", "Machine Learning", "Business Analyst", "Software Developer",
]

DIFFICULTIES = ["Easy", "Medium", "Hard", "Expert"]
INTERVIEW_TYPES = ["Technical", "HR", "Behavioral", "Case Study", "Mixed"]


def load_question_bank() -> List[Dict]:
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _difficulty_at_or_below(target: str) -> List[str]:
    """Lets 'Hard' interviews also draw from Easy/Medium if Hard pool is thin."""
    idx = DIFFICULTIES.index(target) if target in DIFFICULTIES else 1
    return DIFFICULTIES[: idx + 1]


def select_questions(
    role: str,
    difficulty: str,
    interview_type: str,
    num_questions: int,
    preferred_skills: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Filters the bank by role + difficulty (with graceful widening if too few
    match) and interview type, then prioritizes questions whose `skill`
    matches something found on the candidate's resume.
    """
    bank = load_question_bank()
    preferred_skills = preferred_skills or []

    def matches_type(q):
        if interview_type == "Mixed":
            return True
        return q["type"] == interview_type

    pool = [q for q in bank if q["role"] == role and matches_type(q)]

    # widen difficulty pool if there aren't enough exact matches
    exact = [q for q in pool if q["difficulty"] == difficulty]
    if len(exact) >= num_questions:
        candidates = exact
    else:
        allowed = _difficulty_at_or_below(difficulty)
        candidates = [q for q in pool if q["difficulty"] in allowed]
        if len(candidates) < num_questions:
            candidates = pool  # last resort: any difficulty for this role/type

    if not candidates:
        return []

    # personalization: rank resume-matching skills first, then shuffle within groups
    preferred = [q for q in candidates if q.get("skill") in preferred_skills]
    rest = [q for q in candidates if q not in preferred]
    random.shuffle(preferred)
    random.shuffle(rest)
    ordered = preferred + rest

    return ordered[: min(num_questions, len(ordered))]


def get_question_by_text(question_text: str) -> Optional[Dict]:
    bank = load_question_bank()
    for q in bank:
        if q["question"] == question_text:
            return q
    return None
