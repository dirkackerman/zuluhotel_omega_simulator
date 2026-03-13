"""Tests for the spell simulation runner using mock execute_spell."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from omega.combat.spell_result import SpellResult
from omega.config.spells import Spell
from omega.model.constants import SKILLID_MAGERY, SKILLID_EVALINT, SKILLID_MAGICRESISTANCE
from omega.parser.parser import ParseResult
from omega.simulation.spell_runner import run_spell_scenario, run_spell_sweep
from omega.simulation.scenario import (
    CombatantSpec,
    SpellParameterSweep,
    SpellScenario,
    Variable,
)


def _mock_parse_results() -> dict[Path, ParseResult]:
    return {Path("mock.src"): ParseResult(tree=MagicMock(), errors=[])}


def _make_mock_spell(
    damage: float = 10.0,
    fizzled: bool = False,
    resisted: bool = False,
    casting_delay_ms: float = 1500.0,
) -> SpellResult:
    return SpellResult(
        spell_id=int(Spell.FIREBALL),
        base_damage=int(damage) if not fizzled else 0,
        final_damage=damage if not fizzled else 0.0,
        fizzled=fizzled,
        resisted=resisted,
        cast_success=not fizzled,
        success=True,
        casting_delay_ms=casting_delay_ms if not fizzled else 0.0,
    )


def _base_caster() -> CombatantSpec:
    return CombatantSpec(
        name="Caster",
        int_=100,
        mana=100,
        skills={SKILLID_MAGERY: 100, SKILLID_EVALINT: 100},
    )


def _base_target() -> CombatantSpec:
    return CombatantSpec(
        name="Target",
        is_npc=True,
        hp=500,
        skills={SKILLID_MAGICRESISTANCE: 50},
    )


class TestRunSpellScenario:
    def test_runs_n_iterations(self):
        scenario = SpellScenario(
            caster=_base_caster(),
            target=_base_target(),
            spell_id=Spell.FIREBALL,
            iterations=5,
        )
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            mock_spell.return_value = _make_mock_spell(10.0)
            result = run_spell_scenario(scenario, parse_results=_mock_parse_results())

        assert mock_spell.call_count == 5
        assert result.iteration_count == 5
        assert result.damage_stats.mean == 10.0

    def test_deterministic_seeds(self):
        scenario = SpellScenario(
            caster=_base_caster(),
            target=_base_target(),
            spell_id=Spell.FIREBALL,
            iterations=3,
            base_seed=42,
        )
        seeds = []
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            def capture_seed(*args, **kwargs):
                seeds.append(kwargs.get("rng_seed"))
                return _make_mock_spell()
            mock_spell.side_effect = capture_seed
            run_spell_scenario(scenario, parse_results=_mock_parse_results())

        assert seeds == [42 ^ 0, 42 ^ 1, 42 ^ 2]

    def test_state_reset_between_iterations(self):
        """Caster mana and target HP should be restored each iteration."""
        scenario = SpellScenario(
            caster=CombatantSpec(
                name="Caster",
                int_=100,
                mana=100,
                skills={SKILLID_MAGERY: 100},
            ),
            target=CombatantSpec(name="Target", is_npc=True, hp=500),
            spell_id=Spell.FIREBALL,
            iterations=3,
        )
        target_hp_values = []
        caster_mana_values = []

        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            def track_state(pr, caster, target, spell_id, **kw):
                # target can be a single Mobile or list
                t = target if not isinstance(target, list) else target[0]
                target_hp_values.append(t.hp)
                caster_mana_values.append(caster.mana)
                # Simulate consumption
                t.hp -= 50
                caster.mana -= 10
                return _make_mock_spell(50.0)
            mock_spell.side_effect = track_state
            run_spell_scenario(scenario, parse_results=_mock_parse_results())

        assert target_hp_values == [500, 500, 500]
        assert caster_mana_values == [100, 100, 100]

    def test_executor_reuse(self):
        """Same executor instance passed to each call."""
        scenario = SpellScenario(
            caster=_base_caster(),
            target=_base_target(),
            spell_id=Spell.FIREBALL,
            iterations=3,
        )
        executors = []
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            def capture_executor(*args, **kwargs):
                executors.append(kwargs.get("executor"))
                return _make_mock_spell()
            mock_spell.side_effect = capture_executor
            run_spell_scenario(scenario, parse_results=_mock_parse_results())

        # All should be the same executor object
        assert len(executors) == 3
        assert executors[0] is executors[1]
        assert executors[1] is executors[2]

    def test_fizzle_rate_from_mock(self):
        """300/1000 fizzles → fizzle_rate=0.3"""
        scenario = SpellScenario(
            caster=_base_caster(),
            target=_base_target(),
            spell_id=Spell.FIREBALL,
            iterations=1000,
        )
        call_idx = [0]
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            def return_fizzle(*args, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                if idx < 300:
                    return _make_mock_spell(fizzled=True)
                return _make_mock_spell(10.0)
            mock_spell.side_effect = return_fizzle
            result = run_spell_scenario(scenario, parse_results=_mock_parse_results())

        assert result.ratios.fizzle_rate == 0.3

    def test_resist_rate_from_mock(self):
        """200/700 resisted casts (+ 300 fizzles) → resist_rate_on_cast ≈ 200/700"""
        scenario = SpellScenario(
            caster=_base_caster(),
            target=_base_target(),
            spell_id=Spell.FIREBALL,
            iterations=1000,
        )
        call_idx = [0]
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            def return_mixed(*args, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                if idx < 300:
                    return _make_mock_spell(fizzled=True)
                elif idx < 500:
                    return _make_mock_spell(5.0, resisted=True)
                return _make_mock_spell(10.0)
            mock_spell.side_effect = return_mixed
            result = run_spell_scenario(scenario, parse_results=_mock_parse_results())

        assert result.ratios.resist_rate == 0.2  # 200/1000
        assert abs(result.ratios.resist_rate_on_cast - 200 / 700) < 1e-9

    def test_aoe_list_targets(self):
        """AoE with list[CombatantSpec] targets — all get built."""
        targets = [
            CombatantSpec(name=f"Target{i}", is_npc=True, hp=500)
            for i in range(3)
        ]
        scenario = SpellScenario(
            caster=_base_caster(),
            target=targets,
            spell_id=Spell.CHAIN_LIGHTNING,
            iterations=1,
        )
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            def check_targets(pr, caster, target, spell_id, **kw):
                # Target should be a list of 3 mobiles
                assert isinstance(target, list)
                assert len(target) == 3
                return _make_mock_spell()
            mock_spell.side_effect = check_targets
            run_spell_scenario(scenario, parse_results=_mock_parse_results())

    def test_single_target_normalized(self):
        """Single CombatantSpec target is passed as single Mobile, not list."""
        scenario = SpellScenario(
            caster=_base_caster(),
            target=_base_target(),
            spell_id=Spell.FIREBALL,
            iterations=1,
        )
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            def check_target(pr, caster, target, spell_id, **kw):
                # Single target should be passed as-is (not wrapped in list)
                from omega.model.mobile import Mobile
                assert isinstance(target, Mobile)
                return _make_mock_spell()
            mock_spell.side_effect = check_target
            run_spell_scenario(scenario, parse_results=_mock_parse_results())

    def test_requires_parse_results_or_shard(self):
        scenario = SpellScenario(
            caster=_base_caster(),
            target=_base_target(),
            spell_id=Spell.FIREBALL,
            iterations=1,
        )
        with pytest.raises(ValueError, match="parse_results or shard"):
            run_spell_scenario(scenario)


class TestRunSpellSweep:
    def test_sweep_single_variable(self):
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=CombatantSpec(
                    name="Caster",
                    int_=100,
                    skills={SKILLID_MAGERY: 100},
                ),
                target=_base_target(),
                spell_id=Spell.FIREBALL,
                iterations=2,
            ),
            variables=(
                Variable.from_range("caster", f"skills.{SKILLID_MAGERY}", 50, 70, 10),
            ),
        )
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            mock_spell.return_value = _make_mock_spell()
            result = run_spell_sweep(sweep, parse_results=_mock_parse_results())

        # 3 values (50, 60, 70) × 2 iterations = 6 calls
        assert mock_spell.call_count == 6
        assert len(result.cells) == 3
        assert result.cells[0].variable_values == {f"caster.skills.{SKILLID_MAGERY}": 50}

    def test_sweep_target_variable(self):
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_base_caster(),
                target=CombatantSpec(
                    name="Target",
                    is_npc=True,
                    skills={SKILLID_MAGICRESISTANCE: 50},
                ),
                spell_id=Spell.FIREBALL,
                iterations=1,
            ),
            variables=(
                Variable(
                    target="target",
                    parameter=f"skills.{SKILLID_MAGICRESISTANCE}",
                    values=(0, 50, 100),
                ),
            ),
        )
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            mock_spell.return_value = _make_mock_spell()
            result = run_spell_sweep(sweep, parse_results=_mock_parse_results())

        assert len(result.cells) == 3

    def test_sweep_spell_id_variable(self):
        """Sweep spell_id across multiple spells."""
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_base_caster(),
                target=_base_target(),
                spell_id=Spell.FIREBALL,
                iterations=1,
            ),
            variables=(
                Variable(
                    target="spell",
                    parameter="spell_id",
                    values=(Spell.FIREBALL, Spell.LIGHTNING, Spell.FLAME_STRIKE),
                ),
            ),
        )
        spell_ids = []
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            def capture_spell_id(pr, caster, target, spell_id, **kw):
                spell_ids.append(spell_id)
                return _make_mock_spell()
            mock_spell.side_effect = capture_spell_id
            result = run_spell_sweep(sweep, parse_results=_mock_parse_results())

        assert len(result.cells) == 3
        assert spell_ids == [int(Spell.FIREBALL), int(Spell.LIGHTNING), int(Spell.FLAME_STRIKE)]

    def test_sweep_no_variables(self):
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_base_caster(),
                target=_base_target(),
                spell_id=Spell.FIREBALL,
                iterations=2,
            ),
        )
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            mock_spell.return_value = _make_mock_spell()
            result = run_spell_sweep(sweep, parse_results=_mock_parse_results())

        assert len(result.cells) == 1
        assert result.total_time > 0

    def test_sweep_two_variables_cartesian(self):
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_base_caster(),
                target=_base_target(),
                spell_id=Spell.FIREBALL,
                iterations=1,
            ),
            variables=(
                Variable(target="caster", parameter=f"skills.{SKILLID_MAGERY}", values=(80, 100)),
                Variable(target="target", parameter=f"skills.{SKILLID_MAGICRESISTANCE}", values=(0, 50)),
            ),
        )
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            mock_spell.return_value = _make_mock_spell()
            result = run_spell_sweep(sweep, parse_results=_mock_parse_results())

        # 2 × 2 = 4 cells
        assert len(result.cells) == 4

    def test_sweep_shard_integration(self):
        """Verify shard-based defaults are applied."""
        mock_shard = MagicMock()
        mock_shard.parse_combat_scripts.return_value = _mock_parse_results()
        mock_shard.resolve_config_path = MagicMock()
        mock_shard.root = Path("/fake/shard")
        mock_shard.package_map = {}
        mock_shard.spell_registry = MagicMock()

        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_base_caster(),
                target=_base_target(),
                spell_id=Spell.FIREBALL,
                iterations=1,
            ),
        )
        with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
            mock_spell.return_value = _make_mock_spell()
            result = run_spell_sweep(sweep, shard=mock_shard)

        mock_shard.parse_combat_scripts.assert_called_once()
        assert len(result.cells) == 1

    def test_deterministic_across_runs(self):
        """Same sweep produces identical seed sequences."""
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_base_caster(),
                target=_base_target(),
                spell_id=Spell.FIREBALL,
                iterations=3,
                base_seed=99,
            ),
        )
        call_logs = [[], []]
        for run_idx in range(2):
            with patch("omega.simulation.spell_runner.execute_spell") as mock_spell:
                def capture(pr, caster, target, spell_id, **kw):
                    call_logs[run_idx].append(kw.get("rng_seed"))
                    return _make_mock_spell()
                mock_spell.side_effect = capture
                run_spell_sweep(sweep, parse_results=_mock_parse_results())

        assert call_logs[0] == call_logs[1]
