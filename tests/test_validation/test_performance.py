"""Performance validation — verify the simulator meets throughput targets.

Measured throughput after executor caching: ~200 hits/sec.
Target: >= 100 hits/sec (10,000 iterations in under 100 seconds).

The main bottleneck is ANTLR4 parse tree visiting (visitor dispatch per
node).  Executor caching (M10) eliminated the per-hit re-loading of
functions and constants, yielding a 5x speedup (42 → 200+ hits/sec).
"""

import time

import pytest

from omega.model.constants import SKILLID_ANATOMY, SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.simulation import ArmorSpec, CombatantSpec, Scenario, WeaponSpec, run_scenario


@pytest.fixture(scope="module")
def shard(fixture_shard):
    return fixture_shard


@pytest.fixture(scope="module")
def parse_results(fixture_parse_results):
    return fixture_parse_results


_SCENARIO = Scenario(
    attacker=CombatantSpec(
        name="Warrior", str_=100, dex_=100, int_=25,
        skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
        class_levels={"IsWarrior": 5},
        weapon=WeaponSpec(damage="3d5+2"),
    ),
    defender=CombatantSpec(
        name="Target", is_npc=True,
        str_=50, dex_=50, int_=50, hp=500,
        armor=ArmorSpec(ar=30),
    ),
    iterations=10_000,
    base_seed=42,
)


class TestPerformance:
    def test_10k_iterations_throughput(self, shard, parse_results):
        """10,000 iterations should complete in under 100 seconds (>= 100 hits/sec)."""
        start = time.monotonic()
        result = run_scenario(
            _SCENARIO,
            parse_results=parse_results,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=shard.root / "scripts" / "modules",
        )
        elapsed = time.monotonic() - start

        hits_per_sec = result.success_count / elapsed if elapsed > 0 else 0

        assert elapsed < 100, (
            f"10,000 iterations took {elapsed:.1f}s (target: < 100s, "
            f"{hits_per_sec:.0f} hits/sec)"
        )
        assert hits_per_sec >= 100, (
            f"Throughput {hits_per_sec:.0f} hits/sec below target of 100"
        )

        print(
            f"\nPerformance: {result.success_count} hits in {elapsed:.1f}s "
            f"({hits_per_sec:.0f} hits/sec)"
        )

    def test_parse_caching(self, shard):
        """Parsing combat scripts twice should be fast (cached or re-parsed)."""
        start = time.monotonic()
        _ = shard.parse_combat_scripts()
        first = time.monotonic() - start

        start = time.monotonic()
        _ = shard.parse_combat_scripts()
        second = time.monotonic() - start

        assert second < first * 2 + 1.0, (
            f"Second parse ({second:.2f}s) much slower than first ({first:.2f}s)"
        )
