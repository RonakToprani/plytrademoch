"""
paper/notify.py — Spam-free Telegram notifications for the paper strategy.

Synchronous (matches the sync scan/settle engine). Event-driven only: it fires on
a bet opened, a bet settled, or a cycle summary — never on a poll, so it can't
spam the way the old VPN check did. Reads credentials from config.settings
(TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID); silently no-ops if unset.
"""

from __future__ import annotations

import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_API = "https://api.telegram.org/bot{token}/sendMessage"


class PaperNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        self._token = token or settings.telegram_bot_token
        self._chat_id = chat_id or settings.telegram_chat_id
        self._enabled = bool(self._token and self._chat_id)
        if not self._enabled:
            logger.info("paper_notifier_disabled", reason="telegram creds not set")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def send(self, text: str) -> bool:
        if not self._enabled:
            return False
        try:
            with httpx.Client(timeout=10.0) as c:
                r = c.post(
                    _API.format(token=self._token),
                    json={"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"},
                )
                r.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("telegram_send_failed", error=str(exc))
            return False

    # -- event messages -------------------------------------------------

    def bet_opened(self, question: str, outcome: str, price: float, stake: float,
                   hours: float) -> None:
        self.send(
            f"🎯 <b>Paper bet opened</b>\n{question}\n"
            f"Buy <b>{outcome}</b> @ {price:.3f}  •  ${stake:.2f}  •  resolves ~{hours:.0f}h"
        )

    def bet_settled(self, question: str, outcome: str, won: bool, pnl: float) -> None:
        emoji = "✅" if won else "❌"
        sign = "+" if pnl >= 0 else ""
        self.send(
            f"{emoji} <b>Paper bet {'WON' if won else 'LOST'}</b>\n{question}\n"
            f"{outcome}  •  P&L {sign}${pnl:.2f}"
        )

    def cycle_summary(self, opened: int, settled: int, stats: dict) -> None:
        if opened == 0 and settled == 0:
            return  # nothing happened — stay quiet
        self.send(
            f"📊 <b>Paper cycle</b>: +{opened} opened, {settled} settled\n"
            f"Open: {stats['open']} (${stats['open_stake']:.0f})  •  "
            f"Realized P&L: ${stats['realized_pnl']:.2f}  •  "
            f"Win {stats['win_rate']*100:.0f}%  •  ROI {stats['roi']*100:+.0f}%"
        )
