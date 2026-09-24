from __future__ import annotations

import fcntl
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from flask import Flask, flash, redirect, render_template, url_for

from orm_queries import analysis_snapshot


BASE_DIR = Path(__file__).resolve().parent
LOCK_PATH = BASE_DIR / "pull_data.lock"
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "module-3-local-development-key")

_state_lock = threading.Lock()
pull_state: dict[str, Any] = {
    "running": False,
    "message": "No data pull has been started.",
}


def pull_is_running() -> bool:
    """Return whether a Pull Data operation is currently active."""
    with _state_lock:
        return bool(pull_state["running"])


def _set_pull_state(running: bool, message: str) -> None:
    """Update the shared Pull Data status shown by the webpage."""
    with _state_lock:
        pull_state["running"] = running
        pull_state["message"] = message


def _run_pull_data() -> None:
    """Run the protected scraper and load its new records into PostgreSQL."""
    lock_acquired = False
    try:
        with LOCK_PATH.open("w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_acquired = True
            scrape_command = [
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
            scrape_result = subprocess.run(
                scrape_command,
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
            if scrape_result.returncode != 0:
                detail = scrape_result.stderr.strip() or "The scraper stopped without an error message."
                _set_pull_state(False, f"Pull Data stopped: {detail[-500:]}")
                return

            load_result = subprocess.run(
                [sys.executable, "load_data.py", "--input", "applicant_data.json"],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
            if load_result.returncode != 0:
                detail = load_result.stderr.strip() or "The database loader stopped without an error message."
                _set_pull_state(False, f"New data was captured, but database loading failed: {detail[-500:]}")
                return

            _set_pull_state(False, "Pull Data finished. New usable records are now available in the database.")
    except BlockingIOError:
        _set_pull_state(False, "Another Pull Data operation is already running.")
    except Exception as exc:  # pragma: no cover - protects the background request
        _set_pull_state(False, f"Pull Data failed: {exc}")
    finally:
        if lock_acquired:
            try:
                LOCK_PATH.unlink()
            except FileNotFoundError:
                pass


def format_number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (float, int)):
        return f"{value:,.{decimals}f}" if decimals else f"{value:,}"
    return f"{value:.{decimals}f}" if decimals else f"{value:,}"


def page_data() -> dict[str, Any]:
    """Build formatted analysis values for the SQLAlchemy-backed template."""
    data = analysis_snapshot()
    data["display"] = {
        "q1": format_number(data["q1"], 0),
        "q2": f"{format_number(data['q2'])}%",
        "q3_gpa": format_number(data["q3"]["gpa"]),
        "q3_gre": format_number(data["q3"]["gre"]),
        "q3_gre_v": format_number(data["q3"]["gre_v"]),
        "q3_gre_aw": format_number(data["q3"]["gre_aw"]),
        "q4": format_number(data["q4"]),
        "q5": f"{format_number(data['q5'])}%",
        "q6": format_number(data["q6"]),
        "q7": format_number(data["q7"], 0),
        "q8": format_number(data["q8"], 0),
        "q9": format_number(data["q9"], 0),
        "difference": f"{data['q9_difference']:+,}",
        "q11": [(classification.title(), format_number(average)) for classification, average in data["q11"]],
    }
    return data


@app.get("/")
def index() -> str:
    """Render the current database analysis page."""
    return render_template(
        "index.html",
        data=page_data(),
        pull_running=pull_is_running(),
        pull_message=pull_state["message"],
    )


@app.post("/pull-data")
def pull_data() -> Any:
    """Start Pull Data once, or report that an existing pull is active."""
    with _state_lock:
        if pull_state["running"]:
            flash("Pull Data is already running. Please wait for it to finish.", "warning")
            return redirect(url_for("index"))
        pull_state["running"] = True
        pull_state["message"] = "Pull Data is retrieving newly available Grad Cafe records."
    threading.Thread(target=_run_pull_data, daemon=True).start()
    flash("Pull Data started. Update Analysis will show the database when the pull finishes.", "info")
    return redirect(url_for("index"))


@app.post("/update-analysis")
def update_analysis() -> Any:
    """Refresh the page from PostgreSQL without starting a scrape."""
    if pull_is_running():
        flash("New data is currently being retrieved. The displayed analysis is from the latest completed database state.", "warning")
    else:
        flash("Analysis updated from the current PostgreSQL database.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=int(os.getenv("PORT", "5050")))
