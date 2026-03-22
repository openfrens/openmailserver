"""Anonymous, opt-out usage telemetry for openmailserver.

Sends lightweight events to PostHog's HTTP API using only stdlib (no SDK).
All events are anonymous (random machine UUID, no PII). Telemetry never
blocks the CLI or API, and all network errors are silently swallowed.

Opt out by setting any of:
  - OPENMAILSERVER_TELEMETRY=false  (or 0 / no / off)
  - DO_NOT_TRACK=1                  (cross-tool standard)
  - CI=true                         (auto-detected in CI environments)
  - openmailserver telemetry --disable
"""

from __future__ import annotations

import json
import os
import platform
import threading
import time
import urllib.request
import uuid
from pathlib import Path

from openmailserver import __version__

POSTHOG_HOST = "https://us.i.posthog.com"
POSTHOG_API_KEY = "phc_PLACEHOLDER"

_TELEMETRY_DIR = Path.home() / ".openmailserver"
_ID_FILE = _TELEMETRY_DIR / "telemetry_id"
_DISABLED_FILE = _TELEMETRY_DIR / "telemetry_disabled"

_CI_ENV_VARS = ("CI", "GITHUB_ACTIONS", "CIRCLECI", "TRAVIS", "GITLAB_CI", "BUILDKITE")


def _is_disabled() -> bool:
    if os.getenv("OPENMAILSERVER_TELEMETRY", "").lower() in ("false", "0", "no", "off"):
        return True
    if os.getenv("DO_NOT_TRACK", "") == "1":
        return True
    if any(os.getenv(v, "").lower() in ("true", "1") for v in _CI_ENV_VARS):
        return True
    try:
        if _DISABLED_FILE.exists():
            return True
    except OSError:
        pass
    return False


def _get_machine_id() -> str:
    try:
        if _ID_FILE.exists():
            return _ID_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    mid = str(uuid.uuid4())
    try:
        _TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        _ID_FILE.write_text(mid, encoding="utf-8")
    except OSError:
        pass
    return mid


def set_enabled(enabled: bool) -> None:
    """Persist the user's opt-in/opt-out choice to disk."""
    try:
        _TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        if enabled:
            _DISABLED_FILE.unlink(missing_ok=True)
        else:
            _DISABLED_FILE.write_text("1", encoding="utf-8")
    except OSError:
        pass


def track(event: str, properties: dict | None = None) -> None:
    """Fire-and-forget: send a single event in a background daemon thread."""
    if _is_disabled():
        return

    def _send() -> None:
        try:
            payload = json.dumps(
                {
                    "api_key": POSTHOG_API_KEY,
                    "event": event,
                    "distinct_id": _get_machine_id(),
                    "properties": {
                        "version": __version__,
                        "os": platform.system(),
                        "os_version": platform.release(),
                        "python": platform.python_version(),
                        **(properties or {}),
                    },
                }
            ).encode()
            req = urllib.request.Request(
                f"{POSTHOG_HOST}/capture/",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=2)  # noqa: S310
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


def start_heartbeat(interval_seconds: int = 86400) -> None:
    """Start a background daemon thread that sends a heartbeat event periodically."""
    if _is_disabled():
        return

    def _loop() -> None:
        start = time.monotonic()
        while True:
            time.sleep(interval_seconds)
            track(
                "server_heartbeat",
                {"uptime_hours": round((time.monotonic() - start) / 3600, 1)},
            )

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
