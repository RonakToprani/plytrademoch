"""
paper/dashboard.py — POLY TRADING, one-page monitor for the underdog strategy.

Terminal aesthetic: pure black, monospace, all-caps labels, big values, green with
purple/amber accents. Reads paper_underdog.db live, auto-refreshes. Launch with
`python -m paper.run dashboard` → http://<lan-ip>:8060.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import dash
import httpx
from dash import Input, Output, dcc, html
import plotly.graph_objects as go

from paper.store import PaperStore

# Keep in sync with PaperTrader(bankroll=...) and the --bankroll in
# deploy/com.underdog.cycle.plist, or the "% deployed" gauge lies.
BANKROLL = float(os.environ.get("POLY_BANKROLL", "1000"))
_REFRESH_MS = 30_000

_CLOB = "https://clob.polymarket.com"
_MARK_TTL = 25.0          # seconds — just under the refresh interval
_mark_cache: dict[str, object] = {"ts": 0.0, "px": {}}


def _marks(token_ids: list[str]) -> dict[str, float]:
    """
    Best bid ("SELL" side = what the position could be exited at) per token, via
    one batched CLOB call. TTL-cached so a browser refresh storm can't hammer the
    API. Returns {} on any failure — marks are a display nicety, never a reason
    for the page to error out.
    """
    if not token_ids:
        return {}
    now = time.monotonic()
    cached = _mark_cache["px"]
    if isinstance(cached, dict) and now - float(_mark_cache["ts"]) < _MARK_TTL \
            and all(t in cached for t in token_ids):
        return cached  # type: ignore[return-value]
    try:
        r = httpx.post(f"{_CLOB}/prices",
                       json=[{"token_id": t, "side": "SELL"} for t in token_ids],
                       timeout=8.0)
        r.raise_for_status()
        px = {}
        for tok, sides in (r.json() or {}).items():
            try:
                px[tok] = float(sides["SELL"])
            except (KeyError, TypeError, ValueError):
                continue
    except (httpx.HTTPError, ValueError):
        return cached if isinstance(cached, dict) else {}  # type: ignore[return-value]
    _mark_cache["ts"], _mark_cache["px"] = now, px
    return px

# palette (from the reference aesthetic)
BLACK = "#000000"
PANEL = "#0b0b0c"
LINE = "#1c1c1e"
WHITE = "#f4f4f5"
MUTED = "#6b6b70"
GREEN = "#4ade80"
RED = "#f87171"
AMBER = "#fbbf24"
PURPLE = "#c084fc"
MONO = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, monospace"


def _c(v: float, zero: str = WHITE) -> str:
    return GREEN if v > 0 else RED if v < 0 else zero


def _label(text: str, color: str = MUTED):
    return html.Div(text, style={
        "color": color, "fontSize": "0.68rem", "letterSpacing": "0.22em",
        "textTransform": "uppercase", "fontWeight": 500, "marginBottom": "0.35rem"})


def _value(text: str, color: str = WHITE, size: str = "1.9rem"):
    return html.Div(text, style={
        "color": color, "fontSize": size, "fontWeight": 700, "lineHeight": "1.1",
        "letterSpacing": "-0.01em"})


def _cell(children, pad="1.1rem 1.3rem", grow=True):
    return html.Div(children, style={
        "backgroundColor": BLACK, "padding": pad,
        "flex": "1 1 0" if grow else "0 0 auto"})


def _grid(cells, cols, min_px=210):
    # auto-fit + minmax = responsive: N-across on desktop, wraps/stacks on phone.
    return html.Div(cells, style={
        "display": "grid",
        "gridTemplateColumns": f"repeat(auto-fit, minmax({min_px}px, 1fr))",
        "gap": "1px", "backgroundColor": LINE, "border": f"1px solid {LINE}",
        "borderRadius": "12px", "overflow": "hidden", "marginBottom": "10px"})


def _kv(label, value, vcolor=WHITE):
    return html.Div([
        html.Span(label, style={"color": MUTED, "fontSize": "0.72rem",
                                "letterSpacing": "0.12em", "textTransform": "uppercase"}),
        html.Span(value, style={"color": vcolor, "fontSize": "0.9rem", "fontWeight": 700,
                                "float": "right"}),
    ], style={"marginTop": "0.5rem", "overflow": "hidden"})


def _progress(pct: float, color: str = GREEN):
    pct = max(0.0, min(1.0, pct))
    return html.Div(html.Div(style={
        "width": f"{pct*100:.1f}%", "height": "8px", "backgroundColor": color,
        "borderRadius": "6px"}), style={
        "width": "100%", "height": "8px", "backgroundColor": "#161618",
        "borderRadius": "6px", "marginTop": "0.9rem"})


def _panel(dot, title, sub, big, big_color, rows):
    return _cell([
        html.Div([
            html.Span("●", style={"color": dot, "fontSize": "0.7rem", "marginRight": "0.5rem"}),
            html.Span(title, style={"color": WHITE, "fontSize": "0.72rem",
                                    "letterSpacing": "0.18em", "textTransform": "uppercase",
                                    "fontWeight": 600}),
        ]),
        html.Div(sub, style={"color": MUTED, "fontSize": "0.68rem",
                             "letterSpacing": "0.12em", "textTransform": "uppercase",
                             "margin": "0.25rem 0 0.7rem"}),
        _value(big, big_color, "2.5rem"),
        html.Div(rows, style={"marginTop": "0.8rem"}),
    ], pad="1.2rem 1.3rem")


def _pnl_figure(store: PaperStore) -> go.Figure:
    settled = [b for b in store.all_bets(limit=5000)
               if b.status in ("WON", "LOST", "VOID") and b.settled_at]
    settled.sort(key=lambda b: b.settled_at)
    xs, ys, cum = [], [], 0.0
    for b in settled:
        cum += (b.pnl or 0.0)
        xs.append(b.settled_at)
        ys.append(round(cum, 2))
    fig = go.Figure()
    if xs:
        col = GREEN if ys[-1] >= 0 else RED
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line={"color": col, "width": 2},
                                 fill="tozeroy", fillcolor="rgba(74,222,128,0.07)"))
        fig.add_hline(y=0, line={"color": LINE, "width": 1})
    else:
        fig.add_annotation(text="NO SETTLED BETS YET — P&L PLOTS AS MARKETS RESOLVE",
                           showarrow=False, font={"color": MUTED, "size": 12, "family": MONO})
    fig.update_layout(
        paper_bgcolor=BLACK, plot_bgcolor=BLACK, height=200,
        margin={"l": 44, "r": 16, "t": 10, "b": 24}, showlegend=False,
        font={"color": MUTED, "family": MONO, "size": 10},
        xaxis={"showgrid": False, "showticklabels": False},
        yaxis={"gridcolor": "#141416", "zeroline": False, "tickprefix": "$"})
    return fig


def _bet_row(cells):
    return html.Div([
        html.Span(t, style={"color": c, "fontSize": "0.8rem", "flex": f["flex"],
                            "textAlign": f.get("align", "left"),
                            "whiteSpace": "nowrap", "overflow": "hidden",
                            "textOverflow": "ellipsis", "paddingRight": "0.6rem"})
        for t, c, f in cells
    ], style={"display": "flex", "padding": "0.4rem 0", "borderBottom": f"1px solid {LINE}"})


def _table(title, header, rows):
    return _cell([
        _label(title),
        _bet_row([(h, MUTED, f) for h, f in header]),
        html.Div(rows if rows else [html.Div("—", style={"color": MUTED, "padding": "0.6rem 0",
                                                         "fontSize": "0.8rem"})]),
    ])


def create_app() -> dash.Dash:
    app = dash.Dash(__name__, title="POLY TRADING",
                    meta_tags=[{"name": "viewport",
                                "content": "width=device-width, initial-scale=1, "
                                           "maximum-scale=1"}])
    # Kill the default white body margin/background (the "white border") and make
    # the whole page black edge-to-edge on every device.
    app.index_string = """<!DOCTYPE html>
<html>
<head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
  html, body { margin:0; padding:0; background:#000; }
  * { box-sizing:border-box; }
  ::-webkit-scrollbar { width:8px; height:8px; }
  ::-webkit-scrollbar-thumb { background:#26262a; border-radius:4px; }
  ::-webkit-scrollbar-track { background:#000; }
</style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>"""
    app.layout = html.Div([
        dcc.Interval(id="tick", interval=_REFRESH_MS, n_intervals=0),
        html.Div([
            html.Span("POLY TRADING", style={"color": WHITE, "fontSize": "2.2rem",
                     "fontWeight": 800, "letterSpacing": "0.3em"}),
            html.Span(id="sub", style={"color": MUTED, "fontSize": "0.68rem",
                     "letterSpacing": "0.08em"}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "baseline", "flexWrap": "wrap", "gap": "0.4rem",
                  "padding": "0.2rem 0.1rem 1rem"}),
        html.Div(id="content"),
    ], style={"backgroundColor": BLACK, "minHeight": "100vh", "fontFamily": MONO,
              "padding": "1rem 1.1rem", "maxWidth": "1120px", "margin": "0 auto"})

    @app.callback([Output("content", "children"), Output("sub", "children")],
                  Input("tick", "n_intervals"))
    def _refresh(_n):
        store = PaperStore()
        try:
            s = store.stats()
            opens = store.open_bets()

            # Mark open positions to the live bid so a dead bet (trading at ~0)
            # is visible immediately, instead of looking healthy until Polymarket
            # finally resolves the market and the cycle books the loss.
            marks = _marks([b.token_id for b in opens])
            unreal = {b.id: (b.shares * marks[b.token_id] - b.stake_usd)
                      for b in opens if b.token_id in marks}
            unreal_total = round(sum(unreal.values()), 2)

            realized, roi = s["realized_pnl"], s["roi"]
            equity = BANKROLL + realized
            impact = realized / BANKROLL if BANKROLL else 0.0
            deployed = s["open_stake"] / BANKROLL if BANKROLL else 0.0
            potential = round(sum(b.shares - b.stake_usd for b in opens), 2)
            avg_entry = (sum(b.entry_price for b in opens) / len(opens)) if opens else 0.0
            total_staked = round(s["settled_stake"] + s["open_stake"], 2)

            top = _grid([
                _cell([_label("OPEN BOOK"),
                       _value(f"{s['open']} · ${s['open_stake']:.0f}"),
                       html.Div("POSITIONS · EXPOSURE", style={"color": MUTED,
                                "fontSize": "0.68rem", "marginTop": "0.3rem",
                                "letterSpacing": "0.1em"})]),
                _cell([_label("REALIZED P&L"),
                       _value(f"{'+' if realized>=0 else ''}${realized:.2f}", _c(realized)),
                       html.Div(f"{roi*100:+.2f}% ROI", style={"color": _c(roi),
                                "fontSize": "0.8rem", "marginTop": "0.3rem",
                                "fontWeight": 700})]),
                _cell([_label("PORTFOLIO"),
                       _value(f"${equity + unreal_total:.2f}"),
                       html.Div(f"{(impact + unreal_total/BANKROLL)*100:+.2f}%  "
                                f"(REALIZED ${realized:.0f} · UNREAL "
                                f"{'+' if unreal_total>=0 else ''}${unreal_total:.2f})",
                                style={"color": _c(impact + unreal_total),
                                       "fontSize": "0.8rem",
                                       "marginTop": "0.3rem", "fontWeight": 700})]),
            ], 3, min_px=240)

            band = html.Div(_cell([
                html.Div([
                    html.Div([
                        _label("CAPITAL DEPLOYED — UNDERDOG BOOK"),
                        html.Div("BUY 0.15–0.30 · RESOLVES 6–168H · HOLD TO SETTLE",
                                 style={"color": MUTED, "fontSize": "0.68rem",
                                        "letterSpacing": "0.1em"}),
                    ], style={"flex": "1"}),
                    html.Div(f"{deployed*100:.1f}% deployed · ${s['open_stake']:.0f} of ${BANKROLL:.0f}",
                             style={"color": GREEN, "fontSize": "0.82rem", "fontWeight": 700,
                                    "textAlign": "right"}),
                ], style={"display": "flex", "alignItems": "flex-start"}),
                _progress(deployed),
            ]), style={"backgroundColor": BLACK, "border": f"1px solid {LINE}",
                       "borderRadius": "12px", "marginBottom": "10px"})

            mid = _grid([
                _cell([_label("TOTAL BETS"), _value(str(s["total"]), size="1.6rem")]),
                _cell([_label("SETTLED"),
                       _value(f"{s['won']}W · {s['lost']}L", size="1.6rem")]),
                _cell([_label("WIN RATE"),
                       _value(f"{s['win_rate']*100:.0f}%",
                              _c(s['win_rate']-0.20) if s['settled'] else WHITE, "1.6rem"),
                       html.Div("EXP ~27.4%", style={"color": MUTED, "fontSize": "0.66rem",
                                "marginTop": "0.25rem", "letterSpacing": "0.1em"})]),
                _cell([_label("STAKED"), _value(f"${total_staked:.0f}", size="1.6rem")]),
            ], 4, min_px=150)

            panels = _grid([
                _panel(GREEN, "REALIZED", "BOOKED AT RESOLUTION",
                       f"{'+' if realized>=0 else ''}${realized:.2f}", _c(realized), [
                           _kv("WIN RATE", f"{s['win_rate']*100:.0f}%"),
                           _kv("ROI", f"{roi*100:+.1f}%", _c(roi)),
                           _kv("SETTLED", str(s["settled"])),
                       ]),
                _panel(AMBER, "OPEN RISK", "MARKED TO LIVE BID",
                       f"${s['open_stake']:.2f}", AMBER, [
                           _kv("UNREALIZED",
                               f"{'+' if unreal_total >= 0 else ''}${unreal_total:.2f}"
                               if unreal else "—", _c(unreal_total)),
                           _kv("MAX LOSS", f"-${s['open_stake']:.2f}", RED),
                           _kv("MAX GAIN", f"+${potential:.2f}", GREEN),
                           _kv("AVG ENTRY", f"{avg_entry:.3f}"),
                       ]),
                _panel(PURPLE, "BACKTEST EDGE", "VALIDATED EXPECTATION",
                       "+16.7%", PURPLE, [
                           _kv("EXP WIN", "~27.4%"),
                           _kv("HORIZON", "6–168H"),
                           _kv("SKEW", "NEGATIVE"),
                       ]),
            ], 3, min_px=240)

            open_rows = [_bet_row([
                ((b.question or b.slug)[:40], WHITE, {"flex": "5"}),
                (b.outcome[:8], MUTED, {"flex": "2"}),
                (f"{b.entry_price:.3f}", MUTED, {"flex": "1", "align": "right"}),
                (f"{marks[b.token_id]:.3f}" if b.token_id in marks else "—",
                 _c(marks[b.token_id] - b.entry_price) if b.token_id in marks else MUTED,
                 {"flex": "1", "align": "right"}),
                (f"${b.stake_usd:.2f}", MUTED, {"flex": "1", "align": "right"}),
                (f"{'+' if unreal.get(b.id, 0) >= 0 else ''}${unreal[b.id]:.2f}"
                 if b.id in unreal else "—",
                 _c(unreal.get(b.id, 0)) if b.id in unreal else MUTED,
                 {"flex": "2", "align": "right"}),
            ]) for b in opens[:20]]
            settled_bets = [b for b in store.all_bets(limit=200)
                            if b.status in ("WON", "LOST", "VOID")]
            settled_rows = [_bet_row([
                ((b.question or b.slug)[:44], WHITE, {"flex": "5"}),
                (b.status, GREEN if b.status == "WON" else RED if b.status == "LOST" else MUTED,
                 {"flex": "2"}),
                (f"{'+' if (b.pnl or 0)>=0 else ''}${b.pnl:.2f}", _c(b.pnl or 0),
                 {"flex": "2", "align": "right"}),
            ]) for b in settled_bets[:20]]

            tables = _grid([
                _table("OPEN POSITIONS",
                       [("MARKET", {"flex": "5"}), ("SIDE", {"flex": "2"}),
                        ("ENTRY", {"flex": "1", "align": "right"}),
                        ("MARK", {"flex": "1", "align": "right"}),
                        ("STAKE", {"flex": "1", "align": "right"}),
                        ("UNREAL", {"flex": "2", "align": "right"})], open_rows),
                _table("SETTLED",
                       [("MARKET", {"flex": "5"}), ("RESULT", {"flex": "2"}),
                        ("P&L", {"flex": "2", "align": "right"})], settled_rows),
            ], 2, min_px=320)

            chart = html.Div(_cell([_label("CUMULATIVE REALIZED P&L"),
                                    dcc.Graph(figure=_pnl_figure(store),
                                              config={"displayModeBar": False})]),
                             style={"backgroundColor": BLACK, "border": f"1px solid {LINE}",
                                    "borderRadius": "12px", "marginTop": "10px",
                                    "marginBottom": "10px"})

            sub = (f"UPDATED {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC · "
                   f"DRY-RUN · ${BANKROLL:.0f} BANKROLL")
            return [top, band, mid, panels, chart, tables], sub
        finally:
            store.close()

    return app
