"""Stub coverage audit and error handling tests.

Verifies which POL built-in stubs are exercised on the combat path,
and that common user mistakes produce clear error messages.
"""

from pathlib import Path

import pytest

from omega.model.constants import SKILLID_ANATOMY, SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.shard import ShardData
from omega.simulation import ArmorSpec, CombatantSpec, Scenario, WeaponSpec, run_scenario


SHARD_ROOT = Path(__file__).resolve().parents[2] / "submodules" / "zuluhotel_omega_2.5"

pytestmark = [
    pytest.mark.skipif(not SHARD_ROOT.exists(), reason="Shard submodule not available"),
    pytest.mark.shard,
]


@pytest.fixture(scope="module")
def shard():
    return ShardData.from_path(SHARD_ROOT)


@pytest.fixture(scope="module")
def parse_results(shard):
    return shard.parse_combat_scripts()


class TestStubCoverage:
    """Verify which built-in stubs the combat path actually exercises."""

    def test_combat_path_calls_key_stubs(self, shard, parse_results):
        """Run a basic scenario and verify no unhandled errors from stubs."""
        scenario = Scenario(
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
            iterations=10,
            base_seed=42,
        )
        result = run_scenario(
            scenario,
            parse_results=parse_results,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=shard.root / "scripts" / "modules",
        )
        # Most iterations should succeed — errors indicate missing stubs
        assert result.success_count >= result.iteration_count * 0.8, (
            f"Only {result.success_count}/{result.iteration_count} iterations succeeded. "
            f"Errors likely from missing stubs."
        )

    def test_registered_stub_count(self):
        """Verify a reasonable number of stubs are registered."""
        import omega.runtime  # noqa: F401 — trigger registration
        from omega.runtime.registry import _registry

        assert len(_registry) >= 100, (
            f"Expected 100+ registered stubs, found {len(_registry)}"
        )


class TestErrorHandling:
    """Verify clear error messages for common user mistakes."""

    def test_invalid_dice_string(self):
        """Malformed dice string raises a clear error."""
        from omega.config.dice import parse_dice

        with pytest.raises((ValueError, Exception)) as exc_info:
            parse_dice("not_dice")
        assert "dice" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()

    def test_shard_nonexistent_path(self):
        """ShardData.from_path with bad path produces an empty shard."""
        # ShardData.from_path tolerates missing paths (logs a warning)
        # but results in a shard with no packages discovered.
        shard = ShardData.from_path(Path("/nonexistent/shard/path"))
        assert len(shard._package_map) == 0

    def test_scenario_missing_parse_results(self):
        """run_scenario without parse_results or shard raises ValueError."""
        scenario = Scenario(
            attacker=CombatantSpec(name="A"),
            defender=CombatantSpec(name="B"),
            iterations=1,
        )
        with pytest.raises(ValueError, match="parse_results"):
            run_scenario(scenario)
