"""Result aggregation and statistical computation for simulations.

Computes per-cell statistics (mean, median, percentiles, ratios) from
lists of :class:`~omega.combat.result.HitResult` objects.  Uses the
Python ``statistics`` standard library — no numpy required.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from omega.combat.result import HitResult


# ---------------------------------------------------------------------------
# Statistical summary dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DamageStats:
    """Statistical summary over a sequence of damage values."""

    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    min: float = 0.0
    max: float = 0.0
    std_dev: float = 0.0
    p5: float = 0.0
    p25: float = 0.0
    p75: float = 0.0
    p95: float = 0.0


@dataclass(slots=True)
class RatioStats:
    """Event frequency ratios (0.0–1.0)."""

    hit_rate: float = 0.0
    poison_rate: float = 0.0
    equipment_break_rate: float = 0.0


@dataclass
class CellResult:
    """Results for a single scenario (one cell in a sweep grid)."""

    variable_values: dict[str, Any] = field(default_factory=dict)
    damage_stats: DamageStats = field(default_factory=DamageStats)
    base_damage_stats: DamageStats = field(default_factory=DamageStats)
    absorbed_stats: DamageStats = field(default_factory=DamageStats)
    ratios: RatioStats = field(default_factory=RatioStats)
    raw_results: list[HitResult] = field(default_factory=list)
    iteration_count: int = 0
    success_count: int = 0
    error_count: int = 0


@dataclass
class SimulationResult:
    """Full results of a parameter sweep."""

    cells: list[CellResult] = field(default_factory=list)
    total_time: float = 0.0

    def get_cell(self, **variable_values: Any) -> CellResult | None:
        """Look up a cell by its variable values."""
        for cell in self.cells:
            if all(cell.variable_values.get(k) == v for k, v in variable_values.items()):
                return cell
        return None

    def damage_curve(self, variable_name: str) -> list[tuple[Any, DamageStats]]:
        """Extract ``(value, damage_stats)`` pairs for a single variable.

        Useful for plotting damage vs. a swept parameter.
        """
        return [
            (cell.variable_values.get(variable_name), cell.damage_stats)
            for cell in self.cells
            if variable_name in cell.variable_values
        ]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _compute_damage_stats(values: list[float]) -> DamageStats:
    """Compute statistical summary from a list of numeric values."""
    if not values:
        return DamageStats()

    n = len(values)
    sorted_vals = sorted(values)

    mean = statistics.mean(sorted_vals)
    median = statistics.median(sorted_vals)
    std_dev = statistics.stdev(sorted_vals) if n >= 2 else 0.0

    if n >= 4:
        quartiles = statistics.quantiles(sorted_vals, n=20)
        p5 = quartiles[0]    # 5th percentile  (index 0 of 20-quantiles)
        p25 = quartiles[4]   # 25th percentile (index 4)
        p75 = quartiles[14]  # 75th percentile (index 14)
        p95 = quartiles[18]  # 95th percentile (index 18)
    else:
        p5 = sorted_vals[0]
        p25 = sorted_vals[0]
        p75 = sorted_vals[-1]
        p95 = sorted_vals[-1]

    return DamageStats(
        count=n,
        mean=mean,
        median=median,
        min=sorted_vals[0],
        max=sorted_vals[-1],
        std_dev=std_dev,
        p5=p5,
        p25=p25,
        p75=p75,
        p95=p95,
    )


def aggregate_cell(results: list[HitResult]) -> CellResult:
    """Compute all statistics from a list of HitResult objects."""
    cell = CellResult(
        raw_results=results,
        iteration_count=len(results),
    )

    if not results:
        return cell

    # Separate successes/errors
    successes = [r for r in results if r.success]
    cell.success_count = len(successes)
    cell.error_count = len(results) - len(successes)

    if not successes:
        return cell

    # Damage stats (from successful hits only)
    final_damages = [r.final_damage for r in successes]
    base_damages = [float(r.base_damage) for r in successes]
    absorbed_vals = [r.absorbed for r in successes]

    cell.damage_stats = _compute_damage_stats(final_damages)
    cell.base_damage_stats = _compute_damage_stats(base_damages)
    cell.absorbed_stats = _compute_damage_stats(absorbed_vals)

    # Ratio stats
    n = len(successes)
    hits = sum(1 for r in successes if r.final_damage > 0)
    poisons = sum(
        1 for r in successes
        if any(se.kind == "poison_applied" for se in r.side_effects)
    )
    equip_breaks = sum(
        1 for r in successes
        if any(se.kind == "equipment_damaged" for se in r.side_effects)
    )

    cell.ratios = RatioStats(
        hit_rate=hits / n,
        poison_rate=poisons / n,
        equipment_break_rate=equip_breaks / n,
    )

    return cell
