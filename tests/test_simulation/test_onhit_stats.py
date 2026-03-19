"""Tests for armor onhit stats aggregation and reporting.

Covers:
- onhit_trigger_rate computed from onhit_type metric
- onhit_trigger_rate_on_hit conditional rate
- Detection across all three onhit categories (spell, slayer, effect)
- Rate = 0 when no onhit metrics
- _get_stat resolves onhit stats correctly
- Rate formatting as percentage
"""

import pytest

from omega.combat.result import HitResult
from omega.simulation.stats import aggregate_cell


class TestOnHitTriggerRate:
    """Test onhit_trigger_rate computation in aggregate_cell."""

    def test_all_triggered(self):
        """All iterations have onhit_type → rate = 1.0."""
        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "spell"}),
            HitResult(final_damage=10, metrics={"onhit_type": "piercing"}),
            HitResult(final_damage=10, metrics={"onhit_type": "slayer"}),
        ]
        cell = aggregate_cell(results)
        assert cell.ratios.onhit_trigger_rate == 1.0

    def test_half_triggered(self):
        """Half iterations have onhit_type → rate = 0.5."""
        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "spell"}),
            HitResult(final_damage=10, metrics={}),
            HitResult(final_damage=10, metrics={"onhit_type": "piercing"}),
            HitResult(final_damage=10, metrics={}),
        ]
        cell = aggregate_cell(results)
        assert cell.ratios.onhit_trigger_rate == 0.5

    def test_none_triggered(self):
        """No onhit_type → rate = 0.0."""
        results = [
            HitResult(final_damage=10, metrics={}),
            HitResult(final_damage=10, metrics={}),
        ]
        cell = aggregate_cell(results)
        assert cell.ratios.onhit_trigger_rate == 0.0

    def test_spell_type_detected(self):
        """onhit_type='spell' (from spellonhit.src) counts as trigger."""
        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "spell", "onhit_spell_id": 18}),
            HitResult(final_damage=10, metrics={}),
        ]
        cell = aggregate_cell(results)
        assert cell.ratios.onhit_trigger_rate == 0.5

    def test_slayer_type_detected(self):
        """onhit_type='slayer' (from raceresistonhit.src) counts as trigger."""
        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "slayer", "onhit_slayer_match": 1}),
            HitResult(final_damage=10, metrics={}),
        ]
        cell = aggregate_cell(results)
        assert cell.ratios.onhit_trigger_rate == 0.5

    def test_effect_type_detected(self):
        """onhit_type='piercing' (from piercingonhit.src) counts as trigger."""
        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "piercing"}),
        ]
        cell = aggregate_cell(results)
        assert cell.ratios.onhit_trigger_rate == 1.0

    def test_mixed_types(self):
        """Different onhit types in same scenario all count."""
        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "spell"}),
            HitResult(final_damage=10, metrics={"onhit_type": "slayer"}),
            HitResult(final_damage=10, metrics={"onhit_type": "trielemental"}),
            HitResult(final_damage=10, metrics={}),
        ]
        cell = aggregate_cell(results)
        assert cell.ratios.onhit_trigger_rate == 0.75


class TestOnHitTriggerRateOnHit:
    """Test conditional onhit rate (hits only, excluding misses)."""

    def test_on_hit_excludes_misses(self):
        """Misses (damage=0) excluded from on-hit rate denominator."""
        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "spell"}),  # hit + trigger
            HitResult(final_damage=0, metrics={}),  # miss
            HitResult(final_damage=10, metrics={}),  # hit, no trigger
            HitResult(final_damage=0, metrics={}),  # miss
        ]
        cell = aggregate_cell(results)
        # Overall: 1/4 = 0.25
        assert cell.ratios.onhit_trigger_rate == 0.25
        # On-hit: 1/2 = 0.5 (only 2 hits)
        assert cell.ratios.onhit_trigger_rate_on_hit == 0.5

    def test_no_hits_gives_zero(self):
        """All misses → on-hit rate = 0.0 (no division by zero)."""
        results = [
            HitResult(final_damage=0, metrics={}),
            HitResult(final_damage=0, metrics={}),
        ]
        cell = aggregate_cell(results)
        assert cell.ratios.onhit_trigger_rate_on_hit == 0.0


class TestOnHitStatReporting:
    """Test that onhit stats are accessible via _get_stat."""

    def test_get_stat_resolves(self):
        """_get_stat('onhit_trigger_rate') should return the correct value."""
        from omega.reporting.tables import _get_stat

        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "spell"}),
            HitResult(final_damage=10, metrics={}),
        ]
        cell = aggregate_cell(results)

        assert _get_stat(cell, "onhit_trigger_rate") == 0.5
        assert _get_stat(cell, "onhit_trigger_rate_on_hit") == 0.5

    def test_rate_formatted_as_percentage(self):
        """onhit rates should be formatted as percentages."""
        from omega.reporting.tables import _fmt

        assert _fmt(0.5, stat_name="onhit_trigger_rate") == "50.0%"
        assert _fmt(0.25, stat_name="onhit_trigger_rate_on_hit") == "25.0%"

    def test_onhit_in_summary_table(self):
        """summary_table should include onhit stats when requested."""
        from omega.reporting.tables import summary_table
        from omega.simulation.stats import SimulationResult

        results = [
            HitResult(final_damage=10, metrics={"onhit_type": "spell"}),
            HitResult(final_damage=10, metrics={}),
        ]
        cell = aggregate_cell(results)
        sim_result = SimulationResult(cells=[cell])

        rows = summary_table(sim_result, stats=["mean", "onhit_trigger_rate"])
        assert len(rows) == 1
        assert "onhit_trigger_rate" in rows[0]
