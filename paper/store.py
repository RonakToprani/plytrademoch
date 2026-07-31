"""
paper/store.py — SQLite persistence for paper (simulated) underdog bets.

One clean table. A partial unique index enforces "at most one OPEN bet per
market", so re-scanning never double-books the same market.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_DB_PATH = "paper_underdog.db"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Bet:
    id: int | None
    condition_id: str
    token_id: str
    slug: str
    question: str
    outcome: str
    entry_price: float
    stake_usd: float
    shares: float
    opened_at: str
    resolves_at: str | None
    event: str = ""                # real-world event key, for correlated-leg dedupe
    status: str = "OPEN"           # OPEN / WON / LOST / VOID
    settle_price: float | None = None
    pnl: float | None = None
    settled_at: str | None = None


class PaperStore:
    def __init__(self, path: str = _DB_PATH) -> None:
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS bets (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                condition_id  TEXT NOT NULL,
                token_id      TEXT NOT NULL,
                slug          TEXT NOT NULL DEFAULT '',
                question      TEXT NOT NULL DEFAULT '',
                outcome       TEXT NOT NULL DEFAULT '',
                entry_price   REAL NOT NULL,
                stake_usd     REAL NOT NULL,
                shares        REAL NOT NULL,
                opened_at     TEXT NOT NULL,
                resolves_at   TEXT,
                status        TEXT NOT NULL DEFAULT 'OPEN',
                settle_price  REAL,
                pnl           REAL,
                settled_at    TEXT,
                event         TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_bets_status ON bets(status);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bets_open_condition
                ON bets(condition_id) WHERE status = 'OPEN';

            CREATE TABLE IF NOT EXISTS scans (
                ts            TEXT NOT NULL,
                opportunities INTEGER NOT NULL,
                recorded      INTEGER NOT NULL
            );
            """
        )
        # Migrate DBs created before the event column existed. Must run before the
        # event index is created, hence not inside the CREATE TABLE script above.
        cols = {r["name"] for r in self._db.execute("PRAGMA table_info(bets)")}
        if "event" not in cols:
            self._db.execute("ALTER TABLE bets ADD COLUMN event TEXT NOT NULL DEFAULT ''")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_bets_open_event "
                         "ON bets(event) WHERE status = 'OPEN'")
        self._db.commit()

    # ------------------------------------------------------------------

    def record_bet(self, bet: Bet) -> int | None:
        """Insert a new OPEN bet. Returns row id, or None if one already exists
        for this market (partial-unique-index violation)."""
        try:
            cur = self._db.execute(
                """INSERT INTO bets
                   (condition_id, token_id, slug, question, outcome, entry_price,
                    stake_usd, shares, opened_at, resolves_at, event, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?, 'OPEN')""",
                (bet.condition_id, bet.token_id, bet.slug, bet.question, bet.outcome,
                 bet.entry_price, bet.stake_usd, bet.shares, bet.opened_at,
                 bet.resolves_at, bet.event),
            )
            self._db.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None  # already hold an open bet on this market

    def settle_bet(self, bet_id: int, status: str, settle_price: float, pnl: float) -> None:
        self._db.execute(
            "UPDATE bets SET status=?, settle_price=?, pnl=?, settled_at=? WHERE id=?",
            (status, settle_price, pnl, _utcnow(), bet_id),
        )
        self._db.commit()

    def open_bets(self) -> list[Bet]:
        return [self._row(r) for r in
                self._db.execute("SELECT * FROM bets WHERE status='OPEN' ORDER BY opened_at")]

    def all_bets(self, limit: int = 1000) -> list[Bet]:
        return [self._row(r) for r in self._db.execute(
            "SELECT * FROM bets ORDER BY opened_at DESC LIMIT ?", (limit,))]

    def has_open(self, condition_id: str) -> bool:
        return self._db.execute(
            "SELECT 1 FROM bets WHERE condition_id=? AND status='OPEN'", (condition_id,)
        ).fetchone() is not None

    def has_open_event(self, event: str) -> bool:
        """
        Already exposed to this real-world event? The scanner only dedupes within a
        single scan, so without this check each 30-min cycle adds another leg of the
        same event — which is how the book reached 8 Iran legs and 6 Elon buckets
        while Kelly sizing still assumed 38 independent positions.
        """
        if not event:
            return False
        return self._db.execute(
            "SELECT 1 FROM bets WHERE event=? AND status='OPEN'", (event,)
        ).fetchone() is not None

    def open_stake_on(self, resolve_date: str) -> float:
        """Total open stake resolving on a given YYYY-MM-DD (expiry concentration)."""
        row = self._db.execute(
            "SELECT COALESCE(SUM(stake_usd),0) s FROM bets "
            "WHERE status='OPEN' AND SUBSTR(resolves_at,1,10)=?", (resolve_date,)
        ).fetchone()
        return float(row["s"] or 0.0)

    def log_scan(self, opportunities: int, recorded: int) -> None:
        self._db.execute("INSERT INTO scans (ts, opportunities, recorded) VALUES (?,?,?)",
                         (_utcnow(), opportunities, recorded))
        self._db.commit()

    def last_scan(self) -> str | None:
        row = self._db.execute("SELECT ts FROM scans ORDER BY ts DESC LIMIT 1").fetchone()
        return row["ts"] if row else None

    def stats(self) -> dict[str, Any]:
        row = self._db.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(status='OPEN') AS open,
              SUM(status IN ('WON','LOST','VOID')) AS settled,
              SUM(status='WON') AS won,
              SUM(status='LOST') AS lost,
              SUM(CASE WHEN status='OPEN' THEN stake_usd ELSE 0 END) AS open_stake,
              SUM(CASE WHEN status IN ('WON','LOST','VOID') THEN stake_usd ELSE 0 END) AS settled_stake,
              SUM(CASE WHEN status IN ('WON','LOST','VOID') THEN pnl ELSE 0 END) AS realized_pnl
            FROM bets
            """
        ).fetchone()
        settled = row["settled"] or 0
        won = row["won"] or 0
        decided = (row["won"] or 0) + (row["lost"] or 0)
        settled_stake = row["settled_stake"] or 0.0
        realized = row["realized_pnl"] or 0.0
        return {
            "total": row["total"] or 0,
            "open": row["open"] or 0,
            "settled": settled,
            "won": won,
            "lost": row["lost"] or 0,
            "win_rate": (won / decided) if decided else 0.0,
            "open_stake": round(row["open_stake"] or 0.0, 2),
            "settled_stake": round(settled_stake, 2),
            "realized_pnl": round(realized, 2),
            "roi": (realized / settled_stake) if settled_stake else 0.0,
        }

    @staticmethod
    def _row(r: sqlite3.Row) -> Bet:
        return Bet(
            id=r["id"], condition_id=r["condition_id"], token_id=r["token_id"],
            slug=r["slug"], question=r["question"], outcome=r["outcome"],
            entry_price=r["entry_price"], stake_usd=r["stake_usd"], shares=r["shares"],
            opened_at=r["opened_at"], resolves_at=r["resolves_at"], status=r["status"],
            settle_price=r["settle_price"], pnl=r["pnl"], settled_at=r["settled_at"],
            event=r["event"] if "event" in r.keys() else "",
        )

    def close(self) -> None:
        self._db.close()
