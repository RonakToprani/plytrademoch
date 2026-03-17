"""
core/client.py — PolymarketClient: unified async wrapper for all three APIs.

APIs:
  • CLOB API    — order book, order placement, trade history (via py-clob-client)
  • Gamma API   — market metadata (httpx async, 5-min cache)
  • Data API    — user positions, trade history, leaderboard (httpx async)

Rate limiting: 60 req/min shared budget enforced via a token-bucket semaphore.
"""

import asyncio
import time
from typing import Any
from collections import OrderedDict

import httpx
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Simple TTL cache
# ---------------------------------------------------------------------------

class _TTLCache:
    """Thread-safe in-memory TTL cache (LRU-style, max 256 entries)."""

    def __init__(self, ttl_seconds: float = 300, maxsize: int = 256) -> None:
        self._ttl = ttl_seconds
        self._maxsize = maxsize
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[key]
                return None
            # Move to end (LRU)
            self._store.move_to_end(key)
            return value

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (time.monotonic(), value)
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)


# ---------------------------------------------------------------------------
# Rate-limit token bucket (60 req/min)
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Token bucket: 60 tokens/min, replenished continuously."""

    def __init__(self, rate: float = 60.0, per: float = 60.0) -> None:
        self._rate = rate
        self._per = per
        self._tokens = rate
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self._rate, self._tokens + elapsed * (self._rate / self._per))
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / (self._rate / self._per)
                await asyncio.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# ---------------------------------------------------------------------------
# PolymarketClient
# ---------------------------------------------------------------------------

class PolymarketClient:
    """
    Unified async client for all Polymarket API surfaces.

    Usage:
        async with PolymarketClient(clob_client) as pm:
            markets = await pm.get_markets(limit=20)
    """

    def __init__(self, clob_client: ClobClient) -> None:
        self._clob = clob_client
        self._rate_limiter = _RateLimiter(rate=60.0, per=60.0)
        self._gamma_cache: _TTLCache = _TTLCache(ttl_seconds=300)
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "PolymarketClient":
        self._http = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, url: str, params: dict | None = None) -> Any:
        """Rate-limited GET with error logging."""
        await self._rate_limiter.acquire()
        if self._http is None:
            raise RuntimeError("Client not started — use async with")
        try:
            resp = await self._http.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "http_error",
                url=url,
                status=exc.response.status_code,
                body=exc.response.text[:200],
            )
            raise
        except httpx.RequestError as exc:
            logger.error("request_error", url=url, error=str(exc))
            raise

    # ------------------------------------------------------------------
    # CLOB API  (sync py-clob-client → asyncio.to_thread)
    # ------------------------------------------------------------------

    async def get_order_book(self, token_id: str) -> dict[str, Any]:
        """Fetch the order book for a CLOB token."""
        await self._rate_limiter.acquire()
        return await asyncio.to_thread(self._clob.get_order_book, token_id)

    async def place_limit_order(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float,
    ) -> dict[str, Any]:
        """
        Place a limit order on the CLOB.

        side: "BUY" or "SELL"
        price: 0.01–0.99 (2 decimal places)
        size: number of shares (2 decimal places)
        """
        await self._rate_limiter.acquire()
        order_args = OrderArgs(
            token_id=token_id,
            price=round(price, 2),
            size=round(size, 2),
            side=side,
            order_type=OrderType.GTC,
        )
        signed_order = await asyncio.to_thread(self._clob.create_order, order_args)
        result = await asyncio.to_thread(self._clob.post_order, signed_order, OrderType.GTC)
        logger.info(
            "order_placed",
            token_id=token_id,
            side=side,
            size=size,
            price=price,
            order_id=result.get("orderID", "unknown"),
        )
        return result

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an open order by ID."""
        await self._rate_limiter.acquire()
        result = await asyncio.to_thread(self._clob.cancel, order_id)
        logger.info("order_cancelled", order_id=order_id)
        return result

    async def get_trades(
        self,
        market_id: str | None = None,
        maker_address: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch trade history from the CLOB."""
        await self._rate_limiter.acquire()
        params: dict[str, Any] = {"limit": limit}
        if market_id:
            params["market"] = market_id
        if maker_address:
            params["maker_address"] = maker_address
        return await asyncio.to_thread(self._clob.get_trades, params)

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Fetch a single order's current state."""
        await self._rate_limiter.acquire()
        return await asyncio.to_thread(self._clob.get_order, order_id)

    # ------------------------------------------------------------------
    # Gamma API  (httpx async, 5-min cache)
    # ------------------------------------------------------------------

    async def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True,
    ) -> list[dict[str, Any]]:
        """Fetch active markets from the Gamma API (cached 5 min)."""
        cache_key = f"markets:{limit}:{offset}:{active}"
        cached = await self._gamma_cache.get(cache_key)
        if cached is not None:
            return cached

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if active:
            params["active"] = "true"
            params["closed"] = "false"

        data = await self._get(f"{settings.gamma_host}/markets", params=params)
        markets: list[dict[str, Any]] = data if isinstance(data, list) else data.get("markets", [])
        await self._gamma_cache.set(cache_key, markets)
        return markets

    async def get_market_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Fetch a single market by its slug (cached 5 min)."""
        cache_key = f"slug:{slug}"
        cached = await self._gamma_cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._get(
            f"{settings.gamma_host}/markets",
            params={"slug": slug},
        )
        markets = data if isinstance(data, list) else data.get("markets", [])
        result = markets[0] if markets else None
        if result:
            await self._gamma_cache.set(cache_key, result)
        return result

    async def get_market_by_token(self, token_id: str) -> dict[str, Any] | None:
        """Fetch a market given a CLOB token ID (YES or NO token)."""
        cache_key = f"token:{token_id}"
        cached = await self._gamma_cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._get(
            f"{settings.gamma_host}/markets",
            params={"clob_token_ids": token_id},
        )
        markets = data if isinstance(data, list) else data.get("markets", [])
        result = markets[0] if markets else None
        if result:
            await self._gamma_cache.set(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # Data API  (httpx async — no cache, near-real-time data needed)
    # ------------------------------------------------------------------

    async def get_user_positions(self, address: str) -> list[dict[str, Any]]:
        """
        Fetch current open positions for a wallet address.

        Returns list of position objects from the Data API.
        """
        data = await self._get(
            f"{settings.data_api_host}/positions",
            params={"user": address, "sizeThreshold": "0.01"},
        )
        return data if isinstance(data, list) else data.get("positions", [])

    async def get_user_history(
        self,
        address: str,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Fetch trade history for a wallet address.

        Paginates automatically if needed — callers can also use limit/offset.
        """
        data = await self._get(
            f"{settings.data_api_host}/activity",
            params={"user": address, "limit": limit, "offset": offset},
        )
        return data if isinstance(data, list) else data.get("history", [])

    async def get_leaderboard(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Fetch the Polymarket profit leaderboard.

        Returns a ranked list of traders with P&L and win rate data.
        """
        data = await self._get(
            f"{settings.data_api_host}/leaderboard",
            params={"limit": limit, "offset": offset},
        )
        return data if isinstance(data, list) else data.get("leaderboard", [])
