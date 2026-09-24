"""Chrome DevTools capture scripts, driven entirely by fakes (no browser, no network)."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

import auto_next_pages as anp
import capture_chrome_html as cch
import scrape
from fakes import FakeClock, FakeWebSocket, fake_urlopen

SRC = Path(anp.__file__).resolve().parent
GRADCAFE_TAB = {"type": "page", "url": "https://www.thegradcafe.com/survey", "webSocketDebuggerUrl": "ws://tab"}


def row(n: int) -> dict:
    return {"university": f"University {n}", "raw_text": f"row {n}"}


PAGE_ROWS = {"PAGE-1": [row(1), row(2)], "PAGE-2": [row(3)], "EMPTY": []}


class FakeBrowser:
    """Plays back a list of page HTML strings as the tab moves forward."""

    def __init__(self, pages: list[str]) -> None:
        self.pages = pages
        self.index = 0
        self.navigated: list[str] = []

    def read(self, ws_url: str) -> str:
        return self.pages[self.index]

    def advance(self, ws_url: str) -> None:
        self.index = min(self.index + 1, len(self.pages) - 1)

    def navigate(self, ws_url: str, url: str) -> None:
        self.navigated.append(url)


@pytest.fixture
def browser(monkeypatch):
    """Wire run_capture_loop to a FakeBrowser; returns a factory taking the page sequence."""

    def use(pages: list[str]) -> FakeBrowser:
        fake = FakeBrowser(pages)
        monkeypatch.setattr(anp, "verify_collection_allowed", lambda url: "")
        monkeypatch.setattr(anp, "_pick_target", lambda url: GRADCAFE_TAB)
        monkeypatch.setattr(anp, "_read_current_html", fake.read)
        monkeypatch.setattr(anp, "_advance_to_next_page", fake.advance)
        monkeypatch.setattr(anp, "_navigate_to_url", fake.navigate)
        monkeypatch.setattr(anp, "scrape_data_from_html_file", lambda path: PAGE_ROWS[Path(path).read_text()])
        monkeypatch.setattr(anp, "time", FakeClock())
        return fake

    return use


def capture(tmp_path, **kwargs):
    return anp.run_capture_loop(
        "https://www.thegradcafe.com/survey",
        output_dir=tmp_path / "data",
        merged_output=tmp_path / "merged.json",
        **kwargs,
    )


# ---------- run_capture_loop ----------

@pytest.mark.integration
def test_capture_loop_saves_each_page_and_merges_unique_rows(browser, tmp_path, capsys):
    fake = browser(["PAGE-1", "PAGE-2"])

    saved = capture(tmp_path, pages=2, target_rows=100)

    assert [Path(path).name for path in saved] == ["gradcafe_page_1.html", "gradcafe_page_2.html"]
    assert fake.navigated == ["https://www.thegradcafe.com/survey"]
    assert len(json.loads((tmp_path / "merged.json").read_text())) == 3
    assert (tmp_path / "data" / "json" / "applicant_data_page2.json").exists()
    assert "Stopped with 3 unique rows" in capsys.readouterr().out
    assert anp.time.slept == [anp.PAGE_DELAY_SECONDS]


@pytest.mark.integration
def test_capture_loop_stops_at_target_rows(browser, tmp_path, capsys):
    browser(["PAGE-1", "PAGE-2"])

    assert len(capture(tmp_path, target_rows=2)) == 1
    assert "Target reached: 2 unique rows" in capsys.readouterr().out


@pytest.mark.integration
def test_capture_loop_skips_a_repeated_page_after_one_retry(browser, tmp_path):
    browser(["PAGE-1", "PAGE-1", "PAGE-2", "PAGE-2", "PAGE-2"])

    with pytest.raises(RuntimeError, match="same applicant page twice"):
        capture(tmp_path)
    assert len(json.loads((tmp_path / "merged.json").read_text())) == 3


@pytest.mark.integration
@pytest.mark.parametrize("pages", [["Just a moment..."], ["PAGE-1", "PAGE-1", "Verify you are human"]])
def test_capture_loop_stops_when_blocked(browser, tmp_path, pages):
    browser(pages)
    with pytest.raises(anp.BlockedError):
        capture(tmp_path)


@pytest.mark.integration
def test_capture_loop_stops_on_a_page_without_rows(browser, tmp_path):
    browser(["EMPTY"])
    with pytest.raises(RuntimeError, match="No rows were found on page 1"):
        capture(tmp_path)
    assert not (tmp_path / "data" / "html" / "gradcafe_page_1.html").exists()


@pytest.mark.integration
def test_capture_loop_requires_a_debugger_websocket(browser, tmp_path, monkeypatch):
    browser(["PAGE-1"])
    monkeypatch.setattr(anp, "_pick_target", lambda url: {})
    with pytest.raises(RuntimeError, match="debugging websocket"):
        capture(tmp_path)


def seed_previous_run(tmp_path, html: str | None) -> None:
    json_dir, html_dir = tmp_path / "data" / "json", tmp_path / "data" / "html"
    json_dir.mkdir(parents=True)
    html_dir.mkdir(parents=True)
    (json_dir / "applicant_data_page1.json").write_text(json.dumps([row(1)]))
    (json_dir / "applicant_data_pageX.json").write_text("[]")
    (tmp_path / "merged.json").write_text(json.dumps([row(0)]))
    if html is not None:
        (html_dir / "gradcafe_page_1.html").write_text(html)


@pytest.mark.integration
def test_capture_loop_resumes_after_the_last_saved_page(browser, tmp_path, capsys):
    seed_previous_run(tmp_path, '<a href="https://www.thegradcafe.com/survey?cursor=abc">Next</a>')
    fake = browser(["PAGE-2"])

    saved = capture(tmp_path, pages=1)

    assert fake.navigated == ["https://www.thegradcafe.com/survey?cursor=abc"]
    assert [Path(path).name for path in saved] == ["gradcafe_page_2.html"]
    assert len(json.loads((tmp_path / "merged.json").read_text())) == 3
    assert "Resuming after page 1 with 2 unique rows" in capsys.readouterr().out


@pytest.mark.integration
@pytest.mark.parametrize(("html", "message"), [(None, "is missing"), ("<p>no pagination</p>", "has no Next link")])
def test_capture_loop_cannot_resume_without_the_previous_page(browser, tmp_path, html, message):
    seed_previous_run(tmp_path, html)
    browser(["PAGE-2"])
    with pytest.raises(RuntimeError, match=message):
        capture(tmp_path)


@pytest.mark.integration
def test_auto_next_pages_command_line_checks_robots_first(monkeypatch, tmp_path):
    class RobotsChecked(Exception):
        pass

    def stop(url):
        raise RobotsChecked(url)

    monkeypatch.setattr(scrape, "verify_collection_allowed", stop)
    monkeypatch.setattr(sys, "argv", ["auto_next_pages.py", "--pages", "1", "--output-dir", str(tmp_path)])

    with pytest.raises(RobotsChecked, match="thegradcafe.com/survey"):
        runpy.run_path(str(SRC / "auto_next_pages.py"), run_name="__main__")


# ---------- DevTools helpers in auto_next_pages ----------

@pytest.mark.integration
def test_block_detection_and_record_keys(tmp_path):
    assert anp._looks_blocked("<title>Just a moment...</title>") is True
    assert anp._looks_blocked("<table>results</table>") is False
    assert anp._record_key({"university": " MIT ", "status": "Accepted"})[:3] == ("MIT", "", "Accepted")
    path = anp._save_page_html(3, "<html/>", tmp_path / "html", "p_")
    assert Path(path).read_text() == "<html/>"
    (tmp_path / "p_10.json").write_text("[]")
    (tmp_path / "p_2.json").write_text("[]")
    assert [n for n, _ in anp._existing_page_files(tmp_path, "p_")] == [2, 10]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ('<a href="/survey?cursor=1">Next</a>', "/survey?cursor=1"),
        ('<a href="/survey?cursor=2" aria-label="Next">&rsaquo;</a>', "/survey?cursor=2"),
        ('<a href="/survey?cursor=3" rel="next">&raquo;</a>', "/survey?cursor=3"),
        ('<a href="/survey?cursor=0">Previous</a>', ""),
    ],
)
def test_next_page_url_from_html(html, expected):
    assert anp._next_page_url_from_html(html) == expected


@pytest.mark.integration
def test_request_json_and_list_targets(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen([GRADCAFE_TAB]))
    assert anp._request_json("http://localhost:9222/json/list") == [GRADCAFE_TAB]
    assert anp._list_targets() == [GRADCAFE_TAB]


@pytest.mark.integration
@pytest.mark.parametrize("module", [anp, cch], ids=["auto_next_pages", "capture_chrome_html"])
def test_list_targets_explains_how_to_enable_chrome_debugging(monkeypatch, module):
    def refuse(url):
        raise OSError("connection refused")

    monkeypatch.setattr(module, "_request_json", refuse)
    with pytest.raises(RuntimeError, match="remote-debugging-port=9222"):
        module._list_targets()


@pytest.mark.integration
def test_pick_target_prefers_an_open_gradcafe_tab_then_opens_one(monkeypatch):
    other = {"type": "page", "url": "about:blank"}
    monkeypatch.setattr(anp, "time", FakeClock())

    monkeypatch.setattr(anp, "_list_targets", lambda: [other, GRADCAFE_TAB])
    assert anp._pick_target("https://www.thegradcafe.com/survey") is GRADCAFE_TAB

    monkeypatch.setattr(anp, "_list_targets", lambda: [other, other])
    monkeypatch.setattr(anp, "_request_json", lambda url: {"id": "new-tab"})
    assert anp._pick_target("https://www.thegradcafe.com/survey") == {"id": "new-tab"}

    def refuse(url):
        raise OSError("cannot open tab")

    monkeypatch.setattr(anp, "_request_json", refuse)
    with pytest.raises(RuntimeError, match="No GradCafe page"):
        anp._pick_target("https://www.thegradcafe.com/survey")
    monkeypatch.setattr(anp, "_list_targets", lambda: [other])
    assert anp._pick_target("https://www.thegradcafe.com/survey") is other


@pytest.mark.integration
def test_evaluate_js_returns_the_value_for_its_request_id(monkeypatch):
    sockets = [
        FakeWebSocket([{"id": 7}, {"id": 1, "result": {"result": {"value": "done"}}}]),
        FakeWebSocket([{"id": 1, "result": {"result": {}, "value": "fallback"}}]),
    ]
    monkeypatch.setattr(anp.websocket, "create_connection", lambda url, suppress_origin: sockets.pop(0))

    assert anp._evaluate_js("ws://tab", "1 + 1") == "done"
    assert anp._evaluate_js("ws://tab", "1 + 1") == "fallback"


@pytest.mark.integration
def test_click_next_and_read_html_use_devtools(monkeypatch):
    expressions = []
    monkeypatch.setattr(anp, "_evaluate_js", lambda url, expression: expressions.append(expression) or {"clicked": True})

    assert anp._click_next_button("ws://tab") == {"clicked": True}
    assert anp._read_current_html("ws://tab") == {"clicked": True}
    assert "rel === 'next'" in expressions[0] and expressions[1] == "document.documentElement.outerHTML"


def devtools(monkeypatch, *, final_url: str, ready: str = "complete", html: str = "<html/>", clicked: bool = True):
    monkeypatch.setattr(anp, "time", FakeClock())
    monkeypatch.setattr(anp, "_click_next_button", lambda url: {"clicked": clicked})

    def evaluate(url, expression):
        if expression == "document.location.href":
            return "https://old"
        if expression == "document.documentElement.outerHTML":
            return html
        if expression.startswith("({url"):
            return {"url": final_url, "ready": ready}
        return None

    monkeypatch.setattr(anp, "_evaluate_js", evaluate)


@pytest.mark.integration
def test_navigate_to_url(monkeypatch):
    devtools(monkeypatch, final_url="https://new")
    anp._navigate_to_url("ws://tab", "https://old")
    anp._navigate_to_url("ws://tab", "https://new")

    devtools(monkeypatch, final_url="https://old", ready="loading")
    with pytest.raises(RuntimeError, match="did not finish navigating to https://new"):
        anp._navigate_to_url("ws://tab", "https://new")


@pytest.mark.integration
def test_advance_to_next_page(monkeypatch):
    devtools(monkeypatch, final_url="https://new")
    anp._advance_to_next_page("ws://tab")

    devtools(monkeypatch, final_url="https://new", clicked=False)
    with pytest.raises(RuntimeError, match="Could not find an enabled Next link"):
        anp._advance_to_next_page("ws://tab")

    devtools(monkeypatch, final_url="https://old", html="Error code 504")
    with pytest.raises(anp.BlockedError):
        anp._advance_to_next_page("ws://tab")

    devtools(monkeypatch, final_url="https://old")
    with pytest.raises(RuntimeError, match="next results page"):
        anp._advance_to_next_page("ws://tab")


# ---------- capture_chrome_html ----------

@pytest.mark.integration
def test_capture_chrome_html_helpers(monkeypatch):
    monkeypatch.setattr(cch, "urlopen", fake_urlopen([GRADCAFE_TAB]))
    assert cch._request_json("http://localhost:9222/json/list") == [GRADCAFE_TAB]
    assert cch._list_targets() == [GRADCAFE_TAB]

    other = {"type": "page", "url": "about:blank"}
    monkeypatch.setattr(cch, "time", FakeClock())
    assert cch._pick_target([other, GRADCAFE_TAB], "") is GRADCAFE_TAB
    monkeypatch.setattr(cch, "_request_json", lambda url: {"id": "new-tab"})
    assert cch._pick_target([other, other], "https://www.thegradcafe.com/survey") == {"id": "new-tab"}

    def refuse(url):
        raise OSError("cannot open tab")

    monkeypatch.setattr(cch, "_request_json", refuse)
    assert cch._pick_target([other], "https://www.thegradcafe.com/survey") is other
    assert cch._pick_target([other], "") is other
    with pytest.raises(RuntimeError, match="No GradCafe page"):
        cch._pick_target([other, other], "https://www.thegradcafe.com/survey")


@pytest.mark.integration
def test_capture_chrome_html_reads_page_html(monkeypatch):
    sockets = [
        FakeWebSocket([{"id": 3}, {"id": 1, "result": {"result": {"value": "<html>ok</html>"}}}]),
        FakeWebSocket([{"id": 1, "result": {"result": {"value": 42}}}]),
    ]
    monkeypatch.setattr(cch.websocket, "create_connection", lambda url, suppress_origin: sockets.pop(0))

    assert cch._read_current_page_html("ws://tab") == "<html>ok</html>"
    assert cch._read_current_page_html("ws://tab") == ""


@pytest.mark.integration
def test_capture_html_writes_file_and_requires_websocket(monkeypatch, tmp_path):
    monkeypatch.setattr(cch, "_list_targets", lambda: [GRADCAFE_TAB])
    monkeypatch.setattr(cch, "_read_current_page_html", lambda url: "<html>saved</html>")

    assert cch.capture_html("https://www.thegradcafe.com/survey", str(tmp_path / "a" / "p.html")).endswith("p.html")
    assert (tmp_path / "a" / "p.html").read_text() == "<html>saved</html>"

    monkeypatch.setattr(cch, "_list_targets", lambda: [{"type": "page", "url": "https://www.thegradcafe.com/x"}])
    with pytest.raises(RuntimeError, match="debugging websocket"):
        cch.capture_html("https://www.thegradcafe.com/survey", str(tmp_path / "b.html"))


@pytest.mark.integration
def test_capture_chrome_html_command_line(monkeypatch, tmp_path, capsys):
    import websocket

    output = tmp_path / "page.html"
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen([GRADCAFE_TAB]))
    monkeypatch.setattr(
        websocket, "create_connection",
        lambda url, suppress_origin: FakeWebSocket([{"id": 1, "result": {"result": {"value": "<html>cli</html>"}}}]),
    )
    monkeypatch.setattr(sys, "argv", ["capture_chrome_html.py", "--output", str(output)])

    runpy.run_path(str(SRC / "capture_chrome_html.py"), run_name="__main__")

    assert output.read_text() == "<html>cli</html>"
    assert "Saved 16 characters" in capsys.readouterr().out
