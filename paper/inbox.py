"""
paper/inbox.py — local archive of anything sent TO the Telegram bot.

Why this exists: the Claude recommendations arrive on Telegram, but nothing on
this machine can see them. The Bot API deliberately gives no way to read messages
the bot itself SENT — `getUpdates` returns only inbound updates — so outbound
review/rec messages are unrecoverable after the fact.

What is recoverable: anything a human sends or FORWARDS to the bot. So forwarding
a Claude rec to @Plykodobot archives it here, where an agent working in this repo
can read it.

Storage is both:
  • SQLite (`inbox` table in paper_underdog.db) — queryable, dedup by update_id
  • Markdown under reports/inbox/ — greppable, and what an agent will actually read

Polling is offset-based and idempotent: each run acknowledges what it consumed, so
messages are never double-stored and never silently dropped. Telegram discards
un-acknowledged updates after ~24h, which is the one real deadline — hence the
frequent launchd schedule.
"""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime, timezone

import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_DB_PATH = os.environ.get("PAPER_DB", "paper_underdog.db")
_INBOX_DIR = "reports/inbox"
_API = "https://api.telegram.org/bot{token}/{method}"


def _connect(path: str = _DB_PATH) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS inbox (
            update_id   INTEGER PRIMARY KEY,
            ts          TEXT NOT NULL,
            chat_id     TEXT NOT NULL DEFAULT '',
            sender      TEXT NOT NULL DEFAULT '',
            origin      TEXT NOT NULL DEFAULT '',   -- who it was forwarded from
            text        TEXT NOT NULL DEFAULT '',
            saved_path  TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_inbox_ts ON inbox(ts);
        """
    )
    db.commit()
    return db


def _slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "note").lower()).strip("-")
    return (s[:n] or "note").rstrip("-")


def _extract(update: dict) -> dict | None:
    """Flatten a Telegram update into the fields we archive. None if not text."""
    msg = (update.get("message") or update.get("channel_post")
           or update.get("edited_message") or {})
    text = msg.get("text") or msg.get("caption") or ""
    if not text.strip():
        return None
    frm = msg.get("from") or {}
    sender = frm.get("username") or frm.get("first_name") or str(frm.get("id") or "")

    # Forwarded messages: newer Bot API uses forward_origin, older forward_from.
    origin = ""
    fo = msg.get("forward_origin") or {}
    if fo:
        su = fo.get("sender_user") or {}
        origin = (su.get("username") or su.get("first_name")
                  or fo.get("sender_user_name") or (fo.get("chat") or {}).get("title") or "")
    if not origin:
        ff = msg.get("forward_from") or msg.get("forward_from_chat") or {}
        origin = ff.get("username") or ff.get("first_name") or ff.get("title") or ""

    ts = datetime.fromtimestamp(msg.get("date") or 0, tz=timezone.utc)
    return {
        "update_id": update.get("update_id"),
        "ts": ts.isoformat(),
        "chat_id": str((msg.get("chat") or {}).get("id") or ""),
        "sender": sender,
        "origin": origin,
        "text": text,
    }


# ---------------------------------------------------------------- commands
#
# Anything in _COMMANDS sent to the bot (by the configured chat only) gets a
# live book card back instead of being archived as a note. Poll cadence is the
# reply latency — the launchd interval is 60s for this reason.
_COMMANDS = frozenset({"pnl", "book", "detail", "details", "status", "stats"})


def _is_command(text: str) -> bool:
    return text.strip().lstrip("/").lower() in _COMMANDS


def _fmt_usd(x: float, sign: bool = True) -> str:
    s = "+" if sign and x >= 0 else ""
    return f"{s}${x:,.2f}" if x >= 0 or not sign else f"-${abs(x):,.2f}"


def _book_card(db_path: str = _DB_PATH) -> str:
    """The dashboard's headline panels as one monospace Telegram message."""
    from paper.marks import marks
    from paper.review import _EXP_ROI, _EXP_WIN, _STRATEGY_EPOCH, _epoch_stats
    from paper.store import PaperStore

    bankroll = float(os.environ.get("POLY_BANKROLL", "1000"))
    store = PaperStore(db_path)
    try:
        s = store.stats()
        opens = store.open_bets()
        ep = _epoch_stats(store)
    finally:
        store.close()

    px = marks([b.token_id for b in opens])
    unreal = {b.id: b.shares * px[b.token_id] - b.stake_usd
              for b in opens if b.token_id in px}
    unreal_total = sum(unreal.values())
    realized = s["realized_pnl"]
    portfolio = bankroll + realized + unreal_total
    deployed = s["open_stake"] / bankroll if bankroll else 0.0
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")

    lines = [
        "POLY TRADING · DRY-RUN",
        f"updated {now} UTC · ${bankroll:,.0f} bankroll",
        "",
        f"OPEN BOOK   {s['open']} pos · ${s['open_stake']:,.2f} "
        f"({deployed*100:.1f}% deployed)",
        f"REALIZED    {_fmt_usd(realized)} · ROI {s['roi']*100:+.1f}%",
        f"UNREALIZED  {_fmt_usd(unreal_total)} (marked to live bid)"
        if unreal else "UNREALIZED  — (no marks)",
        f"PORTFOLIO   ${portfolio:,.2f} "
        f"({(realized + unreal_total)/bankroll*100:+.1f}%)",
        "",
        f"SETTLED     {s['won']}W · {s['lost']}L · win {s['win_rate']*100:.0f}% "
        f"(exp ~{_EXP_WIN*100:.0f}%)",
        f"SINCE {_STRATEGY_EPOCH}  {ep['won']}W · {ep['lost']}L over "
        f"{ep['events']} events · {_fmt_usd(ep['realized_pnl'])} "
        f"({ep['roi']*100:+.1f}%)",
        f"EXPECTATION {_EXP_ROI*100:+.1f}%/bet · gate {ep['events']}/100 events",
    ]
    if opens:
        lines += ["", "OPEN POSITIONS"]
        for b in sorted(opens, key=lambda b: b.resolves_at or ""):
            mark = (f" → {_fmt_usd(unreal[b.id])}" if b.id in unreal else "")
            q = (b.question or b.slug)[:34]
            lines.append(f"· {q}  @{b.entry_price:.2f} ${b.stake_usd:.0f}{mark}")
    return "\n".join(lines)


def _reply(token: str, chat_id: str, text: str) -> bool:
    import html as _html
    try:
        r = httpx.post(_API.format(token=token, method="sendMessage"),
                       json={"chat_id": chat_id, "parse_mode": "HTML",
                             "text": f"<pre>{_html.escape(text)}</pre>"},
                       timeout=15)
        r.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("inbox_reply_failed", error=str(exc))
        return False


def _reply_photo(token: str, chat_id: str, png: str, caption: str) -> bool:
    """Send the dashboard screenshot. Caption is capped at Telegram's 1024."""
    import html as _html
    try:
        with open(png, "rb") as fh:
            r = httpx.post(
                _API.format(token=token, method="sendPhoto"),
                data={"chat_id": chat_id, "parse_mode": "HTML",
                      "caption": f"<pre>{_html.escape(caption[:900])}</pre>"},
                files={"photo": ("dashboard.png", fh, "image/png")},
                timeout=60)
        r.raise_for_status()
        return True
    except (httpx.HTTPError, OSError) as exc:
        logger.warning("inbox_photo_failed", error=str(exc))
        return False


def _answer(token: str, chat_id: str) -> None:
    """Answer a command: dashboard screenshot + headline caption, falling back
    to the text card whenever the screenshot can't be produced."""
    card = _book_card()
    headline = "\n".join(card.split("\n\n")[:2])   # title block + book summary
    png = None
    try:
        from paper.snapshot import capture
        png = capture(os.path.join(_INBOX_DIR, ".dashboard.png"))
    except Exception as exc:                        # noqa: BLE001
        logger.warning("snapshot_error", error=str(exc))
    if png and _reply_photo(token, chat_id, png, headline):
        return
    _reply(token, chat_id, card)


def poll(limit: int = 100, timeout: int = 0, db_path: str = _DB_PATH) -> int:
    """Fetch new updates, archive them (or answer commands), acknowledge.
    Returns count stored."""
    token = settings.telegram_bot_token
    if not token:
        logger.info("inbox_disabled", reason="no telegram token")
        return 0
    db = _connect(db_path)
    row = db.execute("SELECT MAX(update_id) m FROM inbox").fetchone()
    offset = (row["m"] + 1) if row and row["m"] is not None else None

    params: dict = {"limit": limit, "timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        r = httpx.get(_API.format(token=token, method="getUpdates"),
                      params=params, timeout=timeout + 25)
        r.raise_for_status()
        updates = r.json().get("result", []) or []
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("inbox_poll_failed", error=str(exc))
        db.close()
        return 0

    os.makedirs(_INBOX_DIR, exist_ok=True)
    stored = 0
    my_chat = str(settings.telegram_chat_id or "")
    for up in updates:
        rec = _extract(up)
        if rec is None:
            continue
        if db.execute("SELECT 1 FROM inbox WHERE update_id=?",
                      (rec["update_id"],)).fetchone():
            continue
        # Commands get a live book card back instead of an archive note. The
        # row is still inserted (saved_path='') so the offset advances past
        # them; only the configured chat is answered.
        if _is_command(rec["text"]) and rec["chat_id"] == my_chat:
            _answer(token, rec["chat_id"])
            db.execute(
                "INSERT INTO inbox (update_id, ts, chat_id, sender, origin, text, saved_path)"
                " VALUES (?,?,?,?,?,?,?)",
                (rec["update_id"], rec["ts"], rec["chat_id"], rec["sender"],
                 rec["origin"], rec["text"], ""))
            logger.info("inbox_command", cmd=rec["text"].strip().lower())
            continue
        day = rec["ts"][:10]
        name = f"{day}-{rec['update_id']}-{_slug(rec['text'].splitlines()[0])}.md"
        path = os.path.join(_INBOX_DIR, name)
        header = (f"# Inbox {rec['ts']}\n\n"
                  f"- from: **{rec['sender'] or 'unknown'}**\n"
                  + (f"- forwarded from: **{rec['origin']}**\n" if rec["origin"] else "")
                  + f"- update_id: {rec['update_id']}\n\n---\n\n")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(header + rec["text"] + "\n")
        db.execute(
            "INSERT INTO inbox (update_id, ts, chat_id, sender, origin, text, saved_path)"
            " VALUES (?,?,?,?,?,?,?)",
            (rec["update_id"], rec["ts"], rec["chat_id"], rec["sender"],
             rec["origin"], rec["text"], path))
        stored += 1
    db.commit()

    # Acknowledge everything we just read so Telegram stops resending it. Done
    # only after the rows are committed — otherwise a crash here would lose them.
    if updates:
        last = max(u.get("update_id", 0) for u in updates)
        try:
            httpx.get(_API.format(token=token, method="getUpdates"),
                      params={"offset": last + 1, "limit": 1}, timeout=20)
        except httpx.HTTPError:
            pass
    db.close()
    if stored:
        logger.info("inbox_stored", n=stored)
    return stored


def recent(n: int = 10, db_path: str = _DB_PATH) -> list[sqlite3.Row]:
    db = _connect(db_path)
    rows = list(db.execute(
        "SELECT * FROM inbox ORDER BY ts DESC LIMIT ?", (n,)))
    db.close()
    return rows
