"""
dashboard/pages/trades.py — Trade Log page layout.

Contains:
  • Filters: date range, wallet, market, status, P&L sign
  • Full trade history DataTable
  • Trade P&L bar chart
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.components.charts import pnl_bar_chart
from dashboard.components.tables import data_table
import pandas as pd

_TRADE_COLUMNS = [
    {"name": "Time", "id": "created_at"},
    {"name": "Market", "id": "market_slug"},
    {"name": "Side", "id": "side"},
    {"name": "Size", "id": "size"},
    {"name": "Entry", "id": "entry_price"},
    {"name": "Current", "id": "current_price"},
    {"name": "P&L", "id": "pnl"},
    {"name": "Status", "id": "status"},
    {"name": "Source Wallet", "id": "source_wallet"},
]

_STATUS_OPTIONS = [
    {"label": "All", "value": "all"},
    {"label": "Open", "value": "open"},
    {"label": "Closed", "value": "CLOSED"},
    {"label": "Pending", "value": "PENDING"},
    {"label": "Failed", "value": "FAILED"},
]

_PNL_OPTIONS = [
    {"label": "All", "value": "all"},
    {"label": "Winners", "value": "winners"},
    {"label": "Losers", "value": "losers"},
]


def layout() -> html.Div:
    return html.Div([
        html.H4("Trade Log", className="mb-3 text-light"),

        # --- Filters ---
        dbc.Row([
            dbc.Col([
                html.Label("Date Range", className="text-muted small"),
                dcc.DatePickerRange(
                    id="filter-date-range",
                    display_format="YYYY-MM-DD",
                    className="w-100",
                ),
            ], md=4, className="mb-2"),
            dbc.Col([
                html.Label("Status", className="text-muted small"),
                dbc.Select(id="filter-trade-status", options=_STATUS_OPTIONS, value="all"),
            ], md=2, className="mb-2"),
            dbc.Col([
                html.Label("P&L Filter", className="text-muted small"),
                dbc.Select(id="filter-pnl-sign", options=_PNL_OPTIONS, value="all"),
            ], md=2, className="mb-2"),
            dbc.Col([
                html.Label("Wallet", className="text-muted small"),
                dbc.Input(id="filter-trade-wallet", placeholder="0x… or blank for all", type="text"),
            ], md=4, className="mb-2"),
        ], className="g-2 mb-3 align-items-end"),

        # --- P&L bar chart ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Trade P&L (chronological)", className="text-muted small fw-bold"),
                dbc.CardBody(dcc.Graph(id="chart-trade-pnl-bar", figure=pnl_bar_chart(pd.DataFrame()), config={"displayModeBar": False})),
            ], className="border-0 shadow-sm"), className="mb-3"),
        ]),

        # --- Trade log table ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("All Trades", className="text-muted small fw-bold"),
                dbc.CardBody(html.Div(id="table-trades",
                    children=data_table(pd.DataFrame(), columns=_TRADE_COLUMNS, table_id="tbl-trades", filterable=True))),
            ], className="border-0 shadow-sm")),
        ]),
    ], className="p-3")
