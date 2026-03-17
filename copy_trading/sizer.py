"""
copy_trading/sizer.py — Proportional position sizing for copy trades.

Responsibilities:
  • compute_size(signal, whale_bankroll) — core proportional sizing formula
  • size_for_signal(signal, db)          — fetch whale bankroll from DB and compute size
  • _clamp()                             — enforce [MIN_TRADE_SIZE, MAX_TRADE_SIZE] bounds
  • _fallback_bankroll()                 — conservative estimate when bankroll is unknown

Sizing formula:
    our_size = (our_bankroll / whale_bankroll) * whale_trade_size

  • Clamped to [MIN_TRADE_SIZE, MAX_TRADE_SIZE] (default $1 – $20)
  • Rounded to 2 decimal places (Polymarket share precision)
  • If whale bankroll is unknown: assume 5× the whale's largest visible position

The sizer does NOT enforce risk limits — that is the RiskManager's responsibility.
Call RiskManager.check_order() before placing the sized order.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from config.settings import settings
from data.models import TradeSignal, TrackedWallet
from utils.logger import get_logger

if TYPE_CHECKING:
    from data.database import Database

logger = get_logger(__name__)

# When the whale bankroll is unknown, assume their trade represents 1/5 of their
# total bankroll — i.e. bankroll ≈ 5 × largest visible position value.
_BANKROLL_MULTIPLIER_FALLBACK = 5.0

# Minimum whale bankroll to avoid division producing absurdly large sizes.
_MIN_WHALE_BANKROLL = 1.0


class ProportionalSizer:
    """
    Computes our position size proportional to the whale's bankroll.

    Usage (with database lookup)::

        sizer = ProportionalSizer()
        our_size = await sizer.size_for_signal(signal, db)

    Usage (direct, when whale bankroll already known)::

        sizer = ProportionalSizer()
        our_size = sizer.compute_size(
            whale_trade_size=500.0,
            whale_bankroll=50_000.0,
        )
    """

    def __init__(
        self,
        our_bankroll: float | None = None,
        min_trade_size: float | None = None,
        max_trade_size: float | None = None,
    ) -> None:
        self._our_bankroll = our_bankroll if our_bankroll is not None else settings.bankroll
        self._min_size = min_trade_size if min_trade_size is not None else settings.min_trade_size
        self._max_size = max_trade_size if max_trade_size is not None else settings.max_trade_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_size(
        self,
        whale_trade_size: float,
        whale_bankroll: float,
    ) -> float:
        """
        Compute our proportional order size given the whale's trade size and
        estimated bankroll.

        Args:
            whale_trade_size: Absolute change in the whale's position (shares).
            whale_bankroll:   Estimated total bankroll of the whale (USD).

        Returns:
            Our order size in shares, clamped to [min_trade_size, max_trade_size]
            and rounded to 2 decimal places.
        """
        if whale_bankroll < _MIN_WHALE_BANKROLL:
            logger.warning(
                "whale_bankroll_too_low",
                whale_bankroll=whale_bankroll,
                using_fallback=True,
            )
            whale_bankroll = max(whale_bankroll, _MIN_WHALE_BANKROLL)

        raw_size = (self._our_bankroll / whale_bankroll) * whale_trade_size
        clamped = self._clamp(raw_size)
        result = round(clamped, 2)

        logger.debug(
            "size_computed",
            our_bankroll=self._our_bankroll,
            whale_bankroll=whale_bankroll,
            whale_trade_size=whale_trade_size,
            raw_size=round(raw_size, 4),
            clamped=clamped,
            final=result,
        )
        return result

    def compute_size_from_signal(
        self,
        signal: TradeSignal,
        whale_bankroll: float,
    ) -> float:
        """
        Convenience wrapper: extract trade size from a TradeSignal and compute
        our proportional size.

        Args:
            signal:         Detected trade signal from the whale.
            whale_bankroll: Estimated whale bankroll in USD.

        Returns:
            Our order size in shares, clamped and rounded.
        """
        return self.compute_size(
            whale_trade_size=signal.whale_size_delta,
            whale_bankroll=whale_bankroll,
        )

    async def size_for_signal(
        self,
        signal: TradeSignal,
        db: "Database",
    ) -> float:
        """
        Look up the tracked wallet from the database, retrieve its estimated
        bankroll, and compute our proportional size.

        Falls back to a conservative bankroll estimate when the stored value is
        zero or missing.

        Args:
            signal: Trade signal emitted by the detector.
            db:     Database instance for wallet lookup.

        Returns:
            Our order size in shares, clamped and rounded.
        """
        wallet: TrackedWallet | None = await db.get_wallet(signal.wallet)

        if wallet is not None and wallet.estimated_bankroll > 0:
            whale_bankroll = wallet.estimated_bankroll
            source = "db"
        else:
            # Fallback: assume bankroll ≈ 5× the whale's trade value
            whale_trade_usd = signal.whale_size_delta * max(signal.current_price, 0.01)
            whale_bankroll = max(
                whale_trade_usd * _BANKROLL_MULTIPLIER_FALLBACK,
                _MIN_WHALE_BANKROLL,
            )
            source = "fallback"

        logger.info(
            "sizing_signal",
            wallet=signal.wallet[:10],
            market_slug=signal.market_slug,
            action=signal.action,
            whale_size_delta=signal.whale_size_delta,
            whale_bankroll=round(whale_bankroll, 2),
            bankroll_source=source,
        )

        return self.compute_size_from_signal(signal, whale_bankroll)

    def fallback_bankroll(self, largest_position_usd: float) -> float:
        """
        Estimate a whale's bankroll when no DB record exists.

        Assumes the whale's largest visible position represents 1/5 of their
        total bankroll, i.e. bankroll ≈ 5 × largest_position_usd.

        Args:
            largest_position_usd: USD value of the whale's largest known position.

        Returns:
            Conservative bankroll estimate in USD.
        """
        return max(largest_position_usd * _BANKROLL_MULTIPLIER_FALLBACK, _MIN_WHALE_BANKROLL)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clamp(self, size: float) -> float:
        """Clamp *size* to [min_trade_size, max_trade_size]."""
        if not math.isfinite(size) or size < 0:
            return self._min_size
        return max(self._min_size, min(self._max_size, size))
