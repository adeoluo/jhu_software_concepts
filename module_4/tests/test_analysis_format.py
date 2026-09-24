from __future__ import annotations

import re
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


@pytest.mark.analysis
def test_page_has_answer_labels(client):
    response = client.get("/analysis")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Answer:" in html


@pytest.mark.analysis
def test_percentages_render_with_two_decimal_places(client):
    response = client.get("/analysis")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    matches = re.findall(r"\d+\.\d{2}%", html)
    assert matches
