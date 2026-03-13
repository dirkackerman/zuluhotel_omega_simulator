"""Tests for reporting plot functions."""

import pytest

from omega.combat.result import HitResult
from omega.combat.spell_result import SpellResult
from omega.reporting.plots import (
    comparison_overlay,
    damage_breakdown,
    damage_histogram,
    damage_vs_parameter,
    elemental_breakdown_chart,
    elemental_vs_parameter,
    enchantment_comparison,
    fizzle_rate_vs_parameter,
    spell_comparison,
)
from omega.simulation.stats import (
    CellResult,
    DamageStats,
    ElementDamage,
    ElementalBreakdown,
    RatioStats,
    SimulationResult,
    aggregate_cell,
    aggregate_spell_cell,
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


def _make_spell_results(
    n: int = 20,
    base_damage: int = 30,
    fizzle_count: int = 0,
    resist_count: int = 0,
) -> list[SpellResult]:
    """Generate SpellResult objects for testing."""
    results = []
    for i in range(n):
        if i < fizzle_count:
            results.append(SpellResult(
                spell_id=29, spell_name="Fireball", circle=3,
                fizzled=True, cast_success=False,
                final_damage=0.0, base_damage=0,
                success=True,
                metrics={"elemental_applied": [{"type": "fire", "dmg_gross": 0, "dmg_net": 0, "prot": 0}]},
            ))
        elif i < fizzle_count + resist_count:
            dmg = base_damage // 2 + i
            results.append(SpellResult(
                spell_id=29, spell_name="Fireball", circle=3,
                fizzled=False, cast_success=True, resisted=True,
                final_damage=float(dmg), base_damage=base_damage,
                success=True,
                casting_delay_ms=1500.0,
                metrics={"elemental_applied": [{"type": "fire", "dmg_gross": float(dmg + 5), "dmg_net": float(dmg), "prot": 10.0}]},
            ))
        else:
            dmg = base_damage + i
            results.append(SpellResult(
                spell_id=29, spell_name="Fireball", circle=3,
                fizzled=False, cast_success=True, resisted=False,
                final_damage=float(dmg), base_damage=base_damage,
                success=True,
                casting_delay_ms=1500.0,
                metrics={"elemental_applied": [{"type": "fire", "dmg_gross": float(dmg + 5), "dmg_net": float(dmg), "prot": 10.0}]},
            ))
    return results


def _make_spell_cell(
    n: int = 20,
    base_damage: int = 30,
    fizzle_count: int = 0,
    resist_count: int = 0,
    **kw,
) -> CellResult:
    results = _make_spell_results(n, base_damage, fizzle_count, resist_count)
    cell = aggregate_spell_cell(results)
    cell.variable_values = kw.get("variable_values", {})
    return cell


class TestSpellComparison:
    def test_returns_figure(self):
        cells = {
            "Fireball": _make_spell_cell(),
            "Flame Strike": _make_spell_cell(base_damage=60),
        }
        fig = spell_comparison(cells)
        assert type(fig).__name__ == "Figure"

    def test_custom_title(self):
        cells = {"Fireball": _make_spell_cell()}
        fig = spell_comparison(cells, title="Spell Test")
        assert fig.axes[0].get_title() == "Spell Test"

    def test_single_spell(self):
        cells = {"Solo": _make_spell_cell()}
        fig = spell_comparison(cells)
        assert type(fig).__name__ == "Figure"

    def test_empty_cells(self):
        fig = spell_comparison({})
        assert type(fig).__name__ == "Figure"

    def test_with_fizzle_data(self):
        cells = {"Fireball": _make_spell_cell(fizzle_count=5)}
        fig = spell_comparison(cells)
        assert type(fig).__name__ == "Figure"

    def test_show_fizzle_false(self):
        cells = {"Fireball": _make_spell_cell(fizzle_count=5)}
        fig = spell_comparison(cells, show_fizzle=False)
        assert type(fig).__name__ == "Figure"

    def test_show_resist_false(self):
        cells = {"Fireball": _make_spell_cell(resist_count=3)}
        fig = spell_comparison(cells, show_resist=False)
        assert type(fig).__name__ == "Figure"

    def test_with_real_spell_results(self):
        """Using aggregate_spell_cell with SpellResult objects."""
        results = _make_spell_results(n=50, fizzle_count=10, resist_count=5)
        cell = aggregate_spell_cell(results)
        cells = {"Fireball": cell}
        fig = spell_comparison(cells)
        assert type(fig).__name__ == "Figure"

    def test_multiple_spells_different_elements(self):
        fire_cell = _make_spell_cell()
        # Make an air spell cell
        air_results = [SpellResult(
            spell_id=49, spell_name="Lightning", circle=4,
            fizzled=False, cast_success=True, resisted=False,
            final_damage=40.0 + i, base_damage=45,
            success=True,
            metrics={"elemental_applied": [{"type": "air", "dmg_gross": 45.0, "dmg_net": 40.0 + i, "prot": 5.0}]},
        ) for i in range(20)]
        air_cell = aggregate_spell_cell(air_results)
        cells = {"Fireball": fire_cell, "Lightning": air_cell}
        fig = spell_comparison(cells)
        assert type(fig).__name__ == "Figure"


class TestFizzleRateVsParameter:
    def test_returns_figure(self):
        cells = [
            _make_spell_cell(fizzle_count=15, variable_values={"caster.skills.25": 50}),
            _make_spell_cell(fizzle_count=5, variable_values={"caster.skills.25": 80}),
            _make_spell_cell(fizzle_count=0, variable_values={"caster.skills.25": 110}),
        ]
        result = SimulationResult(cells=cells)
        fig = fizzle_rate_vs_parameter(result, "caster.skills.25")
        assert type(fig).__name__ == "Figure"

    def test_no_data(self):
        result = SimulationResult(cells=[])
        fig = fizzle_rate_vs_parameter(result, "missing")
        assert type(fig).__name__ == "Figure"

    def test_show_resist_false(self):
        cells = [
            _make_spell_cell(fizzle_count=5, variable_values={"x": 1}),
            _make_spell_cell(fizzle_count=0, variable_values={"x": 2}),
        ]
        result = SimulationResult(cells=cells)
        fig = fizzle_rate_vs_parameter(result, "x", show_resist=False)
        assert type(fig).__name__ == "Figure"

    def test_custom_title(self):
        cells = [_make_spell_cell(variable_values={"x": 1})]
        result = SimulationResult(cells=cells)
        fig = fizzle_rate_vs_parameter(result, "x", title="Custom")
        assert fig.axes[0].get_title() == "Custom"
