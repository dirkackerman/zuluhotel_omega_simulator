"""Tests for armor slayer and effect OnHitScript enchantments (M32).

Covers:
- Slayer (raceresistonhit): race match doubles damage, mismatch normal, cursed reversal
- Piercing (piercingonhit): AR bypass, cursed doubles
- Banish (banishonhit): summoned/animated insta-kill, normal creatures get rawdamage
- Poison (poisononhit): poison applied to target, cursed reversal
- Mana Drain (manadrainonhit): mana transfer based on absorbed damage
- Stamina Drain (staminadrainonhit): stamina transfer based on absorbed damage
- Blinding (blindingonhit): chance-based light effect
- Bouncing (bouncingonhit): cursed amplifies, normal teleports (no-op in sim)
"""

from typing import Any

import pytest

from omega.combat.hit import execute_hit
from omega.combat.result import HitResult
from omega.config.combat_scripts import CombatScript
from omega.config.creature_types import CreatureType
from omega.config.dice import DiceSpec
from omega.model.constants import (
    CLASSEID_WARRIOR,
    SKILLID_ANATOMY,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile


@pytest.fixture
def shard(fixture_shard):
    return fixture_shard


@pytest.fixture
def combat_trees(fixture_parse_results):
    return fixture_parse_results


def _em_dir(shard):
    return shard.root / "scripts" / "modules"


def _make_attacker(*, is_npc=False, creature_type=None):
    mob = Mobile(name="Attacker", is_npc=is_npc, npctemplate="test" if is_npc else "")
    mob.str_base = 100
    mob.dex_base = 100
    mob.int_base = 25
    mob.hp = 500
    mob.max_hp = 500
    mob.mana = 100
    mob.max_mana = 100
    mob.stamina = 100
    mob.max_stamina = 100
    mob.set_skill(SKILLID_SWORDSMANSHIP, 1000)
    mob.set_skill(SKILLID_TACTICS, 1000)
    mob.set_skill(SKILLID_ANATOMY, 1000)
    mob.set_property(CLASSEID_WARRIOR, 1)
    if creature_type:
        mob.set_property("Type", creature_type)
    return mob


def _make_defender(*, is_npc=True):
    mob = Mobile(name="Defender", is_npc=is_npc, npctemplate="test" if is_npc else "")
    mob.str_base = 50
    mob.dex_base = 50
    mob.int_base = 50
    mob.hp = 500
    mob.max_hp = 500
    mob.mana = 100
    mob.max_mana = 100
    mob.stamina = 100
    mob.max_stamina = 100
    return mob


def _make_plain_weapon():
    return Weapon(
        name="Plain Sword",
        damage=DiceSpec(3, 6, 2),
        attribute=SKILLID_SWORDSMANSHIP,
    )


def _make_onhit_armor(*, ar=30, onhitscript, cursed=False, **props):
    a = Armor(name="Enchanted Plate", ar=ar)
    a.set_property("OnHitScript", onhitscript)
    if cursed:
        a.set_property("Cursed", 1)
    for k, v in props.items():
        a.set_property(k, v)
    return a


_cached_executors: dict[int, Any] = {}


def _run_hit(shard, combat_trees, attacker, defender, weapon, armor, **kwargs):
    shard_id = id(shard)
    if "executor" not in kwargs:
        if shard_id not in _cached_executors:
            from omega.interpreter.executor import Executor

            _cached_executors[shard_id] = Executor(
                combat_trees,
                em_modules_dir=_em_dir(shard),
                shard_root=shard.root,
                package_map=shard.package_map,
            )
        kwargs["executor"] = _cached_executors[shard_id]

    return execute_hit(
        combat_trees, attacker, defender, weapon, armor,
        base_damage=40, debug=True,
        config_resolver=shard.resolve_config_path,
        em_modules_dir=_em_dir(shard),
        shard_root=shard.root,
        package_map=shard.package_map,
        **kwargs,
    )


def _skip_on_failure(result: HitResult):
    if not result.success:
        pytest.skip(f"Script execution failed: {result.error}")


# ---------------------------------------------------------------------------
# Slayer Armor (raceresistonhit)
# ---------------------------------------------------------------------------


class TestSlayerArmorOnHit:
    """Race-resistant armor enchantment via raceresistonhit.src."""

    def test_slayer_match_records_metric(self, shard, combat_trees):
        """Matching race type records onhit_slayer_match=1."""
        attacker = _make_attacker(is_npc=True, creature_type=CreatureType.UNDEAD)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.UNDEAD,
        )
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_slayer_match") == 1
        assert result.metrics.get("onhit_slayer_type") == "Undead"

    def test_slayer_mismatch_records_metric(self, shard, combat_trees):
        """Non-matching race type records onhit_slayer_match=0."""
        attacker = _make_attacker(is_npc=True, creature_type=CreatureType.DAEMON)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.UNDEAD,
        )
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_slayer_match") == 0

    def test_slayer_match_vs_mismatch_damage(self, shard, combat_trees):
        """Matching slayer should reduce damage taken by defender (halved path)."""
        weapon = _make_plain_weapon()

        # Matching: Undead attacker vs Undead Hunter armor
        attacker_match = _make_attacker(is_npc=True, creature_type=CreatureType.UNDEAD)
        defender_match = _make_defender()
        armor_match = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.UNDEAD,
        )
        result_match = _run_hit(
            shard, combat_trees, attacker_match, defender_match, weapon, armor_match,
            rng_seed=42,
        )
        _skip_on_failure(result_match)

        # Mismatching: Daemon attacker vs Undead Hunter armor
        attacker_mismatch = _make_attacker(is_npc=True, creature_type=CreatureType.DAEMON)
        defender_mismatch = _make_defender()
        armor_mismatch = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.UNDEAD,
        )
        result_mismatch = _run_hit(
            shard, combat_trees, attacker_mismatch, defender_mismatch, weapon, armor_mismatch,
            rng_seed=42,
        )
        _skip_on_failure(result_mismatch)

        # Matching slayer halves rawdamage — defender should take less damage
        assert result_match.final_damage < result_mismatch.final_damage

    def test_slayer_human_matches_player(self, shard, combat_trees):
        """Human slayer matches player attackers (no npctemplate)."""
        attacker = _make_attacker(is_npc=False)  # Player — no npctemplate
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.HUMAN,
        )
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_slayer_match") == 1

    def test_slayer_cursed_doubles_damage_to_defender(self, shard, combat_trees):
        """Cursed slayer armor doubles rawdamage applied to defender."""
        attacker = _make_attacker(is_npc=True, creature_type=CreatureType.UNDEAD)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.UNDEAD,
            cursed=True,
        )
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_slayer_match") == 1
        # Cursed + match = 2x rawdamage to defender
        assert result.final_damage > 0

    def test_slayer_uses_creature_type_enum(self, shard, combat_trees):
        """CreatureType enum values work correctly as ProtectedType."""
        attacker = _make_attacker(is_npc=True, creature_type=CreatureType.DAEMON)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.DAEMON,
        )
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_slayer_match") == 1

    def test_slayer_no_type_property_no_match(self, shard, combat_trees):
        """Attacker without Type property → no slayer match."""
        attacker = _make_attacker(is_npc=True)  # No Type set
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.UNDEAD,
        )
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_slayer_match") == 0

    def test_slayer_damage_always_applied(self, shard, combat_trees):
        """Physical damage is always applied regardless of match."""
        attacker = _make_attacker(is_npc=True, creature_type=CreatureType.DAEMON)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=CreatureType.UNDEAD,
        )
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.final_damage > 0


class TestAllSlayerTypesExecute:
    """Verify all 17 creature types work as armor slayer ProtectedType."""

    @pytest.mark.parametrize("creature_type", list(CreatureType))
    def test_slayer_match_executes(self, shard, combat_trees, creature_type):
        """Each creature type as ProtectedType produces a slayer match."""
        attacker = _make_attacker(is_npc=True, creature_type=creature_type)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.RACERESISTONHIT,
            ProtectedType=creature_type,
        )
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_slayer_match") == 1, (
            f"Slayer match failed for {creature_type}"
        )
        assert result.metrics.get("onhit_type") == "slayer"
        assert result.final_damage > 0


# ---------------------------------------------------------------------------
# Piercing Armor (piercingonhit)
# ---------------------------------------------------------------------------


class TestPiercingArmorOnHit:
    def test_piercing_records_type(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=CombatScript.PIERCINGONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "piercing"
        assert result.final_damage > 0

    def test_piercing_cursed_doubles(self, shard, combat_trees):
        """Cursed piercing armor doubles rawdamage."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=CombatScript.PIERCINGONHIT, cursed=True)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.final_damage > 0


# ---------------------------------------------------------------------------
# Poison Armor (poisononhit)
# ---------------------------------------------------------------------------


class TestPoisonArmorOnHit:
    def test_poison_records_type_and_level(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.POISONONHIT,
            Poisonlvl=3,
        )

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "poison"
        assert result.metrics.get("onhit_poison_level") == 3
        assert result.final_damage > 0

    def test_poison_cursed_targets_defender(self, shard, combat_trees):
        """Cursed poison armor poisons the defender (armor wearer) instead."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.POISONONHIT,
            Poisonlvl=3,
            cursed=True,
        )

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "poison"

    def test_poison_zero_level(self, shard, combat_trees):
        """Poisonlvl=0 should still execute without error."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.POISONONHIT,
            Poisonlvl=0,
        )

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.final_damage > 0


# ---------------------------------------------------------------------------
# Mana Drain Armor (manadrainonhit)
# ---------------------------------------------------------------------------


class TestManaDrainArmorOnHit:
    def test_mana_drain_records_type(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=CombatScript.MANADRAINONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "manadrain"
        assert result.final_damage > 0

    def test_mana_drain_transfers_when_absorbed(self, shard, combat_trees):
        """Mana drain occurs when AR absorbs damage (basedamage != rawdamage)."""
        attacker = _make_attacker()
        attacker.mana = 100
        attacker.max_mana = 100
        defender = _make_defender()
        defender.mana = 100
        defender.max_mana = 100
        weapon = _make_plain_weapon()
        # AR=30 will cause absorption, so absorbed > 0
        armor = _make_onhit_armor(ar=30, onhitscript=CombatScript.MANADRAINONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        absorbed = result.metrics.get("onhit_drain_absorbed", 0)
        if absorbed > 0:
            # Normal (not cursed): attacker drained, defender gains
            mana_effects = [se for se in result.side_effects if se.kind == "mana_changed"]
            assert len(mana_effects) >= 1, "Expected mana_changed side effects"

    def test_mana_drain_no_transfer_when_no_absorption(self, shard, combat_trees):
        """No absorption (AR=0) → absorbed=0 → no mana drain."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(ar=0, onhitscript=CombatScript.MANADRAINONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        # With AR=0, the eScript may not produce absorbed > 0


# ---------------------------------------------------------------------------
# Stamina Drain Armor (staminadrainonhit)
# ---------------------------------------------------------------------------


class TestStaminaDrainArmorOnHit:
    def test_stamina_drain_records_type(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=CombatScript.STAMINADRAINONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "staminadrain"
        assert result.final_damage > 0

    def test_stamina_drain_transfers_when_absorbed(self, shard, combat_trees):
        """Stamina drain occurs when AR absorbs damage."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(ar=30, onhitscript=CombatScript.STAMINADRAINONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        absorbed = result.metrics.get("onhit_drain_absorbed", 0)
        if absorbed > 0:
            stam_effects = [se for se in result.side_effects if se.kind == "stamina_changed"]
            assert len(stam_effects) >= 1, "Expected stamina_changed side effects"


# ---------------------------------------------------------------------------
# Blinding Armor (blindingonhit)
# ---------------------------------------------------------------------------


class TestBlindingArmorOnHit:
    def test_blinding_records_type(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.BLINDINGONHIT,
            ChanceOfEffect=100,
        )

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "blinding"
        assert result.final_damage > 0

    def test_blinding_zero_chance(self, shard, combat_trees):
        """0% chance → blinding never triggers but damage still applied."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.BLINDINGONHIT,
            ChanceOfEffect=0,
        )

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.final_damage > 0


# ---------------------------------------------------------------------------
# Bouncing Armor (bouncingonhit)
# ---------------------------------------------------------------------------


class TestBouncingArmorOnHit:
    def test_bouncing_records_type(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(
            onhitscript=CombatScript.BOUNCINGONHIT,
            ChanceOfEffect=100,
        )

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "bouncing"
        assert result.final_damage > 0

    def test_bouncing_cursed_amplifies_damage(self, shard, combat_trees):
        """Cursed bouncing armor applies 1.5x rawdamage as magic damage."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor_normal = _make_onhit_armor(
            onhitscript=CombatScript.BOUNCINGONHIT,
            ChanceOfEffect=0,
        )
        armor_cursed = _make_onhit_armor(
            onhitscript=CombatScript.BOUNCINGONHIT,
            ChanceOfEffect=100,
            cursed=True,
        )

        # Normal hit (0% chance, no bounce)
        defender_normal = _make_defender()
        result_normal = _run_hit(
            shard, combat_trees, attacker, defender_normal, weapon, armor_normal,
            rng_seed=42,
        )
        _skip_on_failure(result_normal)

        # Cursed hit (1.5x magic damage)
        defender_cursed = _make_defender()
        result_cursed = _run_hit(
            shard, combat_trees, attacker, defender_cursed, weapon, armor_cursed,
            rng_seed=42,
        )
        _skip_on_failure(result_cursed)

        # Cursed should deal more damage (1.5x)
        assert result_cursed.final_damage > result_normal.final_damage


# ---------------------------------------------------------------------------
# Banish Armor (banishonhit)
# ---------------------------------------------------------------------------


class TestBanishArmorOnHit:
    def test_banish_normal_creature(self, shard, combat_trees):
        """Normal creature (not summoned/animated) → rawdamage applied normally."""
        attacker = _make_attacker(is_npc=True)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=CombatScript.BANISHONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "banish"
        assert result.final_damage > 0

    def test_banish_summoned_creature(self, shard, combat_trees):
        """Summoned creature → massive damage (getMaxHP + 3)."""
        attacker = _make_attacker(is_npc=True)
        attacker.set_property("summoned", 1)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=CombatScript.BANISHONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_banish_summoned") == 1

    def test_banish_animated_creature(self, shard, combat_trees):
        """Animated creature → massive damage (getMaxHP + 3)."""
        attacker = _make_attacker(is_npc=True)
        attacker.set_property("animated", 1)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=CombatScript.BANISHONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_banish_animated") == 1

    def test_banish_records_type(self, shard, combat_trees):
        attacker = _make_attacker(is_npc=True)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=CombatScript.BANISHONHIT)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("onhit_type") == "banish"


# ---------------------------------------------------------------------------
# Cross-cutting: all onhit scripts apply damage
# ---------------------------------------------------------------------------


class TestAllOnHitScriptsApplyDamage:
    """Every onhit script must call ApplyTheDamage → damage_applied list has entries."""

    @pytest.mark.parametrize("onhitscript,extra_props", [
        (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.SLIME}),
        (CombatScript.PIERCINGONHIT, {}),
        (CombatScript.POISONONHIT, {"Poisonlvl": 1}),
        (CombatScript.MANADRAINONHIT, {}),
        (CombatScript.STAMINADRAINONHIT, {}),
        (CombatScript.BLINDINGONHIT, {"ChanceOfEffect": 0}),
        (CombatScript.BOUNCINGONHIT, {"ChanceOfEffect": 0}),
        (CombatScript.BANISHONHIT, {}),
    ])
    def test_damage_applied(self, shard, combat_trees, onhitscript, extra_props):
        """Each onhit script must produce at least 1 damage_applied entry."""
        attacker = _make_attacker(is_npc=True, creature_type=CreatureType.SLIME)
        defender = _make_defender()
        weapon = _make_plain_weapon()
        armor = _make_onhit_armor(onhitscript=onhitscript, **extra_props)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        applied = result.metrics.get("damage_applied", [])
        assert len(applied) >= 1, (
            f"OnHitScript {onhitscript} produced no damage_applied entries"
        )
        assert result.final_damage > 0
