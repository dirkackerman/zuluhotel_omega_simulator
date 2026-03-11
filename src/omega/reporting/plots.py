"""Matplotlib figure factories for simulation results.

All functions return ``matplotlib.figure.Figure`` objects, ready for
``fig.savefig(...)`` or inline display in Jupyter notebooks.

Matplotlib is an optional dependency — import errors are raised at call
time, not at module import.
"""

from __future__ import annotations

from typing import Any

from omega.simulation.stats import CellResult, SimulationResult


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
