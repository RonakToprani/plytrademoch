"""
core/wallet.py — Wallet initialisation, balance queries, and allowance checks.

Uses the official py-clob-client (sync) wrapped in asyncio.to_thread so it
never blocks the event loop.
"""

import asyncio
from typing import Any

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def _build_clob_client() -> ClobClient:
    """Construct a ClobClient using the configured private key and chain."""
    client = ClobClient(
        host=settings.clob_host,
        chain_id=settings.chain_id,
        key=settings.private_key,
        signature_type=0,  # EOA
    )
    return client


async def create_authenticated_client() -> ClobClient:
    """
    Initialise a ClobClient, derive API credentials from the private key,
    and attach them to the client.

    Returns the authenticated ClobClient ready for order operations.
    """
    client = await asyncio.to_thread(_build_clob_client)

    # Derive (or fetch) API key / secret / passphrase from the key pair
    creds: ApiCreds = await asyncio.to_thread(client.create_or_derive_api_creds)
    client.set_api_creds(creds)

    logger.info(
        "clob_client_authenticated",
        api_key=creds.api_key[:8] + "…",
    )
    return client


async def get_usdc_balance(client: ClobClient) -> float:
    """
    Return the wallet's USDC balance in dollars.

    Polymarket reports balances in wei (6 decimals for USDC on Polygon).
    """
    raw: dict[str, Any] = await asyncio.to_thread(client.get_balance)
    # raw["balance"] is a string representing the amount in USDC units (not wei)
    # depending on SDK version it may already be float — handle both
    try:
        balance = float(raw.get("balance", raw) if isinstance(raw, dict) else raw)
    except (TypeError, ValueError):
        balance = 0.0

    logger.info("usdc_balance_fetched", balance_usd=balance)
    return balance


async def ensure_allowances(client: ClobClient) -> None:
    """
    Approve USDC spending for the Polymarket exchange contracts if not already set.

    The py-clob-client exposes `update_allowances()` which handles both the
    ERC-20 approve and the Polymarket conditional token approval in one call.
    """
    logger.info("checking_allowances")
    await asyncio.to_thread(client.update_allowances)
    logger.info("allowances_confirmed")
