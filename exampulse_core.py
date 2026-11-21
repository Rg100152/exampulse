"""Core domain logic for ExamPulse 1000.

Holds subject/mode configuration, SQLite access, attempt creation, grading and
report aggregation.  Both the Flask routes and the offline seeder use this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("EXAMPULSE_DB", BASE_DIR / "database" / "exampulse.db"))

CANDIDATE_NAME = os.environ.get("EXAMPULSE_CANDIDATE", "Raj Gautam")

SUBJECTS: dict[str, dict[str, Any]] = {
    "python": {
        "name": "Python Programming",
        "short": "Python",
        "code": "PY",
        "icon": "py",
        "accent": "#2563EB",
        "glow": "rgba(37, 99, 235, .20)",
        "description": "Core syntax, OOP, data structures, generators, decorators, files and libraries.",
        "topics": [
            "Core Syntax", "Data Structures", "OOP", "Functions",
            "Generators & Decorators", "Files & Exceptions", "Libraries", "Advanced Concepts",
        ],
        "file": "python_250.json",
    },
    "datamining": {
        "name": "Data Mining & Warehousing",
        "short": "Data Mining",
        "code": "DM",
        "icon": "dm",
        "accent": "#0D9488",
        "glow": "rgba(13, 148, 136, .20)",
        "description": "KDD, preprocessing, Apriori, classification, clustering, OLAP and evaluation.",
        "topics": [
            "KDD & Preprocessing", "Association Rules", "Classification", "Clustering",
            "Data Warehousing & OLAP", "Evaluation Metrics", "Text Mining", "Big Data Concepts",
        ],
        "file": "datamining_250.json",
    },
    "dotnet": {
        "name": ".NET Framework & C#",
        "short": ".NET / C#",
        "code": "NT",
        "icon": "cs",
        "accent": "#7C3AED",
        "glow": "rgba(124, 58, 237, .20)",
        "description": "CLR, CTS, ASP.NET Core, LINQ, Entity Framework, delegates and memory management.",
        "topics": [
            "CLR & CTS", "C# Fundamentals", "OOP in C#", "LINQ",
            "ASP.NET Core", "Entity Framework", "Memory & Exceptions", "Advanced C#",
        ],
        "file": "dotnet_250.json",
    },
    "webdesign": {
        "name": "Web Design & Frontend",
        "short": "Web Design",
        "code": "WD",
        "icon": "wd",
        "accent": "#F97316",
        "glow": "rgba(249, 115, 22, .20)",
        "description": "Semantic HTML5, CSS Grid/Flexbox, responsive UI, JavaScript ES6 and accessibility.",
        "topics": [
            "HTML5 Semantics", "CSS3 & Layout", "Responsive Design", "JavaScript ES6",
            "DOM & Events", "UI/UX Principles", "Accessibility", "Performance & Tools",
        ],
        "file": "webdesign_250.json",
    },
}

MODES: dict[str, dict[str, Any]] = {
    "quick": {"label": "Quick Practice", "questions": 25, "minutes": 15, "hint": "15 min sprint"},
    "mock": {"label": "Subject Mock", "questions": 100, "minutes": 60, "hint": "60 min full mock"},
    "full": {"label": "Full Bank Explorer", "questions": 250, "minutes": 120, "hint": "All 250 questions"},
}

MARK_SCHEME = {"correct": 1.0, "wrong": -0.25, "unanswered": 0.0}
DIFFICULTIES = ("Easy", "Medium", "Hard")
OPTION_LETTERS = ("A", "B", "C", "D")

SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    subject        TEXT NOT NULL,
    topic          TEXT NOT NULL,
    difficulty     TEXT NOT NULL,
    question       TEXT NOT NULL,
    option_a       TEXT NOT NULL,
    option_b       TEXT NOT NULL,
    option_c       TEXT NOT NULL,
    option_d       TEXT NOT NULL,
    correct_option TEXT NOT NULL CHECK (correct_option IN ('A','B','C','D')),
    explanation    TEXT NOT NULL,
    question_key   TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_questions_subject   ON questions(subject);
CREATE INDEX IF NOT EXISTS idx_questions_topic     ON questions(topic);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);

CREATE TABLE IF NOT EXISTS attempts (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_code       TEXT NOT NULL UNIQUE,
    subject            TEXT NOT NULL,
    mode               TEXT NOT NULL,
    total_questions    INTEGER NOT NULL,
    duration_minutes   INTEGER NOT NULL,
    started_at         TEXT NOT NULL,
    deadline_at        TEXT NOT NULL,
    submitted_at       TEXT,
    time_taken_seconds INTEGER NOT NULL DEFAULT 0,
    correct_count      INTEGER NOT NULL DEFAULT 0,
    wrong_count        INTEGER NOT NULL DEFAULT 0,
    unanswered_count   INTEGER NOT NULL DEFAULT 0,
    marks_earned       REAL NOT NULL DEFAULT 0,
    negative_marks     REAL NOT NULL DEFAULT 0,
    max_marks          REAL NOT NULL DEFAULT 0,
    accuracy           REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_attempts_code ON attempts(attempt_code);

CREATE TABLE IF NOT EXISTS attempt_questions (
    attempt_id  INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    position    INTEGER NOT NULL,
    PRIMARY KEY (attempt_id, position),
    UNIQUE (attempt_id, question_id)
);

CREATE TABLE IF NOT EXISTS responses (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id     INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id    INTEGER NOT NULL REFERENCES questions(id),
    selected_option TEXT,
    is_correct     INTEGER NOT NULL DEFAULT 0,
    UNIQUE (attempt_id, question_id)
);
CREATE INDEX IF NOT EXISTS idx_responses_attempt ON responses(attempt_id);
"""


# --------------------------------------------------------------------------- #
# Database helpers
# --------------------------------------------------------------------------- #
def connect_db(path: Path | str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys and row access enabled."""
    conn = sqlite3.connect(str(path or DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db() -> sqlite3.Connection:
    """Return a request-scoped connection when inside Flask, otherwise a new one."""
    try:
        from flask import g
    except ImportError:  # pragma: no cover - Flask is always installed at runtime
        return connect_db()
    if not hasattr(g, "exampulse_db"):
        g.exampulse_db = connect_db()
    return g.exampulse_db


def close_db(_exception: BaseException | None = None) -> None:
    from flask import g

    conn = g.pop("exampulse_db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        if count == 0 and all((DATA_DIR / s["file"]).exists() for s in SUBJECTS.values()):
            seed_questions(conn=conn)
    finally:
        conn.close()


def normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().casefold()


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #
def load_bank_file(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    items = payload["questions"] if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError(f"{path.name}: expected a list of questions")
    return items


def validate_item(item: dict[str, Any], subject: str, topics: list[str]) -> list[str]:
    errors: list[str] = []
    required = {"question", "options", "correct_option", "difficulty", "topic", "explanation"}
    if set(item) != required:
        errors.append(f"fields must be {sorted(required)}, got {sorted(item)}")
        return errors
    for field in ("question", "correct_option", "difficulty", "topic", "explanation"):
        if not isinstance(item[field], str) or not item[field].strip():
            errors.append(f"empty or invalid {field}")
    options = item.get("options")
    if not isinstance(options, list) or len(options) != 4:
        errors.append("options must contain exactly 4 entries")
    elif any(not isinstance(o, str) or not o.strip() for o in options):
        errors.append("options must be non-empty strings")
    elif len({normalize_question(o) for o in options}) != 4:
        errors.append("options must be distinct")
    if item.get("correct_option") not in OPTION_LETTERS:
        errors.append("correct_option must be A, B, C or D")
    if item.get("difficulty") not in DIFFICULTIES:
        errors.append("difficulty must be Easy, Medium or Hard")
    if item.get("topic") not in topics:
        errors.append(f"topic must be one of {topics}")
    if len((item.get("explanation") or "").strip()) < 40:
        errors.append("explanation is too short")
    return errors


def seed_questions(conn: sqlite3.Connection | None = None, force: bool = False) -> dict[str, int]:
    """Insert every question bank item into SQLite. Returns per-subject counts."""
    owns_connection = conn is None
    conn = conn or connect_db()
    counts: dict[str, int] = {}
    try:
        conn.executescript(SCHEMA)
        if force:
            conn.execute("DELETE FROM responses")
            conn.execute("DELETE FROM attempt_questions")
            conn.execute("DELETE FROM attempts")
            conn.execute("DELETE FROM questions")
        for slug, meta in SUBJECTS.items():
            path = DATA_DIR / meta["file"]
            items = load_bank_file(path)
            rows = []
            seen: set[str] = set()
            for index, item in enumerate(items, start=1):
                problems = validate_item(item, slug, meta["topics"])
                if problems:
                    raise ValueError(f"{path.name} item {index}: {'; '.join(problems)}")
                key = hashlib.sha1(
                    f"{slug}|{normalize_question(item['question'])}".encode("utf-8")
                ).hexdigest()
                if key in seen:
                    raise ValueError(f"{path.name} item {index}: duplicate question text")
                seen.add(key)
                opts = [o.strip() for o in item["options"]]
                rows.append((
                    slug, item["topic"].strip(), item["difficulty"].strip(),
                    item["question"].strip(), opts[0], opts[1], opts[2], opts[3],
                    item["correct_option"].strip(), item["explanation"].strip(), key,
                ))
            conn.executemany(
                """INSERT OR IGNORE INTO questions
                   (subject, topic, difficulty, question, option_a, option_b, option_c,
                    option_d, correct_option, explanation, question_key)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            counts[slug] = conn.execute(
                "SELECT COUNT(*) FROM questions WHERE subject = ?", (slug,)
            ).fetchone()[0]
        conn.commit()
        return counts
    finally:
        if owns_connection:
            conn.close()


# --------------------------------------------------------------------------- #
# Question queries
# --------------------------------------------------------------------------- #
def question_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "subject": row["subject"],
        "topic": row["topic"],
        "difficulty": row["difficulty"],
        "question": row["question"],
        "options": {
            letter: row[f"option_{letter.lower()}"]
            for letter in OPTION_LETTERS
        },
        "correct_option": row["correct_option"],
        "explanation": row["explanation"],
    }


def count_questions(conn: sqlite3.Connection | None = None) -> dict[str, int]:
    conn = conn or get_db()
    rows = conn.execute("SELECT subject, COUNT(*) AS n FROM questions GROUP BY subject").fetchall()
    counts = {slug: 0 for slug in SUBJECTS}
    counts.update({row["subject"]: row["n"] for row in rows})
    counts["total"] = sum(counts.values())
    return counts


def search_questions(
    subject: str,
    *,
    topic: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    conn: sqlite3.Connection | None = None,
) -> tuple[list[dict[str, Any]], int]:
    conn = conn or get_db()
    where = ["subject = ?"]
    params: list[Any] = [subject]
    if topic and topic in SUBJECTS[subject]["topics"]:
        where.append("topic = ?")
        params.append(topic)
    if difficulty in DIFFICULTIES:
        where.append("difficulty = ?")
        params.append(difficulty)
    if search:
        where.append("(question LIKE ? OR explanation LIKE ? OR option_a LIKE ? OR option_b LIKE ?"
                     " OR option_c LIKE ? OR option_d LIKE ?)")
        term = f"%{search.strip()}%"
        params.extend([term] * 6)
    clause = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) FROM questions WHERE {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM questions WHERE {clause} ORDER BY id LIMIT ? OFFSET ?",
        [*params, max(1, min(limit, 250)), max(0, offset)],
    ).fetchall()
    return [question_row_to_dict(row) for row in rows], total


# --------------------------------------------------------------------------- #
# Attempts & grading
# --------------------------------------------------------------------------- #
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def create_attempt(subject: str, mode: str, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    conn = conn or get_db()
    cfg_mode = MODES.get(mode, MODES["quick"])
    rows = conn.execute(
        "SELECT id FROM questions WHERE subject = ? ORDER BY RANDOM() LIMIT ?",
        (subject, cfg_mode["questions"]),
    ).fetchall()
    if not rows:
        raise ValueError(f"No questions found for subject '{subject}'. Run the seeder first.")
    started = utcnow()
    deadline = started + timedelta(minutes=cfg_mode["minutes"])
    code = "EP-" + secrets.token_hex(3).upper()
    cursor = conn.execute(
        """INSERT INTO attempts
           (attempt_code, subject, mode, total_questions, duration_minutes,
            started_at, deadline_at, max_marks)
           VALUES (?,?,?,?,?,?,?,?)""",
        (code, subject, mode, len(rows), cfg_mode["minutes"],
         iso(started), iso(deadline), len(rows) * MARK_SCHEME["correct"]),
    )
    attempt_id = cursor.lastrowid
    conn.executemany(
        "INSERT INTO attempt_questions (attempt_id, question_id, position) VALUES (?,?,?)",
        [(attempt_id, row["id"], pos) for pos, row in enumerate(rows, start=1)],
    )
    conn.commit()
    return {"code": code, "id": attempt_id, "subject": subject, "mode": mode,
            "question_count": len(rows), "deadline_at": iso(deadline)}


def get_active_attempt_code(subject: str, mode: str) -> str | None:
    """Reuse an unfinished, unexpired attempt stored in the Flask session."""
    from flask import session

    code = session.get("active_attempt_code")
    if not code:
        return None
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM attempts WHERE attempt_code = ?", (code,)
    ).fetchone()
    if not row or row["subject"] != subject or row["mode"] != mode or row["submitted_at"]:
        session.pop("active_attempt_code", None)
        return None
    if parse_iso(row["deadline_at"]) <= utcnow():
        session.pop("active_attempt_code", None)
        return None
    return code


def fetch_attempt_questions(code: str, conn: sqlite3.Connection | None = None) -> tuple[sqlite3.Row, list[dict[str, Any]]]:
    conn = conn or get_db()
    attempt = conn.execute("SELECT * FROM attempts WHERE attempt_code = ?", (code,)).fetchone()
    if not attempt:
        raise LookupError(f"Attempt '{code}' was not found")
    rows = conn.execute(
        """SELECT q.* FROM attempt_questions aq
           JOIN questions q ON q.id = aq.question_id
           WHERE aq.attempt_id = ? ORDER BY aq.position""",
        (attempt["id"],),
    ).fetchall()
    return attempt, [question_row_to_dict(row) for row in rows]


def attempt_public_payload(code: str) -> dict[str, Any]:
    attempt, questions = fetch_attempt_questions(code)
    # Answers are deliberately withheld until submission.
    return {
        "code": attempt["attempt_code"],
        "subject": attempt["subject"],
        "mode": attempt["mode"],
        "total_questions": attempt["total_questions"],
        "duration_minutes": attempt["duration_minutes"],
        "started_at": attempt["started_at"],
        "deadline_at": attempt["deadline_at"],
        "candidate": CANDIDATE_NAME,
        "questions": [
            {k: q[k] for k in ("id", "question", "options", "topic", "difficulty")}
            for q in questions
        ],
    }


def grade_attempt(code: str, answers: dict[str, str], client_elapsed: int = 0) -> dict[str, Any]:
    """Server-authoritative grading: correct answers are read from SQLite."""
    conn = get_db()
    attempt, questions = fetch_attempt_questions(code, conn)
    if attempt["submitted_at"]:
        return build_report(code)

    correct = wrong = unanswered = 0
    marks = negative = 0.0
    response_rows = []
    for question in questions:
        selected = str(answers.get(str(question["id"]), "") or "").strip().upper()
        if selected not in OPTION_LETTERS:
            selected = None
        is_correct = selected == question["correct_option"]
        if is_correct:
            correct += 1
            marks += MARK_SCHEME["correct"]
        elif selected:
            wrong += 1
            negative += abs(MARK_SCHEME["wrong"])
            marks += MARK_SCHEME["wrong"]
        else:
            unanswered += 1
        response_rows.append((attempt["id"], question["id"], selected, int(is_correct)))

    now = utcnow()
    started = parse_iso(attempt["started_at"])
    elapsed = max(0, min(int(client_elapsed or 0), int((now - started).total_seconds())))
    attempted = correct + wrong
    accuracy = round((correct / attempted * 100) if attempted else 0.0, 2)
    conn.executemany(
        """INSERT INTO responses (attempt_id, question_id, selected_option, is_correct)
           VALUES (?,?,?,?)""",
        response_rows,
    )
    conn.execute(
        """UPDATE attempts SET submitted_at = ?, time_taken_seconds = ?, correct_count = ?,
           wrong_count = ?, unanswered_count = ?, marks_earned = ?, negative_marks = ?,
           accuracy = ? WHERE id = ?""",
        (iso(now), elapsed, correct, wrong, unanswered, round(marks, 2),
         round(negative, 2), accuracy, attempt["id"]),
    )
    conn.commit()
    return build_report(code)


def build_report(code: str, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    conn = conn or get_db()
    attempt = conn.execute("SELECT * FROM attempts WHERE attempt_code = ?", (code,)).fetchone()
    if not attempt:
        raise LookupError(f"Attempt '{code}' was not found")
    rows = conn.execute(
        """SELECT q.*, r.selected_option, r.is_correct FROM attempt_questions aq
           JOIN questions q ON q.id = aq.question_id
           LEFT JOIN responses r ON r.attempt_id = aq.attempt_id AND r.question_id = q.id
           WHERE aq.attempt_id = ? ORDER BY aq.position""",
        (attempt["id"],),
    ).fetchall()

    items = []
    topic_stats: dict[str, dict[str, int]] = {}
    for row in rows:
        selected = row["selected_option"]
        status = "correct" if row["is_correct"] == 1 else ("wrong" if selected else "unanswered")
        item = question_row_to_dict(row)
        item.update({
            "selected_option": selected,
            "status": status,
            "position": len(items) + 1,
        })
        items.append(item)
        stats = topic_stats.setdefault(row["topic"], {"correct": 0, "wrong": 0, "unanswered": 0, "total": 0})
        stats[status] += 1
        stats["total"] += 1

    topics = [
        {
            "topic": name,
            **counts,
            "accuracy": round(counts["correct"] / counts["total"] * 100, 1),
            "weak": counts["correct"] / counts["total"] < 0.6,
        }
        for name, counts in sorted(topic_stats.items(), key=lambda kv: kv[1]["correct"] / max(1, kv[1]["total"]))
    ]
    total = attempt["total_questions"]
    return {
        "code": attempt["attempt_code"],
        "candidate": CANDIDATE_NAME,
        "subject": attempt["subject"],
        "subject_name": SUBJECTS.get(attempt["subject"], {}).get("name", attempt["subject"]),
        "mode": attempt["mode"],
        "mode_label": MODES.get(attempt["mode"], {}).get("label", attempt["mode"]),
        "started_at": attempt["started_at"],
        "submitted_at": attempt["submitted_at"],
        "deadline_at": attempt["deadline_at"],
        "time_taken_seconds": attempt["time_taken_seconds"],
        "total_questions": total,
        "correct": attempt["correct_count"],
        "wrong": attempt["wrong_count"],
        "unanswered": attempt["unanswered_count"],
        "marks_earned": attempt["marks_earned"],
        "negative_marks": attempt["negative_marks"],
        "max_marks": attempt["max_marks"],
        "accuracy": attempt["accuracy"],
        "percentage": round(attempt["marks_earned"] / max(1, attempt["max_marks"]) * 100, 1),
        "passed": attempt["marks_earned"] >= attempt["max_marks"] * 0.5,
        "questions": items,
        "topics": topics,
    }


def recent_attempts(limit: int = 5, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    conn = conn or get_db()
    rows = conn.execute(
        "SELECT * FROM attempts ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [
        {
            "code": row["attempt_code"],
            "subject": row["subject"],
            "mode": row["mode"],
            "score": row["marks_earned"],
            "max": row["max_marks"],
            "accuracy": row["accuracy"],
            "submitted_at": row["submitted_at"],
        }
        for row in rows
    ]
