"""
dashboard/app.py — Dash app factory and multi-page layout.

Creates a dark-themed (Darkly Bootstrap) multi-page Dash app with:
  • Sidebar navigation
  • dcc.Interval auto-refresh every DASHBOARD_REFRESH_SECONDS
  • dcc.Location for client-side routing between pages
  • All 5 pages: Overview, Wallets, Trades, Markets, Risk

Entry point:
    from dashboard.app import create_app
    app = create_app()
    app.run(host="0.0.0.0", port=settings.dashboard_port, debug=False)

Running on a separate thread in main.py::
    import threading
    t = threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 8050}, daemon=True)
    t.start()
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from config.settings import settings
from dashboard import callbacks as _callbacks
from dashboard.pages import markets, overview, risk, trades, wallets

# ---------------------------------------------------------------------------
# Sidebar navigation items
# ---------------------------------------------------------------------------

_NAV_ITEMS = [
    ("/", "bi bi-speedometer2", "Overview"),
    ("/wallets", "bi bi-people", "Wallets"),
    ("/trades", "bi bi-list-ul", "Trades"),
    ("/markets", "bi bi-bar-chart-line", "Markets"),
    ("/risk", "bi bi-shield-exclamation", "Risk"),
]


def _nav_link(href: str, icon: str, label: str) -> dbc.NavLink:
    return dbc.NavLink(
        [html.I(className=f"{icon} me-2"), label],
        href=href,
        active="exact",
        className="nav-item-link",
    )


# ---------------------------------------------------------------------------
# Layout builder
# ---------------------------------------------------------------------------

def _build_layout() -> html.Div:
    sidebar = html.Div([
        html.Div([
            html.I(className="bi bi-robot me-2 text-primary"),
            html.Span("CopyBot", className="fw-bold text-light fs-5"),
        ], className="d-flex align-items-center p-3 border-bottom border-secondary"),

        dbc.Nav(
            [_nav_link(href, icon, label) for href, icon, label in _NAV_ITEMS],
            vertical=True,
            pills=True,
            className="flex-column px-2 pt-2",
        ),

        # DRY_RUN badge at the bottom of sidebar
        html.Div(
            dbc.Badge("PAPER TRADING" if settings.dry_run else "LIVE", color="warning" if settings.dry_run else "success", className="w-100 text-center"),
            className="p-3 mt-auto",
        ),
    ], style={
        "width": "220px",
        "minHeight": "100vh",
        "backgroundColor": "#161b2e",
        "display": "flex",
        "flexDirection": "column",
        "borderRight": "1px solid #2e3347",
        "flexShrink": "0",
    })

    content = html.Div([
        dcc.Location(id="url", refresh=False),
        dcc.Interval(
            id="interval-refresh",
            interval=settings.dashboard_refresh_seconds * 1000,
            n_intervals=0,
        ),
        html.Div(id="page-content"),
    ], style={"flex": "1", "overflowY": "auto", "backgroundColor": "#1e2130"})

    return html.Div(
        [sidebar, content],
        style={"display": "flex", "minHeight": "100vh", "fontFamily": "Inter, sans-serif"},
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> dash.Dash:
    """
    Build and return the configured Dash application.

    Registers all callbacks and sets the root layout.
    Call app.run(...) to start the server.
    """
    app = dash.Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.DARKLY,
            dbc.icons.BOOTSTRAP,
        ],
        suppress_callback_exceptions=True,
        title="CopyBot Dashboard",
        update_title=None,
    )

    app.layout = _build_layout()

    # Page routing
    @app.callback(Output("page-content", "children"), Input("url", "pathname"))
    def render_page(pathname: str):
        if pathname in ("/", ""):
            return overview.layout()
        if pathname == "/wallets":
            return wallets.layout()
        if pathname == "/trades":
            return trades.layout()
        if pathname == "/markets":
            return markets.layout()
        if pathname == "/risk":
            return risk.layout()
        return html.Div([
            html.H3("404 — Page not found", className="text-danger p-4"),
            dbc.Button("Back to Overview", href="/", color="primary"),
        ], className="p-4")

    # Register all data callbacks
    _callbacks.register_callbacks(app)

    return app
