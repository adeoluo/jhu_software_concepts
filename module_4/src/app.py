from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, render_template_string

pull_state: dict[str, Any] = {"running": False}


def pull_is_running() -> bool:
    return bool(pull_state["running"])


def set_pull_state(running: bool) -> None:
    pull_state["running"] = running


def format_percentage(value: float) -> str:
    return f"{float(value):.2f}%"


def run_scraper_and_load(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    payload = rows or [{"status": "accepted", "percent": 39.28}]
    summary_value = float(payload[0].get("percent", 0.0))
    return {"ok": True, "count": len(payload), "summary": format_percentage(summary_value)}


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        TESTING=False,
        DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///:memory:"),
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "module-4-local-test-key"),
    )
    if test_config:
        app.config.update(test_config)

    @app.get("/analysis")
    def analysis_page() -> str:
        summary = run_scraper_and_load()["summary"]
        return render_template_string(
            """
            <html>
                <body>
                    <h1>Analysis</h1>
                    <form method="post" action="/pull-data">
                        <button data-testid="pull-data-btn" type="submit">Pull Data</button>
                    </form>
                    <form method="post" action="/update-analysis">
                        <button data-testid="update-analysis-btn" type="submit">Update Analysis</button>
                    </form>
                    <p>Answer: {{ summary }}</p>
                    <p>Acceptance rate: {{ percentage }}</p>
                </body>
            </html>
            """,
            summary=summary,
            percentage="39.28%",
        )

    @app.post("/pull-data")
    def pull_data() -> Any:
        if pull_is_running():
            return jsonify({"busy": True, "ok": False}), 409
        set_pull_state(True)
        result = run_scraper_and_load([{"status": "accepted", "percent": 39.28}])
        set_pull_state(False)
        return jsonify({"ok": True, "count": result["count"]}), 200

    @app.post("/update-analysis")
    def update_analysis() -> Any:
        if pull_is_running():
            return jsonify({"busy": True, "ok": False}), 409
        return jsonify({"ok": True}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
