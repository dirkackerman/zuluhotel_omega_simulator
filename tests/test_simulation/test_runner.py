"""Tests for the simulation runner using mock execute_hit."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from omega.combat.result import HitResult
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.parser.parser import ParseResult
from omega.simulation.runner import run_scenario, run_sweep
from omega.simulation.scenario import (
    ArmorSpec,
    CombatantSpec,
    ParameterSweep,
    Scenario,
    Variable,
    WeaponSpec,
)


def _mock_parse_results() -> dict[Path, ParseResult]:
    """A dummy parse_results dict to satisfy the runner's requirement."""
    return {Path("mock.src"): ParseResult(tree=MagicMock(), errors=[])}


def _make_mock_hit(damage: float = 10.0) -> HitResult:
    return HitResult(
        base_damage=15,
        raw_damage=15,
        final_damage=damage,
        absorbed=5.0,
        success=True,
    )


class TestRunScenario:
    def test_runs_n_iterations(self):
        scenario = Scenario(
            attacker=CombatantSpec(
                name="Atk",
                skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
                weapon=WeaponSpec(),
            ),
            defender=CombatantSpec(name="Def", is_npc=True, armor=ArmorSpec(ar=30)),
            iterations=5,
        )

        with patch("omega.simulation.runner.execute_hit") as mock_hit:
            mock_hit.return_value = _make_mock_hit(10.0)
            result = run_scenario(scenario, parse_results=_mock_parse_results())

        assert mock_hit.call_count == 5
        assert result.iteration_count == 5
        assert result.damage_stats.mean == 10.0

    def test_deterministic_seeds(self):
        scenario = Scenario(
            attacker=CombatantSpec(weapon=WeaponSpec()),
            defender=CombatantSpec(armor=ArmorSpec(ar=10)),
            iterations=3,
            base_seed=42,
        )

        seeds = []
        with patch("omega.simulation.runner.execute_hit") as mock_hit:
            def capture_seed(*args, **kwargs):
                seeds.append(kwargs.get("rng_seed"))
                return _make_mock_hit()
            mock_hit.side_effect = capture_seed
            run_scenario(scenario, parse_results=_mock_parse_results())

        assert seeds == [42 ^ 0, 42 ^ 1, 42 ^ 2]

    def test_state_reset_between_iterations(self):
        """Defender HP should be the same at start of each iteration."""
        scenario = Scenario(
            attacker=CombatantSpec(weapon=WeaponSpec()),
            defender=CombatantSpec(hp=500, armor=ArmorSpec(ar=10)),
            iterations=3,
        )

        defender_hp_values = []
        original_execute_hit = None

        with patch("omega.simulation.runner.execute_hit") as mock_hit:
            def track_hp(parse_results, attacker, defender, weapon, armor, **kw):
                defender_hp_values.append(defender.hp)
                # Simulate damage by modifying defender HP
                defender.hp -= 50
                return _make_mock_hit(50.0)
            mock_hit.side_effect = track_hp
            run_scenario(scenario, parse_results=_mock_parse_results())

        # HP should be 500 at start of every iteration (restored)
        assert defender_hp_values == [500, 500, 500]

    def test_requires_parse_results_or_shard(self):
        scenario = Scenario(
            attacker=CombatantSpec(weapon=WeaponSpec()),
            defender=CombatantSpec(),
            iterations=1,
        )
        import pytest
        with pytest.raises(ValueError, match="parse_results or shard"):
            run_scenario(scenario)


class TestRunSweep:
    def test_sweep_generates_correct_cells(self):
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=CombatantSpec(
                    skills={SKILLID_SWORDSMANSHIP: 100},
                    weapon=WeaponSpec(),
                ),
                defender=CombatantSpec(armor=ArmorSpec(ar=10)),
                iterations=2,
            ),
            variables=(
                Variable.from_range("attacker", f"skills.{SKILLID_SWORDSMANSHIP}", 50, 70, 10),
            ),
        )

        with patch("omega.simulation.runner.execute_hit") as mock_hit:
            mock_hit.return_value = _make_mock_hit(10.0)
            result = run_sweep(sweep, parse_results=_mock_parse_results())

        # 3 values (50, 60, 70) × 2 iterations each = 6 total calls
        assert mock_hit.call_count == 6
        assert len(result.cells) == 3
        assert result.cells[0].variable_values == {f"attacker.skills.{SKILLID_SWORDSMANSHIP}": 50}
        assert result.cells[2].variable_values == {f"attacker.skills.{SKILLID_SWORDSMANSHIP}": 70}

    def test_sweep_no_variables(self):
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=CombatantSpec(weapon=WeaponSpec()),
                defender=CombatantSpec(armor=ArmorSpec()),
                iterations=2,
            ),
        )

        with patch("omega.simulation.runner.execute_hit") as mock_hit:
            mock_hit.return_value = _make_mock_hit()
            result = run_sweep(sweep, parse_results=_mock_parse_results())

        assert len(result.cells) == 1
        assert result.total_time > 0

    def test_sweep_multi_variable(self):
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=CombatantSpec(weapon=WeaponSpec()),
                defender=CombatantSpec(armor=ArmorSpec(ar=10)),
                iterations=1,
            ),
            variables=(
                Variable(target="attacker", parameter="str_", values=(80, 100)),
                Variable(target="defender", parameter="str_", values=(50, 60)),
            ),
        )

        with patch("omega.simulation.runner.execute_hit") as mock_hit:
            mock_hit.return_value = _make_mock_hit()
            result = run_sweep(sweep, parse_results=_mock_parse_results())

        # 2 × 2 = 4 cells
        assert len(result.cells) == 4
        # Check that all combos are represented
        combos = [
            (c.variable_values["attacker.str_"], c.variable_values["defender.str_"])
            for c in result.cells
        ]
        assert (80, 50) in combos
        assert (80, 60) in combos
        assert (100, 50) in combos
        assert (100, 60) in combos

    def test_sweep_shard_integration(self):
        """Verify shard-based defaults are applied."""
        mock_shard = MagicMock()
        mock_shard.parse_combat_scripts.return_value = _mock_parse_results()
        mock_shard.resolve_config_path = MagicMock()
        mock_shard.root = Path("/fake/shard")

        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=CombatantSpec(weapon=WeaponSpec()),
                defender=CombatantSpec(armor=ArmorSpec()),
                iterations=1,
            ),
        )

        with patch("omega.simulation.runner.execute_hit") as mock_hit:
            mock_hit.return_value = _make_mock_hit()
            result = run_sweep(sweep, shard=mock_shard)

        mock_shard.parse_combat_scripts.assert_called_once()
        assert len(result.cells) == 1

    def test_deterministic_across_runs(self):
        """Same sweep produces identical results."""
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=CombatantSpec(weapon=WeaponSpec()),
                defender=CombatantSpec(armor=ArmorSpec()),
                iterations=3,
                base_seed=99,
            ),
        )

        call_logs = [[], []]
        for run_idx in range(2):
            with patch("omega.simulation.runner.execute_hit") as mock_hit:
                def capture(pr, atk, dfn, wpn, arm, **kw):
                    call_logs[run_idx].append(kw.get("rng_seed"))
                    return _make_mock_hit()
                mock_hit.side_effect = capture
                run_sweep(sweep, parse_results=_mock_parse_results())

        assert call_logs[0] == call_logs[1]
