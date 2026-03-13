"""Summary and comparison tables for simulation results.

All table functions return ``list[dict]`` — a format that works with:
- ``IPython.display.HTML(format_table_html(rows))``
- ``pandas.DataFrame(rows)`` (if pandas is installed)
- ``tabulate(rows, headers="keys")`` (if tabulate is installed)
- Plain iteration
"""

from __future__ import annotations

from typing import Any

from omega.simulation.stats import CellResult, DamageStats, RatioStats, SimulationResult, TimingStats

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

    # Use CSS custom properties so the table adapts to light/dark mode
    parts = [
        "<style>",
        ".omega-table { border-collapse: collapse; color-scheme: light dark; }",
        ".omega-table th, .omega-table td "
        "{ border: 1px solid rgba(128,128,128,0.4); padding: 4px 8px; text-align: right; }",
        ".omega-table th "
        "{ text-align: left; font-weight: 600; "
        "background: rgba(128,128,128,0.15); }",
        ".omega-table tr:nth-child(even) td "
        "{ background: rgba(128,128,128,0.06); }",
        "</style>",
        '<table class="omega-table">',
    ]

    # Header row
    parts.append("<tr>")
    for h in headers:
        parts.append(f"<th>{_escape(str(h))}</th>")
    parts.append("</tr>")

    # Data rows
    for row in rows:
        parts.append("<tr>")
        for h in headers:
            val = row.get(h, "")
            # Use the stat name from the "stat" column (comparison tables)
            # to determine if this value is a rate that should be formatted as %
            stat_name = row.get("stat", h) if h != "stat" else ""
            parts.append(f"<td>{_escape(_fmt(val, stat_name=stat_name))}</td>")
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

    ds_hit = cell.damage_stats_on_hit

    # Timing stats — use defaults if not computed
    ts = cell.timing or TimingStats()

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
        "reactive_rate": rs.reactive_rate,
        "spell_strike_rate": rs.spell_strike_rate,
        "effect_rate": rs.effect_rate,
        "base_mean": cell.base_damage_stats.mean,
        "total": ds.count * ds.mean,
        "absorbed_mean": cell.absorbed_stats.mean,
        "errors": cell.error_count,
        # Drain stats (mana/hp/stamina drained by effect enchantments)
        "drain_mean": cell.drain_stats.mean,
        "drain_total": cell.drain_stats.count * cell.drain_stats.mean,
        # On-hit drain (only swings that drained)
        "drain_mean_on_hit": cell.drain_stats_on_hit.mean,
        # On-hit damage stats (only swings that connected)
        "mean_on_hit": ds_hit.mean,
        "median_on_hit": ds_hit.median,
        "min_on_hit": ds_hit.min,
        "max_on_hit": ds_hit.max,
        "std_dev_on_hit": ds_hit.std_dev,
        "p5_on_hit": ds_hit.p5,
        "p95_on_hit": ds_hit.p95,
        # On-hit conditional rates
        "reactive_rate_on_hit": rs.reactive_rate_on_hit,
        "spell_strike_rate_on_hit": rs.spell_strike_rate_on_hit,
        "effect_rate_on_hit": rs.effect_rate_on_hit,
        # Elemental totals
        "elem_total_net": cell.elemental_breakdown.total_net,
        "elem_total_gross": cell.elemental_breakdown.total_gross,
        # Timing / DPS
        "swing_delay_ms": ts.swing_delay_ms,
        "swings_per_sec": ts.swings_per_second,
        "dps_mean": ts.dps_mean,
        "dps_on_hit": ts.dps_on_hit,
        "effective_dps": ts.effective_dps,
        # Spell-specific rates
        "fizzle_rate": rs.fizzle_rate,
        "resist_rate": rs.resist_rate,
        "resist_rate_on_cast": rs.resist_rate_on_cast,
        # Spell on-cast damage stats
        "mean_on_cast": cell.damage_stats_on_cast.mean,
        "median_on_cast": cell.damage_stats_on_cast.median,
        "min_on_cast": cell.damage_stats_on_cast.min,
        "max_on_cast": cell.damage_stats_on_cast.max,
        "std_dev_on_cast": cell.damage_stats_on_cast.std_dev,
        "p5_on_cast": cell.damage_stats_on_cast.p5,
        "p95_on_cast": cell.damage_stats_on_cast.p95,
        # Alias: cast_rate = hit_rate for spell contexts
        "cast_rate": rs.hit_rate,
    }

    if name in stat_map:
        return stat_map[name]

    # Dynamic element stats: elem_<element>_<field>
    # e.g. "elem_fire_net", "elem_fire_gross", "elem_fire_prot", "elem_fire_absorbed"
    eb = cell.elemental_breakdown
    if name.startswith("elem_"):
        parts = name[5:].rsplit("_", 1)
        if len(parts) == 2:
            elem_name, field_name = parts
            ed = eb.elements.get(elem_name)
            if ed is not None:
                ed_map = {"net": ed.net, "gross": ed.gross, "prot": ed.prot,
                          "healed": ed.healed, "absorbed": ed.absorbed}
                return ed_map.get(field_name, "")
        # Bare element name defaults to net: "elem_fire" → fire.net
        elem_name = name[5:]
        ed = eb.elements.get(elem_name)
        if ed is not None:
            return ed.net

    return ""


# Stat names that represent rates (0.0–1.0) and should be formatted as percentages
_RATE_STATS = frozenset({
    "hit_rate", "poison_rate", "equipment_break_rate",
    "reactive_rate", "spell_strike_rate", "effect_rate",
    "reactive_rate_on_hit", "spell_strike_rate_on_hit", "effect_rate_on_hit",
    "fizzle_rate", "resist_rate", "resist_rate_on_cast", "cast_rate",
})


def _fmt(val: Any, *, stat_name: str = "") -> str:
    """Format a value for display.

    Rate stats (hit_rate, effect_rate, etc.) are always formatted as
    percentages.  Other floats are formatted as plain decimals.
    """
    if isinstance(val, float):
        if stat_name in _RATE_STATS:
            return f"{val:.1%}"
        return f"{val:.2f}"
    return str(val)


def _escape(s: str) -> str:
    """Minimal HTML escaping."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
