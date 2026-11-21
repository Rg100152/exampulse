"""JSON APIs for question sets, attempt lifecycle and grading."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from exampulse_core import (
    CANDIDATE_NAME,
    MODES,
    OPTION_LETTERS,
    SUBJECTS,
    attempt_public_payload,
    build_report,
    count_questions,
    create_attempt,
    grade_attempt,
    recent_attempts,
    search_questions,
)

api_bp = Blueprint("api", __name__)


def ok(**payload):
    return jsonify({"success": True, **payload})


def fail(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


@api_bp.get("/health")
def health():
    return ok(status="up", candidate=CANDIDATE_NAME, banks=len(SUBJECTS))


@api_bp.get("/stats")
def stats():
    return ok(questions=count_questions(), subjects=len(SUBJECTS), modes=MODES)


@api_bp.get("/subjects")
def subjects():
    counts = count_questions()
    data = [
        {**meta, "slug": slug, "available_questions": counts.get(slug, 0)}
        for slug, meta in SUBJECTS.items()
    ]
    return ok(subjects=data)


@api_bp.get("/questions/<subject>")
def questions(subject: str):
    if subject not in SUBJECTS:
        return fail("Unknown subject", 404)
    try:
        limit = int(request.args.get("limit", 25))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return fail("limit and offset must be integers")
    items, total = search_questions(
        subject,
        topic=request.args.get("topic"),
        difficulty=request.args.get("difficulty"),
        search=request.args.get("q"),
        limit=limit,
        offset=offset,
    )
    return ok(subject=subject, total=total, offset=offset, limit=limit, questions=items)


@api_bp.post("/attempts/start")
def start_attempt():
    payload = request.get_json(silent=True) or {}
    subject = str(payload.get("subject", "")).strip()
    mode = str(payload.get("mode", "quick")).strip()
    if subject not in SUBJECTS:
        return fail("Unknown subject")
    if mode not in MODES:
        return fail("Unknown mode")
    try:
        attempt = create_attempt(subject, mode)
    except ValueError as exc:
        return fail(str(exc), 503)
    session["active_attempt_code"] = attempt["code"]
    session.modified = True
    return ok(
        code=attempt["code"],
        url=f"/exam/{subject}?mode={mode}",
        exam_url=f"/exam/{subject}",
        total_questions=attempt["question_count"],
        deadline_at=attempt["deadline_at"],
    )


@api_bp.get("/attempts")
def attempts():
    return ok(attempts=recent_attempts(50))


@api_bp.get("/attempts/<code>")
def attempt_detail(code: str):
    try:
        return ok(attempt=attempt_public_payload(code))
    except LookupError as exc:
        return fail(str(exc), 404)


@api_bp.post("/attempts/<code>/submit")
def submit_attempt(code: str):
    payload = request.get_json(silent=True) or {}
    raw_answers = payload.get("answers", {})
    if not isinstance(raw_answers, dict):
        return fail("answers must be an object keyed by question id")
    try:
        elapsed = int(payload.get("elapsed_seconds", 0))
    except (TypeError, ValueError):
        elapsed = 0
    answers = {
        str(qid): str(value).strip().upper()
        for qid, value in raw_answers.items()
        if str(qid).isdigit() and str(value).strip().upper() in OPTION_LETTERS
    }
    try:
        report = grade_attempt(code, answers, elapsed)
    except LookupError as exc:
        return fail(str(exc), 404)
    session.pop("active_attempt_code", None)
    return ok(
        code=code,
        result_url=f"/result/{code}",
        score=report["marks_earned"],
        accuracy=report["accuracy"],
        correct=report["correct"],
        wrong=report["wrong"],
    )


@api_bp.get("/attempts/<code>/report")
def attempt_report(code: str):
    try:
        return ok(report=build_report(code))
    except LookupError as exc:
        return fail(str(exc), 404)
