"""
data/database.py — Async SQLite persistence layer via aiosqlite.

Tables:
  • tracked_wallets   — whale wallets we follow, with scores
  • wallet_snapshots  — position snapshots for diff-based trade detection
  • copy_trades        — every trade we've executed (or simulated in paper mode)
  • daily_pnl         — daily P&L rollups for the equity curve
  • market_cache       — cached Gamma API market metadata (5-min TTL)
  • system_events      — bot start/stop, errors, risk events
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from data.models import (
    CopyTrade,
    DailyPnL,
    MarketCache,
    SystemEvent,
    TrackedWallet,
    WalletSnapshot,
)
from utils.logger import get_logger

logger = get_logger(__name__)

_DB_PATH = "polymarket_bot.db"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class Database:
    """Async SQLite database.  Use as an async context manager or call open()/close()."""

    def __init__(self, path: str = _DB_PATH) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def open(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self.init_db()
        logger.info("database_opened", path=self._path)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("database_closed")

    async def __aenter__(self) -> "Database":
        await self.open()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    @property
    def _db(self) -> aiosqlite.Connection:
        assert self._conn is not None, "Database not opened — call open() or use async with"
        return self._conn

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    async def init_db(self) -> None:
        """Create all tables and indexes if they don't exist."""
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS tracked_wallets (
                address             TEXT PRIMARY KEY,
                alias               TEXT NOT NULL DEFAULT '',
                lifetime_pnl        REAL NOT NULL DEFAULT 0,
                win_rate            REAL NOT NULL DEFAULT 0,
                roi                 REAL NOT NULL DEFAULT 0,
                total_trades        INTEGER NOT NULL DEFAULT 0,
                score               REAL NOT NULL DEFAULT 0,
                is_active           INTEGER NOT NULL DEFAULT 1,
                last_scanned        TEXT NOT NULL,
                estimated_bankroll  REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS wallet_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address  TEXT NOT NULL,
                token_id        TEXT NOT NULL,
                market_slug     TEXT NOT NULL DEFAULT '',
                side            TEXT NOT NULL,
                size            REAL NOT NULL,
                avg_entry_price REAL NOT NULL DEFAULT 0,
                current_price   REAL NOT NULL DEFAULT 0,
                timestamp       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_wallet_ts
                ON wallet_snapshots (wallet_address, timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_snapshots_wallet_token
                ON wallet_snapshots (wallet_address, token_id);

            CREATE TABLE IF NOT EXISTS copy_trades (
                id              TEXT PRIMARY KEY,
                source_wallet   TEXT NOT NULL,
                market_slug     TEXT NOT NULL DEFAULT '',
                token_id        TEXT NOT NULL,
                side            TEXT NOT NULL,
                size            REAL NOT NULL,
                whale_size      REAL NOT NULL DEFAULT 0,
                entry_price     REAL NOT NULL DEFAULT 0,
                current_price   REAL NOT NULL DEFAULT 0,
                pnl             REAL NOT NULL DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'PENDING',
                created_at      TEXT NOT NULL,
                filled_at       TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_trades_status
                ON copy_trades (status);
            CREATE INDEX IF NOT EXISTS idx_trades_created
                ON copy_trades (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_trades_wallet
                ON copy_trades (source_wallet);

            CREATE TABLE IF NOT EXISTS daily_pnl (
                date            TEXT PRIMARY KEY,
                realized_pnl    REAL NOT NULL DEFAULT 0,
                unrealized_pnl  REAL NOT NULL DEFAULT 0,
                total_pnl       REAL NOT NULL DEFAULT 0,
                num_trades      INTEGER NOT NULL DEFAULT 0,
                win_rate        REAL NOT NULL DEFAULT 0,
                total_exposure  REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS market_cache (
                condition_id    TEXT PRIMARY KEY,
                slug            TEXT NOT NULL DEFAULT '',
                question        TEXT NOT NULL DEFAULT '',
                yes_token_id    TEXT NOT NULL DEFAULT '',
                no_token_id     TEXT NOT NULL DEFAULT '',
                volume          REAL NOT NULL DEFAULT 0,
                liquidity       REAL NOT NULL DEFAULT 0,
                yes_price       REAL NOT NULL DEFAULT 0,
                no_price        REAL NOT NULL DEFAULT 0,
                end_date        TEXT,
                cached_at       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_market_cache_slug
                ON market_cache (slug);

            CREATE TABLE IF NOT EXISTS system_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT NOT NULL,
                message     TEXT NOT NULL DEFAULT '',
                severity    TEXT NOT NULL DEFAULT 'INFO',
                created_at  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_created
                ON system_events (created_at DESC);
        """)
        await self._db.commit()

    # ------------------------------------------------------------------
    # tracked_wallets
    # ------------------------------------------------------------------

    async def upsert_wallet(self, wallet: TrackedWallet) -> None:
        await self._db.execute(
            """
            INSERT INTO tracked_wallets
                (address, alias, lifetime_pnl, win_rate, roi, total_trades,
                 score, is_active, last_scanned, estimated_bankroll)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                alias              = excluded.alias,
                lifetime_pnl       = excluded.lifetime_pnl,
                win_rate           = excluded.win_rate,
                roi                = excluded.roi,
                total_trades       = excluded.total_trades,
                score              = excluded.score,
                is_active          = excluded.is_active,
                last_scanned       = excluded.last_scanned,
                estimated_bankroll = excluded.estimated_bankroll
            """,
            (
                wallet.address,
                wallet.alias,
                wallet.lifetime_pnl,
                wallet.win_rate,
                wallet.roi,
                wallet.total_trades,
                wallet.score,
                int(wallet.is_active),
                wallet.last_scanned.isoformat(),
                wallet.estimated_bankroll,
            ),
        )
        await self._db.commit()

    async def get_wallet(self, address: str) -> TrackedWallet | None:
        async with self._db.execute(
            "SELECT * FROM tracked_wallets WHERE address = ?", (address,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        return self._row_to_wallet(row)

    async def get_active_wallets(self) -> list[TrackedWallet]:
        async with self._db.execute(
            "SELECT * FROM tracked_wallets WHERE is_active = 1 ORDER BY score DESC"
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_wallet(r) for r in rows]

    async def get_all_wallets(self) -> list[TrackedWallet]:
        async with self._db.execute(
            "SELECT * FROM tracked_wallets ORDER BY score DESC"
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_wallet(r) for r in rows]

    async def deactivate_wallet(self, address: str) -> None:
        await self._db.execute(
            "UPDATE tracked_wallets SET is_active = 0 WHERE address = ?", (address,)
        )
        await self._db.commit()

    @staticmethod
    def _row_to_wallet(row: aiosqlite.Row) -> TrackedWallet:
        return TrackedWallet(
            address=row["address"],
            alias=row["alias"],
            lifetime_pnl=row["lifetime_pnl"],
            win_rate=row["win_rate"],
            roi=row["roi"],
            total_trades=row["total_trades"],
            score=row["score"],
            is_active=bool(row["is_active"]),
            last_scanned=datetime.fromisoformat(row["last_scanned"]),
            estimated_bankroll=row["estimated_bankroll"],
        )

    # ------------------------------------------------------------------
    # wallet_snapshots
    # ------------------------------------------------------------------

    async def save_snapshot(self, snapshot: WalletSnapshot) -> None:
        await self._db.execute(
            """
            INSERT INTO wallet_snapshots
                (wallet_address, token_id, market_slug, side, size,
                 avg_entry_price, current_price, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.wallet_address,
                snapshot.token_id,
                snapshot.market_slug,
                snapshot.side,
                snapshot.size,
                snapshot.avg_entry_price,
                snapshot.current_price,
                snapshot.timestamp.isoformat(),
            ),
        )
        await self._db.commit()

    async def save_snapshots(self, snapshots: list[WalletSnapshot]) -> None:
        """Batch-insert a list of snapshots in a single transaction."""
        await self._db.executemany(
            """
            INSERT INTO wallet_snapshots
                (wallet_address, token_id, market_slug, side, size,
                 avg_entry_price, current_price, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    s.wallet_address,
                    s.token_id,
                    s.market_slug,
                    s.side,
                    s.size,
                    s.avg_entry_price,
                    s.current_price,
                    s.timestamp.isoformat(),
                )
                for s in snapshots
            ],
        )
        await self._db.commit()

    async def get_latest_snapshot(self, wallet_address: str) -> list[WalletSnapshot]:
        """
        Return the most recent snapshot batch for a wallet — all rows sharing
        the latest timestamp for that address.
        """
        async with self._db.execute(
            """
            SELECT * FROM wallet_snapshots
            WHERE wallet_address = ?
              AND timestamp = (
                  SELECT MAX(timestamp) FROM wallet_snapshots
                  WHERE wallet_address = ?
              )
            """,
            (wallet_address, wallet_address),
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    async def get_previous_snapshot(
        self, wallet_address: str, before_timestamp: str
    ) -> list[WalletSnapshot]:
        """Return the snapshot batch immediately preceding before_timestamp."""
        async with self._db.execute(
            """
            SELECT * FROM wallet_snapshots
            WHERE wallet_address = ?
              AND timestamp = (
                  SELECT MAX(timestamp) FROM wallet_snapshots
                  WHERE wallet_address = ? AND timestamp < ?
              )
            """,
            (wallet_address, wallet_address, before_timestamp),
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    @staticmethod
    def _row_to_snapshot(row: aiosqlite.Row) -> WalletSnapshot:
        return WalletSnapshot(
            wallet_address=row["wallet_address"],
            token_id=row["token_id"],
            market_slug=row["market_slug"],
            side=row["side"],
            size=row["size"],
            avg_entry_price=row["avg_entry_price"],
            current_price=row["current_price"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )

    # ------------------------------------------------------------------
    # copy_trades
    # ------------------------------------------------------------------

    async def save_trade(self, trade: CopyTrade) -> None:
        await self._db.execute(
            """
            INSERT INTO copy_trades
                (id, source_wallet, market_slug, token_id, side, size,
                 whale_size, entry_price, current_price, pnl, status,
                 created_at, filled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                current_price = excluded.current_price,
                pnl           = excluded.pnl,
                status        = excluded.status,
                filled_at     = excluded.filled_at
            """,
            (
                trade.id,
                trade.source_wallet,
                trade.market_slug,
                trade.token_id,
                trade.side,
                trade.size,
                trade.whale_size,
                trade.entry_price,
                trade.current_price,
                trade.pnl,
                trade.status,
                trade.created_at.isoformat(),
                trade.filled_at.isoformat() if trade.filled_at else None,
            ),
        )
        await self._db.commit()

    async def update_trade(
        self,
        trade_id: str,
        *,
        current_price: float | None = None,
        pnl: float | None = None,
        status: str | None = None,
        filled_at: datetime | None = None,
    ) -> None:
        """Partially update a copy trade record."""
        updates: list[str] = []
        params: list[Any] = []
        if current_price is not None:
            updates.append("current_price = ?")
            params.append(current_price)
        if pnl is not None:
            updates.append("pnl = ?")
            params.append(pnl)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if filled_at is not None:
            updates.append("filled_at = ?")
            params.append(filled_at.isoformat())
        if not updates:
            return
        params.append(trade_id)
        await self._db.execute(
            f"UPDATE copy_trades SET {', '.join(updates)} WHERE id = ?", params
        )
        await self._db.commit()

    async def get_trade(self, trade_id: str) -> CopyTrade | None:
        async with self._db.execute(
            "SELECT * FROM copy_trades WHERE id = ?", (trade_id,)
        ) as cur:
            row = await cur.fetchone()
        return self._row_to_trade(row) if row else None

    async def get_open_trades(self) -> list[CopyTrade]:
        async with self._db.execute(
            "SELECT * FROM copy_trades WHERE status IN ('PENDING','FILLED','PARTIAL') ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_trade(r) for r in rows]

    async def get_all_trades(
        self,
        limit: int = 500,
        offset: int = 0,
        status: str | None = None,
        source_wallet: str | None = None,
    ) -> list[CopyTrade]:
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if source_wallet:
            conditions.append("source_wallet = ?")
            params.append(source_wallet)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params += [limit, offset]
        async with self._db.execute(
            f"SELECT * FROM copy_trades {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_trade(r) for r in rows]

    @staticmethod
    def _row_to_trade(row: aiosqlite.Row) -> CopyTrade:
        return CopyTrade(
            id=row["id"],
            source_wallet=row["source_wallet"],
            market_slug=row["market_slug"],
            token_id=row["token_id"],
            side=row["side"],
            size=row["size"],
            whale_size=row["whale_size"],
            entry_price=row["entry_price"],
            current_price=row["current_price"],
            pnl=row["pnl"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            filled_at=_parse_dt(row["filled_at"]),
        )

    # ------------------------------------------------------------------
    # daily_pnl
    # ------------------------------------------------------------------

    async def upsert_daily_pnl(self, record: DailyPnL) -> None:
        await self._db.execute(
            """
            INSERT INTO daily_pnl
                (date, realized_pnl, unrealized_pnl, total_pnl,
                 num_trades, win_rate, total_exposure)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                realized_pnl   = excluded.realized_pnl,
                unrealized_pnl = excluded.unrealized_pnl,
                total_pnl      = excluded.total_pnl,
                num_trades     = excluded.num_trades,
                win_rate       = excluded.win_rate,
                total_exposure = excluded.total_exposure
            """,
            (
                record.date,
                record.realized_pnl,
                record.unrealized_pnl,
                record.total_pnl,
                record.num_trades,
                record.win_rate,
                record.total_exposure,
            ),
        )
        await self._db.commit()

    async def get_equity_curve(self, days: int = 90) -> list[DailyPnL]:
        """Return daily P&L records for the equity curve chart (most recent N days)."""
        async with self._db.execute(
            """
            SELECT * FROM daily_pnl
            ORDER BY date DESC
            LIMIT ?
            """,
            (days,),
        ) as cur:
            rows = await cur.fetchall()
        records = [self._row_to_daily_pnl(r) for r in rows]
        records.reverse()  # chronological order
        return records

    async def get_daily_pnl(self, date: str) -> DailyPnL | None:
        async with self._db.execute(
            "SELECT * FROM daily_pnl WHERE date = ?", (date,)
        ) as cur:
            row = await cur.fetchone()
        return self._row_to_daily_pnl(row) if row else None

    @staticmethod
    def _row_to_daily_pnl(row: aiosqlite.Row) -> DailyPnL:
        return DailyPnL(
            date=row["date"],
            realized_pnl=row["realized_pnl"],
            unrealized_pnl=row["unrealized_pnl"],
            total_pnl=row["total_pnl"],
            num_trades=row["num_trades"],
            win_rate=row["win_rate"],
            total_exposure=row["total_exposure"],
        )

    # ------------------------------------------------------------------
    # market_cache
    # ------------------------------------------------------------------

    async def upsert_market(self, market: MarketCache) -> None:
        await self._db.execute(
            """
            INSERT INTO market_cache
                (condition_id, slug, question, yes_token_id, no_token_id,
                 volume, liquidity, yes_price, no_price, end_date, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(condition_id) DO UPDATE SET
                slug         = excluded.slug,
                question     = excluded.question,
                yes_token_id = excluded.yes_token_id,
                no_token_id  = excluded.no_token_id,
                volume       = excluded.volume,
                liquidity    = excluded.liquidity,
                yes_price    = excluded.yes_price,
                no_price     = excluded.no_price,
                end_date     = excluded.end_date,
                cached_at    = excluded.cached_at
            """,
            (
                market.condition_id,
                market.slug,
                market.question,
                market.yes_token_id,
                market.no_token_id,
                market.volume,
                market.liquidity,
                market.yes_price,
                market.no_price,
                market.end_date,
                market.cached_at.isoformat(),
            ),
        )
        await self._db.commit()

    async def get_market_by_slug(self, slug: str) -> MarketCache | None:
        async with self._db.execute(
            "SELECT * FROM market_cache WHERE slug = ?", (slug,)
        ) as cur:
            row = await cur.fetchone()
        return self._row_to_market(row) if row else None

    async def get_market_by_token(self, token_id: str) -> MarketCache | None:
        async with self._db.execute(
            "SELECT * FROM market_cache WHERE yes_token_id = ? OR no_token_id = ?",
            (token_id, token_id),
        ) as cur:
            row = await cur.fetchone()
        return self._row_to_market(row) if row else None

    @staticmethod
    def _row_to_market(row: aiosqlite.Row) -> MarketCache:
        return MarketCache(
            condition_id=row["condition_id"],
            slug=row["slug"],
            question=row["question"],
            yes_token_id=row["yes_token_id"],
            no_token_id=row["no_token_id"],
            volume=row["volume"],
            liquidity=row["liquidity"],
            yes_price=row["yes_price"],
            no_price=row["no_price"],
            end_date=row["end_date"],
            cached_at=datetime.fromisoformat(row["cached_at"]),
        )

    # ------------------------------------------------------------------
    # system_events
    # ------------------------------------------------------------------

    async def log_event(self, event: SystemEvent) -> None:
        await self._db.execute(
            """
            INSERT INTO system_events (event_type, message, severity, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                event.event_type,
                event.message,
                event.severity,
                event.created_at.isoformat(),
            ),
        )
        await self._db.commit()

    async def get_recent_events(self, limit: int = 50) -> list[SystemEvent]:
        async with self._db.execute(
            "SELECT * FROM system_events ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
        return [self._row_to_event(r) for r in rows]

    @staticmethod
    def _row_to_event(row: aiosqlite.Row) -> SystemEvent:
        return SystemEvent(
            id=row["id"],
            event_type=row["event_type"],
            message=row["message"],
            severity=row["severity"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # ------------------------------------------------------------------
    # Aggregated queries (dashboard)
    # ------------------------------------------------------------------

    async def get_portfolio_summary(self) -> dict[str, Any]:
        """
        Return aggregated portfolio stats for the dashboard overview:
          - total_pnl: sum of realized P&L across all closed trades
          - today_pnl: total_pnl for today's date
          - win_rate: fraction of closed trades with pnl > 0
          - open_trades: number of currently open positions
          - total_exposure: sum of (size * current_price) for open trades
        """
        today = datetime.now(timezone.utc).date().isoformat()

        async with self._db.execute(
            """
            SELECT
                SUM(CASE WHEN status = 'CLOSED' THEN pnl ELSE 0 END) AS total_pnl,
                COUNT(CASE WHEN status IN ('FILLED','PARTIAL') THEN 1 END) AS open_trades,
                SUM(CASE WHEN status IN ('FILLED','PARTIAL') THEN size * current_price ELSE 0 END) AS total_exposure,
                COUNT(CASE WHEN status = 'CLOSED' AND pnl > 0 THEN 1 END) AS winning_trades,
                COUNT(CASE WHEN status = 'CLOSED' THEN 1 END) AS closed_trades
            FROM copy_trades
            """
        ) as cur:
            row = await cur.fetchone()

        total_pnl = row["total_pnl"] or 0.0
        open_trades = row["open_trades"] or 0
        total_exposure = row["total_exposure"] or 0.0
        winning_trades = row["winning_trades"] or 0
        closed_trades = row["closed_trades"] or 0
        win_rate = (winning_trades / closed_trades) if closed_trades > 0 else 0.0

        today_record = await self.get_daily_pnl(today)
        today_pnl = today_record.total_pnl if today_record else 0.0

        return {
            "total_pnl": total_pnl,
            "today_pnl": today_pnl,
            "win_rate": win_rate,
            "open_trades": open_trades,
            "total_exposure": total_exposure,
            "closed_trades": closed_trades,
        }
