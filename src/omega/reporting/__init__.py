"""Reporting utilities — tables, plots, and hot-reload for notebooks."""

from omega.reporting.reload import reload_omega
from omega.reporting.tables import (
    comparison_table,
    format_table_html,
    summary_table,
)

# Plots are lazy-imported to avoid hard matplotlib dependency.
# Use: from omega.reporting.plots import damage_histogram, ...

__all__ = [
    "comparison_table",
    "format_table_html",
    "reload_omega",
    "summary_table",
]
