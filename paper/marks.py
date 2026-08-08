"""
paper/marks.py — mark open positions to the live CLOB bid.

Shared by the dashboard and the Telegram `pnl` command so both report the same
unrealized number. Best bid ("SELL" side = what the position could be exited
at) per token, one batched CLOB call, TTL-cached. Returns {} on any failure —
marks are a display nicety, never a reason for a page or a reply to error out.
"""

from __future__ import annotations

import time

import httpx

_CLOB = "https://clob.polymarket.com"
_MARK_TTL = 25.0
_mark_cache: dict[str, object] = {"ts": 0.0, "px": {}}


def marks(token_ids: list[str]) -> dict[str, float]:
    if not token_ids:
        return {}
    now = time.monotonic()
    cached = _mark_cache["px"]
    if isinstance(cached, dict) and now - float(_mark_cache["ts"]) < _MARK_TTL \
            and all(t in cached for t in token_ids):
        return cached  # type: ignore[return-value]
    try:
        r = httpx.post(f"{_CLOB}/prices",
                       json=[{"token_id": t, "side": "SELL"} for t in token_ids],
                       timeout=8.0)
        r.raise_for_status()
        px = {}
        for tok, sides in (r.json() or {}).items():
            try:
                px[tok] = float(sides["SELL"])
            except (KeyError, TypeError, ValueError):
                continue
    except (httpx.HTTPError, ValueError):
        return cached if isinstance(cached, dict) else {}  # type: ignore[return-value]
    _mark_cache["ts"], _mark_cache["px"] = now, px
    return px
