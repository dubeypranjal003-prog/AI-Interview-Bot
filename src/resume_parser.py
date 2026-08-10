"""
resume_parser.py
-----------------
Extracts text from an uploaded PDF resume and pulls out structured info
(name/email/phone/skills/projects) using regex + keyword matching.

This is a rule-based fallback by design (see project brief section 5) —
no external LLM call is required for this to work, so the feature keeps
working even with AI_PROVIDER=local.
"""

import re
from typing import Dict, List, Tuple

# A reasonably broad skill vocabulary for a Data/Python-focused résumé.
# Extend this list to widen detection - it drives both the "skills found"
# section and the personalized question generation.
SKILL_VOCAB = [
    "Python", "SQL", "Excel", "Power BI", "Tableau", "Pandas", "NumPy",
    "Scikit-learn", "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning",
    "Statistics", "Data Cleaning", "Data Visualization", "R", "Java", "C++",
    "MySQL", "PostgreSQL", "MongoDB", "AWS", "Azure", "GCP", "Git", "GitHub",
    "Streamlit", "Flask", "Django", "REST API", "ETL", "Data Warehousing",
    "Spark", "Hadoop", "Airflow", "Docker", "Kubernetes", "NLP", "A/B Testing",
    "Business Analytics", "Dashboard Design", "Google Sheets", "VBA",
]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3}[-.\s]?\d{3,4}")
PROJECT_HEADING_RE = re.compile(r"^(projects?|academic projects?)\s*:?$", re.IGNORECASE)


def extract_text_from_pdf(pdf_file) -> str:
    """
    pdf_file: a file-like object (e.g. Streamlit's UploadedFile).
    Raises ValueError with a friendly message on a corrupted/invalid PDF
    instead of letting PyPDF2's raw exception bubble into the UI.
    """
    import PyPDF2

    try:
        reader = PyPDF2.PdfReader(pdf_file)
    except Exception as e:
        raise ValueError(f"Could not open this PDF — it may be corrupted or password-protected. ({e})")

    if len(reader.pages) == 0:
        raise ValueError("This PDF has no readable pages.")

    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue  # skip an unreadable page rather than failing the whole resume

    text = "\n".join(text_parts).strip()
    if len(text) < 30:
        raise ValueError(
            "Very little text could be extracted from this PDF. "
            "It may be a scanned image rather than selectable text."
        )
    return text


def extract_contact_info(text: str) -> Dict[str, str]:
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    # naive name guess: first non-empty line that isn't an email/phone/heading
    name_guess = ""
    for line in text.splitlines():
        line = line.strip()
        if line and not EMAIL_RE.search(line) and not PHONE_RE.search(line) and len(line.split()) <= 5:
            name_guess = line
            break
    return {
        "name": name_guess,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else "",
    }


def extract_skills(text: str) -> List[str]:
    text_lower = text.lower()
    return [skill for skill in SKILL_VOCAB if skill.lower() in text_lower]


def extract_projects(text: str) -> List[str]:
    """Pulls short lines that follow a 'Projects' heading, up to the next heading."""
    lines = text.splitlines()
    projects = []
    in_projects = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if PROJECT_HEADING_RE.match(stripped):
            in_projects = True
            continue
        if in_projects:
            # Stop at the next ALL-CAPS heading-like line (e.g. "EDUCATION")
            if stripped.isupper() and len(stripped.split()) <= 4:
                break
            if len(stripped) < 100:
                projects.append(stripped)
            if len(projects) >= 6:
                break
    return projects


def compute_resume_score(skills_found: List[str], projects_found: List[str], text: str) -> int:
    """
    Simple, transparent 0-100 rubric:
        up to 50 pts for skill breadth (capped at 10 relevant skills)
        up to 20 pts for having projects listed
        up to 15 pts for contact info present
        up to 15 pts for resume length being substantial (not a 1-line resume)
    """
    skill_pts = min(len(skills_found), 10) * 5
    project_pts = min(len(projects_found), 4) * 5
    contact = extract_contact_info(text)
    contact_pts = (7 if contact["email"] else 0) + (8 if contact["phone"] else 0)
    length_pts = 15 if len(text.split()) > 150 else round(len(text.split()) / 150 * 15)
    return min(int(skill_pts + project_pts + contact_pts + length_pts), 100)


def analyze_resume(text: str) -> Dict:
    skills_found = extract_skills(text)
    missing_skills = [s for s in SKILL_VOCAB if s not in skills_found][:8]
    projects_found = extract_projects(text)
    contact = extract_contact_info(text)
    score = compute_resume_score(skills_found, projects_found, text)

    return {
        "contact": contact,
        "skills_found": skills_found,
        "skills_missing": missing_skills,
        "projects_found": projects_found,
        "resume_score": score,
        "raw_text_excerpt": text[:2000],
    }


def personalized_skill_focus(resume_analysis: Dict) -> List[str]:
    """Returns the skill tags to prioritize when generating interview questions."""
    return resume_analysis.get("skills_found", [])[:6]
