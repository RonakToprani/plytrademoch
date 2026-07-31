"""
backtest/universe.py — deep resolved-market universe via Gamma keyset pagination.

`DataFeed.fetch_resolved_universe` is capped at ~2000 markets: Gamma rejects
offset > ~2000 on /markets ("offset too large, use /markets/keyset"). That ceiling
is why the calibration universe stalled at 2107 markets, which left every
per-segment sample too small to act on.

/markets/keyset walks the full history with an opaque cursor and no depth limit.
It also carries two fields the offset listing needed extra lookups for:
  • events[0].slug  — the real event key, for correlated-leg clustering
  • category        — Polymarket's own taxonomy, better than slug regex

Writes to its own table (resolved_deep) so the live trading path, which reads
resolved_market every 30 minutes, is untouched.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass

import httpx

GAMMA = "https://gamma-api.polymarket.com"
_THROTTLE = 0.12
_DB = "backtest_cache.db"


@dataclass(frozen=True)
class DeepMarket:
    condition_id: str
    winning_token_id: str
    token0: str
    token1: str
    volume: float
    end_date: str
    slug: str
    event: str
    category: str


def _schema(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS resolved_deep (
               condition_id     TEXT PRIMARY KEY,
               winning_token_id TEXT NOT NULL,
               token0           TEXT NOT NULL,
               token1           TEXT NOT NULL,
               volume           REAL NOT NULL,
               end_date         TEXT,
               slug             TEXT NOT NULL DEFAULT '',
               event            TEXT NOT NULL DEFAULT '',
               category         TEXT NOT NULL DEFAULT ''
           )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_deep_event ON resolved_deep(event)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_deep_end ON resolved_deep(end_date)")
    db.execute(
        """CREATE TABLE IF NOT EXISTS horizon_price (
               token_id  TEXT NOT NULL,
               horizon_h INTEGER NOT NULL,
               price     REAL,
               PRIMARY KEY (token_id, horizon_h)
           )"""
    )
    db.commit()


def _event_key(mk: dict) -> str:
    neg = mk.get("negRiskMarketID")
    if neg:
        return f"neg:{neg}"
    ev = mk.get("events") or []
    if ev and isinstance(ev[0], dict) and ev[0].get("slug"):
        return f"ev:{ev[0]['slug']}"
    return f"mk:{mk.get('slug', '') or ''}"


def _parse(mk: dict, min_volume: float) -> DeepMarket | None:
    """Binary, cleanly-resolved, liquid enough. Mirrors _parse_resolved_market."""
    try:
        volume = float(mk.get("volumeNum") or mk.get("volume") or 0)
    except (TypeError, ValueError):
        return None
    if volume < min_volume:
        return None
    raw_t, raw_p = mk.get("clobTokenIds"), mk.get("outcomePrices")
    try:
        tokens = json.loads(raw_t) if isinstance(raw_t, str) else (raw_t or [])
        prices = [float(p) for p in
                  (json.loads(raw_p) if isinstance(raw_p, str) else (raw_p or []))]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if len(tokens) != 2 or len(prices) != 2:
        return None                      # binary only
    if max(prices) < 0.99:
        return None                      # not cleanly resolved (void/ambiguous)
    return DeepMarket(
        condition_id=mk.get("conditionId", "") or "",
        winning_token_id=str(tokens[prices.index(max(prices))]),
        token0=str(tokens[0]), token1=str(tokens[1]),
        volume=volume, end_date=mk.get("endDate") or "",
        slug=mk.get("slug", "") or "", event=_event_key(mk),
        category=(mk.get("category") or "").strip(),
    )


def build(min_volume: float = 10_000.0, max_pages: int = 100_000,
          db_path: str = _DB, progress_every: int = 25) -> int:
    """Walk every closed market via keyset; upsert those that qualify."""
    db = sqlite3.connect(db_path)
    _schema(db)
    cursor, pages, kept, seen = None, 0, 0, 0
    with httpx.Client(timeout=40.0) as client:
        while pages < max_pages:
            # volume_num_min filters server-side, so we never page through the
            # long tail of near-zero-volume auto-generated markets.
            params = {"closed": "true", "limit": 100,
                      "volume_num_min": str(min_volume),
                      "order": "endDate", "ascending": "false"}
            if cursor:
                params["after_cursor"] = cursor   # NOT "cursor" — silently no-ops
            try:
                r = client.get(f"{GAMMA}/markets/keyset", params=params)
                r.raise_for_status()
                payload = r.json()
            except (httpx.HTTPError, ValueError) as exc:
                print(f"  stop: {type(exc).__name__} {exc}", flush=True)
                break
            rows = payload.get("markets") or []
            if not rows:
                break
            seen += len(rows)
            batch = [_parse(mk, min_volume) for mk in rows]
            batch = [m for m in batch if m is not None]
            if batch:
                db.executemany(
                    """INSERT OR REPLACE INTO resolved_deep
                       (condition_id, winning_token_id, token0, token1, volume,
                        end_date, slug, event, category)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    [(m.condition_id, m.winning_token_id, m.token0, m.token1,
                      m.volume, m.end_date, m.slug, m.event, m.category)
                     for m in batch])
                db.commit()
                kept += len(batch)
            pages += 1
            if pages % progress_every == 0:
                print(f"  page {pages}: seen {seen}, kept {kept}", flush=True)
            cursor = payload.get("next_cursor")
            if not cursor:
                break
            time.sleep(_THROTTLE)
    total = db.execute("SELECT COUNT(*) FROM resolved_deep").fetchone()[0]
    print(f"done: scanned {seen} closed markets, {kept} qualified, "
          f"{total} unique in resolved_deep", flush=True)
    db.close()
    return total


if __name__ == "__main__":
    import sys
    mv = float(sys.argv[1]) if len(sys.argv) > 1 else 10_000.0
    build(min_volume=mv)
