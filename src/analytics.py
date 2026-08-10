"""
analytics.py
------------
Pure data-crunching for the Dashboard and Performance pages. Takes the
DataFrames returned by src/database.py and returns summary stats /
chart-ready DataFrames, keeping Pandas logic out of the Streamlit pages.
"""

import pandas as pd
from typing import Dict


def summary_metrics(history_df: pd.DataFrame) -> Dict:
    completed = history_df[history_df["status"] == "completed"]
    if completed.empty:
        return {
            "avg_score": 0, "best_score": 0, "lowest_score": 0,
            "num_interviews": 0, "completion_rate": 0, "avg_questions": 0,
        }

    total = len(history_df)
    return {
        "avg_score": round(completed["overall_score"].mean(), 2),
        "best_score": round(completed["overall_score"].max(), 2),
        "lowest_score": round(completed["overall_score"].min(), 2),
        "num_interviews": len(completed),
        "completion_rate": round(len(completed) / total * 100, 1) if total else 0,
        "avg_questions": round(completed["num_questions"].mean(), 1),
    }


def score_by_domain(history_df: pd.DataFrame) -> pd.DataFrame:
    completed = history_df[history_df["status"] == "completed"]
    if completed.empty:
        return pd.DataFrame(columns=["role", "overall_score"])
    return completed.groupby("role", as_index=False)["overall_score"].mean().round(2)


def score_by_difficulty(history_df: pd.DataFrame) -> pd.DataFrame:
    completed = history_df[history_df["status"] == "completed"]
    if completed.empty:
        return pd.DataFrame(columns=["difficulty", "overall_score"])
    return completed.groupby("difficulty", as_index=False)["overall_score"].mean().round(2)


def score_trend(history_df: pd.DataFrame) -> pd.DataFrame:
    completed = history_df[history_df["status"] == "completed"].copy()
    if completed.empty:
        return pd.DataFrame(columns=["start_time", "overall_score"])
    completed["start_time"] = pd.to_datetime(completed["start_time"])
    return completed.sort_values("start_time")[["start_time", "overall_score"]]


def skill_gap_table(skills_df: pd.DataFrame) -> pd.DataFrame:
    """Average score per skill across all interviews, sorted weakest first."""
    if skills_df.empty:
        return pd.DataFrame(columns=["skill_name", "avg_score"])
    agg = skills_df.groupby("skill_name", as_index=False)["avg_score"].mean().round(2)
    return agg.sort_values("avg_score")


def priority_skills(skills_df: pd.DataFrame, top_n: int = 3) -> list:
    table = skill_gap_table(skills_df)
    return table.head(top_n)["skill_name"].tolist()


def question_performance(scores_df: pd.DataFrame) -> pd.DataFrame:
    if scores_df.empty:
        return pd.DataFrame(columns=["question_text", "final_score"])
    return (
        scores_df.groupby("question_text", as_index=False)["final_score"]
        .mean().round(2).sort_values("final_score")
    )
