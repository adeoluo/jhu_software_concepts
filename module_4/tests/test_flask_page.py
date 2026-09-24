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
def flask_client():
    app = app_module.create_app({"TESTING": True, "DATABASE_URL": "sqlite:///:memory:"})
    with app.test_client() as client:
        yield client


@pytest.mark.web
def test_app_factory_exposes_required_routes():
    app = app_module.create_app({"TESTING": True, "DATABASE_URL": "sqlite:///:memory:"})
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/analysis" in rules
    assert "/pull-data" in rules
    assert "/update-analysis" in rules


@pytest.mark.web
def test_get_analysis_page_returns_200_and_required_content(flask_client):
    response = flask_client.get("/analysis")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Analysis" in html
    assert "Pull Data" in html
    assert "Update Analysis" in html
    assert "Answer:" in html
