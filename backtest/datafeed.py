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
class ResolvedMarket:
    """A resolved market from the Gamma closed-markets universe."""

    condition_id: str
    winning_token_id: str | None   # clobTokenIds[argmax(outcomePrices)]
    sample_token: str              # clobTokenIds[0] — the token we price & score
    volume: float
    end_date: str | None
    slug: str


@dataclass(frozen=True)
class PricePrint:
    """A neutral BUY-taker fill: this token was bought at this price."""

    asset: str
    price: float
    size: float


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

            CREATE TABLE IF NOT EXISTS resolved_market (
                condition_id     TEXT PRIMARY KEY,
                winning_token_id TEXT,
                sample_token     TEXT NOT NULL DEFAULT '',
                volume           REAL NOT NULL DEFAULT 0,
                end_date         TEXT,
                slug             TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS price_history (
                token_id TEXT NOT NULL,
                ts       INTEGER NOT NULL,
                price    REAL NOT NULL,
                PRIMARY KEY (token_id, ts)
            );

            CREATE TABLE IF NOT EXISTS price_history_fetch (
                token_id   TEXT PRIMARY KEY,
                points     INTEGER NOT NULL,
                fetched_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_trades (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                condition_id TEXT NOT NULL,
                asset        TEXT NOT NULL,
                price        REAL NOT NULL,
                size         REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mtrades_cond ON market_trades(condition_id);

            CREATE TABLE IF NOT EXISTS market_trades_fetch (
                condition_id TEXT PRIMARY KEY,
                rows         INTEGER NOT NULL,
                fetched_at   INTEGER NOT NULL
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
    # Resolved-market universe (Gamma closed markets) — neutral, not whale-picked
    # ------------------------------------------------------------------

    def fetch_resolved_universe(
        self,
        max_markets: int = 1_000,
        min_volume: float = 5_000.0,
        refresh: bool = False,
    ) -> list[ResolvedMarket]:
        """
        Return a broad set of resolved binary markets from the Gamma closed-markets
        listing (most recently ended first), filtered to those with real volume.

        The listing carries clobTokenIds + outcomePrices directly, so resolution
        comes free — no per-market lookup. Cached; pass refresh=True to re-pull.
        """
        if not refresh and self._universe_size() >= max_markets:
            return self._load_universe(max_markets)

        out: list[ResolvedMarket] = []
        offset = 0
        # Order by volume desc so the universe is the most *liquid* resolved
        # markets (real elections/sports/crypto), not recent auto-generated junk.
        # Gamma caps this listing at offset ~2000, so we stop there gracefully.
        while len(out) < max_markets:
            try:
                page = self._get(
                    f"{GAMMA_API}/markets",
                    {"closed": "true", "limit": 100, "offset": offset,
                     "order": "volumeNum", "ascending": "false"},
                )
            except httpx.HTTPStatusError:
                break  # hit the offset ceiling
            if not page:
                break
            for mk in page:
                rm = self._parse_resolved_market(mk, min_volume)
                if rm is not None:
                    out.append(rm)
            offset += 100
            if len(page) < 100:
                break
            time.sleep(_THROTTLE)

        self._store_universe(out)
        return out[:max_markets]

    @staticmethod
    def _parse_resolved_market(mk: dict[str, Any], min_volume: float) -> "ResolvedMarket | None":
        try:
            volume = float(mk.get("volume", 0) or 0)
        except (ValueError, TypeError):
            volume = 0.0
        if volume < min_volume:
            return None
        raw_tokens = mk.get("clobTokenIds")
        raw_prices = mk.get("outcomePrices")
        tokens = json.loads(raw_tokens) if isinstance(raw_tokens, str) else (raw_tokens or [])
        prices = json.loads(raw_prices) if isinstance(raw_prices, str) else (raw_prices or [])
        if len(tokens) != 2 or len(prices) != 2:
            return None  # only binary markets
        try:
            fp = [float(p) for p in prices]
        except (ValueError, TypeError):
            return None
        if max(fp) < 0.99:
            return None  # not cleanly resolved
        win_token = str(tokens[fp.index(max(fp))])
        return ResolvedMarket(
            condition_id=mk.get("conditionId", ""),
            winning_token_id=win_token,
            sample_token=str(tokens[0]),
            volume=volume,
            end_date=mk.get("endDate"),
            slug=mk.get("slug", "") or "",
        )

    def _universe_size(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM resolved_market").fetchone()[0]

    def _load_universe(self, limit: int) -> list[ResolvedMarket]:
        cur = self._db.execute(
            "SELECT * FROM resolved_market ORDER BY end_date DESC LIMIT ?", (limit,)
        )
        return [
            ResolvedMarket(r["condition_id"], r["winning_token_id"], r["sample_token"],
                           r["volume"], r["end_date"], r["slug"])
            for r in cur.fetchall()
        ]

    def _store_universe(self, markets: list[ResolvedMarket]) -> None:
        self._db.executemany(
            """INSERT OR REPLACE INTO resolved_market
               (condition_id, winning_token_id, sample_token, volume, end_date, slug)
               VALUES (?,?,?,?,?,?)""",
            [(m.condition_id, m.winning_token_id, m.sample_token, m.volume,
              m.end_date, m.slug) for m in markets],
        )
        self._db.commit()

    # ------------------------------------------------------------------
    # Price history (CLOB /prices-history) — for ex-ante horizon pricing
    # ------------------------------------------------------------------

    def fetch_price_history(
        self, token_id: str, fidelity: int = 1440, refresh: bool = False
    ) -> list[tuple[int, float]]:
        """
        Return a token's full price time-series as [(unix_ts, price), ...] ascending.
        `fidelity` is the bar width in minutes (60 = hourly). Cached per token.
        """
        if not token_id:
            return []
        if not refresh and self._has_price_history(token_id):
            return self._load_price_history(token_id)

        data = self._get(
            f"{CLOB_API}/prices-history",
            {"market": token_id, "interval": "max", "fidelity": fidelity},
        )
        hist = data.get("history", []) if isinstance(data, dict) else (data or [])
        points = sorted(
            (int(p["t"]), float(p["p"]))
            for p in hist if "t" in p and "p" in p
        )
        self._store_price_history(token_id, points)
        return points

    def _has_price_history(self, token_id: str) -> bool:
        return self._db.execute(
            "SELECT 1 FROM price_history_fetch WHERE token_id = ?", (token_id,)
        ).fetchone() is not None

    def _load_price_history(self, token_id: str) -> list[tuple[int, float]]:
        cur = self._db.execute(
            "SELECT ts, price FROM price_history WHERE token_id = ? ORDER BY ts", (token_id,)
        )
        return [(r["ts"], r["price"]) for r in cur.fetchall()]

    def _store_price_history(self, token_id: str, points: list[tuple[int, float]]) -> None:
        self._db.executemany(
            "INSERT OR IGNORE INTO price_history (token_id, ts, price) VALUES (?,?,?)",
            [(token_id, ts, px) for ts, px in points],
        )
        self._db.execute(
            "INSERT OR REPLACE INTO price_history_fetch (token_id, points, fetched_at) VALUES (?,?,?)",
            (token_id, len(points), int(time.time())),
        )
        self._db.commit()

    # ------------------------------------------------------------------
    # Neutral market trade prints (all counterparties)
    # ------------------------------------------------------------------

    def fetch_market_trades(
        self,
        condition_id: str,
        max_rows: int = 500,
        refresh: bool = False,
    ) -> list[PricePrint]:
        """
        Return neutral BUY-taker fills on a market (all traders) via /trades.
        Each print says: this token was bought at this price. Cached per market.
        """
        if not refresh and self._has_market_trades(condition_id):
            return self._load_market_trades(condition_id)

        rows: list[dict[str, Any]] = []
        for offset in range(0, max_rows, _PAGE):
            page = self._get(
                f"{DATA_API}/trades",
                {"market": condition_id, "limit": _PAGE, "offset": offset},
            )
            if not page:
                break
            rows.extend(page)
            if len(page) < _PAGE:
                break
            time.sleep(_THROTTLE)

        prints = [
            PricePrint(asset=str(r.get("asset", "")),
                       price=float(r.get("price", 0) or 0),
                       size=float(r.get("size", 0) or 0))
            for r in rows
            if str(r.get("side", "")).upper() == "BUY" and r.get("asset")
            and 0.0 < float(r.get("price", 0) or 0) < 1.0
        ]
        self._store_market_trades(condition_id, prints)
        return prints

    def _has_market_trades(self, condition_id: str) -> bool:
        row = self._db.execute(
            "SELECT rows FROM market_trades_fetch WHERE condition_id = ?", (condition_id,)
        ).fetchone()
        return row is not None

    def _load_market_trades(self, condition_id: str) -> list[PricePrint]:
        cur = self._db.execute(
            "SELECT asset, price, size FROM market_trades WHERE condition_id = ?", (condition_id,)
        )
        return [PricePrint(r["asset"], r["price"], r["size"]) for r in cur.fetchall()]

    def _store_market_trades(self, condition_id: str, prints: list[PricePrint]) -> None:
        # Delete-then-insert keeps re-fetches idempotent without a dedup key.
        self._db.execute("DELETE FROM market_trades WHERE condition_id = ?", (condition_id,))
        self._db.executemany(
            """INSERT INTO market_trades (condition_id, asset, price, size) VALUES (?,?,?,?)""",
            [(condition_id, p.asset, p.price, p.size) for p in prints],
        )
        self._db.execute(
            "INSERT OR REPLACE INTO market_trades_fetch (condition_id, rows, fetched_at) VALUES (?,?,?)",
            (condition_id, len(prints), int(time.time())),
        )
        self._db.commit()

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
