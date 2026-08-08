"""
paper/snapshot.py — PNG screenshot of the live dashboard.

Used by the Telegram `pnl`/`detail` command so the reply is the real POLY
TRADING page, not a text approximation of it. Headless Chromium via Playwright,
pointed at the dashboard the launchd job already serves on :8060.

Everything here is best-effort: if Playwright isn't installed, the dashboard
isn't up, or the render times out, `capture()` returns None and the caller
falls back to the text card. A screenshot is a nicety; the numbers are not.
"""

from __future__ import annotations

import os

from utils.logger import get_logger

logger = get_logger(__name__)

DASHBOARD_URL = os.environ.get("POLY_DASHBOARD_URL", "http://127.0.0.1:8060")
_VIEWPORT = {"width": 1200, "height": 1400}


def capture(path: str, url: str = DASHBOARD_URL, timeout_ms: int = 25_000) -> str | None:
    """Screenshot the dashboard to `path`. Returns the path, or None on failure."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.info("snapshot_unavailable", reason="playwright not installed")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            try:
                page = browser.new_page(viewport=_VIEWPORT, device_scale_factor=2,
                                        color_scheme="dark")
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                # Dash paints the shell first and fills #content from a callback,
                # so waiting on load alone screenshots an empty page.
                page.wait_for_function(
                    "document.querySelector('#content')?.children.length > 0",
                    timeout=timeout_ms)
                page.wait_for_timeout(600)          # let fonts/CSS settle
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                page.screenshot(path=path, full_page=True)
            finally:
                browser.close()
    except Exception as exc:                        # noqa: BLE001 - never fatal
        logger.warning("snapshot_failed", error=str(exc))
        return None
    return path
