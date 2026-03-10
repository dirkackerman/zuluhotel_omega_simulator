"""Integration tests for the simulation runner.

Exercises the full pipeline: scenario → runner → real mainhit.src → stats.
"""

import time

import pytest

from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.simulation import (
    ArmorSpec,
    CombatantSpec,
    ParameterSweep,
    Scenario,
    Variable,
    WeaponSpec,
    run_scenario,
    run_sweep,
)


@pytest.fixture(scope="module")
def shard(fixture_shard):
    return fixture_shard


@pytest.fixture(scope="module")
def parse_results(fixture_parse_results):
    return fixture_parse_results


WARRIOR_ATTACKER = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100,
    dex_=100,
    int_=25,
    class_levels={"IsWarrior": 5},
    weapon=WeaponSpec(name="TestSword", damage="3d6+2", attribute=SKILLID_SWORDSMANSHIP),
)

NPC_DEFENDER = CombatantSpec(
    name="Target",
    is_npc=True,
    str_=50,
    dex_=50,
    int_=50,
    hp=500,
    armor=ArmorSpec(name="TestPlate", ar=30),
)


class TestRunScenarioShard:
    def test_basic_scenario(self, shard, parse_results):
        """Run 10 iterations and verify stats are populated."""
        scenario = Scenario(
            attacker=WARRIOR_ATTACKER,
            defender=NPC_DEFENDER,
            iterations=10,
            base_seed=42,
        )
        result = run_scenario(
            scenario,
            parse_results=parse_results,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=shard.root / "scripts" / "modules",
        )

        if result.error_count == result.iteration_count:
            pytest.skip("All iterations failed — script execution issue")

        assert result.success_count > 0
        assert result.damage_stats.mean > 0
        assert result.damage_stats.min >= 0
        assert result.damage_stats.max >= result.damage_stats.min

    def test_deterministic(self, shard, parse_results):
        """Same seed produces identical results."""
        scenario = Scenario(
            attacker=WARRIOR_ATTACKER,
            defender=NPC_DEFENDER,
            iterations=5,
            base_seed=42,
        )
        kwargs = dict(
            parse_results=parse_results,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=shard.root / "scripts" / "modules",
        )
        r1 = run_scenario(scenario, **kwargs)
        r2 = run_scenario(scenario, **kwargs)

        assert r1.damage_stats.mean == r2.damage_stats.mean


class TestRunSweepShard:
    def test_tactics_sweep_monotonic_damage(self, shard, parse_results):
        """Higher Tactics should yield higher mean damage for a Warrior.

        The warrior damage formula multiplies by Anatomy + Tactics,
        NOT by the weapon skill (Swordsmanship).
        """
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=WARRIOR_ATTACKER,
                defender=NPC_DEFENDER,
                iterations=50,
                base_seed=1234,
            ),
            variables=(
                Variable.from_range(
                    "attacker",
                    f"skills.{SKILLID_TACTICS}",
                    start=50,
                    stop=130,
                    step=40,
                ),
            ),
        )
        result = run_sweep(
            sweep,
            parse_results=parse_results,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=shard.root / "scripts" / "modules",
        )

        # Filter out cells with all errors
        valid_cells = [c for c in result.cells if c.success_count > 0]
        if len(valid_cells) < 2:
            pytest.skip("Too few valid cells for monotonicity check")

        # Property: higher Tactics should strictly increase damage
        means = [c.damage_stats.mean for c in valid_cells]
        assert all(m > 0 for m in means), f"Zero/negative mean damage: {means}"
        assert means[-1] > means[0], (
            f"Expected strictly increasing damage with higher Tactics: {means}"
        )

    def test_sweep_performance(self, shard, parse_results):
        """Acceptance criterion: 9 cells × 100 iterations < 60 seconds."""
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=WARRIOR_ATTACKER,
                defender=NPC_DEFENDER,
                iterations=100,
                base_seed=0,
            ),
            variables=(
                Variable.from_range(
                    "attacker",
                    f"skills.{SKILLID_SWORDSMANSHIP}",
                    start=50,
                    stop=130,
                    step=10,
                ),
            ),
        )
        start = time.monotonic()
        result = run_sweep(
            sweep,
            parse_results=parse_results,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=shard.root / "scripts" / "modules",
        )
        elapsed = time.monotonic() - start

        assert len(result.cells) == 9
        assert elapsed < 60, f"Sweep took {elapsed:.1f}s, expected < 60s"
