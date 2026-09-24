"""Flask web layer for the Grad Cafe analysis service.

``create_app`` builds the application. The scraper, loader, and analysis query
are injectable so tests can run without the network or a long scrape.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from flask import Flask, current_app, jsonify, render_template

import models
from load_data import load_into_database, load_records
from orm_queries import analysis_snapshot


BASE_DIR = Path(__file__).resolve().parent

Scraper = Callable[[], list[dict[str, Any]]]
Loader = Callable[[list[dict[str, Any]]], int]
Query = Callable[[], dict[str, Any]]


class PullState:
    """Thread-safe busy flag shared by Pull Data and Update Analysis."""

    def __init__(self) -> None:
        """Start idle with a default status message."""
        self._lock = threading.Lock()
        self.running = False
        self.message = "No data pull has been started."

    def try_start(self) -> bool:
        """Mark a pull as running; return ``False`` if one is already active."""
        with self._lock:
            if self.running:
                return False
            self.running = True
            self.message = "Pull Data is retrieving newly available Grad Cafe records."
            return True

    def finish(self, message: str) -> None:
        """Clear the busy flag and record the outcome shown on the page."""
        with self._lock:
            self.running = False
            self.message = message


def scrape_new_records() -> list[dict[str, Any]]:
    """Run the Module 3 browser-capture scraper and return the merged applicant records."""
    command = [
        sys.executable,
        "auto_next_pages.py",
        "--start-url",
        "https://www.thegradcafe.com/survey",
        "--target-rows",
        "100000",
        "--output-dir",
        "data",
        "--merged-output",
        "applicant_data.json",
    ]
    result = subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or "The scraper stopped without an error message."
        raise RuntimeError(f"Pull Data stopped: {detail[-500:]}")
    return load_records(BASE_DIR / "applicant_data.json")


def format_number(value: Any, decimals: int = 2) -> str:
    """Format a number with thousands separators and a fixed number of decimals."""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}" if decimals else f"{value:,}"


def format_percent(value: Any) -> str:
    """Format a percentage with exactly two decimals, e.g. ``39.28%``."""
    if value is None:
        return "N/A"
    return f"{format_number(value)}%"


def page_data(data: dict[str, Any]) -> dict[str, Any]:
    """Add display-ready strings to an analysis snapshot for the template."""
    data = dict(data)
    data["display"] = {
        "q1": format_number(data["q1"], 0),
        "q2": format_percent(data["q2"]),
        "q3_gpa": format_number(data["q3"]["gpa"]),
        "q3_gre": format_number(data["q3"]["gre"]),
        "q3_gre_v": format_number(data["q3"]["gre_v"]),
        "q3_gre_aw": format_number(data["q3"]["gre_aw"]),
        "q4": format_number(data["q4"]),
        "q5": format_percent(data["q5"]),
        "q6": format_number(data["q6"]),
        "q7": format_number(data["q7"], 0),
        "q8": format_number(data["q8"], 0),
        "q9": format_number(data["q9"], 0),
        "difference": f"{data['q9_difference']:+,}",
        "q11": [(classification.title(), format_number(average)) for classification, average in data["q11"]],
    }
    return data


def current_analysis() -> dict[str, Any]:
    """Return the app's cached analysis snapshot, running the injected query on first use."""
    extensions = current_app.extensions
    if extensions["analysis"] is None:
        extensions["analysis"] = extensions["services"]["query"]()
    return extensions["analysis"]


def analysis() -> str:
    """``GET /`` and ``GET /analysis``: render the Analysis page.

    Shows the latest snapshot stored by Update Analysis (or computed on first load),
    the Pull Data / Update Analysis buttons, and the current pull status.
    """
    state: PullState = current_app.extensions["pull_state"]
    return render_template(
        "index.html",
        data=page_data(current_analysis()),
        pull_running=state.running,
        pull_message=state.message,
    )


def pull_data() -> Any:
    """``POST /pull-data``: scrape new records and pass them to the loader.

    :returns: 200 ``{"ok": true, "count": N}`` on success; 409 ``{"ok": false, "busy": true}``
        if a pull is already running; 500 ``{"ok": false, "busy": false, "error": ...}`` if
        scraping or loading fails (the loader's single transaction leaves no partial writes).
    """
    state: PullState = current_app.extensions["pull_state"]
    services = current_app.extensions["services"]
    if not state.try_start():
        return jsonify(ok=False, busy=True), 409
    try:
        count = services["loader"](services["scraper"]())
    except Exception:
        current_app.logger.exception("Pull Data failed")
        state.finish("Pull Data failed. No records were changed; see the server log.")
        return jsonify(ok=False, busy=False, error="Pull Data failed."), 500
    state.finish(f"Pull Data finished. Processed {count:,} records.")
    return jsonify(ok=True, count=count), 200


def update_analysis() -> Any:
    """``POST /update-analysis``: re-run the analysis query and store the new snapshot.

    :returns: 200 ``{"ok": true}`` when not busy; 409 ``{"ok": false, "busy": true}`` while
        a pull is running, in which case the stored snapshot is left unchanged.
    """
    if current_app.extensions["pull_state"].running:
        return jsonify(ok=False, busy=True), 409
    current_app.extensions["analysis"] = current_app.extensions["services"]["query"]()
    return jsonify(ok=True), 200


def create_app(
    config: dict[str, Any] | None = None,
    *,
    scraper: Scraper | None = None,
    loader: Loader | None = None,
    query: Query | None = None,
) -> Flask:
    """Build the Flask app and register its routes.

    :param config: Flask config overrides. ``DATABASE_URL`` repoints all database access.
    :param scraper: Returns raw applicant records; defaults to :func:`scrape_new_records`.
    :param loader: Writes records to PostgreSQL and returns the count; defaults to
        :func:`load_data.load_into_database`.
    :param query: Returns the analysis snapshot; defaults to :func:`orm_queries.analysis_snapshot`.
    """
    app = Flask(__name__)
    app.config.update(DATABASE_URL=os.getenv("DATABASE_URL"))
    app.config.update(config or {})
    if config and config.get("DATABASE_URL"):
        models.use_database(config["DATABASE_URL"])

    app.extensions["services"] = {
        "scraper": scraper or scrape_new_records,
        "loader": loader or load_into_database,
        "query": query or analysis_snapshot,
    }
    app.extensions["pull_state"] = PullState()
    app.extensions["analysis"] = None

    app.add_url_rule("/", view_func=analysis, methods=["GET"])
    app.add_url_rule("/analysis", view_func=analysis, methods=["GET"])
    app.add_url_rule("/pull-data", view_func=pull_data, methods=["POST"])
    app.add_url_rule("/update-analysis", view_func=update_analysis, methods=["POST"])
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=int(os.getenv("PORT", "5050")))
