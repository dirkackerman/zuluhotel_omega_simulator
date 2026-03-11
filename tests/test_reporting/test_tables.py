"""Tests for reporting table functions."""

from omega.combat.result import HitResult
from omega.reporting.tables import (
    _RATE_STATS,
    _fmt,
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
        """Rate stats are formatted as percentages; other floats as decimals."""
        # comparison_table format: {"stat": "...", "label": value}
        rows = [
            {"stat": "hit_rate", "A": 0.5},
            {"stat": "mean", "A": 42.567},
            {"stat": "effect_rate", "A": 0.06},
        ]
        html = format_table_html(rows)

        assert "50.0%" in html     # hit_rate → percentage
        assert "42.57" in html     # mean → float
        assert "6.0%" in html      # effect_rate → percentage

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


class TestEnchantmentStatColumns:
    """Test enchantment-related stat columns in summary_table."""

    def test_spell_strike_rate(self):
        cell = _make_cell()
        cell.ratios.spell_strike_rate = 0.42
        result = SimulationResult(cells=[cell])
        rows = summary_table(result, stats=["spell_strike_rate"])
        assert rows[0]["spell_strike_rate"] == 0.42

    def test_reactive_rate(self):
        cell = _make_cell()
        cell.ratios.reactive_rate = 0.15
        result = SimulationResult(cells=[cell])
        rows = summary_table(result, stats=["reactive_rate"])
        assert rows[0]["reactive_rate"] == 0.15

    def test_effect_rate(self):
        cell = _make_cell()
        cell.ratios.effect_rate = 0.33
        result = SimulationResult(cells=[cell])
        rows = summary_table(result, stats=["effect_rate"])
        assert rows[0]["effect_rate"] == 0.33

    def test_all_enchantment_columns(self):
        cell = _make_cell()
        cell.ratios.spell_strike_rate = 0.5
        cell.ratios.reactive_rate = 0.2
        cell.ratios.effect_rate = 0.3
        result = SimulationResult(cells=[cell])
        rows = summary_table(
            result,
            stats=["mean", "spell_strike_rate", "reactive_rate", "effect_rate"],
        )
        row = rows[0]
        assert row["spell_strike_rate"] == 0.5
        assert row["reactive_rate"] == 0.2
        assert row["effect_rate"] == 0.3


class TestDrainStatColumns:
    """Test drain_mean and drain_total stat columns."""

    def test_drain_mean(self):
        cell = _make_cell()
        cell.drain_stats = DamageStats(count=10, mean=5.0)
        result = SimulationResult(cells=[cell])
        rows = summary_table(result, stats=["drain_mean"])
        assert rows[0]["drain_mean"] == 5.0

    def test_drain_total(self):
        cell = _make_cell()
        cell.drain_stats = DamageStats(count=10, mean=5.0)
        result = SimulationResult(cells=[cell])
        rows = summary_table(result, stats=["drain_total"])
        assert rows[0]["drain_total"] == 50.0

    def test_drain_mean_no_drains(self):
        """Default drain_stats has mean=0."""
        cell = _make_cell()
        result = SimulationResult(cells=[cell])
        rows = summary_table(result, stats=["drain_mean"])
        assert rows[0]["drain_mean"] == 0.0

    def test_drain_in_comparison_table(self):
        cells = {
            "Vampiric": _make_cell(),
            "Plain": _make_cell(),
        }
        cells["Vampiric"].drain_stats = DamageStats(count=100, mean=7.5)
        rows = comparison_table(cells, stats=["drain_mean"])
        assert rows[0]["Vampiric"] == 7.5
        assert rows[0]["Plain"] == 0.0
        assert "delta" in rows[0]  # 2 scenarios → delta

    def test_drain_in_comparison_delta(self):
        cells = {
            "A": _make_cell(),
            "B": _make_cell(),
        }
        cells["A"].drain_stats = DamageStats(count=100, mean=10.0)
        cells["B"].drain_stats = DamageStats(count=100, mean=4.0)
        rows = comparison_table(cells, stats=["drain_mean"])
        assert rows[0]["delta"] == "-6.00"


class TestFmtFormatting:
    """Test _fmt formatting logic — rates as percentages, other floats as decimals."""

    def test_rate_stat_formatted_as_percentage(self):
        assert _fmt(0.5, stat_name="hit_rate") == "50.0%"

    def test_non_rate_stat_formatted_as_decimal(self):
        assert _fmt(0.5, stat_name="mean") == "0.50"

    def test_non_rate_small_float_not_percentage(self):
        """Regression: small floats like drain_mean=0.5 must NOT become '50.0%'."""
        assert _fmt(0.5, stat_name="drain_mean") == "0.50"
        assert _fmt(0.05, stat_name="drain_mean") == "0.05"

    def test_rate_at_zero(self):
        assert _fmt(0.0, stat_name="hit_rate") == "0.0%"

    def test_rate_at_one(self):
        assert _fmt(1.0, stat_name="hit_rate") == "100.0%"

    def test_no_stat_name_uses_decimal(self):
        """Without stat_name context, floats should be plain decimals."""
        assert _fmt(0.75) == "0.75"
        assert _fmt(0.05) == "0.05"

    def test_integer_formatted_as_string(self):
        assert _fmt(42) == "42"

    def test_string_passthrough(self):
        assert _fmt("hello") == "hello"

    def test_all_rate_stats_are_known(self):
        """All rate stats in _RATE_STATS should be recognized."""
        expected = {
            "hit_rate", "poison_rate", "equipment_break_rate",
            "reactive_rate", "spell_strike_rate", "effect_rate",
            "reactive_rate_on_hit", "spell_strike_rate_on_hit", "effect_rate_on_hit",
        }
        assert _RATE_STATS == expected

    def test_elem_total_not_rate(self):
        """elem_total_net is a damage value, not a rate."""
        assert _fmt(0.5, stat_name="elem_total_net") == "0.50"

    def test_drain_mean_not_rate(self):
        """drain_mean is a damage value, not a rate."""
        assert _fmt(3.5, stat_name="drain_mean") == "3.50"


class TestFormatTableHtmlRateFormatting:
    """Test that format_table_html correctly formats rates vs non-rates."""

    def test_comparison_table_rate_as_percentage(self):
        """Rate stats in comparison tables should be formatted as percentages."""
        rows = [{"stat": "hit_rate", "A": 0.75}]
        html = format_table_html(rows)
        assert "75.0%" in html

    def test_comparison_table_damage_as_decimal(self):
        """Damage stats in comparison tables should NOT be formatted as percentages."""
        rows = [{"stat": "drain_mean", "A": 0.5}]
        html = format_table_html(rows)
        assert "0.50" in html
        assert "50.0%" not in html

    def test_comparison_table_elem_total_as_decimal(self):
        """elem_total_net in comparison tables should be a decimal, not percentage."""
        rows = [{"stat": "elem_total_net", "A": 0.8}]
        html = format_table_html(rows)
        assert "0.80" in html
        assert "80.0%" not in html

    def test_summary_table_html_rates_formatted(self):
        """In summary tables (no 'stat' column), rate columns use header name."""
        cell = _make_cell()
        cell.ratios.effect_rate = 0.33
        result = SimulationResult(cells=[cell])
        rows = summary_table(result, stats=["effect_rate", "mean"])
        html = format_table_html(rows)
        assert "33.0%" in html  # effect_rate as percentage
        assert "10.00" in html  # mean as decimal
