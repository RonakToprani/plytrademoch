"""
paper/dashboard.py — One-page monitor for the underdog paper strategy.

Everything at a glance: running P&L vs the backtest expectation, the open book,
and settled results. Reads paper_underdog.db live and auto-refreshes. Launch with
`python -m paper.run dashboard` → http://localhost:8060.
"""

from __future__ import annotations

from datetime import datetime, timezone

import dash
from dash import Input, Output, dash_table, dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from paper.store import PaperStore

# palette
_BG = "#0e1117"
_CARD = "#161b22"
_GREEN = "#3fb950"
_RED = "#f85149"
_MUTED = "#8b949e"
_ACCENT = "#58a6ff"
_REFRESH_MS = 30_000


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "never"
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return iso


def _stat_card(title: str, value: str, sub: str = "", color: str = "#e6edf3") -> dbc.Col:
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.Div(title, style={"color": _MUTED, "fontSize": "0.75rem",
                               "textTransform": "uppercase", "letterSpacing": "0.05em"}),
        html.Div(value, style={"color": color, "fontSize": "1.8rem", "fontWeight": 700,
                               "lineHeight": "1.2"}),
        html.Div(sub, style={"color": _MUTED, "fontSize": "0.75rem"}),
    ]), style={"backgroundColor": _CARD, "border": "1px solid #30363d",
               "borderRadius": "10px", "height": "100%"}), md=2, xs=6, className="mb-3")


def _pnl_figure(store: PaperStore) -> go.Figure:
    settled = [b for b in store.all_bets(limit=5000)
               if b.status in ("WON", "LOST", "VOID") and b.settled_at]
    settled.sort(key=lambda b: b.settled_at)
    xs, ys, cum = [], [], 0.0
    for b in settled:
        cum += (b.pnl or 0.0)
        xs.append(_fmt_dt(b.settled_at))
        ys.append(round(cum, 2))
    fig = go.Figure()
    if xs:
        line_color = _GREEN if ys[-1] >= 0 else _RED
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers",
                                 line={"color": line_color, "width": 2},
                                 marker={"size": 5}, name="Cumulative P&L"))
        fig.add_hline(y=0, line={"color": _MUTED, "width": 1, "dash": "dot"})
    else:
        fig.add_annotation(text="No settled bets yet — P&L appears as markets resolve",
                           showarrow=False, font={"color": _MUTED, "size": 14})
    fig.update_layout(
        paper_bgcolor=_CARD, plot_bgcolor=_CARD, margin={"l": 40, "r": 20, "t": 10, "b": 40},
        height=280, font={"color": "#e6edf3"}, showlegend=False,
        xaxis={"gridcolor": "#21262d", "showgrid": False},
        yaxis={"gridcolor": "#21262d", "title": "Cumulative realized P&L ($)"},
    )
    return fig


def _table(rows: list[dict], columns: list[dict]) -> dash_table.DataTable:
    return dash_table.DataTable(
        data=rows, columns=columns, page_size=15,
        style_as_list_view=True,
        style_header={"backgroundColor": _CARD, "color": _MUTED, "border": "none",
                      "fontWeight": 600, "textTransform": "uppercase", "fontSize": "0.7rem"},
        style_cell={"backgroundColor": _BG, "color": "#e6edf3", "border": "none",
                    "fontSize": "0.85rem", "padding": "8px 10px", "textAlign": "left",
                    "fontFamily": "ui-monospace, monospace"},
        style_data_conditional=[
            {"if": {"filter_query": "{result} = WON"}, "color": _GREEN},
            {"if": {"filter_query": "{result} = LOST"}, "color": _RED},
        ],
    )


def create_app() -> dash.Dash:
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY],
                    title="Underdog Paper Monitor")

    app.layout = dbc.Container([
        dcc.Interval(id="tick", interval=_REFRESH_MS, n_intervals=0),
        html.Div([
            html.H3("🎯 Underdog Paper Trading",
                    style={"color": "#e6edf3", "fontWeight": 700, "display": "inline-block"}),
            html.Span(id="subtitle", style={"color": _MUTED, "marginLeft": "1rem"}),
        ], className="my-3"),
        dbc.Row(id="cards"),
        dbc.Card(dbc.CardBody([
            html.Div("Cumulative realized P&L", style={"color": _MUTED, "fontSize": "0.8rem"}),
            dcc.Graph(id="pnl", config={"displayModeBar": False}),
        ]), style={"backgroundColor": _CARD, "border": "1px solid #30363d",
                   "borderRadius": "10px"}, className="mb-3"),
        dbc.Row([
            dbc.Col([html.H6("Open positions", style={"color": _MUTED}),
                     html.Div(id="open-table")], md=6),
            dbc.Col([html.H6("Recently settled", style={"color": _MUTED}),
                     html.Div(id="settled-table")], md=6),
        ]),
    ], fluid=True, style={"backgroundColor": _BG, "minHeight": "100vh", "padding": "1rem 2rem"})

    @app.callback(
        [Output("cards", "children"), Output("pnl", "figure"),
         Output("open-table", "children"), Output("settled-table", "children"),
         Output("subtitle", "children")],
        Input("tick", "n_intervals"),
    )
    def _refresh(_n):
        store = PaperStore()
        try:
            s = store.stats()
            pnl_color = _GREEN if s["realized_pnl"] >= 0 else _RED
            wr_color = _GREEN if s["win_rate"] >= 0.20 else _RED if s["settled"] else "#e6edf3"
            roi_color = _GREEN if s["roi"] > 0 else _RED if s["settled"] else "#e6edf3"
            cards = [
                _stat_card("Open bets", str(s["open"]), f"${s['open_stake']:.0f} exposure"),
                _stat_card("Settled", str(s["settled"]), f"{s['won']}W / {s['lost']}L"),
                _stat_card("Realized P&L", f"${s['realized_pnl']:.2f}",
                           f"on ${s['settled_stake']:.0f} staked", pnl_color),
                _stat_card("Win rate", f"{s['win_rate']*100:.0f}%", "exp ~27%", wr_color),
                _stat_card("ROI", f"{s['roi']*100:+.0f}%", "exp +50–70%", roi_color),
                _stat_card("Total bets", str(s["total"]), "all-time"),
            ]
            open_rows = [{
                "market": (b.question or b.slug)[:46], "side": b.outcome,
                "entry": f"{b.entry_price:.3f}", "stake": f"${b.stake_usd:.2f}",
            } for b in store.open_bets()]
            open_tbl = _table(open_rows, [
                {"name": "Market", "id": "market"}, {"name": "Side", "id": "side"},
                {"name": "Entry", "id": "entry"}, {"name": "Stake", "id": "stake"}])
            settled = [b for b in store.all_bets(limit=200)
                       if b.status in ("WON", "LOST", "VOID")]
            settled_rows = [{
                "market": (b.question or b.slug)[:40], "result": b.status,
                "pnl": f"{'+' if (b.pnl or 0) >= 0 else ''}${b.pnl:.2f}",
            } for b in settled]
            settled_tbl = _table(settled_rows, [
                {"name": "Market", "id": "market"}, {"name": "Result", "id": "result"},
                {"name": "P&L", "id": "pnl"}])
            subtitle = (f"updated {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC  ·  "
                        f"last scan {_fmt_dt(store.last_scan())}  ·  DRY-RUN")
            return cards, _pnl_figure(store), open_tbl, settled_tbl, subtitle
        finally:
            store.close()

    return app
