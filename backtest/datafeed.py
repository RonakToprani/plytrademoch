"""
backtest/datafeed.py — Fetch and cache the historical data the edge test needs.

Two sources, both read-only and geo-unrestricted (no VPN, no API key):
  • Data API  /activity  — a wallet's trade-level history (BUY/SELL, price, size,
                           timestamp, market). This is what a copy bot would see.
  • Gamma API /markets   — market metadata incl. resolution outcome. Ground truth
                           for whether a position won or lost.

Everything is cached to a local SQLite (`backtest_cache.db`, gitignored) keyed by
wallet / condition_id so repeat runs are instant and we stay polite to the API.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

import httpx

DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
_CACHE_PATH = "backtest_cache.db"

# Data API returns at most this many activity rows per request.
_PAGE = 500
# Politeness delay between paged requests (seconds).
_THROTTLE = 0.15


@dataclass(frozen=True)
class Trade:
    """One TRADE event from a wallet's activity feed."""

    wallet: str
    ts: int                # unix seconds
    condition_id: str
    asset: str             # CLOB token id the wallet traded
    outcome_index: int     # 0 or 1
    side: str              # BUY / SELL
    price: float           # execution price (0-1)
    size: float            # shares
    usdc_size: float       # dollar notional
    slug: str
    title: str


@dataclass(frozen=True)
class Resolution:
    """
    Resolution status + outcome for a market (by condition_id).

    Ground truth comes from the CLOB ``/markets/{condition_id}`` endpoint, which
    flags the winning token directly. We store the winning *token id* rather than
    an outcome index so scoring compares the whale's traded ``asset`` to the
    winner without relying on YES/NO index ordering.
    """

    condition_id: str
    closed: bool
    winning_token_id: str | None   # token_id that settled to $1, else None
    end_date: str | None
    fetched_at: int


class DataFeed:
    """Cached accessor for whale activity and market resolutions."""

    def __init__(self, cache_path: str = _CACHE_PATH, resolution_ttl_days: int = 3) -> None:
        self._db = sqlite3.connect(cache_path)
        self._db.row_factory = sqlite3.Row
        # Unresolved markets may resolve later, so cache them with a TTL.
        self._resolution_ttl = resolution_ttl_days * 86_400
        self._http = httpx.Client(timeout=30.0)
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS activity (
                wallet        TEXT NOT NULL,
                ts            INTEGER NOT NULL,
                condition_id  TEXT NOT NULL,
                asset         TEXT NOT NULL,
                outcome_index INTEGER NOT NULL,
                side          TEXT NOT NULL,
                price         REAL NOT NULL,
                size          REAL NOT NULL,
                usdc_size     REAL NOT NULL,
                slug          TEXT NOT NULL DEFAULT '',
                title         TEXT NOT NULL DEFAULT '',
                tx_hash       TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (wallet, tx_hash, asset, side, ts)
            );
            CREATE INDEX IF NOT EXISTS idx_activity_wallet ON activity(wallet, ts);

            CREATE TABLE IF NOT EXISTS activity_fetch (
                wallet     TEXT PRIMARY KEY,
                rows       INTEGER NOT NULL,
                fetched_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resolution (
                condition_id     TEXT PRIMARY KEY,
                closed           INTEGER NOT NULL,
                winning_token_id TEXT,
                end_date         TEXT,
                fetched_at       INTEGER NOT NULL
            );
            """
        )
        self._db.commit()

    # ------------------------------------------------------------------
    # Activity
    # ------------------------------------------------------------------

    def fetch_activity(
        self,
        wallet: str,
        max_rows: int = 5_000,
        refresh: bool = False,
    ) -> list[Trade]:
        """
        Return a wallet's TRADE history (newest first), paging the Data API up to
        *max_rows*. Cached; pass refresh=True to force a re-fetch.
        """
        wallet = wallet.lower()
        if not refresh and self._has_activity(wallet):
            return self._load_activity(wallet)

        rows: list[dict[str, Any]] = []
        for offset in range(0, max_rows, _PAGE):
            page = self._get(
                f"{DATA_API}/activity",
                {"user": wallet, "limit": _PAGE, "offset": offset},
            )
            if not page:
                break
            rows.extend(page)
            if len(page) < _PAGE:
                break
            time.sleep(_THROTTLE)

        trades = [self._row_to_trade(wallet, r) for r in rows if r.get("type") == "TRADE"]
        self._store_activity(wallet, trades)
        return trades

    def _has_activity(self, wallet: str) -> bool:
        cur = self._db.execute(
            "SELECT rows FROM activity_fetch WHERE wallet = ?", (wallet,)
        )
        row = cur.fetchone()
        return row is not None and row["rows"] > 0

    def _load_activity(self, wallet: str) -> list[Trade]:
        cur = self._db.execute(
            "SELECT * FROM activity WHERE wallet = ? ORDER BY ts DESC", (wallet,)
        )
        return [
            Trade(
                wallet=r["wallet"], ts=r["ts"], condition_id=r["condition_id"],
                asset=r["asset"], outcome_index=r["outcome_index"], side=r["side"],
                price=r["price"], size=r["size"], usdc_size=r["usdc_size"],
                slug=r["slug"], title=r["title"],
            )
            for r in cur.fetchall()
        ]

    def _store_activity(self, wallet: str, trades: list[Trade]) -> None:
        self._db.executemany(
            """
            INSERT OR IGNORE INTO activity
              (wallet, ts, condition_id, asset, outcome_index, side, price, size,
               usdc_size, slug, title, tx_hash)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (t.wallet, t.ts, t.condition_id, t.asset, t.outcome_index, t.side,
                 t.price, t.size, t.usdc_size, t.slug, t.title, "")
                for t in trades
            ],
        )
        self._db.execute(
            "INSERT OR REPLACE INTO activity_fetch (wallet, rows, fetched_at) VALUES (?,?,?)",
            (wallet, len(trades), int(time.time())),
        )
        self._db.commit()

    @staticmethod
    def _row_to_trade(wallet: str, r: dict[str, Any]) -> Trade:
        return Trade(
            wallet=wallet,
            ts=int(r.get("timestamp", 0)),
            condition_id=r.get("conditionId", ""),
            asset=str(r.get("asset", "")),
            outcome_index=int(r.get("outcomeIndex", 0)),
            side=str(r.get("side", "")).upper(),
            price=float(r.get("price", 0) or 0),
            size=float(r.get("size", 0) or 0),
            usdc_size=float(r.get("usdcSize", 0) or 0),
            slug=r.get("slug", "") or "",
            title=r.get("title", "") or "",
        )

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def get_resolution(self, condition_id: str, refresh: bool = False) -> Resolution | None:
        """Return resolution status for a market, cached with a TTL for open ones."""
        if not condition_id:
            return None
        now = int(time.time())
        if not refresh:
            cur = self._db.execute(
                "SELECT * FROM resolution WHERE condition_id = ?", (condition_id,)
            )
            row = cur.fetchone()
            if row is not None:
                # Resolved markets never change; re-fetch open ones after TTL.
                if row["closed"] or (now - row["fetched_at"] < self._resolution_ttl):
                    return Resolution(
                        condition_id=condition_id,
                        closed=bool(row["closed"]),
                        winning_token_id=row["winning_token_id"],
                        end_date=row["end_date"],
                        fetched_at=row["fetched_at"],
                    )

        # CLOB /markets/{condition_id} is the authoritative resolution source:
        # each token carries a `winner` flag. (Gamma's condition_id filter is
        # unreliable — it silently returns unrelated markets.)
        mk = self._get(f"{CLOB_API}/markets/{condition_id}", None)
        if not mk or not isinstance(mk, dict):
            return None
        res = self._parse_resolution(condition_id, mk, now)
        self._db.execute(
            """INSERT OR REPLACE INTO resolution
               (condition_id, closed, winning_token_id, end_date, fetched_at)
               VALUES (?,?,?,?,?)""",
            (res.condition_id, int(res.closed), res.winning_token_id, res.end_date, res.fetched_at),
        )
        self._db.commit()
        return res

    @staticmethod
    def _parse_resolution(condition_id: str, mk: dict[str, Any], now: int) -> Resolution:
        closed = bool(mk.get("closed", False))
        winning_token_id: str | None = None
        for tok in mk.get("tokens", []) or []:
            if tok.get("winner"):
                winning_token_id = str(tok.get("token_id", "")) or None
                break
        return Resolution(
            condition_id=condition_id,
            closed=closed,
            winning_token_id=winning_token_id,
            end_date=mk.get("end_date_iso"),
            fetched_at=now,
        )

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict[str, Any]) -> Any:
        for attempt in range(3):
            try:
                resp = self._http.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    time.sleep(1.0 + attempt)
                    continue
                raise
            except httpx.RequestError:
                time.sleep(0.5 + attempt)
        return None

    def close(self) -> None:
        self._http.close()
        self._db.close()

    def __enter__(self) -> "DataFeed":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
