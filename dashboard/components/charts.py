"""
dashboard/components/charts.py — Reusable Plotly figure builders.

Exports:
  equity_curve(df)                        → go.Figure
  pnl_histogram(df)                       → go.Figure
  pnl_bar_chart(df)                       → go.Figure
  price_chart(df, market_slug)            → go.Figure
  exposure_gauge(current, max_exposure)   → go.Figure
  daily_pnl_gauge(current, max_loss)      → go.Figure
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Theme / shared defaults
# ---------------------------------------------------------------------------

_BG = "#1e2130"
_PAPER_BG = "#1e2130"
_GRID_COLOR = "#2e3347"
_TEXT_COLOR = "#adb5bd"
_GREEN = "#2ecc71"
_RED = "#e74c3c"
_BLUE = "#3498db"

_LAYOUT_DEFAULTS = dict(
    paper_bgcolor=_PAPER_BG,
    plot_bgcolor=_BG,
    font=dict(color=_TEXT_COLOR, size=12),
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(gridcolor=_GRID_COLOR, zeroline=False),
    yaxis=dict(gridcolor=_GRID_COLOR, zeroline=False),
)


def _empty_fig(message: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(color=_TEXT_COLOR, size=14),
    )
    fig.update_layout(**_LAYOUT_DEFAULTS)
    return fig


# ---------------------------------------------------------------------------
# Equity curve
# ---------------------------------------------------------------------------

def equity_curve(df: pd.DataFrame) -> go.Figure:
    """
    Line chart of cumulative total P&L over time.

    Expected columns: date (str), total_pnl (float).
    """
    if df.empty or "total_pnl" not in df.columns:
        return _empty_fig("No equity data yet")

    colors = [_GREEN if v >= 0 else _RED for v in df["total_pnl"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["total_pnl"],
        mode="lines+markers",
        line=dict(color=_BLUE, width=2),
        marker=dict(color=colors, size=5),
        fill="tozeroy",
        fillcolor="rgba(52,152,219,0.08)",
        name="Total P&L",
        hovertemplate="<b>%{x}</b><br>P&L: $%{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Equity Curve", font=dict(size=14)),
        yaxis_title="P&L (USD)",
        showlegend=False,
        **_LAYOUT_DEFAULTS,
    )
    return fig


# ---------------------------------------------------------------------------
# P&L histogram
# ---------------------------------------------------------------------------

def pnl_histogram(df: pd.DataFrame) -> go.Figure:
    """
    Histogram of per-trade P&L distribution.

    Expected column: pnl (float).
    """
    if df.empty or "pnl" not in df.columns:
        return _empty_fig("No trade P&L data yet")

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df["pnl"],
        nbinsx=30,
        marker_color=_BLUE,
        opacity=0.8,
        name="P&L",
        hovertemplate="P&L: $%{x:.2f}<br>Count: %{y}<extra></extra>",
    ))
    fig.add_vline(x=0, line_dash="dash", line_color=_TEXT_COLOR, opacity=0.5)
    fig.update_layout(
        title=dict(text="P&L Distribution", font=dict(size=14)),
        xaxis_title="P&L (USD)",
        yaxis_title="Trades",
        showlegend=False,
        bargap=0.05,
        **_LAYOUT_DEFAULTS,
    )
    return fig


# ---------------------------------------------------------------------------
# P&L bar chart (per trade, chronological)
# ---------------------------------------------------------------------------

def pnl_bar_chart(df: pd.DataFrame) -> go.Figure:
    """
    Vertical bar chart of per-trade P&L, colored green/red.

    Expected columns: created_at (str), pnl (float), market_slug (str).
    """
    if df.empty or "pnl" not in df.columns:
        return _empty_fig("No closed trade data yet")

    colors = [_GREEN if v >= 0 else _RED for v in df["pnl"]]
    x_labels = df.get("market_slug", df.index).astype(str)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(len(df))),
        y=df["pnl"],
        marker_color=colors,
        text=x_labels,
        textposition="inside",
        customdata=df["pnl"].round(2),
        hovertemplate="<b>%{text}</b><br>P&L: $%{customdata}<extra></extra>",
        name="Trade P&L",
    ))
    fig.update_layout(
        title=dict(text="Trade P&L", font=dict(size=14)),
        xaxis=dict(showticklabels=False, gridcolor=_GRID_COLOR),
        yaxis_title="P&L (USD)",
        showlegend=False,
        **_LAYOUT_DEFAULTS,
    )
    return fig


# ---------------------------------------------------------------------------
# Market price chart
# ---------------------------------------------------------------------------

def price_chart(df: pd.DataFrame, market_slug: str = "") -> go.Figure:
    """
    Line chart of YES price snapshots over time for a specific market.

    Expected columns: timestamp (str), current_price (float).
    """
    if df.empty or "current_price" not in df.columns:
        return _empty_fig(f"No price data for {market_slug or 'selected market'}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["current_price"],
        mode="lines",
        line=dict(color=_BLUE, width=2),
        name="Price",
        hovertemplate="<b>%{x}</b><br>Price: $%{y:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=f"Price — {market_slug}" if market_slug else "Market Price", font=dict(size=14)),
        yaxis_title="Price",
        yaxis_range=[0, 1],
        showlegend=False,
        **_LAYOUT_DEFAULTS,
    )
    return fig


# ---------------------------------------------------------------------------
# Exposure gauge
# ---------------------------------------------------------------------------

def exposure_gauge(current: float, max_exposure: float) -> go.Figure:
    """
    Gauge showing total exposure vs MAX_PORTFOLIO_EXPOSURE.

    Green < 60%, yellow 60–85%, red > 85%.
    """
    pct = min(current / max_exposure * 100, 100) if max_exposure > 0 else 0

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current,
        delta={"reference": max_exposure * 0.60, "valueformat": ".2f"},
        number={"prefix": "$", "valueformat": ".2f"},
        title={"text": "Portfolio Exposure", "font": {"color": _TEXT_COLOR, "size": 13}},
        gauge={
            "axis": {"range": [0, max_exposure], "tickcolor": _TEXT_COLOR},
            "bar": {"color": _BLUE},
            "bgcolor": _GRID_COLOR,
            "steps": [
                {"range": [0, max_exposure * 0.60], "color": "rgba(46,204,113,0.2)"},
                {"range": [max_exposure * 0.60, max_exposure * 0.85], "color": "rgba(243,156,18,0.2)"},
                {"range": [max_exposure * 0.85, max_exposure], "color": "rgba(231,76,60,0.2)"},
            ],
            "threshold": {
                "line": {"color": _RED, "width": 2},
                "thickness": 0.75,
                "value": max_exposure,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor=_PAPER_BG,
        font=dict(color=_TEXT_COLOR),
        margin=dict(l=20, r=20, t=50, b=20),
        height=220,
    )
    return fig


# ---------------------------------------------------------------------------
# Daily P&L gauge
# ---------------------------------------------------------------------------

def daily_pnl_gauge(current: float, max_loss: float) -> go.Figure:
    """
    Gauge showing today's P&L vs -MAX_DAILY_LOSS threshold.

    current is signed (negative = loss). max_loss is positive.
    """
    display_val = max(current, -max_loss)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=display_val,
        number={"prefix": "$", "valueformat": "+.2f", "font": {"color": _GREEN if current >= 0 else _RED}},
        title={"text": "Today's P&L", "font": {"color": _TEXT_COLOR, "size": 13}},
        gauge={
            "axis": {"range": [-max_loss, max_loss], "tickcolor": _TEXT_COLOR},
            "bar": {"color": _GREEN if current >= 0 else _RED},
            "bgcolor": _GRID_COLOR,
            "steps": [
                {"range": [-max_loss, 0], "color": "rgba(231,76,60,0.15)"},
                {"range": [0, max_loss], "color": "rgba(46,204,113,0.15)"},
            ],
            "threshold": {
                "line": {"color": _RED, "width": 2},
                "thickness": 0.75,
                "value": -max_loss,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor=_PAPER_BG,
        font=dict(color=_TEXT_COLOR),
        margin=dict(l=20, r=20, t=50, b=20),
        height=220,
    )
    return fig
