"""Matplotlib figure factories for simulation results.

All functions return ``matplotlib.figure.Figure`` objects, ready for
``fig.savefig(...)`` or inline display in Jupyter notebooks.

Matplotlib is an optional dependency — import errors are raised at call
time, not at module import.
"""

from __future__ import annotations

from typing import Any

from omega.simulation.stats import CellResult, SimulationResult, TimingStats


def _require_matplotlib():
    """Import and return (matplotlib.pyplot, matplotlib.figure)."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.figure  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "matplotlib is required for plotting. Install it with: "
            "pip install matplotlib"
        ) from exc
    return plt


def damage_histogram(
    cell: CellResult,
    *,
    bins: int = 30,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Histogram of final damage values for a single cell.

    Parameters
    ----------
    cell:
        A :class:`CellResult` with raw_results populated.
    bins:
        Number of histogram bins.
    title:
        Optional figure title.
    figsize:
        Figure size in inches ``(width, height)``.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    # Filter to hits only — misses (0 damage) would create a spike at 0
    # that distorts the distribution shape.  Hit rate is annotated instead.
    damages = [r.final_damage for r in cell.raw_results if r.success and r.final_damage > 0]

    fig, ax = plt.subplots(figsize=figsize)

    if not damages:
        ax.text(0.5, 0.5, "No hits recorded", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_title(title or "Damage Distribution")
        plt.close(fig)
        return fig

    ax.hist(damages, bins=bins, edgecolor="black", alpha=0.7)

    # Overlay mean and median (on-hit stats)
    ds = cell.damage_stats_on_hit
    ax.axvline(ds.mean, color="red", linestyle="--", linewidth=1.5, label=f"Mean (on hit): {ds.mean:.1f}")
    ax.axvline(ds.median, color="orange", linestyle=":", linewidth=1.5, label=f"Median (on hit): {ds.median:.1f}")

    ax.set_xlabel("Final Damage")
    ax.set_ylabel("Frequency")

    # Annotate hit rate in the title
    hit_rate = cell.ratios.hit_rate
    default_title = f"Damage Distribution (hit rate: {hit_rate:.1%})"
    ax.set_title(title or default_title)
    ax.legend()
    fig.tight_layout()
    plt.close(fig)
    return fig


def damage_vs_parameter(
    result: SimulationResult,
    variable_name: str,
    *,
    show_range: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Line plot of mean damage vs. a swept parameter.

    Optionally shows p5–p95 shaded range.

    Parameters
    ----------
    result:
        A :class:`SimulationResult` from ``run_sweep()``.
    variable_name:
        The variable to plot on the x-axis.
    show_range:
        If True, shade the p5–p95 range.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    curve = result.damage_curve(variable_name)
    if not curve:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, f"No data for variable: {variable_name}",
                ha="center", va="center", transform=ax.transAxes)
        plt.close(fig)
        return fig

    x_vals = [v for v, _ in curve]
    means = [ds.mean for _, ds in curve]
    p5s = [ds.p5 for _, ds in curve]
    p95s = [ds.p95 for _, ds in curve]

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(x_vals, means, marker="o", linewidth=2, label="Mean Damage")

    if show_range:
        ax.fill_between(x_vals, p5s, p95s, alpha=0.2, label="p5–p95 range")

    ax.set_xlabel(variable_name)
    ax.set_ylabel("Damage")
    ax.set_title(title or f"Damage vs. {variable_name}")
    ax.legend()
    fig.tight_layout()
    plt.close(fig)
    return fig


def damage_breakdown(
    cell: CellResult,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (6, 4),
    show_elemental: bool = True,
) -> Any:
    """Grouped bar showing base damage, absorbed, final, and elemental means.

    When *show_elemental* is True and elemental data is available, the chart
    includes an additional bar for total elemental/planar damage.

    Parameters
    ----------
    cell:
        A :class:`CellResult` with stats populated.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.
    show_elemental:
        Include elemental damage bar when data is available.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    base = cell.base_damage_stats.mean
    absorbed = cell.absorbed_stats.mean
    final = cell.damage_stats.mean

    categories = ["Base", "Absorbed", "Final"]
    values = [base, absorbed, final]
    colors = ["#2196F3", "#FF9800", "#4CAF50"]

    elem_total = cell.elemental_breakdown.total_net
    if show_elemental and elem_total > 0:
        categories.append("Elemental")
        values.append(elem_total)
        colors.append("#E53935")

    fig, ax = plt.subplots(figsize=figsize)

    bars = ax.bar(categories, values, color=colors, edgecolor="black", linewidth=0.5)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{val:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_ylabel("Damage")
    ax.set_title(title or "Damage Breakdown")
    fig.tight_layout()
    plt.close(fig)
    return fig


def comparison_breakdown(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Grouped bar chart comparing damage breakdown across scenarios.

    Each scenario shows three side-by-side bars: base, absorbed, final.

    Parameters
    ----------
    cells:
        Mapping of scenario label → :class:`CellResult`.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()
    import numpy as np

    labels = list(cells.keys())
    finals = [cells[l].damage_stats.mean for l in labels]
    absorbeds = [cells[l].absorbed_stats.mean for l in labels]
    bases = [cells[l].base_damage_stats.mean for l in labels]

    x = np.arange(len(labels))
    width = 0.22

    fig, ax = plt.subplots(figsize=figsize)

    b1 = ax.bar(x - width, bases, width, label="Base", color="#2196F3", edgecolor="black", linewidth=0.5)
    b2 = ax.bar(x, absorbeds, width, label="Absorbed", color="#FF9800", edgecolor="black", linewidth=0.5)
    b3 = ax.bar(x + width, finals, width, label="Final", color="#4CAF50", edgecolor="black", linewidth=0.5)

    # Value labels above each bar
    for bars in (b1, b2, b3):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                    f"{h:.1f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Damage")
    ax.set_title(title or "Damage Breakdown Comparison")
    ax.legend()
    fig.tight_layout()
    plt.close(fig)
    return fig


def comparison_overlay(
    cells: dict[str, CellResult],
    *,
    bins: int = 30,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Overlaid histograms comparing damage distributions of named scenarios.

    Parameters
    ----------
    cells:
        Mapping of scenario label → :class:`CellResult`.
    bins:
        Number of histogram bins.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    fig, ax = plt.subplots(figsize=figsize)

    for label, cell in cells.items():
        damages = [r.final_damage for r in cell.raw_results if r.success and r.final_damage > 0]
        if damages:
            hit_rate = cell.ratios.hit_rate
            on_hit_mean = cell.damage_stats_on_hit.mean
            ax.hist(
                damages,
                bins=bins,
                alpha=0.5,
                label=f"{label} (μ={on_hit_mean:.1f}, hit: {hit_rate:.0%})",
                edgecolor="black",
                linewidth=0.5,
            )

    ax.set_xlabel("Final Damage")
    ax.set_ylabel("Frequency")
    ax.set_title(title or "Damage Comparison")
    if cells:
        ax.legend()
    fig.tight_layout()
    plt.close(fig)
    return fig


# Fixed color map for each element type
_ELEMENT_COLORS: dict[str, str] = {
    "fire": "#E53935",
    "air": "#00ACC1",
    "earth": "#6D4C41",
    "water": "#1E88E5",
    "necro": "#8E24AA",
    "holy": "#FFD600",
    "poison": "#43A047",
    "acid": "#C0CA33",
    "physical": "#78909C",
    "magic": "#AB47BC",
    "astral": "#90CAF9",
}


def elemental_breakdown_chart(
    cell: CellResult,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 3),
) -> Any:
    """Horizontal stacked bar showing mean damage by element type.

    Parameters
    ----------
    cell:
        A :class:`CellResult` with elemental_breakdown populated.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    data = cell.elemental_breakdown.net_dict()
    if not data:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No elemental damage data",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or "Elemental Damage Breakdown")
        plt.close(fig)
        return fig

    fig, ax = plt.subplots(figsize=figsize)
    left = 0.0
    total = cell.elemental_breakdown.total_net
    for elem, val in data.items():
        color = _ELEMENT_COLORS.get(elem, "#BDBDBD")
        ax.barh(0, val, left=left, color=color, edgecolor="black",
                linewidth=0.5, label=f"{elem} ({val:.1f})")
        # Label inside the segment if wide enough
        if total > 0 and val > total * 0.08:
            ax.text(left + val / 2, 0, f"{val:.1f}",
                    ha="center", va="center", fontsize=9, fontweight="bold")
        left += val

    ax.set_yticks([])
    ax.set_xlabel("Mean Damage")
    ax.set_title(title or "Elemental Damage Breakdown")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    plt.close(fig)
    return fig


def elemental_vs_parameter(
    result: SimulationResult,
    variable_name: str,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Stacked bar chart of per-element mean damage across a swept parameter.

    Parameters
    ----------
    result:
        A :class:`SimulationResult` from ``run_sweep()``.
    variable_name:
        The variable to plot on the x-axis.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()
    import numpy as np

    # Collect data: x values and per-element means
    x_vals = []
    breakdowns: list[dict[str, float]] = []
    for cell in result.cells:
        if variable_name not in cell.variable_values:
            continue
        x_vals.append(cell.variable_values[variable_name])
        breakdowns.append(cell.elemental_breakdown.net_dict(include_zero=True))

    if not x_vals:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, f"No data for variable: {variable_name}",
                ha="center", va="center", transform=ax.transAxes)
        plt.close(fig)
        return fig

    # Find which elements have non-zero values anywhere
    all_elements = [
        "fire", "air", "earth", "water", "necro", "holy",
        "poison", "acid", "physical", "magic", "astral",
    ]
    active = [e for e in all_elements if any(b.get(e, 0) != 0 for b in breakdowns)]

    if not active:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No elemental damage data",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title(title or f"Elemental Damage vs. {variable_name}")
        plt.close(fig)
        return fig

    x = np.arange(len(x_vals))
    width = 0.7

    fig, ax = plt.subplots(figsize=figsize)
    bottom = np.zeros(len(x_vals))

    for elem in active:
        values = np.array([b.get(elem, 0.0) for b in breakdowns])
        color = _ELEMENT_COLORS.get(elem, "#BDBDBD")
        ax.bar(x, values, width, bottom=bottom, label=elem, color=color,
               edgecolor="black", linewidth=0.3)
        bottom += values

    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in x_vals])
    ax.set_xlabel(variable_name)
    ax.set_ylabel("Mean Elemental Damage")
    ax.set_title(title or f"Elemental Damage vs. {variable_name}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    plt.close(fig)
    return fig


def enchantment_comparison(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 5),
) -> Any:
    """Side-by-side comparison of enchantment effects on damage.

    Shows grouped bars for each scenario: physical damage (final_damage - elemental)
    and elemental/enchantment damage, with mean labels.

    Parameters
    ----------
    cells:
        Mapping of scenario label → :class:`CellResult`.
        E.g. ``{"Plain": plain_cell, "Fireball": fireball_cell, "Piercing": piercing_cell}``
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()
    import numpy as np

    labels = list(cells.keys())
    finals = [cells[l].damage_stats.mean for l in labels]
    elementals = [cells[l].elemental_breakdown.total_net for l in labels]
    drains = [cells[l].drain_stats.mean for l in labels]
    physicals = [f - e for f, e in zip(finals, elementals)]

    has_drains = any(d > 0 for d in drains)

    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=figsize)

    if has_drains:
        width = 0.25
        b1 = ax.bar(x - width, physicals, width, label="Physical",
                    color="#78909C", edgecolor="black", linewidth=0.5)
        b2 = ax.bar(x, elementals, width, label="Elemental/Enchantment",
                    color="#E53935", edgecolor="black", linewidth=0.5)
        b3 = ax.bar(x + width, drains, width, label="Drain (mana/hp/stam)",
                    color="#7B1FA2", edgecolor="black", linewidth=0.5)
        bar_groups = (b1, b2, b3)
    else:
        width = 0.3
        b1 = ax.bar(x - width / 2, physicals, width, label="Physical",
                    color="#78909C", edgecolor="black", linewidth=0.5)
        b2 = ax.bar(x + width / 2, elementals, width, label="Elemental/Enchantment",
                    color="#E53935", edgecolor="black", linewidth=0.5)
        bar_groups = (b1, b2)

    # Value labels
    for bars in bar_groups:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                        f"{h:.1f}", ha="center", va="bottom", fontsize=8)

    # Total damage line
    ax.plot(x, finals, "ko-", markersize=6, linewidth=1.5, label="Total")
    for xi, total in zip(x, finals):
        ax.text(xi, total + 0.8, f"{total:.1f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Mean Damage")
    ax.set_title(title or "Enchantment Comparison")
    ax.legend()
    fig.tight_layout()
    plt.close(fig)
    return fig


def dps_vs_parameter(
    result: SimulationResult,
    variable_name: str,
    *,
    show_range: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Line plot of effective DPS vs. a swept parameter.

    Shows effective DPS (accounting for hit rate) with optional damage-per-hit
    p5–p95 shaded range for context.

    Parameters
    ----------
    result:
        A :class:`SimulationResult` from ``run_sweep()``.
    variable_name:
        The variable to plot on the x-axis.
    show_range:
        If True, shade the damage p5–p95 range (secondary axis).
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    x_vals = []
    dps_vals = []
    delay_vals = []
    for cell in result.cells:
        if variable_name not in cell.variable_values:
            continue
        ts = cell.timing or TimingStats()
        x_vals.append(cell.variable_values[variable_name])
        dps_vals.append(ts.effective_dps)
        delay_vals.append(ts.swing_delay_ms)

    if not x_vals:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, f"No data for variable: {variable_name}",
                ha="center", va="center", transform=ax.transAxes)
        plt.close(fig)
        return fig

    fig, ax1 = plt.subplots(figsize=figsize)
    ax1.plot(x_vals, dps_vals, marker="o", linewidth=2, color="#E53935",
             label="Effective DPS")
    ax1.set_xlabel(variable_name)
    ax1.set_ylabel("DPS", color="#E53935")
    ax1.tick_params(axis="y", labelcolor="#E53935")

    # Secondary axis: swing delay
    ax2 = ax1.twinx()
    ax2.plot(x_vals, delay_vals, marker="s", linewidth=1, color="#1E88E5",
             linestyle="--", alpha=0.7, label="Swing Delay (ms)")
    ax2.set_ylabel("Swing Delay (ms)", color="#1E88E5")
    ax2.tick_params(axis="y", labelcolor="#1E88E5")

    ax1.set_title(title or f"DPS vs. {variable_name}")

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="best")

    fig.tight_layout()
    plt.close(fig)
    return fig


def dps_comparison(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Bar chart comparing DPS across named scenarios.

    Shows effective DPS with swing delay annotations.

    Parameters
    ----------
    cells:
        Mapping of scenario label → :class:`CellResult`.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    labels = list(cells.keys())
    dps_vals = []
    delays = []
    for label in labels:
        ts = cells[label].timing or TimingStats()
        dps_vals.append(ts.effective_dps)
        delays.append(ts.swing_delay_ms)

    fig, ax = plt.subplots(figsize=figsize)

    bars = ax.bar(labels, dps_vals, color="#E53935", edgecolor="black",
                  linewidth=0.5, alpha=0.85)

    # Label each bar with DPS value and swing delay
    for bar, dps, delay in zip(bars, dps_vals, delays):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.2,
                f"{dps:.2f}\n({delay:.0f}ms)",
                ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_ylabel("Effective DPS")
    ax.set_title(title or "DPS Comparison")
    fig.tight_layout()
    plt.close(fig)
    return fig


def spell_comparison(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 6),
    show_fizzle: bool = True,
    show_resist: bool = True,
) -> Any:
    """Bar chart comparing spells by mean on-cast damage.

    Each bar shows ``damage_stats_on_cast.mean`` for a spell scenario,
    color-coded by element when available.  Fizzle and resist rate
    annotations are added above each bar.

    Parameters
    ----------
    cells:
        Mapping of spell label → :class:`CellResult`.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.
    show_fizzle:
        Annotate fizzle rate above each bar.
    show_resist:
        Annotate resist rate above each bar.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    if not cells:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No spell data", ha="center", va="center",
                transform=ax.transAxes)
        ax.set_title(title or "Spell Comparison")
        plt.close(fig)
        return fig

    labels = list(cells.keys())
    means = [cells[l].damage_stats_on_cast.mean for l in labels]

    # Determine bar color from elemental breakdown (dominant element)
    colors = []
    for label in labels:
        cell = cells[label]
        eb = cell.elemental_breakdown.net_dict()
        if eb:
            dominant = max(eb, key=eb.get)
            colors.append(_ELEMENT_COLORS.get(dominant, "#78909C"))
        else:
            colors.append("#78909C")

    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(labels, means, color=colors, edgecolor="black", linewidth=0.5,
                  alpha=0.85)

    # Value labels and rate annotations
    for bar, label in zip(bars, labels):
        h = bar.get_height()
        cell = cells[label]

        # Damage value
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                f"{h:.1f}", ha="center", va="bottom", fontsize=10,
                fontweight="bold")

        # Rate annotations below the bar label
        annotations = []
        if show_fizzle and cell.ratios.fizzle_rate > 0:
            annotations.append(f"fizzle: {cell.ratios.fizzle_rate:.0%}")
        if show_resist and cell.ratios.resist_rate_on_cast > 0:
            annotations.append(f"resist: {cell.ratios.resist_rate_on_cast:.0%}")

        if annotations:
            ax.text(bar.get_x() + bar.get_width() / 2, -0.5,
                    "\n".join(annotations), ha="center", va="top",
                    fontsize=8, color="gray",
                    transform=ax.get_xaxis_transform())

    ax.set_ylabel("Mean Damage (on cast)")
    ax.set_title(title or "Spell Comparison")
    if len(labels) > 4:
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=15, ha="right")
    fig.tight_layout()
    plt.close(fig)
    return fig


def fizzle_rate_vs_parameter(
    result: SimulationResult,
    variable_name: str,
    *,
    show_resist: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Any:
    """Line plot of fizzle rate (and optionally resist rate) vs. a parameter.

    Parameters
    ----------
    result:
        A :class:`SimulationResult` from ``run_spell_sweep()``.
    variable_name:
        The variable to plot on the x-axis.
    show_resist:
        If True, also plot resist rate on the same axis.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()

    x_vals = []
    fizzle_vals = []
    resist_vals = []
    for cell in result.cells:
        if variable_name not in cell.variable_values:
            continue
        x_vals.append(cell.variable_values[variable_name])
        fizzle_vals.append(cell.ratios.fizzle_rate)
        resist_vals.append(cell.ratios.resist_rate_on_cast)

    if not x_vals:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, f"No data for variable: {variable_name}",
                ha="center", va="center", transform=ax.transAxes)
        plt.close(fig)
        return fig

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(x_vals, fizzle_vals, marker="o", linewidth=2, color="#E53935",
            label="Fizzle Rate")

    if show_resist:
        ax.plot(x_vals, resist_vals, marker="s", linewidth=2, color="#1E88E5",
                label="Resist Rate (on cast)")

    ax.set_xlabel(variable_name)
    ax.set_ylabel("Rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(title or f"Spell Rates vs. {variable_name}")
    ax.legend()
    fig.tight_layout()
    plt.close(fig)
    return fig


def armor_enchantment_comparison(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 5),
) -> Any:
    """Side-by-side comparison of armor enchantment effects.

    Shows grouped bars for each scenario: physical damage and total damage,
    with an overlay line for the onhit trigger rate.

    Parameters
    ----------
    cells:
        Mapping of enchantment label → :class:`CellResult`.
        E.g. ``{"Plain": plain_cell, "Fireball Armor": fb_cell, "Undead Hunter": uh_cell}``
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    plt = _require_matplotlib()
    import numpy as np

    labels = list(cells.keys())
    finals = [cells[l].damage_stats.mean for l in labels]
    trigger_rates = [cells[l].ratios.onhit_trigger_rate for l in labels]
    elementals = [cells[l].elemental_breakdown.total_net for l in labels]
    physicals = [f - e for f, e in zip(finals, elementals)]

    x = np.arange(len(labels))
    width = 0.3

    fig, ax1 = plt.subplots(figsize=figsize)

    b1 = ax1.bar(x - width / 2, physicals, width, label="Physical",
                  color="#78909C", edgecolor="black", linewidth=0.5)
    b2 = ax1.bar(x + width / 2, elementals, width, label="OnHit Additional",
                  color="#FF7043", edgecolor="black", linewidth=0.5)

    # Value labels
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                         f"{h:.1f}", ha="center", va="bottom", fontsize=8)

    # Total damage line
    ax1.plot(x, finals, "ko-", markersize=6, linewidth=1.5, label="Total Damage")
    for xi, total in zip(x, finals):
        ax1.text(xi, total + 0.8, f"{total:.1f}", ha="center", va="bottom",
                 fontsize=9, fontweight="bold")

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=15, ha="right")
    ax1.set_ylabel("Mean Damage")

    # Trigger rate on secondary axis
    ax2 = ax1.twinx()
    ax2.plot(x, trigger_rates, "s--", color="#1565C0", markersize=8,
             linewidth=1.5, label="OnHit Trigger Rate")
    for xi, rate in zip(x, trigger_rates):
        ax2.text(xi, rate + 0.02, f"{rate:.0%}", ha="center", va="bottom",
                 fontsize=8, color="#1565C0")
    ax2.set_ylabel("OnHit Trigger Rate", color="#1565C0")
    ax2.set_ylim(0, 1.1)
    ax2.tick_params(axis="y", labelcolor="#1565C0")

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    ax1.set_title(title or "Armor Enchantment Comparison")
    fig.tight_layout()
    plt.close(fig)
    return fig
