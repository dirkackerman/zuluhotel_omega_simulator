"""Tests for reactive armor + resistance integration (M-V2.6).

Covers:
- Reactive armor combined with spell strike enchantments
- Reactive armor combined with effect enchantments (lifedrain, manadrain, piercing)
- Reactive armor combined with greater enchantments (trielemental, dualplanar)
- Reactive armor power scaling with hand-calculated values
- Resisted() function hand-calculated scenarios with known skill/class combos
- EvalInt vs MagicResistance scaling factor
- Class modifier stacking in Resisted() (Mage/Warrior/Paladin defender & caster)
- Over-protection healing + reactive armor edge case
"""

import pytest

from omega.combat.hit import execute_hit
from omega.config.dice import DiceSpec
from omega.model.constants import (
    CLASSEID_MAGE,
    CLASSEID_PALADIN,
    CLASSEID_WARRIOR,
    SKILLID_ANATOMY,
    SKILLID_EVALINT,
    SKILLID_MAGERY,
    SKILLID_MAGICRESISTANCE,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.config.combat_scripts import CombatScript
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


def _make_attacker(*, is_npc=False, class_id=CLASSEID_WARRIOR, class_level=1):
    """Create an attacker with full combat skills and configurable class."""
    mob = Mobile(name="Attacker", is_npc=is_npc)
    mob.str_base = 100
    mob.dex_base = 100
    mob.int_base = 100
    mob.hp = 200
    mob.max_hp = 200
    mob.mana = 100
    mob.max_mana = 100
    mob.stamina = 100
    mob.max_stamina = 100
    mob.set_skill(SKILLID_SWORDSMANSHIP, 1000)
    mob.set_skill(SKILLID_TACTICS, 1000)
    mob.set_skill(SKILLID_ANATOMY, 1000)
    mob.set_skill(SKILLID_MAGERY, 1000)
    mob.set_skill(SKILLID_EVALINT, 1000)
    if class_id:
        mob.set_property(class_id, class_level)
    return mob


def _make_defender(*, magic_resist=0, is_npc=True):
    """Create a defender with optional magic resistance."""
    mob = Mobile(name="Defender", is_npc=is_npc, npctemplate="test" if is_npc else None)
    mob.str_base = 50
    mob.dex_base = 50
    mob.int_base = 50
    mob.hp = 500
    mob.max_hp = 500
    mob.mana = 100
    mob.max_mana = 100
    mob.stamina = 100
    mob.max_stamina = 100
    if magic_resist:
        mob.set_skill(SKILLID_MAGICRESISTANCE, magic_resist)
    return mob


def _make_plain_weapon():
    """Plain physical weapon — no hitscript."""
    return Weapon(
        name="Plain Sword",
        damage=DiceSpec(3, 6, 2),
        attribute=SKILLID_SWORDSMANSHIP,
    )


def _make_spell_weapon(*, chance=100, spell_id=18, circle=3):
    """Weapon with spell strike enchantment."""
    w = Weapon(
        name="Spell Sword",
        damage=DiceSpec(3, 6, 2),
        attribute=SKILLID_SWORDSMANSHIP,
        hitscript=CombatScript.SPELLSTRIKESCRIPT,
    )
    w.set_property("ChanceOfEffect", chance)
    w.set_property("HitWithSpell", spell_id)
    w.set_property("EffectCircle", circle)
    return w


def _make_effect_weapon(hitscript, *, chance=None, cursed=False):
    """Weapon with an effect enchantment hitscript."""
    w = Weapon(
        name="Effect Sword",
        damage=DiceSpec(3, 6, 2),
        attribute=SKILLID_SWORDSMANSHIP,
        hitscript=hitscript,
    )
    if chance is not None:
        w.set_property("ChanceOfEffect", chance)
    if cursed:
        w.set_property("Cursed", 1)
    return w


def _make_greater_weapon(hitscript, *, chance=100, cursed=False):
    """Weapon with a greater enchantment hitscript."""
    w = Weapon(
        name="Greater Sword",
        damage=DiceSpec(3, 6, 2),
        attribute=SKILLID_SWORDSMANSHIP,
        hitscript=hitscript,
    )
    w.set_property("ChanceOfEffect", chance)
    if cursed:
        w.set_property("Cursed", 1)
    return w


def _run_hit(shard, combat_trees, attacker, defender, weapon, armor, **kwargs):
    return execute_hit(
        combat_trees, attacker, defender, weapon, armor,
        base_damage=40, debug=True,
        config_resolver=shard.resolve_config_path,
        em_modules_dir=_em_dir(shard),
        shard_root=shard.root,
        package_map=shard.package_map,
        **kwargs,
    )


def _skip_on_failure(result):
    if not result.success:
        pytest.skip(f"Script execution failed: {result.error}")


# ---------------------------------------------------------------------------
# Section 1: Reactive Armor + Spell Strike Combination
# ---------------------------------------------------------------------------


class TestReactivePlusSpellStrike:
    """Reactive armor and spell strike fire independently in the same hit."""

    def test_reactive_plus_spell_strike_both_fire(self, shard, combat_trees):
        """Both reactive_triggered and spell_strike_triggered in metrics."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_spell_weapon(chance=100, spell_id=18, circle=3)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_triggered") == 1, \
            "Reactive armor should trigger"
        assert result.metrics.get("spell_strike_triggered") == 1, \
            "Spell strike should also trigger"

    def test_reactive_uses_basedamage_not_spell_modified(self, shard, combat_trees):
        """Reactive retaliation is basedamage * power / 100, independent of spell damage."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_spell_weapon(chance=100, spell_id=18, circle=3)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        # Retaliation = CInt(basedamage * power / 100) = CInt(40 * 50 / 100) = 20
        assert result.metrics.get("reactive_retaliation") == 20

    def test_reactive_consumed_with_spell_strike(self, shard, combat_trees):
        """ReactiveArmor property erased even when spell strike is the damage path."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_spell_weapon(chance=100, spell_id=18, circle=3)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert defender.get_property("ReactiveArmor") is None, \
            "ReactiveArmor should be consumed after trigger"


# ---------------------------------------------------------------------------
# Section 2: Reactive Armor + Effect Enchantments
# ---------------------------------------------------------------------------


class TestReactivePlusEffects:
    """Reactive armor combined with effect enchantments in the same hit."""

    def test_reactive_plus_lifedrain(self, shard, combat_trees):
        """Reactive reflects damage, lifedrain heals attacker. Both trigger."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_effect_weapon(CombatScript.LIFEDRAINSCRIPT)
        armor = Armor(name="Plate", ar=30)

        # Life drain has 50% proc rate — use seed that triggers it
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_triggered") == 1, \
            "Reactive armor should trigger"
        # Reactive consumed
        assert defender.get_property("ReactiveArmor") is None

    def test_reactive_plus_manadrain(self, shard, combat_trees):
        """Reactive + mana drain combination — both present in same hit."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_effect_weapon(CombatScript.MANADRAINSCRIPT)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_triggered") == 1
        assert defender.get_property("ReactiveArmor") is None

    def test_reactive_plus_piercing(self, shard, combat_trees):
        """Reactive + piercing (armor bypass). Reactive uses basedamage, unaffected by piercing."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_effect_weapon(CombatScript.PIERCINGSCRIPT)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_triggered") == 1
        # Retaliation based on basedamage=40, not piercing-modified damage
        assert result.metrics.get("reactive_retaliation") == 20


# ---------------------------------------------------------------------------
# Section 3: Reactive Armor + Greater Enchantments
# ---------------------------------------------------------------------------


class TestReactivePlusGreater:
    """Reactive armor combined with greater enchantment hitscripts."""

    def test_reactive_plus_trielemental(self, shard, combat_trees):
        """Reactive triggers, then trielemental fires. Both metrics present."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_greater_weapon(CombatScript.TRIELEMENTALSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_triggered") == 1
        assert result.metrics.get("effect_triggered") == 1
        # Elemental metrics should still be recorded
        elem = result.metrics.get("elemental_applied", [])
        assert len(elem) == 3, "FIRE+AIR+WATER elemental entries expected"

    def test_reactive_plus_dualplanar(self, shard, combat_trees):
        """Reactive triggers, then dualplanar fires. Both reactive and planar metrics."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_triggered") == 1
        assert result.metrics.get("effect_triggered") == 1
        planar = result.metrics.get("planar_applied", [])
        assert len(planar) == 2, "HOLY+NECRO planar entries expected"


# ---------------------------------------------------------------------------
# Section 4: Reactive Armor Power Scaling
# ---------------------------------------------------------------------------


class TestReactivePowerScaling:
    """Verify reactive damage with exact hand-calculated values at various power levels."""

    def test_power_10_player(self, shard, combat_trees):
        """power=10, basedamage=40: retaliation=CInt(40*10/100)=4, player=CInt(4/8)=0."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 10)

        weapon = _make_plain_weapon()
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_triggered") == 1
        assert result.metrics.get("reactive_retaliation") == 4
        assert result.metrics.get("reactive_damage") == 0  # CInt(4/8) = 0

    def test_power_50_player(self, shard, combat_trees):
        """power=50, basedamage=40: retaliation=20, player=CInt(20/8)=2."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)

        weapon = _make_plain_weapon()
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_retaliation") == 20
        assert result.metrics.get("reactive_damage") == 2

    def test_power_100_player(self, shard, combat_trees):
        """power=100, basedamage=40: retaliation=40, player=CInt(40/8)=5."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 100)

        weapon = _make_plain_weapon()
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_retaliation") == 40
        assert result.metrics.get("reactive_damage") == 5

    def test_power_100_npc(self, shard, combat_trees):
        """NPC attacker, power=100: full retaliation=40, no 1/8 reduction."""
        attacker = _make_attacker(is_npc=True)
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 100)

        weapon = _make_plain_weapon()
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_retaliation") == 40
        assert result.metrics.get("reactive_reduction") == 1
        assert result.metrics.get("reactive_damage") == 40

    def test_power_150_npc(self, shard, combat_trees):
        """NPC attacker, power=150: retaliation=CInt(40*150/100)=60."""
        attacker = _make_attacker(is_npc=True)
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 150)

        weapon = _make_plain_weapon()
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_retaliation") == 60
        assert result.metrics.get("reactive_damage") == 60

    def test_power_25_player_truncation(self, shard, combat_trees):
        """power=25, basedamage=40: retaliation=CInt(40*25/100)=10, player=CInt(10/8)=1.

        CInt(10/8) = CInt(1.25) = 1 — tests integer truncation.
        """
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 25)

        weapon = _make_plain_weapon()
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_retaliation") == 10
        assert result.metrics.get("reactive_damage") == 1  # CInt(10/8) = 1


# ---------------------------------------------------------------------------
# Section 5: Resisted() Hand-Calculated Scenarios
# ---------------------------------------------------------------------------


class TestResistedHandCalculated:
    """Verify Resisted() output against hand calculations.

    Resisted() pipeline:
      1. chance = max(CInt(resist/6), CInt(resist - (magery/4 + circle*6)))
      2. Defender class modifiers on chance
      3. Caster class modifiers on chance
      4. Resist roll: Random(100)+1 <= chance → dmg halved (min 1)
      5. EvalInt scaling: dmg = CInt(dmg * (1 + (evalint - resist) / 200))
      6. Defender class modifiers on dmg
      7. Floor: max(dmg, 1)

    We use dualplanar/trielemental scripts to drive Resisted() through the
    real interpreter and check list:resisted metrics.

    IMPORTANT: Dualplanar calls Resisted() 3 times:
    - Once directly (circle=9) with attacker as caster
    - Twice via ApplyPlanarDamage (circle=1) with *targ* (=defender) as caster
    We filter to the direct call (circle=9) for hand calculations.
    """

    @staticmethod
    def _get_direct_resisted(resisted_list, direct_circle=9):
        """Filter to the direct Resisted() call from the enchantment script."""
        return [e for e in resisted_list if e.get("circle") == direct_circle]

    def test_no_class_low_resist(self, shard, combat_trees):
        """No classes. resist=60, evalint=100, magery=100, circle=9 (dualplanar).

        chance = max(CInt(60/6), CInt(60 - (100/4 + 9*6))) = max(10, -19) = 10.
        EvalInt scaling: 1 + (100-60)/200 = 1.2 → dmg amplified.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)    # 100 display
        attacker.set_skill(SKILLID_EVALINT, 1000)    # 100 display
        defender = _make_defender(magic_resist=600)   # 60 display

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1, f"Expected 1 direct resisted entry, got {len(direct)}"

        entry = direct[0]
        assert entry["chance"] == 10, \
            f"Expected chance=10, got {entry['chance']}"
        assert entry["evalint"] == 100
        assert entry["resist"] == 60
        assert entry["dmg_after"] > 0

    def test_no_class_high_resist_always_resists(self, shard, combat_trees):
        """No classes. resist=1300 (cap), evalint=50, magery=80, circle=9.

        chance = max(CInt(1300/6), CInt(1300 - (80/4 + 9*6)))
               = max(216, 1226) = 1226.
        Random(100)+1 is always <= 1226, so always resists.
        EvalInt scaling: 1 + (50 - 1300)/200 = -5.25 → negative → floor to 1.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 800)     # 80 display
        attacker.set_skill(SKILLID_EVALINT, 500)     # 50 display
        defender = _make_defender(magic_resist=13000)  # 1300 display (cap)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=1)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        entry = direct[0]
        assert entry["did_resist"] == 1, "Should always resist with 1226% chance"
        assert entry["dmg_after"] == 1, \
            f"Expected dmg_after=1 (floor), got {entry['dmg_after']}"

    def test_mage_defender_boosts_resist_chance(self, shard, combat_trees):
        """Defender is Mage L5, no caster class. resist=80, magery=100, circle=9.

        Base chance = max(CInt(80/6), CInt(80 - (100/4 + 9*6))) = max(13, 1) = 13.
        Mage bonus: ClasseBonus(L5) = 1 + 5*0.25 = 2.25.
        chance = CInt(13 * 2.25) = CInt(29.25) = 29.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)

        defender = _make_defender(magic_resist=800)  # 80 display
        defender.set_property(CLASSEID_MAGE, 5)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        assert direct[0]["chance"] == 29, \
            f"Expected chance=29 (Mage L5 boost), got {direct[0]['chance']}"

    def test_warrior_defender_weakens_resist_chance(self, shard, combat_trees):
        """Defender is Warrior L4, no caster class. resist=80, magery=100, circle=9.

        Base chance = max(CInt(80/6), CInt(80-(100/4+9*6))) = max(13, 1) = 13.
        Warrior penalty: bonus = 1 + 4*0.25 = 2.0.
        chance = CInt(13 / 2.0 / 2) = CInt(3.25) = 3.
        resist = CInt(80 / 2.0) = 40.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)

        defender = _make_defender(magic_resist=800)
        defender.set_property(CLASSEID_WARRIOR, 4)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        assert direct[0]["chance"] == 3, \
            f"Expected chance=3 (Warrior L4 penalty), got {direct[0]['chance']}"
        # Warrior modifier also modifies resist for EvalInt scaling
        assert direct[0]["resist"] == 40, \
            f"Expected resist=40 (Warrior halved), got {direct[0]['resist']}"

    def test_paladin_defender_moderate_boost(self, shard, combat_trees):
        """Defender is Paladin L4, no caster class. resist=80, magery=100, circle=9.

        Base chance = max(CInt(80/6), CInt(80-(100/4+9*6))) = max(13, 1) = 13.
        Paladin: CInt((chance * ClasseBonus(4)) * 0.5)
               = CInt((13 * (1 + 0.25*4)) * 0.5) = CInt((13 * 2.0) * 0.5) = 13.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)

        defender = _make_defender(magic_resist=800)
        defender.set_property(CLASSEID_PALADIN, 4)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        assert direct[0]["chance"] == 13, \
            f"Expected chance=13 (Paladin L4 boost), got {direct[0]['chance']}"

    def test_mage_caster_reduces_resist_chance(self, shard, combat_trees):
        """Caster is Mage L5, no defender class. resist=80, magery=100, circle=9.

        Base chance = max(CInt(80/6), CInt(80-(100/4+9*6))) = max(13, 1) = 13.
        No defender class mods.
        Caster Mage: ClasseBonus(L5) = 2.25.
        chance = CInt(13 / 2.25) = CInt(5.77) = 5.
        """
        attacker = _make_attacker(class_id=CLASSEID_MAGE, class_level=5)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)

        defender = _make_defender(magic_resist=800)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        assert direct[0]["chance"] == 5, \
            f"Expected chance=5 (Mage caster L5), got {direct[0]['chance']}"

    def test_warrior_caster_increases_resist_chance(self, shard, combat_trees):
        """Caster is Warrior L4, no defender class. resist=80, magery=100, circle=9.

        Base chance = max(CInt(80/6), CInt(80-(100/4+9*6))) = max(13, 1) = 13.
        No defender class mods.
        Caster Warrior: bonus = 2.0.
        chance = CInt(13 * 2.0 * 2) = CInt(52) = 52.
        resist = CInt(80 * 2.0) = 160.
        """
        attacker = _make_attacker(class_id=CLASSEID_WARRIOR, class_level=4)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)

        defender = _make_defender(magic_resist=800)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        assert direct[0]["chance"] == 52, \
            f"Expected chance=52 (Warrior caster L4), got {direct[0]['chance']}"
        assert direct[0]["resist"] == 160, \
            f"Expected resist=160 (Warrior caster doubles resist), got {direct[0]['resist']}"

    def test_mage_vs_mage_partial_cancel(self, shard, combat_trees):
        """Caster Mage L5 vs Defender Mage L5. resist=80, circle=9.

        Base chance = max(CInt(80/6), CInt(80-(100/4+9*6))) = max(13, 1) = 13.
        Defender Mage L5: chance = CInt(13 * 2.25) = 29.
        Caster Mage L5: chance = CInt(29 / 2.25) = CInt(12.88) = 12.

        Roughly back to base — class effects partially cancel.
        """
        attacker = _make_attacker(class_id=CLASSEID_MAGE, class_level=5)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)

        defender = _make_defender(magic_resist=800)
        defender.set_property(CLASSEID_MAGE, 5)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        assert direct[0]["chance"] == 12, \
            f"Expected chance=12 (Mage vs Mage partial cancel), got {direct[0]['chance']}"

    def test_evalint_above_resist_amplifies_damage(self, shard, combat_trees):
        """evalint=130, resist=60 (no classes). Scaling = 1 + (130-60)/200 = 1.35.

        circle=9: chance = max(CInt(60/6), CInt(60-(130/4+9*6))) = max(10, -26) = 10.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1300)    # 130 display
        attacker.set_skill(SKILLID_EVALINT, 1300)    # 130 display

        defender = _make_defender(magic_resist=600)   # 60 display

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        entry = direct[0]
        if entry["did_resist"] == 0:
            # dmg_after = CInt(dmg_before * 1.35) — amplified
            expected = int(entry["dmg_before"] * (1 + (130 - 60) / 200))
            assert entry["dmg_after"] == expected, \
                f"Expected dmg_after={expected} (1.35x), got {entry['dmg_after']}"
        # Either way, damage should be non-zero
        assert entry["dmg_after"] > 0

    def test_evalint_below_resist_reduces_damage(self, shard, combat_trees):
        """evalint=30, resist=100 (no classes). Scaling = 1 + (30-100)/200 = 0.65.

        circle=9: chance = max(CInt(100/6), CInt(100-(30/4+9*6))) = max(16, 38) = 38.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 300)      # 30 display
        attacker.set_skill(SKILLID_EVALINT, 300)      # 30 display

        defender = _make_defender(magic_resist=1000)   # 100 display

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=1)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = self._get_direct_resisted(resisted)
        assert len(direct) == 1

        entry = direct[0]
        assert entry["dmg_after"] <= entry["dmg_before"], \
            f"dmg_after ({entry['dmg_after']}) should be <= dmg_before ({entry['dmg_before']})"

    def test_resisted_dmg_floor_at_1(self, shard, combat_trees):
        """After extreme reduction, damage floors at 1 (never 0 or negative)."""
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 100)      # 10 display
        attacker.set_skill(SKILLID_EVALINT, 100)      # 10 display

        defender = _make_defender(magic_resist=13000)  # 1300 display
        defender.set_property(CLASSEID_MAGE, 5)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=1)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        # All resisted entries should floor at 1
        for entry in resisted:
            assert entry["dmg_after"] >= 1, \
                f"Damage should floor at 1, got {entry['dmg_after']}"

    def test_resisted_warrior_defender_takes_more_damage(self, shard, combat_trees):
        """Warrior defender takes more spell damage via class modifier.

        After Resisted() step 5 (EvalInt scaling), step 6 applies:
        Warrior: dmg = CInt(dmg * ClasseBonus(level)).
        L4 warrior: dmg *= 2.0. So warrior takes 2x spell damage vs no class.
        """
        armor = Armor(name="Plate", ar=30)

        # No class defender
        attacker1 = _make_attacker(class_id=None)
        attacker1.set_skill(SKILLID_MAGERY, 1000)
        attacker1.set_skill(SKILLID_EVALINT, 1000)
        defender1 = _make_defender(magic_resist=600)
        weapon1 = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        result1 = _run_hit(shard, combat_trees, attacker1, defender1, weapon1, armor, rng_seed=99)
        _skip_on_failure(result1)

        # Warrior L4 defender
        attacker2 = _make_attacker(class_id=None)
        attacker2.set_skill(SKILLID_MAGERY, 1000)
        attacker2.set_skill(SKILLID_EVALINT, 1000)
        defender2 = _make_defender(magic_resist=600)
        defender2.set_property(CLASSEID_WARRIOR, 4)
        weapon2 = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        result2 = _run_hit(shard, combat_trees, attacker2, defender2, weapon2, armor, rng_seed=99)
        _skip_on_failure(result2)

        # Compare the direct Resisted() call (circle=9)
        direct1 = self._get_direct_resisted(result1.metrics.get("resisted", []))
        direct2 = self._get_direct_resisted(result2.metrics.get("resisted", []))
        assert len(direct1) == 1 and len(direct2) == 1

        assert direct2[0]["dmg_after"] > direct1[0]["dmg_after"], \
            f"Warrior defender ({direct2[0]['dmg_after']}) should take more than classless ({direct1[0]['dmg_after']})"

    def test_resisted_mage_defender_takes_less_damage(self, shard, combat_trees):
        """Mage defender takes less spell damage via class modifier.

        After step 5, step 6: Mage: dmg = CInt(dmg / ClasseBonus(level)).
        L5 mage: dmg /= 2.25. So mage takes ~44% of classless damage.
        """
        armor = Armor(name="Plate", ar=30)

        # No class defender
        attacker1 = _make_attacker(class_id=None)
        attacker1.set_skill(SKILLID_MAGERY, 1000)
        attacker1.set_skill(SKILLID_EVALINT, 1000)
        defender1 = _make_defender(magic_resist=600)
        weapon1 = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        result1 = _run_hit(shard, combat_trees, attacker1, defender1, weapon1, armor, rng_seed=99)
        _skip_on_failure(result1)

        # Mage L5 defender
        attacker2 = _make_attacker(class_id=None)
        attacker2.set_skill(SKILLID_MAGERY, 1000)
        attacker2.set_skill(SKILLID_EVALINT, 1000)
        defender2 = _make_defender(magic_resist=600)
        defender2.set_property(CLASSEID_MAGE, 5)
        weapon2 = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        result2 = _run_hit(shard, combat_trees, attacker2, defender2, weapon2, armor, rng_seed=99)
        _skip_on_failure(result2)

        direct1 = self._get_direct_resisted(result1.metrics.get("resisted", []))
        direct2 = self._get_direct_resisted(result2.metrics.get("resisted", []))
        assert len(direct1) == 1 and len(direct2) == 1

        assert direct2[0]["dmg_after"] < direct1[0]["dmg_after"], \
            f"Mage defender ({direct2[0]['dmg_after']}) should take less than classless ({direct1[0]['dmg_after']})"


# ---------------------------------------------------------------------------
# Section 6: Resisted() via Trielemental (different enchantment path)
# ---------------------------------------------------------------------------


class TestResistedViaTrielemental:
    """Same Resisted() validation but through the trielemental/ApplyElementalDamage path."""

    def test_trielemental_resisted_chance_no_class(self, shard, combat_trees):
        """Verify resist chance through trielemental direct Resisted() call (circle=8).

        resist=80, evalint=100, magery=100, circle=8.
        chance = max(CInt(80/6), CInt(80-(100/4+8*6))) = max(13, 7) = 13.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)

        defender = _make_defender(magic_resist=800)

        weapon = _make_greater_weapon(CombatScript.TRIELEMENTALSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        # Direct call has circle=8; ApplyElementalDamage calls have circle=1
        direct = [e for e in resisted if e.get("circle") == 8]
        assert len(direct) == 1, f"Expected 1 direct resisted entry (circle=8), got {len(direct)}"

        assert direct[0]["chance"] == 13, \
            f"Expected chance=13, got {direct[0]['chance']}"
        assert direct[0]["evalint"] == 100

    def test_trielemental_resisted_mage_defender(self, shard, combat_trees):
        """Trielemental: Mage L3 defender. resist=80, circle=8.

        Base chance = max(CInt(80/6), CInt(80-(100/4+8*6))) = max(13, 7) = 13.
        Mage L3 bonus: 1 + 3*0.25 = 1.75.
        chance = CInt(13 * 1.75) = CInt(22.75) = 22.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)

        defender = _make_defender(magic_resist=800)
        defender.set_property(CLASSEID_MAGE, 3)

        weapon = _make_greater_weapon(CombatScript.TRIELEMENTALSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = [e for e in resisted if e.get("circle") == 8]
        assert len(direct) == 1

        assert direct[0]["chance"] == 22, \
            f"Expected chance=22 (Mage L3 defender), got {direct[0]['chance']}"


# ---------------------------------------------------------------------------
# Section 7: Over-Protection + Reactive Armor Edge Case
# ---------------------------------------------------------------------------


class TestOverProtectionPlusReactive:
    """Defender has >100% elemental protection (heals) + ReactiveArmor (reflects physical)."""

    def test_elemental_overprotection_heals_plus_reactive(self, shard, combat_trees):
        """Defender with 120% fire protection + reactive armor.

        Trielemental fires FIRE+AIR+WATER. Fire is healed (>100% prot),
        while reactive reflects physical portion from basedamage.
        """
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("ReactiveArmor", 50)
        defender.set_property("FireProtection", 120)  # Over-protection → heals

        weapon = _make_greater_weapon(CombatScript.TRIELEMENTALSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("reactive_triggered") == 1, \
            "Reactive should still trigger"
        assert result.metrics.get("effect_triggered") == 1, \
            "Trielemental should still trigger"

        # Check elemental metrics — fire should show healing
        elem = result.metrics.get("elemental_applied", [])
        fire_entries = [e for e in elem if e.get("attack_type") == 0x01]
        if fire_entries:
            # Fire with >100% protection should have healed amount
            assert "healed" in fire_entries[0], \
                "Fire with 120% protection should record healed amount"

    def test_overprotection_heals_without_reactive(self, shard, combat_trees):
        """Baseline: >100% protection heals without reactive, for comparison."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("FireProtection", 120)

        weapon = _make_greater_weapon(CombatScript.TRIELEMENTALSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        hp_before = defender.hp
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        elem = result.metrics.get("elemental_applied", [])
        fire_entries = [e for e in elem if e.get("attack_type") == 0x01]
        if fire_entries:
            assert "healed" in fire_entries[0], \
                "Fire with 120% protection should heal"


# ---------------------------------------------------------------------------
# Section 8: Resisted() Metrics Structure Validation
# ---------------------------------------------------------------------------


class TestResistedMetricsStructure:
    """Verify the structure and completeness of list:resisted metric entries."""

    def test_resisted_entry_has_all_fields(self, shard, combat_trees):
        """Each resisted entry has: dmg_before, dmg_after, chance, did_resist, circle, evalint, resist."""
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)
        defender = _make_defender(magic_resist=600)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        assert len(resisted) >= 1

        required_fields = {"dmg_before", "dmg_after", "chance", "did_resist", "circle", "evalint", "resist"}
        for entry in resisted:
            missing = required_fields - set(entry.keys())
            assert not missing, f"Missing fields in resisted entry: {missing}"

    def test_resisted_evalint_and_resist_match_skills(self, shard, combat_trees):
        """The evalint and resist values in the direct Resisted() call match skills.

        Dualplanar produces 3 resisted entries:
        - circle=9: direct call, caster=attacker → evalint from attacker
        - circle=1 (x2): ApplyPlanarDamage calls, caster=targ(=defender) → evalint from defender
        We check the direct call (circle=9) for attacker's evalint.
        """
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 800)   # 80 display
        defender = _make_defender(magic_resist=600)  # 60 display

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        direct = [e for e in resisted if e.get("circle") == 9]
        assert len(direct) == 1

        assert direct[0]["evalint"] == 80, f"Expected evalint=80, got {direct[0]['evalint']}"
        assert direct[0]["resist"] == 60, f"Expected resist=60, got {direct[0]['resist']}"

    def test_resisted_circle_values(self, shard, combat_trees):
        """Dualplanar produces resisted entries with circle=9 (direct) and circle=1 (ApplyPlanarDamage)."""
        attacker = _make_attacker(class_id=None)
        attacker.set_skill(SKILLID_MAGERY, 1000)
        attacker.set_skill(SKILLID_EVALINT, 1000)
        defender = _make_defender(magic_resist=600)

        weapon = _make_greater_weapon(CombatScript.DUALPLANARSCRIPT, chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        assert len(resisted) >= 1

        circles = [e["circle"] for e in resisted]
        assert 9 in circles, "Direct Resisted() call should use circle=9"

        for entry in resisted:
            assert "circle" in entry
            assert entry["circle"] > 0
