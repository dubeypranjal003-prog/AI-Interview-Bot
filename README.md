# 🎯 AI Interview Bot — AI-Powered Interview Assessment & Performance Analytics Platform

Practice interviews across 8 job roles, get answers scored on a 5-signal rubric
(not just similarity to one sample answer), get resume-personalized questions,
and track skill gaps over time on an analytics dashboard.

Built with **Python, Streamlit, Sentence-Transformers, scikit-learn, Pandas, and SQLite.**

---

## Features

- 🎤 **Adaptive interviews** across 8 roles (HR, Data Analyst, Data Scientist, Python
  Developer, SQL Developer, Machine Learning, Business Analyst, Software Developer),
  4 difficulty levels (Easy → Expert), and 5 interview types (Technical, HR,
  Behavioral, Case Study, Mixed).
- 📄 **Resume analysis** — upload a PDF, get a resume score, detected skills, and
  missing skills. Detected skills personalize which interview questions you get.
- 🤖 **5-signal AI evaluation** — relevance (semantic similarity), technical
  keyword coverage, completeness, clarity, and keyword match, blended into a
  weighted score, so two differently-worded correct answers can both score well.
- 🔁 **Dynamic follow-up questions** — a strong answer gets a deeper follow-up,
  a weak answer gets a simpler one.
- 📊 **Analytics dashboard** — average/best/lowest score, completion rate, score
  by role, score by difficulty, score trend over time.
- 📈 **Skill gap analysis** with ranked priority-skill recommendations.
- 📝 **Filterable interview history** with score-improvement comparison.
- 📥 **CSV export** for any interview report or the full history.
- 🛡 Error handling for empty input, corrupted PDFs, and missing/failed model
  loads (falls back to a keyword-only scorer so the app never crashes).

## Architecture

```text
AI-Interview-Bot/
├── app.py                     # Home page + one-time app bootstrap (DB init, CSS)
├── pages/                     # Streamlit auto-discovers these for sidebar nav
│   ├── 1_🎤_Start_Interview.py
│   ├── 2_📄_Resume_Analysis.py
│   ├── 3_📊_Dashboard.py
│   ├── 4_📈_Performance.py
│   ├── 5_📝_Interview_History.py
│   └── 6_⚙️_Settings.py
├── src/
│   ├── database.py            # All SQLite access (schema, CRUD, dedupe guard)
│   ├── scoring.py              # Weighted 5-signal scoring rubric
│   ├── ai_evaluator.py         # Cached model loading + follow-up question logic
│   ├── resume_parser.py        # PDF text extraction + rule-based resume analysis
│   ├── question_engine.py      # Loads/filters/personalizes the question bank
│   └── analytics.py            # Pandas aggregations for the dashboard
├── data/questions.json         # 59-question bank (role/skill/difficulty/type tagged)
├── assets/styles.css           # Shared UI styling
├── tests/                      # pytest unit tests (offline-safe, no model download)
├── requirements.txt
├── .gitignore
├── .env.example
└── LICENSE
```

**Design choices worth knowing:**

- **Question bank lives in JSON, not hard-coded Python** (`data/questions.json`),
  and is synced into a `questions` table on startup — easy to extend without
  touching app logic.
- **Scoring never crashes if the embedding model can't load** — `ai_evaluator.py`
  catches the load failure and `scoring.py` falls back to keyword/heuristic
  scoring only.
- **Duplicate-save protection**: `finalize_interview()` checks the interview's
  `status` column before writing, so a Streamlit rerun after the final screen
  can never insert the same result twice (see `tests/test_database.py`).
- **No secrets in code**: the AI provider is read from `.env` (`AI_PROVIDER`,
  default `local`), never hard-coded. `.env` and `*.db` are git-ignored.

## Database Design

7 tables: `candidates`, `interviews`, `questions`, `answers`, `scores`, `skills`,
`resume_analysis` — normalized so one interview can have many answers, one
answer has one score breakdown, and skill-level averages are computed once per
completed interview rather than recomputed from scratch every dashboard load.

## AI Evaluation Method

Each answer is scored 0–10 on five signals, combined with these weights:

| Signal        | Weight | How it's computed                                   |
|---------------|--------|------------------------------------------------------|
| Relevance     | 25%    | Cosine similarity between answer and ideal-answer embeddings (SentenceTransformer `all-MiniLM-L6-v2`) |
| Technical     | 30%    | Fraction of the question's expected keywords/concepts present |
| Completeness  | 20%    | Answer length vs. expected length + sentence structure |
| Clarity       | 15%    | Filler-word ratio + average sentence length heuristics |
| Keywords      | 10%    | Same keyword list as Technical, weighted separately as a lightweight topic check |

This means two candidates who answer correctly in different words can both
score well — the evaluator isn't just checking similarity to one canned answer.

If `sentence-transformers` fails to load (e.g. no internet on first run), the
app automatically falls back to keyword-only scoring instead of crashing.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # optional — defaults to AI_PROVIDER=local
streamlit run app.py
```

The SQLite database (`interview_bot.db`) and question bank sync happen
automatically on first run — no manual setup needed.

## Usage

1. Open the app → **📄 Resume Analysis** → upload a PDF resume (optional but
   recommended — it personalizes your questions).
2. Go to **🎤 Start Interview** → enter your name, pick a role/difficulty/type,
   and start.
3. Answer each question → see your score breakdown, feedback, and the ideal
   answer → continue (strong/weak answers may trigger a follow-up question).
4. At the end, view your **Final Interview Report** and download it as CSV.
5. Check **📊 Dashboard** and **📈 Performance** for trends and skill gaps.
6. Browse **📝 Interview History** to filter and compare past attempts.

## Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests cover scoring (empty answers, strong-vs-weak differentiation, bounded
scores), database (schema creation, candidate dedupe, duplicate-save
protection), and resume parsing (contact extraction, skill detection, project
extraction) — all offline-safe, no model download required.

## Deployment

Deploy for free on [Streamlit Community Cloud](https://streamlit.io/cloud):
push this repo to GitHub, connect it in Streamlit Cloud, set `app.py` as the
entry point, and add any secrets under the app's **Secrets** settings
(mirroring `.env.example`) instead of committing a `.env` file.

## What I Learned

- Structuring a multi-page Streamlit app with clean separation between UI,
  database, scoring, and analytics logic.
- Designing a normalized SQLite schema and guarding against duplicate writes
  caused by Streamlit's rerun model.
- Building a semantic + rule-based hybrid evaluator (Sentence-Transformers +
  keyword coverage) instead of relying on a single similarity score.
- Rule-based resume parsing (regex + keyword vocabulary) as a reliable
  fallback when LLM API access isn't guaranteed.
- Turning raw interview data into dashboard-ready aggregations with Pandas.

## Future Improvements

- PDF export of the final report (currently CSV).
- OCR support for scanned/image-based resumes.
- Optional LLM-backed evaluator behind the `AI_PROVIDER` config.
- Live JS-based countdown timer (current timer recalculates on each rerun).
- User authentication for multi-candidate deployments.

## Author

**Pranjal Dubey** — [GitHub](https://github.com/dubeypranjal003-prog) ·
[LinkedIn](https://linkedin.com/in/pranjal-dubey-1b7865367)
