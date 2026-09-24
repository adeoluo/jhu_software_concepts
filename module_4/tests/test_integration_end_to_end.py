from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import app as app_module  # noqa: E402


@pytest.fixture
def client():
    app = app_module.create_app({"TESTING": True, "DATABASE_URL": "sqlite:///:memory:"})
    with app.test_client() as test_client:
        yield test_client


@pytest.mark.integration
def test_end_to_end_pull_update_render_flow(client, monkeypatch):
    monkeypatch.setattr(app_module, "pull_is_running", lambda: False)
    monkeypatch.setattr(
        app_module,
        "run_scraper_and_load",
        lambda rows=None: {"ok": True, "count": 2, "summary": "39.28%"},
    )

    pull = client.post("/pull-data")
    assert pull.status_code == 200

    update = client.post("/update-analysis")
    assert update.status_code == 200

    page = client.get("/analysis")
    assert page.status_code == 200
    assert "Analysis" in page.get_data(as_text=True)
    assert "39.28%" in page.get_data(as_text=True)
