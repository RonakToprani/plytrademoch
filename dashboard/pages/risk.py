"""
dashboard/pages/risk.py — Risk Dashboard page layout.

Contains:
  • Exposure gauge (current vs MAX_PORTFOLIO_EXPOSURE)
  • Daily P&L gauge (today vs MAX_DAILY_LOSS)
  • System health indicators (bot status, VPN, feed freshness, rate limit, balance)
  • Risk event log table
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from config.settings import settings
from dashboard.components.charts import daily_pnl_gauge, exposure_gauge
from dashboard.components.tables import data_table
import pandas as pd

_EVENT_COLUMNS = [
    {"name": "Time", "id": "created_at"},
    {"name": "Type", "id": "event_type"},
    {"name": "Severity", "id": "severity"},
    {"name": "Message", "id": "message"},
]


def _health_row(label: str, value: str, badge_color: str, row_id: str) -> dbc.Row:
    return dbc.Row([
        dbc.Col(html.Span(label, className="text-muted small"), width=6),
        dbc.Col(dbc.Badge(value, color=badge_color, id=row_id, className="w-100 text-center"), width=6),
    ], className="mb-2 align-items-center")


def layout() -> html.Div:
    return html.Div([
        html.H4("Risk Dashboard", className="mb-3 text-light"),

        # --- Gauges ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Portfolio Exposure", className="text-muted small fw-bold"),
                dbc.CardBody(dcc.Graph(
                    id="gauge-exposure",
                    figure=exposure_gauge(0, settings.max_portfolio_exposure),
                    config={"displayModeBar": False},
                    style={"height": "220px"},
                )),
            ], className="border-0 shadow-sm"), md=6, className="mb-3"),

            dbc.Col(dbc.Card([
                dbc.CardHeader("Today's P&L vs Limit", className="text-muted small fw-bold"),
                dbc.CardBody(dcc.Graph(
                    id="gauge-daily-pnl",
                    figure=daily_pnl_gauge(0, settings.max_daily_loss),
                    config={"displayModeBar": False},
                    style={"height": "220px"},
                )),
            ], className="border-0 shadow-sm"), md=6, className="mb-3"),
        ]),

        # --- System health ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("System Health", className="text-muted small fw-bold"),
                dbc.CardBody([
                    _health_row("Bot Status", "Unknown", "secondary", "badge-bot-status"),
                    _health_row("VPN (tun0)", "Unknown", "secondary", "badge-vpn-status"),
                    _health_row("Data Feed", "Unknown", "secondary", "badge-feed-status"),
                    _health_row("Wallet Balance", "$0.00 USDC", "secondary", "badge-balance"),
                    _health_row("Open Orders", "0", "secondary", "badge-open-orders"),
                    html.Hr(className="border-secondary my-2"),
                    html.Div([
                        html.Span("Max Daily Loss: ", className="text-muted small"),
                        html.Span(f"${settings.max_daily_loss:.2f}", className="text-warning small fw-bold"),
                        html.Span(" | Max Exposure: ", className="text-muted small ms-2"),
                        html.Span(f"${settings.max_portfolio_exposure:.2f}", className="text-warning small fw-bold"),
                    ]),
                ]),
            ], className="border-0 shadow-sm"), md=4, className="mb-3"),

            # --- Risk event log ---
            dbc.Col(dbc.Card([
                dbc.CardHeader("Risk Event Log", className="text-muted small fw-bold"),
                dbc.CardBody(html.Div(id="table-risk-events",
                    children=data_table(pd.DataFrame(), columns=_EVENT_COLUMNS, table_id="tbl-risk-events", page_size=10))),
            ], className="border-0 shadow-sm"), md=8, className="mb-3"),
        ]),
    ], className="p-3")
