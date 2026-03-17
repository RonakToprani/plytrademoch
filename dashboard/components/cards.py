"""
dashboard/components/cards.py — Reusable Bootstrap stat cards.

Exports:
  stat_card(title, value, subtitle, color, icon_class) → dbc.Card
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def stat_card(
    title: str,
    value: str,
    subtitle: str = "",
    color: str = "primary",
    icon_class: str = "",
    card_id: str = "",
) -> dbc.Card:
    """
    Build a Bootstrap stat card.

    Args:
        title:      Label shown above the value (e.g. "Total P&L").
        value:      Main figure to display (e.g. "+$12.45").
        subtitle:   Small text below the value (e.g. "since inception").
        color:      Bootstrap color name: primary, success, danger, warning, info, secondary.
        icon_class: Optional Bootstrap Icons class (e.g. "bi bi-graph-up").
        card_id:    Optional id for the card body (for callback targeting).

    Returns:
        A dbc.Card component.
    """
    icon = html.I(className=f"{icon_class} me-2") if icon_class else None

    header_children: list = []
    if icon:
        header_children.append(icon)
    header_children.append(title)

    body_children = [
        html.P(header_children, className="card-title text-muted small mb-1"),
        html.H4(value, className=f"card-text fw-bold text-{color} mb-0"),
    ]
    if subtitle:
        body_children.append(html.P(subtitle, className="card-subtitle text-muted small mt-1"))

    kwargs: dict = {"className": "h-100 shadow-sm border-0"}
    if card_id:
        kwargs["id"] = card_id

    return dbc.Card(
        dbc.CardBody(body_children, className="p-3"),
        **kwargs,
    )


def pnl_card(title: str, value_usd: float, subtitle: str = "") -> dbc.Card:
    """Convenience wrapper: green if positive, red if negative."""
    sign = "+" if value_usd >= 0 else ""
    color = "success" if value_usd >= 0 else "danger"
    icon = "bi bi-graph-up-arrow" if value_usd >= 0 else "bi bi-graph-down-arrow"
    return stat_card(
        title=title,
        value=f"{sign}${value_usd:.2f}",
        subtitle=subtitle,
        color=color,
        icon_class=icon,
    )
