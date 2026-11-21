"""ExamPulse 1000 - main Flask application.

Run locally:
    python seed_1000_questions.py
    python app.py
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request

from exampulse_core import CANDIDATE_NAME, MODES, SUBJECTS, close_db, init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("EXAMPULSE_SECRET", "exampulse-1000-local-dev-key"),
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=256 * 1024,
    )

    # Creates the schema and (on first run) imports the four JSON question banks.
    init_db()
    app.teardown_appcontext(close_db)

    from routes.api_routes import api_bp
    from routes.exam_routes import exam_bp

    app.register_blueprint(exam_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.context_processor
    def inject_globals() -> dict:
        return {
            "subjects": SUBJECTS,
            "modes": MODES,
            "candidate_name": CANDIDATE_NAME,
            "app_name": "ExamPulse 1000",
        }

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Endpoint not found"}), 404
        return render_template("not_found.html"), 404

    @app.errorhandler(400)
    def bad_request(error):
        description = getattr(error, "description", "Bad request")
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": str(description)}), 400
        return render_template("not_found.html"), 400

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create/refresh the SQLite schema and import all question banks."""
        from exampulse_core import seed_questions

        counts = seed_questions(force=True)
        print("Seeded:", counts, "total:", sum(counts.values()))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("EXAMPULSE_HOST", "0.0.0.0"),
        port=int(os.environ.get("EXAMPULSE_PORT", "5000")),
        debug=os.environ.get("EXAMPULSE_DEBUG", "1") == "1",
    )
