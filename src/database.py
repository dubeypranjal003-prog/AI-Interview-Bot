"""
database.py
------------
All SQLite access for the app lives here. Nothing in the UI code should
open a connection directly — this keeps schema changes and duplicate-
prevention logic in one place.

Schema (7 tables, matches the relationships used by the app):
    candidates        -> one row per person who has ever run an interview
    interviews        -> one row per interview session (links to a candidate)
    questions         -> a cache/mirror of data/questions.json inside the DB
    answers           -> one row per answered question in an interview
    scores            -> one row per answer, the score breakdown
    skills            -> per-interview, per-skill aggregated score
    resume_analysis   -> one row per uploaded resume
"""

import sqlite3
import os
import json
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interview_bot.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    interview_type TEXT NOT NULL,
    num_questions INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    overall_score REAL,
    status TEXT NOT NULL DEFAULT 'in_progress',
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    question_text TEXT NOT NULL,
    role TEXT,
    skill TEXT,
    difficulty TEXT,
    qtype TEXT,
    keywords TEXT,
    ideal_answer TEXT
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interview_id INTEGER NOT NULL,
    question_id INTEGER,
    question_text TEXT NOT NULL,
    skill TEXT,
    answer_text TEXT,
    time_taken_seconds REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (interview_id) REFERENCES interviews(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id INTEGER NOT NULL,
    relevance REAL,
    technical REAL,
    completeness REAL,
    clarity REAL,
    keyword_score REAL,
    final_score REAL,
    feedback_positive TEXT,
    feedback_improve TEXT,
    FOREIGN KEY (answer_id) REFERENCES answers(id)
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interview_id INTEGER NOT NULL,
    skill_name TEXT NOT NULL,
    avg_score REAL NOT NULL,
    FOREIGN KEY (interview_id) REFERENCES interviews(id)
);

CREATE TABLE IF NOT EXISTS resume_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    resume_score REAL,
    skills_found TEXT,
    skills_missing TEXT,
    projects_found TEXT,
    raw_text_excerpt TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);
"""


@contextmanager
def get_connection():
    """Context-managed connection so every caller commits/closes safely."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they don't exist yet. Safe to call every run."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def sync_questions_from_json(questions_path: str) -> None:
    """Load data/questions.json into the questions table (idempotent)."""
    if not os.path.exists(questions_path):
        return
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    with get_connection() as conn:
        cur = conn.cursor()
        for q in questions:
            cur.execute(
                """INSERT OR REPLACE INTO questions
                   (id, question_text, role, skill, difficulty, qtype, keywords, ideal_answer)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    q["id"], q["question"], q.get("role"), q.get("skill"),
                    q.get("difficulty"), q.get("type"),
                    json.dumps(q.get("keywords", [])), q.get("ideal_answer", ""),
                ),
            )


def get_or_create_candidate(name: str, email: Optional[str] = None) -> int:
    """Returns candidate_id, creating a row if this name hasn't been seen."""
    name = name.strip()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM candidates WHERE name = ? ORDER BY id DESC LIMIT 1", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO candidates (name, email, created_at) VALUES (?, ?, ?)",
            (name, email, datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def create_interview(candidate_id: int, role: str, difficulty: str,
                      interview_type: str, num_questions: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO interviews
               (candidate_id, role, difficulty, interview_type, num_questions, start_time, status)
               VALUES (?, ?, ?, ?, ?, ?, 'in_progress')""",
            (candidate_id, role, difficulty, interview_type, num_questions,
             datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def save_answer(interview_id: int, question_id: Optional[int], question_text: str,
                 skill: str, answer_text: str, time_taken_seconds: float,
                 score_breakdown: dict) -> int:
    """Saves one answer + its score breakdown in a single transaction."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO answers
               (interview_id, question_id, question_text, skill, answer_text,
                time_taken_seconds, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (interview_id, question_id, question_text, skill, answer_text,
             time_taken_seconds, datetime.now().isoformat(timespec="seconds")),
        )
        answer_id = cur.lastrowid
        cur.execute(
            """INSERT INTO scores
               (answer_id, relevance, technical, completeness, clarity, keyword_score,
                final_score, feedback_positive, feedback_improve)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                answer_id,
                score_breakdown["relevance"], score_breakdown["technical"],
                score_breakdown["completeness"], score_breakdown["clarity"],
                score_breakdown["keyword_score"], score_breakdown["final_score"],
                json.dumps(score_breakdown.get("positives", [])),
                json.dumps(score_breakdown.get("improvements", [])),
            ),
        )
        return answer_id


def finalize_interview(interview_id: int, overall_score: float, skill_scores: dict) -> None:
    """Marks an interview complete, guarding against double-submission on reruns."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM interviews WHERE id = ?", (interview_id,))
        row = cur.fetchone()
        if row is None or row[0] == "completed":
            return  # already finalized (e.g. a Streamlit rerun) -> no-op
        cur.execute(
            "UPDATE interviews SET end_time = ?, overall_score = ?, status = 'completed' WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), overall_score, interview_id),
        )
        for skill_name, avg in skill_scores.items():
            cur.execute(
                "INSERT INTO skills (interview_id, skill_name, avg_score) VALUES (?, ?, ?)",
                (interview_id, skill_name, avg),
            )


def save_resume_analysis(candidate_id: Optional[int], resume_score: float,
                          skills_found: list, skills_missing: list,
                          projects_found: list, raw_text_excerpt: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO resume_analysis
               (candidate_id, resume_score, skills_found, skills_missing,
                projects_found, raw_text_excerpt, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (candidate_id, resume_score, json.dumps(skills_found),
             json.dumps(skills_missing), json.dumps(projects_found),
             raw_text_excerpt, datetime.now().isoformat(timespec="seconds")),
        )


def get_interview_history():
    """Returns a pandas-ready list of dicts joining interviews + candidates."""
    import pandas as pd
    with get_connection() as conn:
        df = pd.read_sql_query(
            """SELECT i.id AS interview_id, c.name AS candidate, i.role, i.difficulty,
                      i.interview_type, i.num_questions, i.overall_score, i.status,
                      i.start_time, i.end_time
               FROM interviews i
               JOIN candidates c ON c.id = i.candidate_id
               ORDER BY i.id DESC""",
            conn,
        )
    return df


def get_all_scores():
    import pandas as pd
    with get_connection() as conn:
        df = pd.read_sql_query(
            """SELECT a.interview_id, a.skill, a.question_text, s.relevance, s.technical,
                      s.completeness, s.clarity, s.keyword_score, s.final_score, a.created_at
               FROM answers a
               JOIN scores s ON s.answer_id = a.id""",
            conn,
        )
    return df


def get_skill_scores():
    import pandas as pd
    with get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM skills", conn)
    return df


def get_candidate_previous_score(candidate_id: int, role: str, exclude_interview_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT overall_score FROM interviews
               WHERE candidate_id = ? AND role = ? AND status = 'completed' AND id != ?
               ORDER BY id DESC LIMIT 1""",
            (candidate_id, role, exclude_interview_id),
        )
        row = cur.fetchone()
        return row[0] if row else None
