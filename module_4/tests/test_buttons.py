"""Pull Data / Update Analysis endpoints and busy-state gating."""

from __future__ import annotations

import subprocess

import pytest

import app as app_module


class Spy:
    """Callable test double that records its calls and returns a fixed value."""

    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return self.result


@pytest.mark.buttons
def test_pull_data_returns_ok_and_loads_scraped_rows(make_app, sample_records):
    scraper = Spy(sample_records)
    loader = Spy(len(sample_records))
    app = make_app(scraper=scraper, loader=loader, query=Spy({}))

    response = app.test_client().post("/pull-data")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "count": 5}
    assert len(scraper.calls) == 1
    assert loader.calls == [(sample_records,)]
    assert app.extensions["pull_state"].running is False
    assert "Processed 5 records" in app.extensions["pull_state"].message


@pytest.mark.buttons
def test_update_analysis_returns_200_and_refreshes_when_not_busy(make_app, snapshot):
    query = Spy(snapshot)
    app = make_app(query=query)

    response = app.test_client().post("/update-analysis")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert len(query.calls) == 1
    assert app.extensions["analysis"] is snapshot


@pytest.mark.buttons
def test_update_analysis_returns_409_and_does_not_update_when_busy(make_app, snapshot):
    query = Spy(snapshot)
    app = make_app(query=query)
    app.extensions["pull_state"].running = True

    response = app.test_client().post("/update-analysis")

    assert response.status_code == 409
    assert response.get_json()["busy"] is True
    assert query.calls == []
    assert app.extensions["analysis"] is None


@pytest.mark.buttons
def test_pull_data_returns_409_and_does_not_scrape_when_busy(make_app):
    scraper, loader = Spy([]), Spy(0)
    app = make_app(scraper=scraper, loader=loader)
    app.extensions["pull_state"].running = True

    response = app.test_client().post("/pull-data")

    assert response.status_code == 409
    assert response.get_json() == {"ok": False, "busy": True}
    assert scraper.calls == [] and loader.calls == []


@pytest.mark.buttons
def test_pull_data_loader_error_returns_500_and_clears_busy_state(make_app, sample_records):
    def failing_loader(rows):
        raise RuntimeError("database is down")

    app = make_app(scraper=lambda: sample_records, loader=failing_loader)

    response = app.test_client().post("/pull-data")

    assert response.status_code == 500
    assert response.get_json() == {"ok": False, "busy": False, "error": "Pull Data failed."}
    assert app.extensions["pull_state"].running is False
    assert "No records were changed" in app.extensions["pull_state"].message


@pytest.mark.buttons
def test_pull_state_allows_only_one_pull_at_a_time():
    state = app_module.PullState()

    assert state.try_start() is True
    assert state.try_start() is False
    state.finish("done")
    assert state.running is False and state.message == "done"
    assert state.try_start() is True


@pytest.mark.buttons
def test_default_scraper_runs_module_3_capture_then_reads_merged_json(monkeypatch, sample_records):
    commands = []

    def fake_run(command, **kwargs):
        commands.append((command, kwargs["cwd"]))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(app_module.subprocess, "run", fake_run)
    monkeypatch.setattr(app_module, "load_records", lambda path: sample_records if path.name == "applicant_data.json" else [])

    assert app_module.scrape_new_records() == sample_records
    command, cwd = commands[0]
    assert "auto_next_pages.py" in command and cwd == app_module.BASE_DIR


@pytest.mark.buttons
@pytest.mark.parametrize(
    ("stderr", "expected"),
    [("blocked by challenge", "blocked by challenge"), ("", "The scraper stopped without an error message.")],
)
def test_default_scraper_raises_when_capture_fails(monkeypatch, stderr, expected):
    monkeypatch.setattr(
        app_module.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 1, "", stderr)
    )

    with pytest.raises(RuntimeError, match=expected):
        app_module.scrape_new_records()
