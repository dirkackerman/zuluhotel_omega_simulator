"""Tests for scenario definitions and materialization."""

import dataclasses
from pathlib import Path

import pytest

from omega.config.enchantments import Enchantment, EnchantmentRegistry
from omega.config.spells import Spell
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.simulation.scenario import (
    ArmorSpec,
    CombatantSpec,
    ParameterSweep,
    Scenario,
    Variable,
    WeaponSpec,
    apply_variable,
    build_armor,
    build_combatant,
    build_weapon,
)

from tests.conftest import FIXTURE_SHARD_ROOT


class TestWeaponSpec:
    def test_defaults(self):
        spec = WeaponSpec()
        assert spec.name == "Weapon"
        assert spec.damage == "3d6+2"
        assert spec.attribute == SKILLID_SWORDSMANSHIP

    def test_build_weapon(self):
        spec = WeaponSpec(name="Broadsword", damage="3d5+2", speed=35)
        w = build_weapon(spec)
        assert w.name == "Broadsword"
        assert w.damage.count == 3
        assert w.damage.sides == 5
        assert w.damage.bonus == 2
        assert w.speed == 35

    def test_build_weapon_properties(self):
        spec = WeaponSpec(properties={"SlayType": "Undead"})
        w = build_weapon(spec)
        assert w.get_property("SlayType") == "Undead"


class TestArmorSpec:
    def test_defaults(self):
        spec = ArmorSpec()
        assert spec.ar == 0

    def test_build_armor(self):
        spec = ArmorSpec(name="Plate", ar=50, coverage=("Body",))
        a = build_armor(spec)
        assert a.name == "Plate"
        assert a.ar == 50
        assert a.coverage == ["Body"]

    def test_build_armor_properties(self):
        spec = ArmorSpec(properties={"Cursed": 1})
        a = build_armor(spec)
        assert a.get_property("Cursed") == 1


class TestCombatantSpec:
    def test_inline_defaults(self):
        spec = CombatantSpec()
        assert spec.str_ == 100
        assert spec.npc_template is None

    def test_build_combatant_inline(self):
        spec = CombatantSpec(
            name="Warrior",
            str_=100,
            int_=25,
            dex_=80,
            skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 90},
            class_levels={"IsWarrior": 5},
            weapon=WeaponSpec(damage="3d6+2"),
            armor=ArmorSpec(ar=30),
        )
        mob, weapon, armor = build_combatant(spec)
        assert mob.name == "Warrior"
        assert mob.str_base == 100
        assert mob.dex_base == 80
        # Skills stored as display * 10
        assert mob.get_skill(SKILLID_SWORDSMANSHIP) == 1000
        assert mob.get_skill(SKILLID_TACTICS) == 900
        # Class level stored as property
        assert mob.get_property("IsWarrior") == 5
        # Vitals default to stat-derived
        assert mob.hp == 200  # str * 2
        assert mob.max_hp == 200
        assert mob.mana == 25  # int
        assert mob.stamina == 80  # dex
        # Weapon and armor
        assert weapon.damage.count == 3
        assert armor.ar == 30

    def test_build_combatant_explicit_vitals(self):
        spec = CombatantSpec(hp=500, mana=200, stamina=150)
        mob, _, _ = build_combatant(spec)
        assert mob.hp == 500
        assert mob.max_hp == 500
        assert mob.mana == 200
        assert mob.stamina == 150

    def test_build_combatant_no_weapon(self):
        spec = CombatantSpec()
        mob, weapon, armor = build_combatant(spec)
        assert weapon.name == "Fist"
        assert armor.ar == 0

    def test_build_combatant_npc(self):
        spec = CombatantSpec(name="Target", is_npc=True)
        mob, _, _ = build_combatant(spec)
        assert mob.is_npc is True


class TestVariable:
    def test_from_range_inclusive(self):
        v = Variable.from_range("attacker", "skills.40", start=50, stop=130, step=10)
        assert v.target == "attacker"
        assert v.parameter == "skills.40"
        assert v.values == (50, 60, 70, 80, 90, 100, 110, 120, 130)

    def test_from_range_step_1(self):
        v = Variable.from_range("defender", "str_", start=50, stop=53)
        assert v.values == (50, 51, 52, 53)

    def test_explicit_values(self):
        v = Variable(target="attacker", parameter="weapon.damage", values=("2d6+1", "3d6+2"))
        assert len(v.values) == 2


class TestParameterSweep:
    def test_grid_size(self):
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=CombatantSpec(),
                defender=CombatantSpec(),
                iterations=10,
            ),
            variables=(
                Variable.from_range("attacker", "skills.40", 50, 100, 10),  # 6 values
                Variable.from_range("defender", "str_", 50, 100, 50),  # 2 values
            ),
        )
        # Grid = 6 * 2 = 12
        from itertools import product
        combos = list(product(*(v.values for v in sweep.variables)))
        assert len(combos) == 12


class TestApplyVariable:
    def test_apply_stat(self):
        spec = CombatantSpec(str_=100)
        new = apply_variable(spec, "str_", 80)
        assert new.str_ == 80
        assert spec.str_ == 100  # original unchanged

    def test_apply_skill(self):
        spec = CombatantSpec(skills={SKILLID_SWORDSMANSHIP: 100})
        new = apply_variable(spec, f"skills.{SKILLID_SWORDSMANSHIP}", 80)
        assert new.skills[SKILLID_SWORDSMANSHIP] == 80

    def test_apply_class_level(self):
        spec = CombatantSpec(class_levels={"IsWarrior": 5})
        new = apply_variable(spec, "class_levels.IsWarrior", 3)
        assert new.class_levels["IsWarrior"] == 3

    def test_apply_weapon_field(self):
        spec = CombatantSpec(weapon=WeaponSpec(damage="3d6+2"))
        new = apply_variable(spec, "weapon.damage", "2d8+1")
        assert new.weapon.damage == "2d8+1"

    def test_apply_armor_field(self):
        spec = CombatantSpec(armor=ArmorSpec(ar=30))
        new = apply_variable(spec, "armor.ar", 50)
        assert new.armor.ar == 50

    def test_apply_weapon_creates_default(self):
        spec = CombatantSpec(weapon=None)
        new = apply_variable(spec, "weapon.speed", 25)
        assert new.weapon.speed == 25

    def test_apply_unknown_raises(self):
        spec = CombatantSpec()
        with pytest.raises(ValueError, match="Unknown variable parameter"):
            apply_variable(spec, "nonexistent", 42)

    def test_apply_hp(self):
        spec = CombatantSpec(hp=100)
        new = apply_variable(spec, "hp", 500)
        assert new.hp == 500

    def test_apply_weapon_hitscript(self):
        spec = CombatantSpec(weapon=WeaponSpec())
        new = apply_variable(spec, "weapon.hitscript", ":combat:spellstrikescript")
        assert new.weapon.hitscript == ":combat:spellstrikescript"


class TestWeaponSpecHitscript:
    """Tests for WeaponSpec.hitscript and enchantment name resolution."""

    def test_hitscript_default_none(self):
        spec = WeaponSpec()
        assert spec.hitscript is None

    def test_build_weapon_no_hitscript(self):
        spec = WeaponSpec()
        w = build_weapon(spec)
        assert w.hitscript is None

    def test_build_weapon_raw_package_path(self):
        spec = WeaponSpec(hitscript=":combat:spellstrikescript")
        w = build_weapon(spec)
        assert w.hitscript == ":combat:spellstrikescript"

    def test_build_weapon_enchantment_name_fireball(self):
        cfg = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "hitscriptdesc.cfg"
        reg = EnchantmentRegistry.from_cfg(cfg)
        spec = WeaponSpec(hitscript="Fireball")
        w = build_weapon(spec, enchantment_registry=reg)
        assert w.hitscript == ":combat:spellstrikescript"
        assert w.get_property("HitWithSpell") == 18

    def test_build_weapon_enchantment_name_piercing(self):
        cfg = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "hitscriptdesc.cfg"
        reg = EnchantmentRegistry.from_cfg(cfg)
        spec = WeaponSpec(hitscript="Piercing")
        w = build_weapon(spec, enchantment_registry=reg)
        assert w.hitscript == ":combat:piercingscript"

    def test_build_weapon_enchantment_name_planar_fury(self):
        cfg = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "hitscriptdesc.cfg"
        reg = EnchantmentRegistry.from_cfg(cfg)
        spec = WeaponSpec(hitscript="Planar Fury")
        w = build_weapon(spec, enchantment_registry=reg)
        assert w.hitscript == ":combat:dualplanarscript"
        assert w.get_property("ChanceOfEffect") == 7

    def test_build_weapon_unknown_name_raises(self):
        spec = WeaponSpec(hitscript="Nonexistent")
        reg = EnchantmentRegistry()
        with pytest.raises(ValueError, match="Unknown enchantment name"):
            build_weapon(spec, enchantment_registry=reg)

    def test_build_combatant_with_hitscript(self):
        cfg = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "hitscriptdesc.cfg"
        reg = EnchantmentRegistry.from_cfg(cfg)
        spec = CombatantSpec(
            weapon=WeaponSpec(hitscript="Fireball"),
        )
        mob, weapon, armor = build_combatant(spec, enchantment_registry=reg)
        assert weapon.hitscript == ":combat:spellstrikescript"
        assert weapon.get_property("HitWithSpell") == 18


class TestEnchantWith:
    """Tests for WeaponSpec.enchant_with()."""

    def test_spell_enchantment(self):
        spec = WeaponSpec(damage="3d6+2").enchant_with(Enchantment.OF_DAEMONS_BREATH)
        assert spec.hitscript == ":combat:spellstrikescript"
        assert spec.properties["HitWithSpell"] == Spell.FIREBALL

    def test_slayer_enchantment(self):
        spec = WeaponSpec().enchant_with(Enchantment.SILVER)
        assert spec.hitscript == ":combat:slayerscript"
        assert spec.properties["SlayType"] == "Undead"

    def test_effect_enchantment(self):
        spec = WeaponSpec().enchant_with(Enchantment.OF_PIERCING)
        assert spec.hitscript == ":combat:piercingscript"

    def test_greater_enchantment(self):
        spec = WeaponSpec().enchant_with(Enchantment.OF_PLANAR_FURY)
        assert spec.hitscript == ":combat:dualplanarscript"
        assert spec.properties["ChanceOfEffect"] == 7

    def test_preserves_existing_fields(self):
        spec = WeaponSpec(name="Claymore", damage="1d20+35", speed=70)
        enchanted = spec.enchant_with(Enchantment.OF_GAIAS_WRATH)
        assert enchanted.name == "Claymore"
        assert enchanted.damage == "1d20+35"
        assert enchanted.speed == 70

    def test_existing_properties_override_defaults(self):
        spec = WeaponSpec(
            properties={"ChanceOfEffect": 30, "EffectCircle": 9},
        ).enchant_with(Enchantment.OF_DAEMONS_BREATH)
        # User-set properties take precedence
        assert spec.properties["ChanceOfEffect"] == 30
        assert spec.properties["EffectCircle"] == 9
        # Enchantment still provides HitWithSpell
        assert spec.properties["HitWithSpell"] == Spell.FIREBALL

    def test_build_weapon_from_enchant_with(self):
        spec = WeaponSpec(damage="1d20+35").enchant_with(Enchantment.SILVER)
        w = build_weapon(spec)
        assert w.hitscript == ":combat:slayerscript"
        assert w.get_property("SlayType") == "Undead"
