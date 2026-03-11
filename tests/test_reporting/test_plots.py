"""Tests for reporting plot functions."""

import pytest

from omega.combat.result import HitResult
from omega.reporting.plots import (
    comparison_overlay,
    damage_breakdown,
    damage_histogram,
    damage_vs_parameter,
    elemental_breakdown_chart,
    elemental_vs_parameter,
    enchantment_comparison,
)
from omega.simulation.stats import (
    CellResult,
    DamageStats,
    ElementDamage,
    ElementalBreakdown,
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


def _make_elemental_cell(**kw) -> CellResult:
    cell = _make_cell(**kw)
    cell.elemental_breakdown = ElementalBreakdown(elements={
        "fire": ElementDamage(gross=20.0, net=14.0, prot=30.0),
        "water": ElementDamage(gross=10.0, net=10.0, prot=0.0),
    })
    return cell


class TestElementalBreakdownChart:
    def test_returns_figure(self):
        cell = _make_elemental_cell()
        fig = elemental_breakdown_chart(cell)
        assert type(fig).__name__ == "Figure"

    def test_custom_title(self):
        cell = _make_elemental_cell()
        fig = elemental_breakdown_chart(cell, title="Element Test")
        assert fig.axes[0].get_title() == "Element Test"

    def test_empty_breakdown(self):
        cell = _make_cell()
        fig = elemental_breakdown_chart(cell)
        assert type(fig).__name__ == "Figure"


class TestElementalVsParameter:
    def test_returns_figure(self):
        cells = [
            _make_elemental_cell(variable_values={"prot": 0}),
            _make_elemental_cell(variable_values={"prot": 50}),
        ]
        result = SimulationResult(cells=cells)
        fig = elemental_vs_parameter(result, "prot")
        assert type(fig).__name__ == "Figure"

    def test_no_data(self):
        result = SimulationResult(cells=[])
        fig = elemental_vs_parameter(result, "x")
        assert type(fig).__name__ == "Figure"

    def test_no_elemental_data(self):
        cells = [_make_cell(variable_values={"x": 1})]
        result = SimulationResult(cells=cells)
        fig = elemental_vs_parameter(result, "x")
        assert type(fig).__name__ == "Figure"


class TestDamageBreakdownElemental:
    """Test damage_breakdown with elemental data."""

    def test_includes_elemental_bar(self):
        cell = _make_elemental_cell()
        fig = damage_breakdown(cell)
        ax = fig.axes[0]
        # Should have 4 bars: Base, Absorbed, Final, Elemental
        patches = ax.patches
        assert len(patches) == 4

    def test_no_elemental_bar_without_data(self):
        cell = _make_cell()
        fig = damage_breakdown(cell)
        ax = fig.axes[0]
        assert len(ax.patches) == 3  # Base, Absorbed, Final

    def test_show_elemental_false(self):
        cell = _make_elemental_cell()
        fig = damage_breakdown(cell, show_elemental=False)
        ax = fig.axes[0]
        assert len(ax.patches) == 3


class TestEnchantmentComparison:
    def test_returns_figure(self):
        cells = {
            "Plain": _make_cell(mean=20.0),
            "Fireball": _make_elemental_cell(mean=30.0),
        }
        fig = enchantment_comparison(cells)
        assert type(fig).__name__ == "Figure"

    def test_custom_title(self):
        cells = {
            "A": _make_cell(mean=10.0),
            "B": _make_cell(mean=20.0),
        }
        fig = enchantment_comparison(cells, title="Compare")
        assert fig.axes[0].get_title() == "Compare"

    def test_single_scenario(self):
        cells = {"Only": _make_cell(mean=15.0)}
        fig = enchantment_comparison(cells)
        assert type(fig).__name__ == "Figure"

    def test_three_scenarios(self):
        cells = {
            "Plain": _make_cell(mean=10.0),
            "Piercing": _make_cell(mean=15.0),
            "Fireball": _make_elemental_cell(mean=25.0),
        }
        fig = enchantment_comparison(cells)
        assert type(fig).__name__ == "Figure"

    def test_with_drain_stats(self):
        """When drain_stats.mean > 0, a third 'Drain' bar group should appear."""
        plain = _make_cell(mean=20.0)
        vampiric = _make_cell(mean=20.0)
        vampiric.drain_stats = DamageStats(count=50, mean=5.0)
        cells = {"Plain": plain, "Vampiric": vampiric}
        fig = enchantment_comparison(cells)
        assert type(fig).__name__ == "Figure"
        # Should have 3 bar groups (Physical, Elemental, Drain) in the legend
        legend_texts = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
        assert any("Drain" in t for t in legend_texts)
