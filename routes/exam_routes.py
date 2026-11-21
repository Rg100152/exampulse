"""Page routes: lobby, CBT arena, analytics report, study bank and PDF export."""

from __future__ import annotations

import json

from flask import (
    Blueprint,
    abort,
    make_response,
    render_template,
    request,
    session,
)

from exampulse_core import (
    MODES,
    SUBJECTS,
    attempt_public_payload,
    build_report,
    count_questions,
    create_attempt,
    get_active_attempt_code,
    get_db,
    recent_attempts,
    search_questions,
)

exam_bp = Blueprint("exam", __name__)


@exam_bp.route("/")
def lobby():
    conn = get_db()
    return render_template(
        "index.html",
        question_counts=count_questions(conn),
        recent=recent_attempts(4, conn),
    )


@exam_bp.route("/exam/<subject>")
def exam_arena(subject: str):
    if subject not in SUBJECTS:
        abort(404)
    mode = request.args.get("mode", "quick")
    if mode not in MODES:
        mode = "quick"

    code = get_active_attempt_code(subject, mode)
    if not code:
        code = create_attempt(subject, mode)["code"]
    session["active_attempt_code"] = code
    session.modified = True

    payload = attempt_public_payload(code)
    return render_template(
        "exam_arena.html",
        subject=SUBJECTS[subject],
        subject_slug=subject,
        mode=MODES[mode],
        mode_slug=mode,
        attempt=payload,
        questions_json=json.dumps(payload),
    )


@exam_bp.route("/result/<code>")
def result(code: str):
    try:
        report = build_report(code)
    except LookupError:
        abort(404)
    return render_template(
        "feedback_report.html",
        report=report,
        report_json=json.dumps(report),
    )


@exam_bp.route("/result/<code>/pdf")
def scorecard_pdf(code: str):
    try:
        report = build_report(code)
    except LookupError:
        abort(404)
    from utils.pdf_scorecard import generate_scorecard_pdf

    response = make_response(generate_scorecard_pdf(report))
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="ExamPulse_Scorecard_{code}.pdf"'
    )
    return response


@exam_bp.route("/bank/<subject>")
def study_bank(subject: str):
    if subject not in SUBJECTS:
        abort(404)
    query = request.args.get("q", "").strip()
    topic = request.args.get("topic", "")
    difficulty = request.args.get("difficulty", "")
    try:
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        offset = 0
    items, total = search_questions(
        subject,
        topic=topic or None,
        difficulty=difficulty or None,
        search=query or None,
        limit=50,
        offset=offset,
    )
    return render_template(
        "bank_viewer.html",
        subject=SUBJECTS[subject],
        subject_slug=subject,
        items=items,
        total=total,
        query=query,
        active_topic=topic,
        active_difficulty=difficulty,
    )


@exam_bp.route("/results")
def all_results():
    return render_template("results.html", attempts=recent_attempts(60))
