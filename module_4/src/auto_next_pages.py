"""Capture Grad Cafe survey pages from a user-verified Chrome tab via the DevTools protocol.

The loop saves each page's HTML and parsed JSON, resumes from the last saved page, and
stops (rather than retrying or bypassing) on any challenge, block, or rate-limit page.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict

import websocket  # type: ignore
from bs4 import BeautifulSoup

from scrape import load_data, save_data, scrape_data_from_html_file, verify_collection_allowed

CHROME_DEBUG_URL = "http://localhost:9222"
DEFAULT_HOST = "thegradcafe.com"
DEFAULT_TARGET_ROWS = 100000
PAGE_DELAY_SECONDS = 2.0

BLOCK_MARKERS = (
    "just a moment",
    "checking your browser",
    "verify you are human",
    "attention required",
    "access denied",
    "rate limit",
    "too many requests",
    "cf-error-details",
    "cf-mitigated",
    "gateway time-out",
    "gateway timeout",
    "error code 504",
    "error code 502",
    "error code 503",
)


class BlockedError(RuntimeError):
    """Raised when the site appears to be blocking, throttling, or challenging requests."""


def _looks_blocked(html: str) -> bool:
    """Detect Cloudflare/challenge/rate-limit pages so collection stops instead of retrying."""
    lowered = html.lower()
    return any(marker in lowered for marker in BLOCK_MARKERS)


def _request_json(url: str) -> Any:
    """Send an HTTP request to Chrome DevTools JSON endpoints."""
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _list_targets() -> list[dict[str, Any]]:
    """Query Chrome DevTools for open tab target descriptors."""
    try:
        return _request_json(f"{CHROME_DEBUG_URL}/json/list")
    except Exception as exc:
        raise RuntimeError(
            "Chrome remote debugging is not available. Start Chrome with: "
            'open -a "Google Chrome" --args --remote-debugging-port=9222'
        ) from exc


def _pick_target(preferred_url: str) -> dict[str, Any]:
    """Find and return the Chrome DevTools target for GradCafe."""
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
    """Execute JavaScript in the remote Chrome browser tab via WebSocket."""
    ws = websocket.create_connection(websocket_url, suppress_origin=True)
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
    """Locate and click the Next pagination link in Chrome."""
    expression = r"""
    (() => {
        const candidates = [...document.querySelectorAll('a, button')].filter((el) => {
            if (!el || el.offsetParent === null || el.disabled) return false;
            const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
            const label = (el.getAttribute('aria-label') || '').trim().toLowerCase();
            const rel = (el.getAttribute('rel') || '').trim().toLowerCase();
            const href = (el.getAttribute('href') || '').toLowerCase();
            return rel === 'next' || text === 'next' || label === 'next' || href.includes('/survey?cursor=');
        });

        const target = candidates.find((el) => (el.getAttribute('rel') || '').toLowerCase() === 'next')
            || candidates.find((el) => (el.innerText || el.textContent || '').trim().toLowerCase() === 'next')
            || candidates.find((el) => (el.getAttribute('aria-label') || '').trim().toLowerCase() === 'next')
            || candidates.find((el) => (el.getAttribute('href') || '').toLowerCase().includes('/survey?cursor='));

        if (!target) {
            return { clicked: false, url: document.location.href };
        }

        target.scrollIntoView({ block: 'center', behavior: 'instant' });
        target.click();

        const currentUrl = document.location.href;
        return { clicked: true, url: currentUrl };
    })();
    """
    return _evaluate_js(websocket_url, expression)


def _read_current_html(websocket_url: str) -> str:
    """Fetch outerHTML of current document from the remote browser tab."""
    return _evaluate_js(websocket_url, "document.documentElement.outerHTML")


def _next_page_url_from_html(html: str) -> str:
    """Parse HTML and extract the next pagination cursor URL."""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        text = " ".join(link.get_text(" ", strip=True).split()).lower()
        label = (link.get("aria-label") or "").strip().lower()
        rel = [value.lower() for value in link.get("rel", [])]
        if text == "next" or label == "next" or "next" in rel:
            return str(link["href"])
    return ""


def _navigate_to_url(websocket_url: str, destination_url: str) -> None:
    """Direct Chrome browser tab to destination URL and wait until ready."""
    previous_url = _evaluate_js(websocket_url, "document.location.href")
    if previous_url == destination_url:
        return

    _evaluate_js(websocket_url, f"window.location.assign({json.dumps(destination_url)})")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        time.sleep(0.5)
        state = _evaluate_js(
            websocket_url,
            "({url: document.location.href, ready: document.readyState})",
        )
        if state.get("url") != previous_url and state.get("ready") == "complete":
            return
    raise RuntimeError(f"Chrome did not finish navigating to {destination_url}")


def _advance_to_next_page(websocket_url: str) -> None:
    """Click Next button and wait for pagination navigation completion."""
    previous_url = _evaluate_js(websocket_url, "document.location.href")
    click_result = _click_next_button(websocket_url)
    if not click_result.get("clicked"):
        raise RuntimeError("Could not find an enabled Next link in the results pagination.")

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        time.sleep(0.5)
        state = _evaluate_js(
            websocket_url,
            "({url: document.location.href, ready: document.readyState})",
        )
        if state.get("url") != previous_url and state.get("ready") == "complete":
            return
    # Distinguish a transient upstream error (e.g. Cloudflare 504) from a real navigation failure.
    current_html = _read_current_html(websocket_url)
    if _looks_blocked(current_html):
        raise BlockedError(
            "GradCafe returned a challenge/block/error page while navigating to the next page. "
            "Collection stopped instead of retrying or bypassing the restriction."
        )
    raise RuntimeError("Chrome did not finish navigating to the next results page.")


def _save_page_html(page_number: int, html: str, output_dir: Path, prefix: str) -> str:
    """Save captured HTML page string to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{prefix}{page_number}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def _record_key(record: dict[str, Any]) -> tuple[str, ...]:
    """Return composite tuple key for applicant record deduplication."""
    return tuple(
        str(record.get(field, "")).strip()
        for field in ("university", "raw_program", "status", "date_added", "decision_date", "raw_text")
    )


def _existing_page_files(json_dir: Path, json_prefix: str) -> list[tuple[int, Path]]:
    """Locate and return existing page-level JSON checkpoint files."""
    pattern = re.compile(rf"^{re.escape(json_prefix)}(\d+)\.json$")
    pages: list[tuple[int, Path]] = []
    for path in json_dir.glob(f"{json_prefix}*.json"):
        match = pattern.match(path.name)
        if match:
            pages.append((int(match.group(1)), path))
    return sorted(pages)


def run_capture_loop(
    start_url: str,
    pages: int | None = None,
    target_rows: int = DEFAULT_TARGET_ROWS,
    output_dir: str | Path = "data",
    prefix: str = "gradcafe_page_",
    json_prefix: str = "applicant_data_page",
    merged_output: str | Path = "applicant_data.json",
) -> list[str]:
    """Execute main pagination and capture loop across GradCafe survey pages."""
    verify_collection_allowed(start_url)
    output_path = Path(output_dir)
    html_dir = output_path / "html"
    json_dir = output_path / "json"
    html_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    target = _pick_target(start_url)
    if "webSocketDebuggerUrl" not in target:
        raise RuntimeError("Chrome target did not expose a debugging websocket endpoint.")

    existing_pages = _existing_page_files(json_dir, json_prefix)
    merged_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    merged_output_path = Path(merged_output)
    if merged_output_path.exists():
        # Seed from the merged file too, so a missing/pruned data/json page cache never loses prior rows.
        for row in load_data(merged_output_path):
            merged_by_key[_record_key(row)] = row
    previous_page_keys: list[tuple[str, ...]] = []
    for _, path in existing_pages:
        page_rows = load_data(path)
        previous_page_keys = [_record_key(row) for row in page_rows]
        for row in page_rows:
            merged_by_key[_record_key(row)] = row

    saved_files: list[str] = []
    page_number = existing_pages[-1][0] + 1 if existing_pages else 1
    last_page = page_number + pages - 1 if pages is not None else None
    if existing_pages:
        previous_html_path = html_dir / f"{prefix}{page_number - 1}.html"
        if not previous_html_path.exists():
            raise RuntimeError(f"Cannot resume because {previous_html_path} is missing.")
        next_url = _next_page_url_from_html(previous_html_path.read_text(encoding="utf-8", errors="replace"))
        if not next_url:
            raise RuntimeError(f"Cannot resume because {previous_html_path} has no Next link.")
        _navigate_to_url(target["webSocketDebuggerUrl"], next_url)
        print(f"Resuming after page {page_number - 1} with {len(merged_by_key)} unique rows already saved.")
    else:
        _navigate_to_url(target["webSocketDebuggerUrl"], start_url)

    while (last_page is None or page_number <= last_page) and len(merged_by_key) < target_rows:
        html = _read_current_html(target["webSocketDebuggerUrl"])
        if _looks_blocked(html):
            raise BlockedError(
                f"GradCafe appears to be blocking, rate-limiting, or challenging this session at page {page_number}. "
                "Collection stopped instead of retrying or bypassing the restriction."
            )
        rows = scrape_data_from_html_file(_save_page_html(page_number, html, html_dir, prefix))
        current_page_keys = [_record_key(row) for row in rows]
        if previous_page_keys and current_page_keys == previous_page_keys:
            _advance_to_next_page(target["webSocketDebuggerUrl"])
            html = _read_current_html(target["webSocketDebuggerUrl"])
            if _looks_blocked(html):
                raise BlockedError(
                    f"GradCafe appears to be blocking, rate-limiting, or challenging this session at page {page_number}. "
                    "Collection stopped instead of retrying or bypassing the restriction."
                )
            rows = scrape_data_from_html_file(_save_page_html(page_number, html, html_dir, prefix))
            current_page_keys = [_record_key(row) for row in rows]

        page_file = str(html_dir / f"{prefix}{page_number}.html")
        if len(rows) == 0:
            Path(page_file).unlink(missing_ok=True)
            raise RuntimeError(f"No rows were found on page {page_number}. The page structure may have changed.")
        if previous_page_keys and current_page_keys == previous_page_keys:
            Path(page_file).unlink(missing_ok=True)
            raise RuntimeError("The browser returned the same applicant page twice; collection stopped before duplicating data.")

        saved_files.append(page_file)
        json_path = json_dir / f"{json_prefix}{page_number}.json"
        save_data(rows, json_path)
        for row in rows:
            merged_by_key[_record_key(row)] = row
        save_data(merged_by_key.values(), merged_output)
        print(
            f"Page {page_number}: saved {len(rows)} applicant records -> {json_path} "
            f"(unique total: {len(merged_by_key)})"
        )

        if len(merged_by_key) >= target_rows:
            print(f"Target reached: {len(merged_by_key)} unique rows collected.")
            break
        if last_page is not None and page_number >= last_page:
            break

        previous_page_keys = current_page_keys
        time.sleep(PAGE_DELAY_SECONDS)  # polite throttling between page requests
        _advance_to_next_page(target["webSocketDebuggerUrl"])
        page_number += 1

    if len(merged_by_key) < target_rows:
        print(f"Stopped with {len(merged_by_key)} unique rows. Target was {target_rows} rows.")

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
    parser.add_argument("--merged-output", default="applicant_data.json", help="Incremental merged JSON output path.")
    args = parser.parse_args()

    run_capture_loop(
        start_url=args.start_url,
        pages=args.pages,
        target_rows=args.target_rows,
        output_dir=args.output_dir,
        prefix=args.html_prefix,
        json_prefix=args.json_prefix,
        merged_output=args.merged_output,
    )
