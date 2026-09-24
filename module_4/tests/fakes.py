"""Test doubles for network, browser, and clock dependencies (no live internet in tests)."""

from __future__ import annotations

import json
from typing import Any


ALLOW_ALL_ROBOTS = "User-agent: *\nAllow: /\n"
DENY_SURVEY_ROBOTS = "User-agent: *\nDisallow: /survey\n"


class FakeResponse:
    """Minimal stand-in for the object returned by ``urllib.request.urlopen``."""

    def __init__(self, body: str | bytes) -> None:
        self.body = body.encode("utf-8") if isinstance(body, str) else body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False


def fake_urlopen(body: str | bytes | Any):
    """Return a ``urlopen`` replacement that always answers with ``body`` (JSON-encoded if not text)."""
    payload = body if isinstance(body, (str, bytes)) else json.dumps(body)

    def urlopen(request: Any, timeout: float | None = None, context: Any = None) -> FakeResponse:
        return FakeResponse(payload)

    return urlopen


class FakeWebSocket:
    """Replays queued DevTools messages; records what was sent."""

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = [json.dumps(message) for message in messages]
        self.sent: list[dict[str, Any]] = []
        self.closed = False

    def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    def recv(self) -> str:
        return self.messages.pop(0)

    def close(self) -> None:
        self.closed = True


class FakeClock:
    """Deterministic replacement for the ``time`` module: sleeps are recorded, the clock advances per read."""

    def __init__(self, step: float = 5.0) -> None:
        self.now = 0.0
        self.step = step
        self.slept: list[float] = []

    def monotonic(self) -> float:
        self.now += self.step
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
