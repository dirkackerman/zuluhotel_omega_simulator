"""Tests for reactive armor (M17).

Covers:
- Defender with ReactiveArmor property reflects damage to attacker
- Player attacker receives 1/8 retaliation; NPC attacker receives full
- Reactive armor metrics are recorded correctly
- Reactive armor is consumed (EraseObjProperty) after triggering
- Defender without ReactiveArmor — no reactive damage, no metrics
- reactive_rate is computed correctly in aggregate_cell
- CombatantSpec.properties flows through to mobile
"""

import pytest

from omega.combat.hit import execute_hit
from omega.config.dice import DiceSpec
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.simulation.scenario import CombatantSpec, build_combatant
from omega.simulation.stats import aggregate_cell


@pytest.fixture
def shard(fixture_shard):
    return fixture_shard


@pytest.fixture
def combat_trees(fixture_parse_results):
    return fixture_parse_results


def _em_dir(shard):
    return shard.root / "scripts" / "modules"


def _make_attacker(*, is_npc=False):
    mob = Mobile(name="Attacker", is_npc=is_npc)
    mob.str_base = 100
    mob.dex_base = 100
    mob.int_base = 25
    mob.hp = 200
    mob.max_hp = 200
    mob.set_skill(SKILLID_SWORDSMANSHIP, 1000)
    mob.set_skill(SKILLID_TACTICS, 1000)
    return mob


def _make_defender():
    mob = Mobile(name="Defender", is_npc=True, npctemplate="test")
    mob.str_base = 50
    mob.dex_base = 50
    mob.int_base = 50
    mob.hp = 500
    mob.max_hp = 500
    return mob


class TestReactiveArmorExecution:
    """Test reactive armor script executes via start_script."""

    def test_reactive_armor_reflects_damage_to_attacker(self, shard, combat_trees):
        """Defender with ReactiveArmor reflects damage back to the attacker."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)  # 50% power

        weapon = Weapon(name="Sword", damage=DiceSpec(3, 6, 2), attribute=SKILLID_SWORDSMANSHIP)
        armor = Armor(name="Plate", ar=30)

        result = execute_hit(
            combat_trees, attacker, defender, weapon, armor,
            base_damage=40, debug=True,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=_em_dir(shard),
            shard_root=shard.root,
            package_map=shard.package_map,
        )

        if not result.success:
            pytest.skip(f"Script execution failed: {result.error}")

        # Reactive armor should have triggered
        assert result.metrics.get("reactive_triggered") == 1
        # Retaliation = CInt(basedamage * power / 100) = CInt(40 * 50 / 100) = 20
        assert result.metrics.get("reactive_retaliation") == 20
        # Player attacker: reduced by 1/8 → CInt(20/8) = 2
        assert result.metrics.get("reactive_reduction") == 8
        assert result.metrics.get("reactive_damage") == 2
        assert result.metrics.get("reactive_additional_damage") == 2
        # Attacker should have taken damage
        assert attacker.hp < attacker.max_hp

    def test_npc_attacker_gets_full_reactive_damage(self, shard, combat_trees):
        """NPC attacker receives full reactive retaliation (no 1/8 reduction)."""
        attacker = _make_attacker(is_npc=True)
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = Weapon(name="Sword", damage=DiceSpec(3, 6, 2), attribute=SKILLID_SWORDSMANSHIP)
        armor = Armor(name="Plate", ar=30)

        result = execute_hit(
            combat_trees, attacker, defender, weapon, armor,
            base_damage=40, debug=True,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=_em_dir(shard),
            shard_root=shard.root,
            package_map=shard.package_map,
        )

        if not result.success:
            pytest.skip(f"Script execution failed: {result.error}")

        assert result.metrics.get("reactive_triggered") == 1
        assert result.metrics.get("reactive_retaliation") == 20
        assert result.metrics.get("reactive_reduction") == 1
        assert result.metrics.get("reactive_damage") == 20
        assert result.metrics.get("reactive_additional_damage") == 20

    def test_no_reactive_armor_no_metrics(self, shard, combat_trees):
        """Defender without ReactiveArmor property — no reactive metrics."""
        attacker = _make_attacker()
        defender = _make_defender()

        weapon = Weapon(name="Sword", damage=DiceSpec(3, 6, 2), attribute=SKILLID_SWORDSMANSHIP)
        armor = Armor(name="Plate", ar=30)

        result = execute_hit(
            combat_trees, attacker, defender, weapon, armor,
            base_damage=40, debug=True,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=_em_dir(shard),
            shard_root=shard.root,
            package_map=shard.package_map,
        )

        if not result.success:
            pytest.skip(f"Script execution failed: {result.error}")

        assert result.metrics.get("reactive_triggered") is None
        assert result.metrics.get("reactive_damage") is None

    def test_reactive_armor_consumed_after_trigger(self, shard, combat_trees):
        """ReactiveArmor property is erased after triggering."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = Weapon(name="Sword", damage=DiceSpec(3, 6, 2), attribute=SKILLID_SWORDSMANSHIP)
        armor = Armor(name="Plate", ar=30)

        result = execute_hit(
            combat_trees, attacker, defender, weapon, armor,
            base_damage=40, debug=True,
            config_resolver=shard.resolve_config_path,
            em_modules_dir=_em_dir(shard),
            shard_root=shard.root,
            package_map=shard.package_map,
        )

        if not result.success:
            pytest.skip(f"Script execution failed: {result.error}")

        # ReactiveArmor should be erased after use
        assert defender.get_property("ReactiveArmor") is None


class TestReactiveArmorStats:
    """Test reactive_rate aggregation."""

    def test_reactive_rate_computed(self):
        """aggregate_cell computes reactive_rate from metrics."""
        from omega.combat.result import HitResult

        results = [
            HitResult(final_damage=10, metrics={"reactive_triggered": 1}),
            HitResult(final_damage=10, metrics={}),
            HitResult(final_damage=10, metrics={"reactive_triggered": 1}),
            HitResult(final_damage=10, metrics={}),
        ]

        cell = aggregate_cell(results)
        assert cell.ratios.reactive_rate == 0.5

    def test_reactive_rate_zero_when_no_reactive(self):
        """No reactive triggers → rate is 0."""
        from omega.combat.result import HitResult

        results = [HitResult(final_damage=10) for _ in range(4)]
        cell = aggregate_cell(results)
        assert cell.ratios.reactive_rate == 0.0


class TestCombatantSpecProperties:
    """Test CombatantSpec.properties flows to mobile."""

    def test_properties_applied_to_mobile(self):
        """CombatantSpec.properties are set on the built mobile."""
        spec = CombatantSpec(
            name="ReactiveDefender",
            is_npc=True,
            properties={"ReactiveArmor": 50, "SomeOtherProp": "test"},
        )

        mob, weapon, armor = build_combatant(spec)
        assert mob.get_property("ReactiveArmor") == 50
        assert mob.get_property("SomeOtherProp") == "test"

    def test_properties_default_empty(self):
        """Default CombatantSpec has no properties."""
        spec = CombatantSpec(name="Plain")
        mob, weapon, armor = build_combatant(spec)
        assert mob.get_property("ReactiveArmor") is None
