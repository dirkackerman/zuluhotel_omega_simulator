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

    damages = [r.final_damage for r in cell.raw_results if r.success]

    fig, ax = plt.subplots(figsize=figsize)
    ax.hist(damages, bins=bins, edgecolor="black", alpha=0.7)

    # Overlay mean and median
    ds = cell.damage_stats
    ax.axvline(ds.mean, color="red", linestyle="--", linewidth=1.5, label=f"Mean: {ds.mean:.1f}")
    ax.axvline(ds.median, color="orange", linestyle=":", linewidth=1.5, label=f"Median: {ds.median:.1f}")

    ax.set_xlabel("Final Damage")
    ax.set_ylabel("Frequency")
    ax.set_title(title or "Damage Distribution")
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
) -> Any:
    """Grouped bar showing base damage, absorbed, and final damage means.

    Parameters
    ----------
    cell:
        A :class:`CellResult` with stats populated.
    title:
        Optional figure title.
    figsize:
        Figure size in inches.

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
        damages = [r.final_damage for r in cell.raw_results if r.success]
        if damages:
            ax.hist(
                damages,
                bins=bins,
                alpha=0.5,
                label=f"{label} (μ={cell.damage_stats.mean:.1f})",
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
