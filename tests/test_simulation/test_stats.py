"""Tests for result aggregation and statistics."""

from omega.combat.result import HitResult
from omega.runtime.context import SideEffect
from omega.simulation.stats import (
    CellResult,
    DamageStats,
    ElementDamage,
    ElementalBreakdown,
    SimulationResult,
    aggregate_cell,
)


def _make_hit(final_damage: float = 10.0, base_damage: int = 15,
              absorbed: float = 5.0, success: bool = True,
              side_effects: list | None = None) -> HitResult:
    return HitResult(
        base_damage=base_damage,
        raw_damage=base_damage,
        final_damage=final_damage,
        absorbed=absorbed,
        success=success,
        side_effects=side_effects or [],
    )


class TestAggregateCell:
    def test_empty_results(self):
        cell = aggregate_cell([])
        assert cell.iteration_count == 0
        assert cell.damage_stats.count == 0

    def test_single_result(self):
        cell = aggregate_cell([_make_hit(final_damage=20.0, base_damage=25)])
        assert cell.iteration_count == 1
        assert cell.success_count == 1
        assert cell.damage_stats.mean == 20.0
        assert cell.damage_stats.min == 20.0
        assert cell.damage_stats.max == 20.0
        assert cell.base_damage_stats.mean == 25.0

    def test_multiple_results(self):
        hits = [_make_hit(final_damage=float(d)) for d in [10, 20, 30, 40, 50]]
        cell = aggregate_cell(hits)
        assert cell.damage_stats.count == 5
        assert cell.damage_stats.mean == 30.0
        assert cell.damage_stats.median == 30.0
        assert cell.damage_stats.min == 10.0
        assert cell.damage_stats.max == 50.0
        assert cell.damage_stats.std_dev > 0

    def test_error_results_excluded_from_stats(self):
        hits = [
            _make_hit(final_damage=20.0),
            _make_hit(success=False),  # error
        ]
        cell = aggregate_cell(hits)
        assert cell.iteration_count == 2
        assert cell.success_count == 1
        assert cell.error_count == 1
        assert cell.damage_stats.mean == 20.0

    def test_all_errors(self):
        hits = [_make_hit(success=False), _make_hit(success=False)]
        cell = aggregate_cell(hits)
        assert cell.error_count == 2
        assert cell.damage_stats.count == 0

    def test_hit_rate(self):
        hits = [
            _make_hit(final_damage=10.0),
            _make_hit(final_damage=0.0),
            _make_hit(final_damage=5.0),
            _make_hit(final_damage=0.0),
        ]
        cell = aggregate_cell(hits)
        assert cell.ratios.hit_rate == 0.5

    def test_poison_rate(self):
        poison_se = SideEffect(kind="poison_applied", target_serial=1, value=3)
        hits = [
            _make_hit(side_effects=[poison_se]),
            _make_hit(),
            _make_hit(side_effects=[poison_se]),
            _make_hit(),
        ]
        cell = aggregate_cell(hits)
        assert cell.ratios.poison_rate == 0.5

    def test_equipment_break_rate(self):
        break_se = SideEffect(kind="equipment_damaged", target_serial=1)
        hits = [_make_hit(side_effects=[break_se])] + [_make_hit() for _ in range(9)]
        cell = aggregate_cell(hits)
        assert cell.ratios.equipment_break_rate == 0.1

    def test_absorbed_stats(self):
        hits = [_make_hit(absorbed=float(a)) for a in [5, 10, 15, 20, 25]]
        cell = aggregate_cell(hits)
        assert cell.absorbed_stats.mean == 15.0

    def test_raw_results_preserved(self):
        hits = [_make_hit() for _ in range(5)]
        cell = aggregate_cell(hits)
        assert len(cell.raw_results) == 5

    def test_percentiles_with_enough_data(self):
        hits = [_make_hit(final_damage=float(i)) for i in range(1, 101)]
        cell = aggregate_cell(hits)
        assert cell.damage_stats.p5 < cell.damage_stats.p25
        assert cell.damage_stats.p25 < cell.damage_stats.median
        assert cell.damage_stats.median < cell.damage_stats.p75
        assert cell.damage_stats.p75 < cell.damage_stats.p95


class TestSimulationResult:
    def test_get_cell(self):
        c1 = CellResult(variable_values={"attacker.skills.40": 50})
        c2 = CellResult(variable_values={"attacker.skills.40": 100})
        sr = SimulationResult(cells=[c1, c2])
        found = sr.get_cell(**{"attacker.skills.40": 100})
        assert found is c2

    def test_get_cell_not_found(self):
        sr = SimulationResult(cells=[])
        assert sr.get_cell(**{"foo": 1}) is None

    def test_damage_curve(self):
        cells = []
        for val in [50, 60, 70]:
            c = CellResult(variable_values={"attacker.skills.40": val})
            c.damage_stats = DamageStats(mean=float(val))
            cells.append(c)
        sr = SimulationResult(cells=cells)
        curve = sr.damage_curve("attacker.skills.40")
        assert len(curve) == 3
        assert curve[0] == (50, cells[0].damage_stats)
        assert curve[2] == (70, cells[2].damage_stats)


class TestElementDamage:
    def test_defaults(self):
        ed = ElementDamage()
        assert ed.gross == 0.0
        assert ed.net == 0.0
        assert ed.prot == 0.0
        assert ed.healed == 0.0
        assert ed.absorbed == 0.0

    def test_absorbed_is_gross_minus_net(self):
        ed = ElementDamage(gross=100.0, net=70.0)
        assert ed.absorbed == 30.0


class TestElementalBreakdown:
    def test_empty_breakdown(self):
        eb = ElementalBreakdown()
        assert eb.total_net == 0.0
        assert eb.total_gross == 0.0
        assert eb.net_dict() == {}
        assert eb.gross_dict() == {}
        assert eb.prot_dict() == {}

    def test_single_element(self):
        eb = ElementalBreakdown(elements={
            "fire": ElementDamage(gross=20.0, net=14.0, prot=30.0),
        })
        assert eb.total_net == 14.0
        assert eb.total_gross == 20.0
        assert eb.net_dict() == {"fire": 14.0}
        assert eb.gross_dict() == {"fire": 20.0}
        assert eb.prot_dict() == {"fire": 30.0}

    def test_multi_element(self):
        eb = ElementalBreakdown(elements={
            "fire": ElementDamage(gross=20.0, net=14.0, prot=30.0),
            "water": ElementDamage(gross=10.0, net=10.0, prot=0.0),
        })
        assert eb.total_net == 24.0
        assert eb.total_gross == 30.0

    def test_net_dict_include_zero(self):
        eb = ElementalBreakdown(elements={
            "fire": ElementDamage(net=5.0),
        })
        d = eb.net_dict(include_zero=True)
        assert d["fire"] == 5.0
        assert d["water"] == 0.0
        assert len(d) == 11  # all 11 elements

    def test_healed_element(self):
        eb = ElementalBreakdown(elements={
            "fire": ElementDamage(gross=10.0, net=0.0, prot=150.0, healed=5.0),
        })
        assert eb.elements["fire"].healed == 5.0
        assert eb.elements["fire"].absorbed == 10.0  # gross - net


class TestAggregateCellElemental:
    """Test elemental breakdown aggregation from HitResult.metrics."""

    def _make_elemental_hit(self, entries: list[dict]) -> HitResult:
        """Create a HitResult with elemental_applied metrics."""
        return HitResult(
            final_damage=10.0,
            base_damage=15,
            absorbed=5.0,
            success=True,
            metrics={"elemental_applied": entries},
        )

    def test_single_element_aggregation(self):
        hits = [
            self._make_elemental_hit([
                {"attack_type": 0x0001, "dmg_gross": 20, "dmg_net": 14, "prot": 30},
            ]),
            self._make_elemental_hit([
                {"attack_type": 0x0001, "dmg_gross": 20, "dmg_net": 14, "prot": 30},
            ]),
        ]
        cell = aggregate_cell(hits)
        eb = cell.elemental_breakdown
        assert "fire" in eb.elements
        assert eb.elements["fire"].gross == 20.0
        assert eb.elements["fire"].net == 14.0
        assert eb.elements["fire"].prot == 30.0

    def test_multi_element_aggregation(self):
        hits = [
            self._make_elemental_hit([
                {"attack_type": 0x0001, "dmg_gross": 10, "dmg_net": 7, "prot": 30},
                {"attack_type": 0x0008, "dmg_gross": 10, "dmg_net": 10, "prot": 0},
            ]),
        ]
        cell = aggregate_cell(hits)
        eb = cell.elemental_breakdown
        assert "fire" in eb.elements
        assert "water" in eb.elements
        assert eb.elements["fire"].net == 7.0
        assert eb.elements["water"].net == 10.0
        assert eb.total_net == 17.0

    def test_healed_aggregation(self):
        hits = [
            self._make_elemental_hit([
                {"attack_type": 0x0001, "prot": 150, "dmg_gross": 10, "healed": 5},
            ]),
        ]
        cell = aggregate_cell(hits)
        assert cell.elemental_breakdown.elements["fire"].healed == 5.0
        assert cell.elemental_breakdown.elements["fire"].prot == 150.0

    def test_no_elemental_metrics_empty_breakdown(self):
        hits = [_make_hit(final_damage=10.0)]
        cell = aggregate_cell(hits)
        assert cell.elemental_breakdown.elements == {}
        assert cell.elemental_breakdown.total_net == 0.0

    def test_mean_across_iterations(self):
        hits = [
            self._make_elemental_hit([
                {"attack_type": 0x0001, "dmg_gross": 20, "dmg_net": 10, "prot": 50},
            ]),
            self._make_elemental_hit([
                {"attack_type": 0x0001, "dmg_gross": 20, "dmg_net": 20, "prot": 0},
            ]),
        ]
        cell = aggregate_cell(hits)
        # Mean: (10 + 20) / 2 = 15 net, (50 + 0) / 2 = 25 prot
        assert cell.elemental_breakdown.elements["fire"].net == 15.0
        assert cell.elemental_breakdown.elements["fire"].prot == 25.0
