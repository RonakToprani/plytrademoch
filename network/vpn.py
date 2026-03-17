"""
network/vpn.py — OpenVPN (tun0) monitoring and public IP helpers.

Responsibilities:
  • check_vpn()      → bool    — verify tun0 interface is up via `ip addr show tun0`
  • get_public_ip()  → str     — fetch current public IP via ipify.org

These functions are synchronous (called via asyncio.to_thread in RiskManager).
"""

from __future__ import annotations

import subprocess

import httpx

from utils.logger import get_logger

logger = get_logger(__name__)

_IPIFY_URL = "https://api.ipify.org?format=json"
_TUN_INTERFACE = "tun0"


def check_vpn() -> bool:
    """
    Return True if the OpenVPN tunnel interface (tun0) is present and UP.

    Uses `ip addr show tun0`; returns False if the command fails or the
    interface is absent / DOWN.
    """
    try:
        result = subprocess.run(
            ["ip", "addr", "show", _TUN_INTERFACE],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.debug("vpn_check_no_interface", interface=_TUN_INTERFACE)
            return False

        output = result.stdout
        is_up = "UP" in output or "LOWER_UP" in output
        logger.debug("vpn_check", interface=_TUN_INTERFACE, is_up=is_up)
        return is_up

    except FileNotFoundError:
        # `ip` command not available (non-Linux)
        logger.warning("vpn_check_ip_not_found")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("vpn_check_timeout")
        return False
    except Exception as exc:
        logger.warning("vpn_check_error", error=str(exc))
        return False


def get_public_ip() -> str | None:
    """
    Fetch the current public IP address via ipify.org.

    Returns the IP string, or None on failure.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(_IPIFY_URL)
            resp.raise_for_status()
            data = resp.json()
            ip: str = data.get("ip", "")
            logger.debug("public_ip_fetched", ip=ip)
            return ip or None
    except Exception as exc:
        logger.warning("get_public_ip_error", error=str(exc))
        return None
