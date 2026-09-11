from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

import websocket  # type: ignore

from scrape import save_data, scrape_data_from_html_file

CHROME_DEBUG_URL = "http://localhost:9222"
DEFAULT_HOST = "thegradcafe.com"
DEFAULT_TARGET_ROWS = 100000


def _request_json(url: str) -> Any:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _list_targets() -> list[dict[str, Any]]:
    try:
        return _request_json(f"{CHROME_DEBUG_URL}/json/list")
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Chrome remote debugging is not available. Start Chrome with: "
            'open -a "Google Chrome" --args --remote-debugging-port=9222'
        ) from exc


def _pick_target(preferred_url: str) -> dict[str, Any]:
    targets = _list_targets()
    matches = [t for t in targets if t.get("type") == "page" and DEFAULT_HOST in (t.get("url") or "")]
    if matches:
        return matches[0]

    try:
        new_target = _request_json(f"{CHROME_DEBUG_URL}/json/new?{preferred_url}")
        time.sleep(1.5)
        return new_target
    except Exception:
        pass

    if len(targets) == 1:
        return targets[0]

    raise RuntimeError(
        "No GradCafe page is currently open in Chrome DevTools. "
        "Open the GradCafe results page in Chrome and run the script again."
    )


def _evaluate_js(websocket_url: str, expression: str) -> Any:
    ws = websocket.create_connection(websocket_url)
    try:
        ws.send(
            json.dumps(
                {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {"expression": expression, "returnByValue": True},
                }
            )
        )

        while True:
            message = ws.recv()
            payload = json.loads(message)
            if payload.get("id") == 1:
                result = payload.get("result", {}).get("result", {})
                value = result.get("value")
                if value is not None:
                    return value
                return payload.get("result", {}).get("value")
    finally:
        ws.close()


def _click_next_button(websocket_url: str) -> Dict[str, Any]:
    expression = r"""
    (() => {
        const candidates = [];
        const all = document.querySelectorAll('a, button, input, span, div');
        for (const el of all) {
            if (!el || el.offsetParent === null) continue;
            const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
            const label = (el.getAttribute('aria-label') || '').toLowerCase();
            const title = (el.getAttribute('title') || '').toLowerCase();
            const value = (el.value || '').toLowerCase();
            const href = (el.getAttribute('href') || '').toLowerCase();
            const className = (el.className || '').toString().toLowerCase();
            const id = (el.id || '').toLowerCase();
            const textMatches = ['next', 'older', 'more', 'continue', 'view more'];
            const matches = textMatches.some((word) => text.includes(word) || label.includes(word) || title.includes(word) || value.includes(word) || href.includes(word) || className.includes(word) || id.includes(word));
            if (matches) candidates.push(el);
        }

        const target = candidates.find((el) => {
            const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
            return text.includes('next') || text.includes('older') || text.includes('more') || text.includes('continue');
        }) || candidates[0];

        if (!target) {
            return { clicked: false, url: document.location.href };
        }

        target.scrollIntoView({ block: 'center', behavior: 'instant' });
        target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
        if (typeof target.click === 'function') target.click();

        const currentUrl = document.location.href;
        return { clicked: true, url: currentUrl };
    })();
    """
    return _evaluate_js(websocket_url, expression)


def _read_current_html(websocket_url: str) -> str:
    return _evaluate_js(websocket_url, "document.documentElement.outerHTML")


def _save_page_html(page_number: int, html: str, output_dir: Path, prefix: str) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{prefix}{page_number}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def run_capture_loop(
    start_url: str,
    pages: int | None = None,
    target_rows: int = DEFAULT_TARGET_ROWS,
    output_dir: str | Path = "data",
    prefix: str = "gradcafe_page_",
    json_prefix: str = "applicant_data_page",
) -> list[str]:
    output_path = Path(output_dir)
    html_dir = output_path / "html"
    json_dir = output_path / "json"
    html_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    target = _pick_target(start_url)
    if "webSocketDebuggerUrl" not in target:
        raise RuntimeError("Chrome target did not expose a debugging websocket endpoint.")

    saved_files: list[str] = []
    total_rows = 0
    page_number = 1
    max_pages = pages if pages is not None else max(1, target_rows // 10 + 100)

    while page_number <= max_pages and total_rows < target_rows:
        if page_number > 1:
            time.sleep(1.5)
            click_result = _click_next_button(target["webSocketDebuggerUrl"])
            if not click_result.get("clicked"):
                raise RuntimeError(f"Could not find the Next button on page {page_number - 1}.")
            time.sleep(3)
            current_url = _evaluate_js(target["webSocketDebuggerUrl"], "document.location.href")
            if not current_url or current_url.startswith("about:blank"):
                raise RuntimeError("The browser did not advance to the next page after clicking Next.")

        html = _read_current_html(target["webSocketDebuggerUrl"])
        page_file = _save_page_html(page_number, html, html_dir, prefix)
        saved_files.append(page_file)

        rows = scrape_data_from_html_file(page_file)
        total_rows += len(rows)

        json_path = json_dir / f"{json_prefix}{page_number}.json"
        save_data(rows, json_path)
        print(f"Page {page_number}: saved {len(rows)} rows -> {json_path} (total so far: {total_rows})")

        if len(rows) == 0:
            raise RuntimeError(f"No rows were found on page {page_number}. The page structure may have changed.")

        if total_rows >= target_rows:
            print(f"Target reached: {total_rows} rows collected, exceeding {target_rows}.")
            break

        page_number += 1
        time.sleep(1.0)

    if total_rows < target_rows:
        print(f"Stopped after {page_number - 1} pages with {total_rows} rows. Target was {target_rows} rows.")

    return saved_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Capture GradCafe pages using the browser’s Next button and save parsed JSON; default target is 100,000 rows."
    )
    parser.add_argument("--start-url", default="https://www.thegradcafe.com/survey", help="The page to begin from.")
    parser.add_argument("--pages", type=int, default=None, help="Maximum number of pages to capture in sequence.")
    parser.add_argument("--target-rows", type=int, default=DEFAULT_TARGET_ROWS, help="Target row count before stopping.")
    parser.add_argument("--output-dir", default="data", help="Base directory for captured HTML and JSON outputs. Subfolders html/ and json/ are used automatically.")
    parser.add_argument("--html-prefix", default="gradcafe_page_", help="HTML file prefix.")
    parser.add_argument("--json-prefix", default="applicant_data_page", help="JSON file prefix.")
    args = parser.parse_args()

    run_capture_loop(
        start_url=args.start_url,
        pages=args.pages,
        target_rows=args.target_rows,
        output_dir=args.output_dir,
        prefix=args.html_prefix,
        json_prefix=args.json_prefix,
    )
