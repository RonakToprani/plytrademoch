"""
backtest/depth.py — Order-book depth check for the underdog scanner.

The backtest models a flat slippage; this asks the real question: on the live CLOB
book, what would we actually PAY to buy the underdog token, and how much size can
we get before the price walks out of the edge band?

To buy a token you lift the ASKS from the best (lowest) upward. For a target
stake in dollars we walk the asks, accumulating shares, and report the volume-
weighted average fill price. `capacity_in_band` is the total dollar size available
at asks priced at or below `band_hi` — i.e. how much you could deploy on this one
market while still buying inside the edge band.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FillQuality:
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    avg_fill_price: float | None    # VWAP to fill the requested stake
    filled_frac: float              # fraction of the stake that could be filled
    capacity_in_band: float         # $ available at asks <= band_hi
    in_band: bool                   # is the best ask still within the edge band?


def analyze(
    book: dict[str, list[tuple[float, float]]] | None,
    stake_usd: float,
    band_hi: float = 0.20,
) -> FillQuality:
    """Assess fill price and depth for BUYING `stake_usd` of a token."""
    if not book or not book.get("asks"):
        return FillQuality(None, None, None, None, 0.0, 0.0, False)

    asks = book["asks"]                       # sorted low→high (best first)
    bids = book.get("bids") or []             # sorted high→low
    best_ask = asks[0][0]
    best_bid = bids[0][0] if bids else None
    spread = (best_ask - best_bid) if best_bid is not None else None

    # Walk asks to fill the stake.
    remaining = stake_usd
    cost = 0.0
    shares = 0.0
    for price, size in asks:
        level_usd = price * size
        take_usd = min(remaining, level_usd)
        if take_usd <= 0:
            break
        cost += take_usd
        shares += take_usd / price
        remaining -= take_usd
        if remaining <= 1e-9:
            break
    filled_frac = (stake_usd - remaining) / stake_usd if stake_usd > 0 else 0.0
    avg_fill = (cost / shares) if shares > 0 else None

    capacity_in_band = sum(p * s for p, s in asks if p <= band_hi)

    return FillQuality(
        best_bid=best_bid,
        best_ask=best_ask,
        spread=round(spread, 4) if spread is not None else None,
        avg_fill_price=round(avg_fill, 4) if avg_fill is not None else None,
        filled_frac=round(filled_frac, 4),
        capacity_in_band=round(capacity_in_band, 2),
        in_band=best_ask <= band_hi,
    )
