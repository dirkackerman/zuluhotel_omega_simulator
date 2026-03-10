"""Tests for reporting table functions."""

from omega.combat.result import HitResult
from omega.reporting.tables import (
    comparison_table,
    format_table_html,
    summary_table,
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


def _make_cell(
    *,
    mean: float = 10.0,
    median: float = 9.0,
    min_: float = 2.0,
    max_: float = 20.0,
    hit_rate: float = 0.9,
    variable_values: dict | None = None,
) -> CellResult:
    return CellResult(
        variable_values=variable_values or {},
        damage_stats=DamageStats(
            count=100, mean=mean, median=median,
            min=min_, max=max_, std_dev=3.5,
            p5=3.0, p25=6.0, p75=14.0, p95=18.0,
        ),
        base_damage_stats=DamageStats(count=100, mean=mean + 5),
        absorbed_stats=DamageStats(count=100, mean=5.0),
        ratios=RatioStats(hit_rate=hit_rate),
        iteration_count=100,
        success_count=90,
        error_count=10,
    )


class TestSummaryTable:
    def test_default_columns(self):
        result = SimulationResult(cells=[_make_cell()])
        rows = summary_table(result)

        assert len(rows) == 1
        row = rows[0]
        assert row["mean"] == 10.0
        assert row["median"] == 9.0
        assert row["hit_rate"] == 0.9
        assert row["count"] == 100

    def test_custom_columns(self):
        result = SimulationResult(cells=[_make_cell()])
        rows = summary_table(result, stats=["mean", "max"])

        assert list(rows[0].keys()) == ["mean", "max"]

    def test_variable_values_in_rows(self):
        cell = _make_cell(variable_values={"attacker.str_": 100})
        result = SimulationResult(cells=[cell])
        rows = summary_table(result)

        assert rows[0]["attacker.str_"] == 100

    def test_multiple_cells(self):
        cells = [
            _make_cell(mean=10.0, variable_values={"skill": 50}),
            _make_cell(mean=20.0, variable_values={"skill": 100}),
        ]
        result = SimulationResult(cells=cells)
        rows = summary_table(result)

        assert len(rows) == 2
        assert rows[0]["skill"] == 50
        assert rows[1]["skill"] == 100
        assert rows[0]["mean"] == 10.0
        assert rows[1]["mean"] == 20.0


class TestComparisonTable:
    def test_two_scenarios_with_delta(self):
        cells = {
            "Warrior": _make_cell(mean=25.0),
            "Mage": _make_cell(mean=15.0),
        }
        rows = comparison_table(cells, stats=["mean", "max"])

        assert len(rows) == 2
        mean_row = rows[0]
        assert mean_row["stat"] == "mean"
        assert mean_row["Warrior"] == 25.0
        assert mean_row["Mage"] == 15.0
        assert mean_row["delta"] == "-10.00"  # Mage - Warrior

    def test_three_scenarios_no_delta(self):
        cells = {
            "A": _make_cell(mean=10.0),
            "B": _make_cell(mean=20.0),
            "C": _make_cell(mean=30.0),
        }
        rows = comparison_table(cells, stats=["mean"])

        assert "delta" not in rows[0]

    def test_default_stats(self):
        cells = {"X": _make_cell()}
        rows = comparison_table(cells)

        stat_names = [r["stat"] for r in rows]
        assert "mean" in stat_names
        assert "hit_rate" in stat_names


class TestFormatTableHtml:
    def test_empty_rows(self):
        assert format_table_html([]) == "<table></table>"

    def test_basic_html(self):
        rows = [{"name": "Test", "value": 42}]
        html = format_table_html(rows)

        assert "<table" in html
        assert "Test" in html
        assert "42" in html
        assert "</table>" in html

    def test_escapes_html(self):
        rows = [{"col": "<script>alert('xss')</script>"}]
        html = format_table_html(rows)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_formats_floats(self):
        rows = [{"rate": 0.5, "damage": 42.567}]
        html = format_table_html(rows)

        assert "50.0%" in html
        assert "42.57" in html

    def test_from_real_aggregation(self):
        """End-to-end: aggregate → summary_table → HTML."""
        hits = [
            HitResult(base_damage=15, raw_damage=15, final_damage=10.0, absorbed=5.0, success=True),
            HitResult(base_damage=18, raw_damage=18, final_damage=12.0, absorbed=6.0, success=True),
            HitResult(base_damage=10, raw_damage=10, final_damage=8.0, absorbed=2.0, success=True),
        ]
        cell = aggregate_cell(hits)
        cell.variable_values = {"skill": 100}
        result = SimulationResult(cells=[cell])

        rows = summary_table(result, stats=["mean", "min", "max"])
        html = format_table_html(rows)

        assert "skill" in html
        assert "100" in html
        assert "10.00" in html  # mean


class TestElementalStatColumns:
    """Test elemental stat columns in summary_table."""

    def _make_elemental_cell(self) -> CellResult:
        cell = _make_cell()
        cell.elemental_breakdown = ElementalBreakdown(elements={
            "fire": ElementDamage(gross=20.0, net=14.0, prot=30.0, healed=0.0),
            "water": ElementDamage(gross=10.0, net=10.0, prot=0.0, healed=0.0),
        })
        return cell

    def test_elem_fire_defaults_to_net(self):
        result = SimulationResult(cells=[self._make_elemental_cell()])
        rows = summary_table(result, stats=["elem_fire"])
        assert rows[0]["elem_fire"] == 14.0

    def test_elem_fire_net_explicit(self):
        result = SimulationResult(cells=[self._make_elemental_cell()])
        rows = summary_table(result, stats=["elem_fire_net"])
        assert rows[0]["elem_fire_net"] == 14.0

    def test_elem_fire_gross(self):
        result = SimulationResult(cells=[self._make_elemental_cell()])
        rows = summary_table(result, stats=["elem_fire_gross"])
        assert rows[0]["elem_fire_gross"] == 20.0

    def test_elem_fire_prot(self):
        result = SimulationResult(cells=[self._make_elemental_cell()])
        rows = summary_table(result, stats=["elem_fire_prot"])
        assert rows[0]["elem_fire_prot"] == 30.0

    def test_elem_fire_absorbed(self):
        result = SimulationResult(cells=[self._make_elemental_cell()])
        rows = summary_table(result, stats=["elem_fire_absorbed"])
        assert rows[0]["elem_fire_absorbed"] == 6.0  # 20 - 14

    def test_elem_total_net(self):
        result = SimulationResult(cells=[self._make_elemental_cell()])
        rows = summary_table(result, stats=["elem_total_net"])
        assert rows[0]["elem_total_net"] == 24.0  # 14 + 10

    def test_elem_total_gross(self):
        result = SimulationResult(cells=[self._make_elemental_cell()])
        rows = summary_table(result, stats=["elem_total_gross"])
        assert rows[0]["elem_total_gross"] == 30.0  # 20 + 10

    def test_unknown_element_returns_empty(self):
        result = SimulationResult(cells=[self._make_elemental_cell()])
        rows = summary_table(result, stats=["elem_astral"])
        assert rows[0]["elem_astral"] == ""

    def test_no_elemental_data_returns_zero(self):
        result = SimulationResult(cells=[_make_cell()])
        rows = summary_table(result, stats=["elem_total_net"])
        assert rows[0]["elem_total_net"] == 0.0
