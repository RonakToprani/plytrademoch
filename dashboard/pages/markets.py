"""
dashboard/pages/markets.py — Active Markets page layout.

Contains:
  • Active markets table (markets we currently hold positions in)
  • Market price chart (select from dropdown)
  • Market search box (queries Gamma API cache)
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.components.charts import price_chart
from dashboard.components.tables import data_table
import pandas as pd

_MARKET_COLUMNS = [
    {"name": "Market", "id": "question"},
    {"name": "YES Price", "id": "yes_price"},
    {"name": "NO Price", "id": "no_price"},
    {"name": "Volume", "id": "volume"},
    {"name": "Our Position", "id": "our_position"},
    {"name": "Unrealized P&L", "id": "unrealized_pnl"},
]


def layout() -> html.Div:
    return html.Div([
        html.H4("Markets", className="mb-3 text-light"),

        # --- Active markets table ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Active Positions", className="text-muted small fw-bold"),
                dbc.CardBody(html.Div(id="table-markets",
                    children=data_table(pd.DataFrame(), columns=_MARKET_COLUMNS, table_id="tbl-markets"))),
            ], className="border-0 shadow-sm"), className="mb-3"),
        ]),

        # --- Price chart ---
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        html.Label("Select Market", className="text-muted small"),
                        dcc.Dropdown(
                            id="dropdown-market-select",
                            placeholder="Choose a market…",
                            className="dash-dark-dropdown",
                            style={"backgroundColor": "#262b3d", "color": "#e9ecef"},
                        ),
                    ], md=6),
                    dbc.Col([
                        html.Label("Search Markets", className="text-muted small"),
                        dbc.InputGroup([
                            dbc.Input(id="input-market-search", placeholder="Keywords…", type="text"),
                            dbc.Button("Search", id="btn-market-search", color="secondary", outline=True, n_clicks=0),
                        ]),
                    ], md=6),
                ], className="g-2 mb-2 align-items-end"),

                dbc.Card([
                    dbc.CardHeader("Price History", className="text-muted small fw-bold"),
                    dbc.CardBody(dcc.Graph(id="chart-market-price", figure=price_chart(pd.DataFrame()), config={"displayModeBar": False})),
                ], className="border-0 shadow-sm"),
            ]),
        ]),

        # Store for market search results
        dcc.Store(id="store-market-search"),
    ], className="p-3")
