"""
dashboard/components/tables.py — Reusable Dash DataTable wrapper.

Exports:
  data_table(df, columns, table_id, ...)  → dash_table.DataTable
"""

from __future__ import annotations

import pandas as pd
from dash import dash_table


# Default style for header cells
_HEADER_STYLE = {
    "backgroundColor": "#1e2130",
    "color": "#adb5bd",
    "fontWeight": "600",
    "fontSize": "12px",
    "textTransform": "uppercase",
    "letterSpacing": "0.05em",
    "border": "none",
    "padding": "8px 12px",
}

# Default style for data cells
_CELL_STYLE = {
    "backgroundColor": "#262b3d",
    "color": "#e9ecef",
    "fontSize": "13px",
    "border": "none",
    "borderBottom": "1px solid #2e3347",
    "padding": "8px 12px",
}

# Alternating row highlight
_STYLE_DATA_CONDITIONAL = [
    {
        "if": {"row_index": "odd"},
        "backgroundColor": "#2a2f42",
    },
    {
        "if": {"state": "selected"},
        "backgroundColor": "#3b4263",
        "border": "1px solid #4e5a8a",
    },
]


def data_table(
    df: pd.DataFrame,
    columns: list[dict] | None = None,
    table_id: str = "data-table",
    page_size: int = 15,
    sortable: bool = True,
    filterable: bool = False,
    row_selectable: str | bool = False,
) -> dash_table.DataTable:
    """
    Build a styled dark-theme Dash DataTable.

    Args:
        df:             Data to display (may be empty).
        columns:        List of {"name": ..., "id": ...} dicts.  If None,
                        inferred from df.columns.
        table_id:       HTML id for the DataTable element.
        page_size:      Rows per page.
        sortable:       Enable column sorting.
        filterable:     Enable per-column filter row.
        row_selectable: "single", "multi", or False.

    Returns:
        A dash_table.DataTable component.
    """
    if columns is None:
        columns = [{"name": col, "id": col} for col in df.columns]

    records = df.to_dict("records") if not df.empty else []

    return dash_table.DataTable(
        id=table_id,
        columns=columns,
        data=records,
        page_size=page_size,
        sort_action="native" if sortable else "none",
        filter_action="native" if filterable else "none",
        row_selectable=row_selectable if row_selectable else False,
        style_table={"overflowX": "auto", "borderRadius": "6px", "overflow": "hidden"},
        style_header=_HEADER_STYLE,
        style_cell=_CELL_STYLE,
        style_data_conditional=_STYLE_DATA_CONDITIONAL,
        style_as_list_view=True,
    )
