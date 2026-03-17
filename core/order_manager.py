"""
core/order_manager.py — Order placement, tracking, and retry logic.

Responsibilities:
  • place_order()          — submit limit order to CLOB with exponential-backoff retry
  • check_order_status()   — poll order state until FILLED, PARTIAL, or expired
  • cancel_order()         — cancel an unfilled order
  • reconcile()            — reconcile in-memory open orders with exchange state every 60s
  • cancel_all_open()      — emergency shutdown: cancel every tracked order

Retry policy: up to 3 attempts with 1s → 2s → 4s backoff.
In-memory order registry is keyed by order_id (string).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from core.client import PolymarketClient
from utils.logger import get_logger

logger = get_logger(__name__)

# Statuses returned by the CLOB API
STATUS_LIVE = "LIVE"          # order is on the book
STATUS_MATCHED = "MATCHED"    # fully matched / filled
STATUS_CANCELLED = "CANCELLED"
STATUS_UNMATCHED = "UNMATCHED"

# Retry config
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0   # seconds; doubled each attempt (1 → 2 → 4)

# Reconciliation interval
_RECONCILE_INTERVAL = 60  # seconds


class OpenOrder:
    """Lightweight record of an in-flight order."""

    __slots__ = ("order_id", "token_id", "side", "size", "price", "placed_at", "status")

    def __init__(
        self,
        order_id: str,
        token_id: str,
        side: str,
        size: float,
        price: float,
    ) -> None:
        self.order_id = order_id
        self.token_id = token_id
        self.side = side
        self.size = size
        self.price = price
        self.placed_at: datetime = datetime.now(timezone.utc)
        self.status: str = STATUS_LIVE


class OrderManager:
    """
    Manages the lifecycle of CLOB limit orders.

    Usage::

        om = OrderManager(client)
        result = await om.place_order(token_id, "BUY", 5.0, 0.62)
        # later…
        status = await om.check_order_status(result["orderID"])
        # on shutdown…
        await om.cancel_all_open()
    """

    def __init__(self, client: PolymarketClient) -> None:
        self._client = client
        # order_id → OpenOrder
        self._open_orders: dict[str, OpenOrder] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def place_order(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict[str, Any]:
        """
        Place a limit order on the CLOB, retrying up to _MAX_RETRIES times
        with exponential backoff (1s, 2s, 4s).

        Args:
            token_id: CLOB token ID (YES or NO token).
            side:     "BUY" or "SELL".
            size:     Number of shares (rounded to 2 dp by the client).
            price:    Limit price 0.01–0.99 (rounded to 2 dp).

        Returns:
            The raw API response dict (contains "orderID").

        Raises:
            Exception: if all retries fail.
        """
        last_exc: Exception | None = None
        backoff = _BACKOFF_BASE

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                result = await self._client.place_limit_order(
                    token_id=token_id,
                    side=side,
                    size=size,
                    price=price,
                )
                order_id = result.get("orderID", "")
                if order_id:
                    order = OpenOrder(
                        order_id=order_id,
                        token_id=token_id,
                        side=side,
                        size=size,
                        price=price,
                    )
                    async with self._lock:
                        self._open_orders[order_id] = order

                logger.info(
                    "order_placed_ok",
                    order_id=order_id,
                    token_id=token_id[:12],
                    side=side,
                    size=size,
                    price=price,
                    attempt=attempt,
                )
                return result

            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "order_place_failed",
                    attempt=attempt,
                    max_retries=_MAX_RETRIES,
                    token_id=token_id[:12],
                    side=side,
                    error=str(exc),
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    backoff *= 2

        raise RuntimeError(
            f"place_order failed after {_MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc

    async def check_order_status(self, order_id: str) -> str:
        """
        Poll the CLOB for the current status of *order_id*.

        Updates the in-memory registry if the status has changed.

        Returns:
            One of: "LIVE", "MATCHED", "CANCELLED", "UNMATCHED", or "UNKNOWN".
        """
        try:
            data = await self._client.get_order(order_id)
            status: str = data.get("status", "UNKNOWN")
            async with self._lock:
                if order_id in self._open_orders:
                    self._open_orders[order_id].status = status
                    if status in (STATUS_MATCHED, STATUS_CANCELLED):
                        del self._open_orders[order_id]
            logger.debug(
                "order_status_checked",
                order_id=order_id,
                status=status,
            )
            return status
        except Exception as exc:
            logger.warning(
                "order_status_check_failed",
                order_id=order_id,
                error=str(exc),
            )
            return "UNKNOWN"

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """
        Cancel an open order by ID and remove it from the registry.

        Returns:
            The raw API response dict.
        """
        try:
            result = await self._client.cancel_order(order_id)
            async with self._lock:
                self._open_orders.pop(order_id, None)
            logger.info("order_cancelled_ok", order_id=order_id)
            return result
        except Exception as exc:
            logger.warning(
                "order_cancel_failed",
                order_id=order_id,
                error=str(exc),
            )
            raise

    async def cancel_all_open(self) -> int:
        """
        Cancel every currently tracked open order (used on emergency shutdown).

        Returns:
            Number of cancellation requests sent.
        """
        async with self._lock:
            order_ids = list(self._open_orders.keys())

        if not order_ids:
            logger.info("cancel_all_open_no_orders")
            return 0

        logger.warning("cancel_all_open_started", count=len(order_ids))
        cancelled = 0
        for order_id in order_ids:
            try:
                await self._client.cancel_order(order_id)
                async with self._lock:
                    self._open_orders.pop(order_id, None)
                cancelled += 1
            except Exception as exc:
                logger.error(
                    "cancel_all_open_error",
                    order_id=order_id,
                    error=str(exc),
                )

        logger.info("cancel_all_open_done", cancelled=cancelled, total=len(order_ids))
        return cancelled

    async def reconcile(self) -> None:
        """
        Check each tracked open order against the exchange and remove any
        that are no longer live (filled, cancelled, etc.).

        Intended to be called periodically every ~60s.
        """
        async with self._lock:
            order_ids = list(self._open_orders.keys())

        if not order_ids:
            return

        logger.debug("reconcile_started", open_orders=len(order_ids))
        for order_id in order_ids:
            await self.check_order_status(order_id)

    async def run_reconcile_loop(self) -> None:
        """
        Continuously reconcile open orders against exchange state every
        _RECONCILE_INTERVAL seconds.  Runs until cancelled.
        """
        logger.info("reconcile_loop_started", interval=_RECONCILE_INTERVAL)
        try:
            while True:
                await asyncio.sleep(_RECONCILE_INTERVAL)
                await self.reconcile()
        except asyncio.CancelledError:
            logger.info("reconcile_loop_cancelled")
            raise

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def open_order_count(self) -> int:
        return len(self._open_orders)

    def get_open_orders(self) -> list[OpenOrder]:
        return list(self._open_orders.values())
