from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import websocket  # type: ignore

CHROME_DEBUG_URL = "http://localhost:9222"


def _request_json(url: str) -> Any:
    """Send an HTTP request to Chrome DevTools endpoint and return JSON response."""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _list_targets() -> list[dict[str, Any]]:
    """Query Chrome DevTools HTTP endpoint for active page targets."""
    try:
        return _request_json(f"{CHROME_DEBUG_URL}/json/list")
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Chrome remote debugging is not available. Start Chrome with: "
            'open -a "Google Chrome" --args --remote-debugging-port=9222'
        ) from exc


def _pick_target(targets: list[dict[str, Any]], preferred_url: str) -> dict[str, Any]:
    """Select the active GradCafe page target from Chrome DevTools targets."""
    preferred_host = "thegradcafe.com"
    matches = [t for t in targets if t.get("type") == "page" and preferred_host in (t.get("url") or "")]
    if matches:
        return matches[0]
    if preferred_url:
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


def _read_current_page_html(websocket_url: str) -> str:
    """Fetch document outerHTML from the selected Chrome WebSocket target."""
    ws = websocket.create_connection(websocket_url, suppress_origin=True)
    try:
        ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True,
            },
        }))
        while True:
            message = ws.recv()
            payload = json.loads(message)
            if payload.get("id") == 1:
                result = payload.get("result", {}).get("result", {})
                value = result.get("value")
                if isinstance(value, str):
                    return value
                return ""
    finally:
        ws.close()


def capture_html(url: str, output_path: str) -> str:
    """Capture current page HTML from Chrome and write it to output_path."""
    targets = _list_targets()
    target = _pick_target(targets, url)
    if "webSocketDebuggerUrl" not in target:
        raise RuntimeError("Chrome target did not expose a debugging websocket endpoint.")

    html = _read_current_page_html(target["webSocketDebuggerUrl"])
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    print(f"Saved {len(html)} characters to {destination}")
    return str(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture the current HTML from a Chrome tab and save it locally.")
    parser.add_argument("--url", default="https://www.thegradcafe.com/survey", help="URL to open or match in Chrome.")
    parser.add_argument("--output", default="gradcafe_page_1.html", help="File to save the captured HTML.")
    args = parser.parse_args()

    capture_html(args.url, args.output)
