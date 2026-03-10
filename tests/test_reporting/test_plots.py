"""Tests for reporting plot functions."""

import pytest

from omega.combat.result import HitResult
from omega.reporting.plots import (
    comparison_overlay,
    damage_breakdown,
    damage_histogram,
    damage_vs_parameter,
)
from omega.simulation.stats import (
    CellResult,
    DamageStats,
    RatioStats,
    SimulationResult,
    aggregate_cell,
)

matplotlib = pytest.importorskip("matplotlib")


def _make_hits(n: int = 50, base: float = 15.0) -> list[HitResult]:
    """Generate n HitResult objects with varying damage."""
    return [
        HitResult(
            base_damage=int(base),
            raw_damage=int(base),
            final_damage=base - 5.0 + i * 0.5,
            absorbed=5.0,
            success=True,
        )
        for i in range(n)
    ]


def _make_cell(mean: float = 10.0, n: int = 50, **kw) -> CellResult:
    hits = _make_hits(n=n, base=mean + 5)
    cell = aggregate_cell(hits)
    cell.variable_values = kw.get("variable_values", {})
    return cell


class TestDamageHistogram:
    def test_returns_figure(self):
        cell = _make_cell()
        fig = damage_histogram(cell)
        assert type(fig).__name__ == "Figure"

    def test_custom_title(self):
        cell = _make_cell()
        fig = damage_histogram(cell, title="My Histogram")
        assert fig.axes[0].get_title() == "My Histogram"

    def test_custom_bins(self):
        cell = _make_cell()
        fig = damage_histogram(cell, bins=10)
        # Should have one axes with histogram patches
        assert len(fig.axes) == 1


class TestDamageVsParameter:
    def test_returns_figure(self):
        cells = [
            _make_cell(mean=10.0, variable_values={"skill": 50}),
            _make_cell(mean=15.0, variable_values={"skill": 75}),
            _make_cell(mean=20.0, variable_values={"skill": 100}),
        ]
        result = SimulationResult(cells=cells)
        fig = damage_vs_parameter(result, "skill")
        assert type(fig).__name__ == "Figure"

    def test_no_data_shows_message(self):
        result = SimulationResult(cells=[])
        fig = damage_vs_parameter(result, "nonexistent")
        assert type(fig).__name__ == "Figure"

    def test_without_range(self):
        cells = [
            _make_cell(mean=10.0, variable_values={"x": 1}),
            _make_cell(mean=20.0, variable_values={"x": 2}),
        ]
        result = SimulationResult(cells=cells)
        fig = damage_vs_parameter(result, "x", show_range=False)
        assert type(fig).__name__ == "Figure"


class TestDamageBreakdown:
    def test_returns_figure(self):
        cell = _make_cell()
        fig = damage_breakdown(cell)
        assert type(fig).__name__ == "Figure"

    def test_custom_title(self):
        cell = _make_cell()
        fig = damage_breakdown(cell, title="Breakdown")
        assert fig.axes[0].get_title() == "Breakdown"


class TestComparisonOverlay:
    def test_returns_figure(self):
        cells = {
            "Warrior": _make_cell(mean=25.0),
            "Mage": _make_cell(mean=15.0),
        }
        fig = comparison_overlay(cells)
        assert type(fig).__name__ == "Figure"

    def test_empty_cells(self):
        fig = comparison_overlay({})
        assert type(fig).__name__ == "Figure"

    def test_single_scenario(self):
        cells = {"Solo": _make_cell(mean=20.0)}
        fig = comparison_overlay(cells)
        assert type(fig).__name__ == "Figure"
