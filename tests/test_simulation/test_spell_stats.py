"""Tests for spell result aggregation via aggregate_spell_cell()."""

from omega.combat.spell_result import SpellResult
from omega.simulation.stats import (
    CellResult,
    DamageStats,
    TimingStats,
    aggregate_spell_cell,
    aggregate_cell,
)
from omega.combat.result import HitResult


def _make_spell(
    *,
    final_damage: float = 10.0,
    base_damage: int = 15,
    absorbed: float = 0.0,
    resisted: bool = False,
    fizzled: bool = False,
    cast_success: bool = True,
    immuned: bool = False,
    success: bool = True,
    casting_delay_ms: float = 0.0,
    metrics: dict | None = None,
    spell_id: int = 18,
) -> SpellResult:
    return SpellResult(
        spell_id=spell_id,
        base_damage=base_damage,
        final_damage=final_damage,
        absorbed=absorbed,
        resisted=resisted,
        fizzled=fizzled,
        cast_success=cast_success,
        immuned=immuned,
        success=success,
        casting_delay_ms=casting_delay_ms,
        metrics=metrics or {},
    )


class TestAggregateSpellCellEmpty:
    def test_empty_results(self):
        cell = aggregate_spell_cell([])
        assert cell.iteration_count == 0
        assert cell.damage_stats.count == 0
        assert cell.ratios.fizzle_rate == 0.0
        assert cell.ratios.resist_rate == 0.0
        assert cell.ratios.resist_rate_on_cast == 0.0


class TestAggregateSpellCellBasic:
    def test_single_success_no_fizzle(self):
        cell = aggregate_spell_cell([
            _make_spell(final_damage=20.0, base_damage=25),
        ])
        assert cell.iteration_count == 1
        assert cell.success_count == 1
        assert cell.damage_stats.mean == 20.0
        assert cell.ratios.fizzle_rate == 0.0
        assert cell.ratios.resist_rate == 0.0

    def test_multiple_successes(self):
        results = [_make_spell(final_damage=float(d)) for d in [10, 20, 30, 40, 50]]
        cell = aggregate_spell_cell(results)
        assert cell.damage_stats.count == 5
        assert cell.damage_stats.mean == 30.0
        assert cell.damage_stats.median == 30.0


class TestAggregateSpellCellFizzle:
    def test_fizzle_rate(self):
        """3 fizzles + 7 casts → fizzle_rate=0.3"""
        results = (
            [_make_spell(fizzled=True, final_damage=0.0, cast_success=False)] * 3
            + [_make_spell(final_damage=10.0)] * 7
        )
        cell = aggregate_spell_cell(results)
        assert cell.ratios.fizzle_rate == 0.3
        assert cell.ratios.hit_rate == 0.7  # cast success rate

    def test_all_fizzles(self):
        results = [_make_spell(fizzled=True, final_damage=0.0, cast_success=False)] * 10
        cell = aggregate_spell_cell(results)
        assert cell.ratios.fizzle_rate == 1.0
        assert cell.ratios.resist_rate_on_cast == 0.0  # no division by zero
        assert cell.damage_stats.mean == 0.0

    def test_damage_stats_include_fizzle_zeros(self):
        """damage_stats includes fizzle zeros, damage_stats_on_cast excludes them."""
        results = [
            _make_spell(fizzled=True, final_damage=0.0, cast_success=False),
            _make_spell(final_damage=20.0),
        ]
        cell = aggregate_spell_cell(results)
        # Overall includes the fizzle 0
        assert cell.damage_stats.mean == 10.0
        # On-cast excludes fizzles
        assert cell.damage_stats_on_cast.mean == 20.0


class TestAggregateSpellCellResist:
    def test_resist_rate_overall(self):
        """2 resisted / 10 total → resist_rate=0.2"""
        results = (
            [_make_spell(resisted=True, final_damage=5.0)] * 2
            + [_make_spell(final_damage=10.0)] * 8
        )
        cell = aggregate_spell_cell(results)
        assert cell.ratios.resist_rate == 0.2

    def test_resist_rate_on_cast(self):
        """2 resisted / 7 casts (3 fizzles) → resist_rate_on_cast ≈ 2/7"""
        results = (
            [_make_spell(fizzled=True, final_damage=0.0, cast_success=False)] * 3
            + [_make_spell(resisted=True, final_damage=5.0)] * 2
            + [_make_spell(final_damage=10.0)] * 5
        )
        cell = aggregate_spell_cell(results)
        assert abs(cell.ratios.resist_rate_on_cast - 2 / 7) < 1e-9
        assert cell.ratios.resist_rate == 0.2  # 2/10

    def test_resist_rate_with_all_fizzles(self):
        """All fizzles → resist counts stay zero, no division by zero."""
        results = [_make_spell(fizzled=True, final_damage=0.0, cast_success=False)] * 5
        cell = aggregate_spell_cell(results)
        assert cell.ratios.resist_rate == 0.0
        assert cell.ratios.resist_rate_on_cast == 0.0


class TestAggregateSpellCellErrors:
    def test_all_errors(self):
        results = [_make_spell(success=False)] * 5
        cell = aggregate_spell_cell(results)
        assert cell.error_count == 5
        assert cell.success_count == 0
        assert cell.damage_stats.count == 0

    def test_errors_excluded_from_stats(self):
        results = [
            _make_spell(final_damage=20.0),
            _make_spell(success=False),
        ]
        cell = aggregate_spell_cell(results)
        assert cell.iteration_count == 2
        assert cell.success_count == 1
        assert cell.error_count == 1
        assert cell.damage_stats.mean == 20.0


class TestAggregateSpellCellOnCast:
    def test_base_damage_from_casts_only(self):
        """base_damage_stats only from casts (fizzles have base_damage=0)."""
        results = [
            _make_spell(fizzled=True, final_damage=0.0, base_damage=0, cast_success=False),
            _make_spell(final_damage=20.0, base_damage=30),
            _make_spell(final_damage=15.0, base_damage=25),
        ]
        cell = aggregate_spell_cell(results)
        assert cell.base_damage_stats.mean == 27.5  # (30+25)/2
        assert cell.base_damage_stats.count == 2

    def test_damage_stats_on_hit_excludes_immuned(self):
        """On-hit = casts with damage > 0 (excludes immuned with 0 damage)."""
        results = [
            _make_spell(final_damage=20.0),
            _make_spell(immuned=True, final_damage=0.0, cast_success=False),
            _make_spell(final_damage=30.0),
        ]
        cell = aggregate_spell_cell(results)
        # on_hit excludes the immuned (0 damage) cast
        assert cell.damage_stats_on_hit.count == 2
        assert cell.damage_stats_on_hit.mean == 25.0

    def test_hit_rate_is_cast_success_rate(self):
        """hit_rate = n_casts / n_successes (analogous to weapon hit_rate)."""
        results = (
            [_make_spell(fizzled=True, final_damage=0.0, cast_success=False)] * 4
            + [_make_spell(final_damage=10.0)] * 6
        )
        cell = aggregate_spell_cell(results)
        assert cell.ratios.hit_rate == 0.6


class TestAggregateSpellCellImmuned:
    def test_immuned_not_counted_as_fizzle(self):
        """Immuned but not fizzled — counts as a cast, not a fizzle."""
        results = [
            _make_spell(immuned=True, fizzled=False, final_damage=0.0, cast_success=False),
            _make_spell(final_damage=10.0),
        ]
        cell = aggregate_spell_cell(results)
        # Both are casts (neither fizzled)
        assert cell.ratios.fizzle_rate == 0.0
        assert cell.ratios.hit_rate == 1.0  # both are "casts"

    def test_mixed_results(self):
        """Fizzle + immuned + resisted + clean hit — all counted correctly."""
        results = [
            _make_spell(fizzled=True, final_damage=0.0, cast_success=False),  # fizzle
            _make_spell(immuned=True, final_damage=0.0, cast_success=False),  # immuned cast
            _make_spell(resisted=True, final_damage=5.0),  # resisted cast
            _make_spell(final_damage=15.0),  # clean hit
        ]
        cell = aggregate_spell_cell(results)
        assert cell.ratios.fizzle_rate == 0.25  # 1/4
        assert cell.ratios.hit_rate == 0.75  # 3/4 casts
        assert cell.ratios.resist_rate == 0.25  # 1/4 overall
        assert abs(cell.ratios.resist_rate_on_cast - 1 / 3) < 1e-9  # 1/3 casts


class TestAggregateSpellCellUninit:
    def test_uninit_metric_values_handled(self):
        """UNINIT in absorbed field handled via _safe_float."""
        results = [
            _make_spell(final_damage=10.0, absorbed=0.0),
        ]
        # Directly set absorbed to a string to simulate UNINIT
        results[0].absorbed = "UNINIT"  # type: ignore[assignment]
        cell = aggregate_spell_cell(results)
        assert cell.absorbed_stats.mean == 0.0


class TestAggregateSpellCellTiming:
    def test_timing_from_casting_delay(self):
        """DPS computed from casting_delay_ms."""
        results = [
            _make_spell(final_damage=30.0, casting_delay_ms=1500.0),
            _make_spell(final_damage=20.0, casting_delay_ms=1500.0),
        ]
        cell = aggregate_spell_cell(results)
        assert cell.timing is not None
        assert cell.timing.swing_delay_ms == 1500.0
        assert abs(cell.timing.swings_per_second - 1000 / 1500) < 1e-9
        # mean damage = 25.0, casts_per_sec = 0.667
        expected_dps = 25.0 * (1000.0 / 1500.0)
        assert abs(cell.timing.dps_mean - expected_dps) < 0.01

    def test_timing_zero_delay(self):
        """No timing stats when casting delay is 0 (NPC mode)."""
        results = [
            _make_spell(final_damage=30.0, casting_delay_ms=0.0),
        ]
        cell = aggregate_spell_cell(results)
        assert cell.timing is None

    def test_timing_uses_first_non_fizzled(self):
        """Timing taken from first non-fizzled result."""
        results = [
            _make_spell(fizzled=True, final_damage=0.0, casting_delay_ms=0.0, cast_success=False),
            _make_spell(final_damage=20.0, casting_delay_ms=2000.0),
        ]
        cell = aggregate_spell_cell(results)
        assert cell.timing is not None
        assert cell.timing.swing_delay_ms == 2000.0

    def test_effective_dps(self):
        """effective_dps = cast_rate * mean_on_cast * casts_per_second."""
        results = (
            [_make_spell(fizzled=True, final_damage=0.0, casting_delay_ms=0.0, cast_success=False)] * 2
            + [_make_spell(final_damage=30.0, casting_delay_ms=1000.0)] * 8
        )
        cell = aggregate_spell_cell(results)
        assert cell.timing is not None
        cast_rate = 0.8  # 8/10
        mean_on_cast = 30.0
        casts_per_sec = 1.0  # 1000ms delay
        expected = cast_rate * mean_on_cast * casts_per_sec
        assert abs(cell.timing.effective_dps - expected) < 0.01


class TestAggregateSpellCellElemental:
    def test_elemental_breakdown_from_metrics(self):
        """Elemental breakdown populated from elemental_applied metrics."""
        results = [
            _make_spell(
                final_damage=20.0,
                metrics={"elemental_applied": [
                    {"attack_type": 0x0001, "dmg_gross": 20, "dmg_net": 15, "prot": 25},
                ]},
            ),
        ]
        cell = aggregate_spell_cell(results)
        assert "fire" in cell.elemental_breakdown.elements
        assert cell.elemental_breakdown.elements["fire"].net == 15.0

    def test_no_elemental_metrics(self):
        results = [_make_spell(final_damage=10.0)]
        cell = aggregate_spell_cell(results)
        assert cell.elemental_breakdown.elements == {}


class TestAggregateSpellCellRegression:
    def test_hit_aggregate_cell_has_zero_spell_rates(self):
        """Existing aggregate_cell for HitResults still has fizzle_rate=0.0."""
        hits = [
            HitResult(final_damage=10.0, base_damage=15, absorbed=5.0, success=True),
            HitResult(final_damage=20.0, base_damage=25, absorbed=5.0, success=True),
        ]
        cell = aggregate_cell(hits)
        # Spell-specific rates should be 0 for weapon hits
        assert cell.ratios.fizzle_rate == 0.0
        assert cell.ratios.resist_rate == 0.0
        assert cell.ratios.resist_rate_on_cast == 0.0


class TestAggregateSpellCellPercentiles:
    def test_percentiles_with_enough_data(self):
        results = [_make_spell(final_damage=float(i)) for i in range(1, 101)]
        cell = aggregate_spell_cell(results)
        assert cell.damage_stats.p5 < cell.damage_stats.p25
        assert cell.damage_stats.p25 < cell.damage_stats.median
        assert cell.damage_stats.median < cell.damage_stats.p75
        assert cell.damage_stats.p75 < cell.damage_stats.p95


class TestAggregateSpellCellRawResults:
    def test_raw_results_preserved(self):
        results = [_make_spell() for _ in range(5)]
        cell = aggregate_spell_cell(results)
        assert len(cell.raw_results) == 5
