"""
data/models.py — Core dataclasses for all entities in the copy trading bot.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrackedWallet:
    address: str              # Proxy address on Polygon
    alias: str                # Human-readable name (e.g., "Theo4")
    lifetime_pnl: float       # Total realized P&L in USD
    win_rate: float           # Fraction of profitable trades (0-1)
    roi: float                # Return on investment percentage
    total_trades: int         # Number of historical trades
    score: float              # Composite score (0-100)
    is_active: bool           # Currently being tracked
    last_scanned: datetime
    estimated_bankroll: float  # For proportional sizing


@dataclass
class WalletSnapshot:
    wallet_address: str
    token_id: str             # CLOB token ID
    market_slug: str          # Human-readable market name
    side: str                 # "YES" or "NO"
    size: float               # Number of shares
    avg_entry_price: float
    current_price: float
    timestamp: datetime


@dataclass
class CopyTrade:
    id: str                   # UUID
    source_wallet: str        # Whale address we copied
    market_slug: str
    token_id: str
    side: str                 # BUY or SELL
    size: float               # Our position size (proportionally scaled)
    whale_size: float         # Whale's position size
    entry_price: float
    current_price: float
    pnl: float
    status: str               # PENDING, FILLED, PARTIAL, FAILED, CLOSED
    created_at: datetime
    filled_at: datetime | None


@dataclass
class DailyPnL:
    date: str                 # ISO date string e.g. "2024-01-15"
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    num_trades: int
    win_rate: float
    total_exposure: float


@dataclass
class MarketCache:
    condition_id: str         # Gamma API condition ID
    slug: str
    question: str
    yes_token_id: str
    no_token_id: str
    volume: float
    liquidity: float
    yes_price: float
    no_price: float
    end_date: str | None
    cached_at: datetime


@dataclass
class SystemEvent:
    id: int | None            # Auto-assigned by DB
    event_type: str           # "BOT_START", "BOT_STOP", "RISK_BREACH", "ERROR", etc.
    message: str
    severity: str             # "INFO", "WARNING", "ERROR", "CRITICAL"
    created_at: datetime = field(default_factory=datetime.utcnow)
