"""
dashboard/callbacks.py — All Dash callbacks for the copy trading dashboard.

Callback groups:
  1. Auto-refresh (dcc.Interval) → updates all live data components
  2. Wallet add/remove → writes to DB, refreshes wallet table
  3. Wallet drill-down → shows per-wallet position detail on row click
  4. Trade log filters → date range, status, P&L sign, wallet filter
  5. Market price chart → updates chart when dropdown selection changes
  6. Market search → queries DB cache, populates dropdown options

The database path is resolved at module level; callbacks use asyncio.run()
via a sync wrapper because Dash callbacks are synchronous.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from dash import Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate

from config.settings import settings
from data.database import Database
from dashboard.components.cards import pnl_card, stat_card
from dashboard.components.charts import (
    daily_pnl_gauge,
    equity_curve,
    exposure_gauge,
    pnl_bar_chart,
    pnl_histogram,
    price_chart,
)
from dashboard.components.tables import data_table
from network.vpn import check_vpn
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run an async coroutine from a sync Dash callback.

    Uses a dedicated background event loop so that all callbacks share one
    loop instead of creating (and tearing down) a new loop per invocation.
    This avoids resource leaks and is safe to call from Dash's sync
    callback threads.
    """
    return _BG_LOOP.run(coro)


class _BackgroundLoop:
    """Runs a single asyncio event loop on a background daemon thread."""

    def __init__(self) -> None:
        import threading
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True, name="dash-async")
        self._thread.start()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=30)


_BG_LOOP = _BackgroundLoop()


async def _fetch_summary() -> dict[str, Any]:
    async with Database() as db:
        return await db.get_portfolio_summary()


async def _fetch_equity_curve() -> pd.DataFrame:
    async with Database() as db:
        records = await db.get_equity_curve(days=90)
    if not records:
        return pd.DataFrame(columns=["date", "total_pnl"])
    return pd.DataFrame([{"date": r.date, "total_pnl": r.total_pnl} for r in records])


async def _fetch_open_positions() -> pd.DataFrame:
    async with Database() as db:
        trades = await db.get_open_trades()
    if not trades:
        return pd.DataFrame()
    rows = []
    for t in trades:
        rows.append({
            "market_slug": t.market_slug,
            "side": t.side,
            "size": round(t.size, 2),
            "entry_price": round(t.entry_price, 3),
            "current_price": round(t.current_price, 3),
            "pnl": round(t.pnl, 4),
            "status": t.status,
            "source_wallet": t.source_wallet[:10] + "…",
        })
    return pd.DataFrame(rows)


async def _fetch_trades(
    status_filter: str,
    pnl_filter: str,
    wallet_filter: str,
    start_date: str | None,
    end_date: str | None,
) -> pd.DataFrame:
    async with Database() as db:
        status = None if status_filter in ("all", "open") else status_filter
        wallet = wallet_filter.strip() if wallet_filter else None
        trades = await db.get_all_trades(limit=1000, status=status, source_wallet=wallet or None)

    if status_filter == "open":
        trades = [t for t in trades if t.status in ("PENDING", "FILLED", "PARTIAL")]

    if start_date:
        trades = [t for t in trades if t.created_at.date().isoformat() >= start_date]
    if end_date:
        trades = [t for t in trades if t.created_at.date().isoformat() <= end_date]

    if pnl_filter == "winners":
        trades = [t for t in trades if t.pnl > 0]
    elif pnl_filter == "losers":
        trades = [t for t in trades if t.pnl < 0]

    if not trades:
        return pd.DataFrame()

    rows = []
    for t in trades:
        rows.append({
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "market_slug": t.market_slug,
            "side": t.side,
            "size": round(t.size, 2),
            "entry_price": round(t.entry_price, 3),
            "current_price": round(t.current_price, 3),
            "pnl": round(t.pnl, 4),
            "status": t.status,
            "source_wallet": t.source_wallet[:10] + "…",
        })
    return pd.DataFrame(rows)


async def _fetch_wallets() -> pd.DataFrame:
    async with Database() as db:
        wallets = await db.get_all_wallets()
    if not wallets:
        return pd.DataFrame()
    rows = []
    for w in wallets:
        rows.append({
            "address": w.address[:10] + "…",
            "alias": w.alias or "—",
            "score": round(w.score, 1),
            "lifetime_pnl": f"${w.lifetime_pnl:,.0f}",
            "win_rate": f"{w.win_rate * 100:.1f}%",
            "roi": f"{w.roi:.1f}%",
            "total_trades": w.total_trades,
            "status": "Active" if w.is_active else "Paused",
        })
    return pd.DataFrame(rows)


async def _fetch_risk_events() -> pd.DataFrame:
    async with Database() as db:
        events = await db.get_recent_events(limit=50)
    if not events:
        return pd.DataFrame()
    rows = [
        {
            "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": e.event_type,
            "severity": e.severity,
            "message": e.message,
        }
        for e in events
    ]
    return pd.DataFrame(rows)


async def _fetch_market_options() -> list[dict]:
    async with Database() as db:
        trades = await db.get_open_trades()
    seen: dict[str, str] = {}
    for t in trades:
        if t.market_slug not in seen:
            seen[t.market_slug] = t.token_id
    return [{"label": slug, "value": token_id} for slug, token_id in seen.items()]


async def _fetch_price_history(token_id: str) -> pd.DataFrame:
    """Get price history from wallet_snapshots table as a proxy."""
    async with Database() as db:
        snapshots = await db.get_latest_snapshot(token_id)
    if not snapshots:
        return pd.DataFrame()
    rows = [{"timestamp": s.timestamp.isoformat(), "current_price": s.current_price} for s in snapshots]
    return pd.DataFrame(rows)


async def _fetch_active_markets_table() -> pd.DataFrame:
    async with Database() as db:
        trades = await db.get_open_trades()
        market_rows = {}
        for t in trades:
            if t.market_slug not in market_rows:
                mkt = await db.get_market_by_slug(t.market_slug)
                market_rows[t.market_slug] = {
                    "question": mkt.question if mkt else t.market_slug,
                    "yes_price": round(mkt.yes_price, 3) if mkt else "—",
                    "no_price": round(mkt.no_price, 3) if mkt else "—",
                    "volume": f"${mkt.volume:,.0f}" if mkt else "—",
                    "our_position": round(t.size, 2),
                    "unrealized_pnl": round(t.pnl, 4),
                }
    return pd.DataFrame(list(market_rows.values())) if market_rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Callback registration
# ---------------------------------------------------------------------------

def register_callbacks(app) -> None:
    """Register all callbacks on *app*.  Called from app.py after layout is set."""

    # ------------------------------------------------------------------
    # 1. Auto-refresh — Overview page
    # ------------------------------------------------------------------

    @app.callback(
        Output("card-total-pnl", "children"),
        Output("card-today-pnl", "children"),
        Output("card-win-rate", "children"),
        Output("card-exposure", "children"),
        Output("chart-equity-curve", "figure"),
        Output("chart-pnl-histogram", "figure"),
        Output("table-open-positions", "children"),
        Input("interval-refresh", "n_intervals"),
        prevent_initial_call=False,
    )
    def refresh_overview(n_intervals):
        summary = _run(_fetch_summary())
        equity_df = _run(_fetch_equity_curve())
        positions_df = _run(_fetch_open_positions())

        total_pnl = summary.get("total_pnl", 0.0)
        today_pnl = summary.get("today_pnl", 0.0)
        win_rate = summary.get("win_rate", 0.0)
        exposure = summary.get("total_exposure", 0.0)

        total_card = pnl_card("Total P&L", total_pnl)
        today_card = pnl_card("Today's P&L", today_pnl)
        wr_color = "success" if win_rate >= 0.55 else ("warning" if win_rate >= 0.45 else "danger")
        wr_card = stat_card("Win Rate", f"{win_rate * 100:.1f}%", color=wr_color, icon_class="bi bi-trophy")
        exp_color = "success" if exposure < settings.max_portfolio_exposure * 0.6 else (
            "warning" if exposure < settings.max_portfolio_exposure * 0.85 else "danger"
        )
        exp_card = stat_card(
            "Exposure",
            f"${exposure:.0f} / ${settings.max_portfolio_exposure:.0f}",
            color=exp_color,
            icon_class="bi bi-shield-check",
        )

        # All closed trades for histogram
        all_closed_df = _run(_fetch_trades("CLOSED", "all", "", None, None))

        pos_table = data_table(positions_df, table_id="tbl-positions")
        return (
            total_card.children,
            today_card.children,
            wr_card.children,
            exp_card.children,
            equity_curve(equity_df),
            pnl_histogram(all_closed_df),
            pos_table,
        )

    # ------------------------------------------------------------------
    # 2. Auto-refresh — Wallets page
    # ------------------------------------------------------------------

    @app.callback(
        Output("table-wallets", "children"),
        Input("interval-refresh", "n_intervals"),
        prevent_initial_call=False,
    )
    def refresh_wallets(n_intervals):
        df = _run(_fetch_wallets())
        from dashboard.pages.wallets import _WALLET_COLUMNS
        return data_table(df, columns=_WALLET_COLUMNS, table_id="tbl-wallets", row_selectable="single")

    # ------------------------------------------------------------------
    # 3. Wallet drill-down
    # ------------------------------------------------------------------

    @app.callback(
        Output("store-selected-wallet", "data"),
        Input("tbl-wallets", "selected_rows"),
        State("tbl-wallets", "data"),
        prevent_initial_call=True,
    )
    def select_wallet(selected_rows, table_data):
        if not selected_rows or not table_data:
            raise PreventUpdate
        row = table_data[selected_rows[0]]
        return row.get("address", "")

    @app.callback(
        Output("drilldown-title", "children"),
        Output("drilldown-positions", "children"),
        Input("store-selected-wallet", "data"),
        prevent_initial_call=True,
    )
    def update_drilldown(address_prefix):
        if not address_prefix:
            raise PreventUpdate

        async def _fetch():
            async with Database() as db:
                wallets = await db.get_all_wallets()
            for w in wallets:
                if w.address.startswith(address_prefix.rstrip("…")):
                    return w
            return None

        wallet = _run(_fetch())
        if wallet is None:
            return "Wallet Detail", "Wallet not found."

        info = [
            f"Address: {wallet.address}",
            f"Score: {wallet.score:.1f}  |  Win Rate: {wallet.win_rate*100:.1f}%  |  ROI: {wallet.roi:.1f}%",
            f"Lifetime P&L: ${wallet.lifetime_pnl:,.2f}  |  Trades: {wallet.total_trades}",
        ]
        from dash import html as _html
        return f"Wallet: {wallet.alias or wallet.address[:14]}…", _html.Div([
            _html.P(line, className="text-muted small mb-1") for line in info
        ])

    # ------------------------------------------------------------------
    # 4. Wallet add / remove
    # ------------------------------------------------------------------

    @app.callback(
        Output("wallet-action-feedback", "children"),
        Input("btn-add-wallet", "n_clicks"),
        Input("btn-remove-wallet", "n_clicks"),
        State("input-wallet-address", "value"),
        State("store-selected-wallet", "data"),
        prevent_initial_call=True,
    )
    def wallet_action(add_clicks, remove_clicks, add_address, selected_address):
        from dash import ctx
        triggered = ctx.triggered_id

        if triggered == "btn-add-wallet":
            if not add_address or len(add_address) < 10:
                return "Please enter a valid wallet address."
            # Minimal stub insert — full scoring handled by WalletScanner
            async def _add():
                from data.models import TrackedWallet
                async with Database() as db:
                    existing = await db.get_wallet(add_address)
                    if existing:
                        return "Wallet already tracked."
                    new_wallet = TrackedWallet(
                        address=add_address,
                        alias="",
                        lifetime_pnl=0.0,
                        win_rate=0.0,
                        roi=0.0,
                        total_trades=0,
                        score=0.0,
                        is_active=True,
                        last_scanned=datetime.now(timezone.utc),
                        estimated_bankroll=0.0,
                    )
                    await db.upsert_wallet(new_wallet)
                    return f"Added {add_address[:14]}… to tracked wallets."
            return _run(_add())

        if triggered == "btn-remove-wallet":
            if not selected_address:
                return "Select a wallet row first."
            async def _remove():
                async with Database() as db:
                    wallets = await db.get_all_wallets()
                    prefix = selected_address.rstrip("…")
                    for w in wallets:
                        if w.address.startswith(prefix):
                            await db.deactivate_wallet(w.address)
                            return f"Deactivated {w.address[:14]}…"
                    return "Wallet not found."
            return _run(_remove())

        return no_update

    # ------------------------------------------------------------------
    # 5. Auto-refresh — Trades page
    # ------------------------------------------------------------------

    @app.callback(
        Output("table-trades", "children"),
        Output("chart-trade-pnl-bar", "figure"),
        Input("interval-refresh", "n_intervals"),
        Input("filter-trade-status", "value"),
        Input("filter-pnl-sign", "value"),
        Input("filter-trade-wallet", "value"),
        Input("filter-date-range", "start_date"),
        Input("filter-date-range", "end_date"),
        prevent_initial_call=False,
    )
    def refresh_trades(n_intervals, status, pnl_sign, wallet, start_date, end_date):
        from dashboard.pages.trades import _TRADE_COLUMNS
        df = _run(_fetch_trades(
            status_filter=status or "all",
            pnl_filter=pnl_sign or "all",
            wallet_filter=wallet or "",
            start_date=start_date,
            end_date=end_date,
        ))
        table = data_table(df, columns=_TRADE_COLUMNS, table_id="tbl-trades", filterable=True)
        chart = pnl_bar_chart(df[["market_slug", "pnl"]].copy() if not df.empty else pd.DataFrame())
        return table, chart

    # ------------------------------------------------------------------
    # 6. Markets page — table + dropdown population
    # ------------------------------------------------------------------

    @app.callback(
        Output("table-markets", "children"),
        Output("dropdown-market-select", "options"),
        Input("interval-refresh", "n_intervals"),
        prevent_initial_call=False,
    )
    def refresh_markets(n_intervals):
        from dashboard.pages.markets import _MARKET_COLUMNS
        df = _run(_fetch_active_markets_table())
        options = _run(_fetch_market_options())
        table = data_table(df, columns=_MARKET_COLUMNS, table_id="tbl-markets")
        return table, options

    @app.callback(
        Output("chart-market-price", "figure"),
        Input("dropdown-market-select", "value"),
        prevent_initial_call=True,
    )
    def update_price_chart(token_id):
        if not token_id:
            raise PreventUpdate
        df = _run(_fetch_price_history(token_id))
        return price_chart(df, market_slug=token_id[:20])

    # ------------------------------------------------------------------
    # 7. Risk page — gauges + system health + event log
    # ------------------------------------------------------------------

    @app.callback(
        Output("gauge-exposure", "figure"),
        Output("gauge-daily-pnl", "figure"),
        Output("badge-bot-status", "children"),
        Output("badge-bot-status", "color"),
        Output("badge-vpn-status", "children"),
        Output("badge-vpn-status", "color"),
        Output("badge-feed-status", "children"),
        Output("badge-feed-status", "color"),
        Output("table-risk-events", "children"),
        Input("interval-refresh", "n_intervals"),
        prevent_initial_call=False,
    )
    def refresh_risk(n_intervals):
        summary = _run(_fetch_summary())
        exposure = summary.get("total_exposure", 0.0)
        today_pnl = summary.get("today_pnl", 0.0)

        events_df = _run(_fetch_risk_events())

        # VPN check (synchronous)
        vpn_ok = check_vpn()
        vpn_text = "Connected" if vpn_ok else "Disconnected"
        vpn_color = "success" if vpn_ok else "danger"

        from dashboard.pages.risk import _EVENT_COLUMNS
        events_table = data_table(events_df, columns=_EVENT_COLUMNS, table_id="tbl-risk-events", page_size=10)

        return (
            exposure_gauge(exposure, settings.max_portfolio_exposure),
            daily_pnl_gauge(today_pnl, settings.max_daily_loss),
            "Running", "success",
            vpn_text, vpn_color,
            "Live", "success",
            events_table,
        )
