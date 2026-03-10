"""Summary and comparison tables for simulation results.

All table functions return ``list[dict]`` — a format that works with:
- ``IPython.display.HTML(format_table_html(rows))``
- ``pandas.DataFrame(rows)`` (if pandas is installed)
- ``tabulate(rows, headers="keys")`` (if tabulate is installed)
- Plain iteration
"""

from __future__ import annotations

from typing import Any

from omega.simulation.stats import CellResult, DamageStats, RatioStats, SimulationResult

# Default stat columns for summary tables
_DEFAULT_STATS = (
    "mean", "median", "min", "max", "std_dev", "p5", "p95", "hit_rate", "count",
)


def summary_table(
    result: SimulationResult,
    *,
    stats: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Formatted table of stats per sweep cell.

    Parameters
    ----------
    result:
        A :class:`SimulationResult` from ``run_sweep()``.
    stats:
        Which stat columns to include.  Defaults to mean, median, min,
        max, std_dev, p5, p95, hit_rate, count.

    Returns
    -------
    list[dict[str, Any]]:
        One dict per cell, keys are column names.
    """
    cols = stats or list(_DEFAULT_STATS)
    rows: list[dict[str, Any]] = []

    for cell in result.cells:
        row: dict[str, Any] = {}

        # Variable values come first
        for k, v in cell.variable_values.items():
            row[k] = v

        # Stat columns
        for col in cols:
            row[col] = _get_stat(cell, col)

        rows.append(row)

    return rows


def comparison_table(
    cells: dict[str, CellResult],
    *,
    stats: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Side-by-side comparison of named scenarios.

    Parameters
    ----------
    cells:
        Mapping of scenario label → :class:`CellResult`.
    stats:
        Which stats to compare.  Defaults to the standard set.

    Returns
    -------
    list[dict[str, Any]]:
        One dict per stat row.  Keys: ``"stat"``, one key per scenario
        label, and ``"delta"`` if exactly 2 scenarios.
    """
    cols = stats or list(_DEFAULT_STATS)
    labels = list(cells.keys())
    rows: list[dict[str, Any]] = []

    for col in cols:
        row: dict[str, Any] = {"stat": col}
        values = []
        for label in labels:
            val = _get_stat(cells[label], col)
            row[label] = val
            if isinstance(val, (int, float)):
                values.append(val)
        # Delta column when comparing exactly 2 scenarios
        if len(labels) == 2 and len(values) == 2:
            row["delta"] = _fmt(values[1] - values[0])
        rows.append(row)

    return rows


def format_table_html(rows: list[dict[str, Any]]) -> str:
    """Render list-of-dicts as an HTML table string.

    Suitable for ``IPython.display.HTML(format_table_html(rows))``.
    """
    if not rows:
        return "<table></table>"

    headers = list(rows[0].keys())

    parts = ['<table style="border-collapse:collapse;">']
    # Header row
    parts.append("<tr>")
    for h in headers:
        parts.append(
            f'<th style="border:1px solid #ccc;padding:4px 8px;'
            f'background:#f5f5f5;text-align:left;">{_escape(str(h))}</th>'
        )
    parts.append("</tr>")

    # Data rows
    for row in rows:
        parts.append("<tr>")
        for h in headers:
            val = row.get(h, "")
            parts.append(
                f'<td style="border:1px solid #ccc;padding:4px 8px;">'
                f"{_escape(_fmt(val))}</td>"
            )
        parts.append("</tr>")

    parts.append("</table>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_stat(cell: CellResult, name: str) -> Any:
    """Extract a named statistic from a CellResult."""
    ds = cell.damage_stats
    rs = cell.ratios

    stat_map: dict[str, Any] = {
        "mean": ds.mean,
        "median": ds.median,
        "min": ds.min,
        "max": ds.max,
        "std_dev": ds.std_dev,
        "p5": ds.p5,
        "p25": ds.p25,
        "p75": ds.p75,
        "p95": ds.p95,
        "count": ds.count,
        "hit_rate": rs.hit_rate,
        "poison_rate": rs.poison_rate,
        "equipment_break_rate": rs.equipment_break_rate,
        "base_mean": cell.base_damage_stats.mean,
        "absorbed_mean": cell.absorbed_stats.mean,
        "errors": cell.error_count,
    }
    return stat_map.get(name, "")


def _fmt(val: Any) -> str:
    """Format a value for display."""
    if isinstance(val, float):
        if 0.0 < abs(val) < 1.0:
            return f"{val:.1%}"
        return f"{val:.2f}"
    return str(val)


def _escape(s: str) -> str:
    """Minimal HTML escaping."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
