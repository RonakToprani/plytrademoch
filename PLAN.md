# Polymarket Copy Trading Bot — Implementation Plan

## Context

**Why:** Only 0.51% of Polymarket wallets have profits exceeding $1,000 — the top traders have a genuine, trackable edge. Since Polymarket runs on Polygon, every trade is publicly visible on-chain. We exploit this transparency by identifying the most profitable wallets, monitoring their positions in real-time, and automatically copying their trades with proportional sizing.

**Why copy trading over other strategies:**
- Market making spreads compressed from 4.5% → 1.2%, dominated by sub-100ms bots — not viable for us
- Cross-platform arbitrage excluded per user requirement
- Copy trading has moderate complexity, works with small bankroll ($50-$200), and leverages proven alpha from whale wallets with $100K+ lifetime P&L

**What we're building:** A fully autonomous Python bot that discovers, scores, and follows top Polymarket traders — plus a real-time Dash web dashboard to monitor everything. Paper trading mode first, then live with small capital.

---

## Project Structure

```
polymarket_bot/
├── main.py                          # Async orchestrator — runs bot + dashboard
├── config/
│   ├── settings.py                  # Pydantic BaseSettings from .env
│   └── .env.example                 # Template with all config keys
├── core/
│   ├── client.py                    # Polymarket API wrapper (CLOB + Gamma + Data API)
│   ├── wallet.py                    # Our wallet init, balances, allowances
│   └── order_manager.py             # Order placement, tracking, retry logic
├── copy_trading/
│   ├── scanner.py                   # Wallet discovery & scoring engine
│   ├── tracker.py                   # Real-time position monitoring for target wallets
│   ├── detector.py                  # Trade detection — diff snapshots to find new trades
│   ├── sizer.py                     # Proportional position sizing
│   └── executor.py                  # Copy trade execution pipeline
├── data/
│   ├── feed.py                      # WebSocket real-time market data
│   ├── models.py                    # SQLAlchemy-style dataclasses for all entities
│   └── database.py                  # aiosqlite persistence layer (all tables)
├── risk/
│   ├── manager.py                   # Pre-trade checks, daily loss limit, auto-shutdown
│   └── portfolio.py                 # Position tracking, mark-to-market, exposure calc
├── dashboard/
│   ├── app.py                       # Dash app factory & layout
│   ├── pages/
│   │   ├── overview.py              # Portfolio overview — equity curve, P&L, positions
│   │   ├── wallets.py               # Tracked whale wallets — scores, performance
│   │   ├── trades.py                # Trade log — all copied trades with P&L
│   │   ├── markets.py               # Active markets — prices, volumes, positions
│   │   └── risk.py                  # Risk dashboard — exposure, limits, system health
│   ├── components/
│   │   ├── cards.py                 # Reusable stat cards (P&L, win rate, etc.)
│   │   ├── tables.py                # Reusable data tables
│   │   └── charts.py                # Reusable Plotly chart builders
│   └── callbacks.py                 # Dash callbacks for interactivity & auto-refresh
├── network/
│   └── vpn.py                       # OpenVPN (tun0) monitoring
├── utils/
│   ├── logger.py                    # structlog configuration
│   └── notifications.py             # Telegram alerts
├── tests/
│   ├── test_scanner.py              # Wallet scoring logic
│   ├── test_detector.py             # Trade detection (snapshot diffing)
│   ├── test_sizer.py                # Proportional sizing math
│   ├── test_risk.py                 # Risk limit enforcement
│   └── test_executor.py             # Order placement logic
├── requirements.txt
└── README.md
```

---

## Data Models (`data/models.py`)

```python
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
    estimated_bankroll: float # For proportional sizing

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
    date: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    num_trades: int
    win_rate: float
    total_exposure: float
```

---

## Database Schema (`data/database.py`)

SQLite tables via aiosqlite:

| Table | Purpose |
|-------|---------|
| `tracked_wallets` | Scored whale wallets we follow |
| `wallet_snapshots` | Position snapshots for diff detection |
| `copy_trades` | All trades we've executed (or simulated in paper mode) |
| `daily_pnl` | Daily P&L rollups for equity curve |
| `market_cache` | Cached Gamma API market metadata (5-min TTL) |
| `system_events` | Bot start/stop, errors, risk events |

---

## Implementation Sequence (10 Steps)

### Step 1: Foundation & Config
**Files:** `requirements.txt`, `config/settings.py`, `config/.env.example`, `utils/logger.py`

- **requirements.txt**: py-clob-client, httpx, websockets, aiosqlite, pydantic, pydantic-settings, structlog, dash, plotly, pandas, python-dotenv, apscheduler
- **config/settings.py**: Pydantic v2 BaseSettings loading from .env:
  - `PRIVATE_KEY`, `CHAIN_ID=137`, `POLYMARKET_HOST`, `CLOB_HOST`, `GAMMA_HOST`, `DATA_API_HOST`
  - Copy trading params: `POLL_INTERVAL_SECONDS=30`, `MIN_WHALE_PNL=100000`, `MIN_WIN_RATE=0.65`, `MIN_TRADES=50`, `MAX_TRACKED_WALLETS=10`
  - Sizing: `BANKROLL`, `MIN_TRADE_SIZE=1.0`, `MAX_TRADE_SIZE=20.0`
  - Risk: `MAX_POSITION_PER_MARKET=20`, `MAX_PORTFOLIO_EXPOSURE=150`, `MAX_DAILY_LOSS=10`
  - Dashboard: `DASHBOARD_PORT=8050`, `DASHBOARD_REFRESH_SECONDS=10`
  - `DRY_RUN=true` (paper trading mode), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- **utils/logger.py**: structlog with JSON (prod) / colored console (dev), context binding for wallet addresses and trade IDs

### Step 2: Core API Layer
**Files:** `core/client.py`, `core/wallet.py`

- **core/wallet.py**:
  - `create_authenticated_client()` — init ClobClient with private key, derive API credentials
  - `get_usdc_balance()` — query balance (wei ÷ 1e6)
  - `ensure_allowances()` — approve USDC spending for exchange contracts
- **core/client.py** — `PolymarketClient` class wrapping three APIs:
  - **CLOB API** (via py-clob-client, sync→`asyncio.to_thread`): `get_order_book()`, `place_limit_order()`, `cancel_order()`, `get_trades()`
  - **Gamma API** (httpx async): `get_markets()`, `get_market_by_slug()`, `get_market_by_token()` — with 5-min response cache
  - **Data API** (httpx async): `get_user_positions(address)`, `get_user_history(address)`, `get_leaderboard()` — the key endpoints for copy trading
  - Rate limit handling: respect 60 req/min, queue excess requests

### Step 3: Database & Data Models
**Files:** `data/models.py`, `data/database.py`

- All dataclasses as defined above
- **database.py** — `Database` class:
  - `init_db()` — create all tables with proper indexes
  - CRUD methods for each table: `upsert_wallet()`, `save_snapshot()`, `save_trade()`, `get_equity_curve()`, etc.
  - `get_latest_snapshot(wallet)` — for diffing against new data
  - `get_portfolio_summary()` — aggregated stats for dashboard

### Step 4: Wallet Scanner & Scoring
**Files:** `copy_trading/scanner.py`

- **WalletScanner** class:
  - `discover_wallets()` — fetch from Data API leaderboard endpoint, paginate through top traders
  - `score_wallet(address)` — fetch full trade history, compute composite score:
    ```
    score = (0.30 * normalized_pnl) +
            (0.25 * win_rate) +
            (0.20 * roi) +
            (0.15 * consistency_score) +
            (0.10 * recency_score)
    ```
    - `consistency_score`: Sharpe-like ratio of returns across trades
    - `recency_score`: Higher weight for recent activity (active in last 30 days)
  - `filter_wallets()` — apply minimum thresholds: P&L > $100K, win rate > 65%, trades > 50
  - `estimate_bankroll(address)` — sum of current position values + available balance (via on-chain query or position data)
  - `rescan_all()` — daily re-scoring of all tracked wallets, remove any that drop below thresholds
  - Store results in `tracked_wallets` table

### Step 5: Trade Detection Engine
**Files:** `copy_trading/tracker.py`, `copy_trading/detector.py`

- **WalletTracker** (`tracker.py`):
  - `poll_positions(address)` — fetch current positions from Data API
  - `take_snapshot(address)` — save current state to `wallet_snapshots` table
  - `run()` — async loop polling all tracked wallets every `POLL_INTERVAL_SECONDS` (default 30s)
  - Stagger requests across wallets to stay under rate limits (60 req/min ÷ 10 wallets = 6 req/wallet/min is fine)

- **TradeDetector** (`detector.py`):
  - `detect_changes(address)` — compare latest snapshot vs previous:
    - **New position**: token_id exists in new but not old → whale entered a new market
    - **Increased position**: same token_id, new size > old size → whale added to position
    - **Decreased/closed position**: same token_id, new size < old size → whale is exiting
    - **Side flip**: was YES, now NO (or vice versa) → whale reversed conviction
  - Returns list of `TradeSignal` objects: `(wallet, token_id, action, whale_size_delta, market_slug, current_price)`
  - **Filtering**: ignore delta-neutral legs (if whale has both YES and NO on same market), ignore very small position changes (<$100 for the whale)

### Step 6: Position Sizing
**Files:** `copy_trading/sizer.py`

- **ProportionalSizer** class:
  - Core formula: `our_size = (our_bankroll / whale_bankroll) * whale_trade_size`
  - Clamp to `[MIN_TRADE_SIZE, MAX_TRADE_SIZE]`
  - Check against risk limits before returning size
  - If whale bankroll unknown, use conservative estimate (assume 5x their largest visible position)
  - Round to 2 decimal places (Polymarket precision)

### Step 7: Trade Execution
**Files:** `copy_trading/executor.py`, `core/order_manager.py`

- **CopyExecutor** (`executor.py`):
  - `execute_signal(signal)` — full pipeline:
    1. Compute size via `ProportionalSizer`
    2. Risk check via `RiskManager.check_order()`
    3. If DRY_RUN: log signal, simulate fill at current mid price, save to DB
    4. If live: place limit order at (mid + 0.01) for quick fill via `OrderManager`
    5. Save `CopyTrade` to database
    6. Send Telegram notification
  - `close_position(trade_id)` — when whale exits, we exit too
  - `handle_detection_batch(signals)` — process multiple signals from one poll cycle

- **OrderManager** (`order_manager.py`):
  - `place_order()` — submit to CLOB, retry up to 3x with exponential backoff (1s, 2s, 4s)
  - `check_order_status()` — poll order state until FILLED, PARTIAL, or expired
  - `cancel_order()` — cancel unfilled orders
  - Track all open orders in memory, reconcile with exchange state every 60s

### Step 8: Risk Management
**Files:** `risk/manager.py`, `risk/portfolio.py`

- **Portfolio** (`portfolio.py`):
  - Track all open positions from `copy_trades` table
  - `mark_to_market()` — update current prices via CLOB API, recalculate unrealized P&L
  - `total_exposure()` — sum of all position values
  - `daily_pnl()` — realized + unrealized P&L since midnight UTC
  - `generate_report()` — summary dict for dashboard and Telegram

- **RiskManager** (`manager.py`):
  - `check_order(signal)` → bool — pre-trade validation:
    - Position per market ≤ MAX_POSITION_PER_MARKET ($20)
    - Total exposure ≤ MAX_PORTFOLIO_EXPOSURE ($150)
    - Daily loss not breached (MAX_DAILY_LOSS = $10)
    - VPN is connected
    - Data feed is not stale (last update < 5 min ago)
  - `check_stop_losses()` — close any position down >50% from entry
  - `emergency_shutdown()` — cancel all orders, send Telegram alert
  - Runs periodic check every 30s

### Step 9: Dashboard
**Files:** `dashboard/app.py`, `dashboard/pages/*`, `dashboard/components/*`, `dashboard/callbacks.py`

Built with **Dash by Plotly** — runs on a separate thread alongside the async bot.

#### Layout (`dashboard/app.py`)
- Multi-page Dash app with sidebar navigation
- Dark theme (Dash Bootstrap Components, `DARKLY` theme)
- Auto-refresh every 10 seconds via `dcc.Interval`
- Served at `http://localhost:8050`

#### Page 1: Portfolio Overview (`pages/overview.py`)
- **Top row — 4 stat cards:**
  - Total P&L (color-coded green/red)
  - Today's P&L
  - Win Rate (%)
  - Total Exposure / Max Exposure
- **Equity curve chart** — line chart of daily total P&L over time (from `daily_pnl` table)
- **Current positions table** — market, side, size, entry price, current price, unrealized P&L, source wallet
- **P&L distribution** — histogram of per-trade P&L

#### Page 2: Tracked Wallets (`pages/wallets.py`)
- **Wallet scorecard table** — address (truncated), alias, score, lifetime P&L, win rate, ROI, trades, status (active/paused)
- **Per-wallet drill-down** (click a row):
  - Wallet's current positions on Polymarket
  - Recent trade history
  - P&L chart for this wallet's signals
- **Add/Remove wallet** — input field to manually add a wallet address, button to remove
- **Auto-discovery button** — trigger `WalletScanner.discover_wallets()` on demand

#### Page 3: Trade Log (`pages/trades.py`)
- **Full trade history table** — timestamp, market, side, size, entry price, exit price, P&L, status, source wallet
- **Filters**: date range, wallet, market, status (open/closed/all), P&L (winners/losers)
- **Trade P&L chart** — bar chart of each trade's P&L chronologically

#### Page 4: Markets (`pages/markets.py`)
- **Active markets we're trading** — market name, YES price, NO price, volume, our position size, unrealized P&L
- **Market price chart** — select a market, show price history (from cached snapshots)
- **Market search** — search Gamma API for new markets

#### Page 5: Risk Dashboard (`pages/risk.py`)
- **Exposure gauge** — current total exposure as % of MAX_PORTFOLIO_EXPOSURE (green/yellow/red zones)
- **Daily P&L gauge** — today's P&L vs MAX_DAILY_LOSS threshold
- **System health indicators:**
  - Bot status (running/stopped)
  - VPN status (connected/disconnected)
  - Last data feed update (timestamp + staleness indicator)
  - API rate limit usage
  - Wallet balance (USDC)
- **Risk event log** — table of recent risk events (stop losses, limit breaches, shutdowns)

#### Components (`dashboard/components/`)
- **cards.py**: `stat_card(title, value, color, icon)` — reusable Bootstrap card
- **tables.py**: `data_table(df, columns, id)` — reusable Dash DataTable with sorting/filtering
- **charts.py**: `equity_curve(df)`, `pnl_histogram(df)`, `price_chart(df)`, `exposure_gauge(current, max)` — Plotly figure builders

#### Callbacks (`dashboard/callbacks.py`)
- Auto-refresh callback: reads latest data from SQLite every N seconds, updates all visible components
- Wallet add/remove callbacks
- Drill-down callbacks for wallet detail view
- Filter callbacks for trade log
- Market selection callback for price chart

### Step 10: Orchestrator, Notifications & Tests
**Files:** `main.py`, `utils/notifications.py`, `network/vpn.py`, `tests/*`

- **main.py** — async entry point:
  ```
  1. Load config from .env
  2. Init database (create tables)
  3. Init PolymarketClient (CLOB + Gamma + Data API auth)
  4. Check VPN status
  5. Check USDC balance
  6. Run initial wallet scan (or load from DB)
  7. Start dashboard on separate thread (threading.Thread)
  8. Start async tasks:
     a. WalletTracker.run() — poll positions every 30s
     b. TradeDetector loop — detect changes, emit signals
     c. CopyExecutor loop — consume signals, execute/simulate trades
     d. RiskManager loop — check stop losses, exposure, daily P&L every 30s
     e. Portfolio mark-to-market — every 60s
     f. Daily wallet rescan — every 24h
     g. Daily P&L snapshot — at midnight UTC
  9. Graceful shutdown on SIGINT/SIGTERM:
     - Cancel all open orders
     - Save final state to DB
     - Send Telegram shutdown notification
  ```

- **utils/notifications.py**:
  - `send_telegram(message, severity)` — via Bot API `sendMessage`
  - Alert triggers: new copy trade, trade closed, daily P&L report, risk event, bot start/stop
  - Daily report at midnight UTC: total P&L, number of trades, win rate, top/worst trades

- **network/vpn.py**:
  - `check_vpn()` → bool — check `tun0` via `ip addr show tun0`
  - `get_public_ip()` — via ipify.org
  - Continuous monitoring, pause all trading if VPN drops

- **Tests:**
  - `test_scanner.py` — scoring formula, filtering, edge cases (wallets with 0 trades, negative P&L)
  - `test_detector.py` — snapshot diffing: new position, increased, decreased, closed, side flip
  - `test_sizer.py` — proportional sizing math, clamping, edge cases (unknown bankroll)
  - `test_risk.py` — limit enforcement, daily loss shutdown, stale data rejection, VPN check
  - `test_executor.py` — DRY_RUN simulation, order placement, retry logic

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python 3.11+ | py-clob-client is Python, async/await support |
| Concurrency | asyncio + threading | Bot is async; Dash runs on a separate thread |
| CLOB SDK | py-clob-client via `asyncio.to_thread()` | Official SDK is sync, must not block event loop |
| HTTP client | httpx (async) | For Data API, Gamma API, Telegram |
| Persistence | SQLite via aiosqlite | Lightweight, no external DB, async-compatible |
| Dashboard | Dash by Plotly | Python-native, rich charts, real-time callbacks, Bootstrap themes |
| Config | Pydantic v2 BaseSettings | Type-safe, .env loading, validation |
| Logging | structlog | Structured, context-aware, JSON for prod |
| Detection method | Polling + snapshot diffing | Data API doesn't offer push notifications; 30s polling is sufficient for copy trading latency |
| Position sizing | Proportional to whale bankroll | Only mathematically correct way to replicate whale's % ROI |

## Polymarket-Specific Notes
- Must use **Proxy Addresses** (not EOA) — trades execute through proxy contracts
- USDC balance returned in wei (÷ 1e6 for dollars)
- YES = clobTokenIds[0], NO = clobTokenIds[1]; to "short" YES, buy NO
- Batch order endpoint supports up to 15 orders
- Rate limit: 60 req/min public endpoints; cache Gamma API responses 5 min
- Prices: 2 decimal places, range 0.01–0.99
- signature_type: 0=EOA, 1=Magic, 2=browser proxy
- The Graph: 100K free queries/month for subgraph data

## User-Specific Configuration
- **Bankroll**: $50–$200, paper trading first via `DRY_RUN=true`
- **Risk limits (small bankroll)**: $20/market, $150 total exposure, $10 daily loss limit
- **VPN**: OpenVPN — check `tun0` interface
- **Notifications**: Telegram only
- **Dashboard**: localhost:8050, 10s auto-refresh
- **Wallet targets**: Top 5-10 wallets with $100K+ P&L, >65% win rate

## Risk Guardrails
- Max $20 per market, $150 total exposure, $10 daily loss limit (auto-shutdown)
- Close any position losing >50% of entry value
- Pause trading if VPN (tun0) drops
- Pause if no position update received in 5 minutes (stale data)
- Never copy a trade if market resolves within 24 hours (too risky for latency)
- Ignore whale trades < $100 (noise)
- DRY_RUN mode simulates fills at midpoint, tracks phantom P&L

---

## Verification

1. **Unit tests**: `pytest tests/` — wallet scoring math, snapshot diffing, proportional sizing, risk limits
2. **Paper trading**: `DRY_RUN=true` — bot discovers wallets, detects trades, simulates fills, tracks P&L. Verify via dashboard at localhost:8050 and Telegram reports. Run for 48-72h.
3. **Dashboard verification**: Start dashboard, confirm all 5 pages render, stat cards update on refresh, equity curve plots, trade log filters work, wallet add/remove functions
4. **Small live test**: Fund wallet with $10 USDC on Polygon. Track 2-3 wallets. Verify copied orders appear on Polymarket, fills recorded, P&L updates on dashboard. Confirm VPN monitoring pauses trading on disconnect.
5. **Scale up**: Increase to $50-$200 bankroll, track 5-10 wallets, monitor daily P&L reports. Adjust polling interval and risk limits based on observed performance.
