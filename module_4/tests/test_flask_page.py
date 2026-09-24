"""Flask app factory and Analysis page rendering."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import app as app_module

SRC = Path(app_module.__file__).resolve().parent


@pytest.mark.web
def test_create_app_is_testable_and_registers_routes(make_app, db_url):
    app = make_app()
    routes = {rule.rule: rule.methods for rule in app.url_map.iter_rules()}

    assert app.testing is True
    assert app.config["DATABASE_URL"] == db_url
    assert "GET" in routes["/"]
    assert "GET" in routes["/analysis"]
    assert "POST" in routes["/pull-data"]
    assert "POST" in routes["/update-analysis"]
    assert app.extensions["pull_state"].running is False


@pytest.mark.web
def test_create_app_defaults_to_database_url_env(db_url):
    app = app_module.create_app()
    assert app.config["DATABASE_URL"] == db_url
    assert app.testing is False


@pytest.mark.web
def test_get_analysis_renders_required_components(make_app, snapshot):
    client = make_app(query=lambda: snapshot).test_client()

    response = client.get("/analysis")

    assert response.status_code == 200
    soup = BeautifulSoup(response.data, "html.parser")
    assert "Analysis" in soup.title.get_text()
    assert "Analysis" in soup.select_one('[data-testid="page-title"]').get_text()
    pull = soup.select_one('[data-testid="pull-data-btn"]')
    update = soup.select_one('[data-testid="update-analysis-btn"]')
    assert pull is not None and pull.name == "button" and pull.get_text(strip=True) == "Pull Data"
    assert update is not None and update.name == "button" and update.get_text(strip=True) == "Update Analysis"
    assert pull.find_parent("form")["action"] == "/pull-data"
    assert update.find_parent("form")["action"] == "/update-analysis"
    assert "Answer:" in soup.get_text()


@pytest.mark.web
def test_root_route_renders_the_analysis_page(make_app, snapshot):
    client = make_app(query=lambda: snapshot).test_client()
    assert client.get("/").data == client.get("/analysis").data


@pytest.mark.web
def test_buttons_are_disabled_while_a_pull_is_running(make_app, snapshot):
    app = make_app(query=lambda: snapshot)
    app.extensions["pull_state"].running = True

    soup = BeautifulSoup(app.test_client().get("/analysis").data, "html.parser")

    assert soup.select_one('[data-testid="pull-data-btn"]').has_attr("disabled")
    assert soup.select_one('[data-testid="update-analysis-btn"]').has_attr("disabled")
    assert "Pull in progress" in soup.select_one('[data-testid="pull-status"]').get_text()


@pytest.mark.web
def test_running_app_py_starts_the_dev_server(monkeypatch, db_url):
    started = {}
    monkeypatch.setattr("flask.Flask.run", lambda self, **kwargs: started.update(kwargs))

    runpy.run_path(str(SRC / "app.py"), run_name="__main__")

    assert started == {"debug": False, "host": "127.0.0.1", "port": 5050}
