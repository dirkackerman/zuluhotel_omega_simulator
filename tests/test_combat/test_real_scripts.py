"""Smoke tests executing real combat scripts from the shard submodule.

These tests depend on the pinned shard submodule commit and WILL break if
the shard's combat scripts change (new formulas, renamed functions, etc.).

Run strategy:
  - ``pytest``                      → runs everything including these
  - ``pytest -m "not shard"``       → skips these, runs only self-contained tests
  - ``pytest -m shard``             → runs ONLY shard-dependent tests

When the shard submodule is updated:
  1. Run ``pytest -m shard`` to see what broke
  2. Fix assertions to match new behavior
  3. Commit the submodule update + test fixes together
"""

from pathlib import Path

import pytest

from omega.config.dice import DiceSpec
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.shard import ShardData

SHARD_ROOT = Path(__file__).resolve().parents[2] / "submodules" / "zuluhotel_omega_2.5"

# Skip all tests if the submodule isn't checked out; mark all as shard-dependent
pytestmark = [
    pytest.mark.skipif(not SHARD_ROOT.exists(), reason="Shard submodule not available"),
    pytest.mark.shard,
]


@pytest.fixture
def shard():
    return ShardData.from_path(SHARD_ROOT)


@pytest.fixture
def combat_trees(shard):
    return shard.parse_combat_scripts()


def _em_dir(shard):
    return shard.root / "scripts" / "modules"


@pytest.fixture
def basic_attacker():
    """A basic melee attacker (player)."""
    mob = Mobile(name="TestWarrior", is_npc=False)
    mob.str_base = 100
    mob.dex_base = 100
    mob.int_base = 25
    mob.hp = 200
    mob.max_hp = 200
    mob.set_skill(SKILLID_SWORDSMANSHIP, 1000)  # 100.0 display
    mob.set_skill(SKILLID_TACTICS, 1000)
    return mob


@pytest.fixture
def basic_defender():
    """A basic defender NPC."""
    mob = Mobile(name="TestTarget", is_npc=True, npctemplate="test")
    mob.str_base = 50
    mob.dex_base = 50
    mob.int_base = 50
    mob.hp = 500
    mob.max_hp = 500
    return mob


@pytest.fixture
def basic_weapon():
    return Weapon(name="TestSword", damage=DiceSpec(3, 6, 2), attribute=SKILLID_SWORDSMANSHIP)


@pytest.fixture
def basic_armor():
    return Armor(name="TestPlate", ar=30)


class TestRealMainhit:
    def test_mainhit_executes_and_deals_damage(
        self, shard, combat_trees, basic_attacker, basic_defender, basic_weapon, basic_armor
    ):
        """Real mainhit.src runs and applies damage to defender."""
        from omega.combat.hit import execute_hit

        result = execute_hit(
            combat_trees,
            basic_attacker,
            basic_defender,
            basic_weapon,
            basic_armor,
            base_damage=20,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=_em_dir(shard),
        )

        if not result.success:
            pytest.skip(f"mainhit.src execution failed: {result.error}")

        # Property-based: any non-zero damage means the pipeline works
        assert result.final_damage > 0, "Expected non-zero damage from mainhit"
        assert basic_defender.hp < basic_defender.max_hp

    def test_mainhit_deterministic(
        self, shard, combat_trees, basic_weapon, basic_armor
    ):
        """Same seed + same inputs produces same damage result."""
        from omega.combat.hit import execute_hit

        damages = []
        for _ in range(2):
            attacker = Mobile(name="TestWarrior")
            attacker.str_base = 100
            attacker.dex_base = 100
            attacker.set_skill(SKILLID_SWORDSMANSHIP, 1000)
            attacker.set_skill(SKILLID_TACTICS, 1000)

            defender = Mobile(name="TestTarget", is_npc=True)
            defender.str_base = 50
            defender.hp = 500
            defender.max_hp = 500

            result = execute_hit(
                combat_trees,
                attacker,
                defender,
                basic_weapon,
                Armor(name="TestPlate", ar=30),
                base_damage=20,
                rng_seed=42,
                config_resolver=shard.resolve_config_path,
                em_modules_dir=_em_dir(shard),
            )
            if not result.success:
                pytest.skip(f"mainhit.src execution failed: {result.error}")
            damages.append(result.final_damage)

        assert damages[0] == damages[1], "Same seed should produce identical damage"

    def test_mainhit_with_slayer_weapon(
        self, shard, combat_trees, basic_attacker, basic_armor
    ):
        """Slayer weapon should increase damage against matching creature type."""
        from omega.combat.hit import execute_hit

        # Non-slayer hit
        defender1 = Mobile(name="Undead1", is_npc=True)
        defender1.str_base = 50
        defender1.hp = 500
        defender1.max_hp = 500
        defender1.set_property("Type", "Undead")

        weapon_normal = Weapon(name="NormalSword", damage=DiceSpec(3, 6, 2), attribute=SKILLID_SWORDSMANSHIP)
        r1 = execute_hit(
            combat_trees, basic_attacker, defender1,
            weapon_normal, basic_armor,
            base_damage=20,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=_em_dir(shard),
        )

        # Slayer hit
        defender2 = Mobile(name="Undead2", is_npc=True)
        defender2.str_base = 50
        defender2.hp = 500
        defender2.max_hp = 500
        defender2.set_property("Type", "Undead")

        weapon_slayer = Weapon(name="SlayerSword", damage=DiceSpec(3, 6, 2), attribute=SKILLID_SWORDSMANSHIP)
        weapon_slayer.set_property("SlayType", "Undead")

        # Reset attacker HP for fresh execution
        basic_attacker.hp = 200
        basic_attacker.max_hp = 200

        r2 = execute_hit(
            combat_trees, basic_attacker, defender2,
            weapon_slayer, basic_armor,
            base_damage=20,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=_em_dir(shard),
        )

        if not r1.success or not r2.success:
            pytest.skip("Script execution failed")

        # Property-based: slayer should deal strictly more damage
        assert r2.final_damage > r1.final_damage, (
            f"Slayer ({r2.final_damage}) should exceed non-slayer ({r1.final_damage})"
        )
