"""
dashboard/pages/wallets.py — Tracked Whale Wallets page layout.

Contains:
  • Wallet scorecard table (click for drill-down)
  • Per-wallet detail panel (positions, recent trade signals, P&L)
  • Add wallet input + Remove button
  • Auto-discovery trigger button
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.components.tables import data_table
import pandas as pd

_WALLET_COLUMNS = [
    {"name": "Address", "id": "address"},
    {"name": "Alias", "id": "alias"},
    {"name": "Score", "id": "score"},
    {"name": "Lifetime P&L", "id": "lifetime_pnl"},
    {"name": "Win Rate", "id": "win_rate"},
    {"name": "ROI %", "id": "roi"},
    {"name": "Trades", "id": "total_trades"},
    {"name": "Status", "id": "status"},
]


def layout() -> html.Div:
    return html.Div([
        html.H4("Tracked Wallets", className="mb-3 text-light"),

        # --- Controls ---
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.Input(id="input-wallet-address", placeholder="0x… wallet address", type="text"),
                    dbc.Button("Add Wallet", id="btn-add-wallet", color="primary", n_clicks=0),
                    dbc.Button("Remove Selected", id="btn-remove-wallet", color="danger", outline=True, n_clicks=0),
                ]),
                html.Div(id="wallet-action-feedback", className="text-muted small mt-1"),
            ], md=8),
            dbc.Col([
                dbc.Button(
                    [html.I(className="bi bi-search me-1"), "Auto-Discover Wallets"],
                    id="btn-discover-wallets",
                    color="secondary",
                    outline=True,
                    n_clicks=0,
                    className="w-100",
                ),
                dbc.Spinner(html.Div(id="discover-status", className="text-muted small mt-1"), size="sm"),
            ], md=4),
        ], className="mb-3 g-2"),

        # --- Wallet scorecard table ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Wallet Scoreboard", className="text-muted small fw-bold"),
                dbc.CardBody(html.Div(id="table-wallets",
                    children=data_table(pd.DataFrame(), columns=_WALLET_COLUMNS, table_id="tbl-wallets", row_selectable="single"))),
            ], className="border-0 shadow-sm"), className="mb-3"),
        ]),

        # --- Drill-down panel (hidden until row selected) ---
        html.Div(id="wallet-drilldown", children=[
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader(html.Span(id="drilldown-title", children="Wallet Detail"), className="text-muted small fw-bold"),
                    dbc.CardBody([
                        html.P("Select a wallet row above to see detail.", className="text-muted", id="drilldown-placeholder"),
                        html.Div(id="drilldown-positions"),
                    ]),
                ], className="border-0 shadow-sm")),
            ]),
        ]),

        # Store for selected wallet
        dcc.Store(id="store-selected-wallet"),
    ], className="p-3")
