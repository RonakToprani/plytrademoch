"""
utils/notifications.py — Telegram alert delivery.

Responsibilities:
  • Notifier.send(message, severity)  — post a message via Bot API sendMessage
  • Alert triggers (called by other modules):
      - new copy trade opened / closed
      - daily P&L report (at midnight UTC)
      - risk event (stop loss, limit breach, shutdown)
      - bot start / stop

Configuration:
  TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env.
  If either is empty the Notifier silently no-ops (useful for local dev /
  paper-trading without a bot configured).
"""

from __future__ import annotations

import httpx

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Severity → Telegram prefix emoji
_SEVERITY_PREFIX = {
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "🔴",
    "CRITICAL": "🚨",
}


class Notifier:
    """
    Async Telegram notifier.

    Usage::

        notifier = Notifier()
        await notifier.send("Bot started", severity="INFO")

    If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID are not configured the instance
    silently becomes a no-op so the rest of the bot continues without Telegram.
    """

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        self._token = bot_token or settings.telegram_bot_token
        self._chat_id = chat_id or settings.telegram_chat_id
        self._enabled = bool(self._token and self._chat_id)

        if not self._enabled:
            logger.info("notifier_disabled", reason="TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send(self, message: str, severity: str = "INFO") -> bool:
        """
        Send a Telegram message.

        Args:
            message:  Plain-text message body.
            severity: One of INFO, WARNING, ERROR, CRITICAL.

        Returns:
            True on success, False on failure or when disabled.
        """
        if not self._enabled:
            return False

        prefix = _SEVERITY_PREFIX.get(severity.upper(), "")
        full_message = f"{prefix} {message}".strip() if prefix else message

        url = _TELEGRAM_API.format(token=self._token)
        payload = {
            "chat_id": self._chat_id,
            "text": full_message,
            "parse_mode": "HTML",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            logger.debug("telegram_sent", severity=severity, length=len(full_message))
            return True
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "telegram_http_error",
                status=exc.response.status_code,
                body=exc.response.text[:200],
            )
            return False
        except Exception as exc:
            logger.warning("telegram_send_error", error=str(exc))
            return False

    # ------------------------------------------------------------------
    # Convenience methods (called by bot modules)
    # ------------------------------------------------------------------

    async def trade_opened(self, market_slug: str, side: str, size: float, price: float, dry_run: bool) -> None:
        mode = "PAPER" if dry_run else "LIVE"
        sign = "+" if side.upper() in ("BUY", "YES") else "-"
        await self.send(
            f"[{mode}] Trade opened\nMarket: {market_slug}\n"
            f"Side: {side}  Size: {sign}{size:.2f} @ ${price:.3f}",
            severity="INFO",
        )

    async def trade_closed(self, market_slug: str, pnl: float, dry_run: bool) -> None:
        mode = "PAPER" if dry_run else "LIVE"
        sign = "+" if pnl >= 0 else ""
        severity = "INFO" if pnl >= 0 else "WARNING"
        await self.send(
            f"[{mode}] Trade closed\nMarket: {market_slug}\nP&L: {sign}${pnl:.2f}",
            severity=severity,
        )

    async def daily_report(
        self,
        total_pnl: float,
        today_pnl: float,
        num_trades: int,
        win_rate: float,
        exposure: float,
    ) -> None:
        sign = "+" if today_pnl >= 0 else ""
        await self.send(
            f"📊 Daily Report\n"
            f"Today P&L: {sign}${today_pnl:.2f}\n"
            f"Total P&L: ${total_pnl:.2f}\n"
            f"Trades today: {num_trades}  |  Win rate: {win_rate*100:.1f}%\n"
            f"Exposure: ${exposure:.2f}",
            severity="INFO",
        )

    async def risk_event(self, event_type: str, message: str) -> None:
        await self.send(f"Risk event [{event_type}]\n{message}", severity="WARNING")

    async def bot_started(self, dry_run: bool) -> None:
        mode = "PAPER TRADING" if dry_run else "LIVE TRADING"
        await self.send(f"🤖 CopyBot started — {mode} mode", severity="INFO")

    async def bot_stopped(self, reason: str = "graceful shutdown") -> None:
        await self.send(f"🛑 CopyBot stopped\nReason: {reason}", severity="WARNING")
