"""
dashboard/pages/overview.py — Portfolio Overview page layout.

Contains:
  • 4 stat cards: Total P&L, Today's P&L, Win Rate, Exposure
  • Equity curve chart
  • Current open positions table
  • P&L distribution histogram
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.components.cards import stat_card
from dashboard.components.charts import equity_curve, pnl_histogram
from dashboard.components.tables import data_table

import pandas as pd


def layout() -> html.Div:
    """Return the Overview page layout (static shell; callbacks fill in data)."""
    return html.Div([
        html.H4("Portfolio Overview", className="mb-3 text-light"),

        # --- Stat cards row ---
        dbc.Row([
            dbc.Col(stat_card("Total P&L", "$0.00", color="secondary", icon_class="bi bi-currency-dollar", card_id="card-total-pnl"), md=3, className="mb-3"),
            dbc.Col(stat_card("Today's P&L", "$0.00", color="secondary", icon_class="bi bi-calendar-day", card_id="card-today-pnl"), md=3, className="mb-3"),
            dbc.Col(stat_card("Win Rate", "0.0%", color="secondary", icon_class="bi bi-trophy", card_id="card-win-rate"), md=3, className="mb-3"),
            dbc.Col(stat_card("Exposure", "$0 / $150", color="secondary", icon_class="bi bi-shield-check", card_id="card-exposure"), md=3, className="mb-3"),
        ], className="g-3"),

        # --- Equity curve ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Equity Curve", className="text-muted small fw-bold"),
                dbc.CardBody(dcc.Graph(id="chart-equity-curve", figure=equity_curve(pd.DataFrame()), config={"displayModeBar": False})),
            ], className="border-0 shadow-sm"), md=8, className="mb-3"),

            # P&L distribution
            dbc.Col(dbc.Card([
                dbc.CardHeader("P&L Distribution", className="text-muted small fw-bold"),
                dbc.CardBody(dcc.Graph(id="chart-pnl-histogram", figure=pnl_histogram(pd.DataFrame()), config={"displayModeBar": False})),
            ], className="border-0 shadow-sm"), md=4, className="mb-3"),
        ]),

        # --- Open positions table ---
        dbc.Row([
            dbc.Col(dbc.Card([
                dbc.CardHeader("Open Positions", className="text-muted small fw-bold"),
                dbc.CardBody(html.Div(id="table-open-positions", children=data_table(pd.DataFrame(), table_id="tbl-positions"))),
            ], className="border-0 shadow-sm"), className="mb-3"),
        ]),
    ], className="p-3")
