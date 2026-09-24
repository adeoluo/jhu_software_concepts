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


@pytest.mark.buttons
def test_post_pull_data_returns_ok_when_not_busy(client, monkeypatch):
    monkeypatch.setattr(app_module, "pull_is_running", lambda: False)
    monkeypatch.setattr(app_module, "run_scraper_and_load", lambda rows=None: {"ok": True, "count": 2})

    response = client.post("/pull-data")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True


@pytest.mark.buttons
def test_post_update_analysis_returns_200_when_not_busy(client, monkeypatch):
    monkeypatch.setattr(app_module, "pull_is_running", lambda: False)

    response = client.post("/update-analysis")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True


@pytest.mark.buttons
def test_busy_state_returns_409_and_skips_update(client, monkeypatch):
    monkeypatch.setattr(app_module, "pull_is_running", lambda: True)
    response = client.post("/update-analysis")
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["busy"] is True

    response = client.post("/pull-data")
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["busy"] is True


@pytest.mark.buttons
def test_helper_functions_cover_state_and_formatting():
    app_module.set_pull_state(False)
    assert app_module.pull_is_running() is False
    app_module.set_pull_state(True)
    assert app_module.pull_is_running() is True
    assert app_module.format_percentage(39.28) == "39.28%"

    payload = app_module.run_scraper_and_load([{"percent": 12.5}])
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert payload["summary"] == "12.50%"


@pytest.mark.buttons
def test_module_entry_point_runs_app(monkeypatch):
    called = {"value": False}

    def fake_run(self, *args, **kwargs):
        called["value"] = True

    monkeypatch.setattr("flask.Flask.run", fake_run)
    runpy = __import__("runpy")
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "src" / "app.py"), run_name="__main__")
    assert called["value"] is True
