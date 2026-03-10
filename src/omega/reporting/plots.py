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
    """Stacked bar showing base damage, absorbed, and final damage means.

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

    fig, ax = plt.subplots(figsize=figsize)

    bars = ax.bar(
        ["Damage"],
        [final],
        label=f"Final: {final:.1f}",
        color="#4CAF50",
    )
    ax.bar(
        ["Damage"],
        [absorbed],
        bottom=[final],
        label=f"Absorbed: {absorbed:.1f}",
        color="#FF9800",
        alpha=0.7,
    )

    ax.set_ylabel("Damage")
    ax.set_title(title or "Damage Breakdown")
    ax.legend()

    # Annotate total base damage
    ax.annotate(
        f"Base: {base:.1f}",
        xy=(0, base),
        xytext=(0.3, base + base * 0.05),
        fontsize=9,
        color="gray",
    )

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
