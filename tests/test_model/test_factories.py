"""Tests for factory functions — inline and config-based object creation."""

from omega.config.dice import DiceSpec
from omega.model.constants import (
    CLASSEID_WARRIOR,
    LAYER_HAND1,
    POLCLASS_MOBILE,
    POLCLASS_NPC,
    POLCLASS_WEAPON,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.model.factories import create_mobile_inline
from omega.model.items import Armor, Weapon


class TestCreateMobileInline:
    def test_basic_warrior(self):
        w = Weapon(
            name="Broadsword",
            damage=DiceSpec(3, 5, 2),
            speed=35,
            attribute=SKILLID_SWORDSMANSHIP,
        )
        m = create_mobile_inline(
            name="TestWarrior",
            str_=100,
            int_=25,
            dex_=100,
            skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
            class_levels={CLASSEID_WARRIOR: 5},
            weapon=w,
        )
        assert m.name == "TestWarrior"
        assert m.strength == 100
        assert m.intelligence == 25
        assert m.dexterity == 100
        assert m.get_effective_skill(SKILLID_SWORDSMANSHIP) == 100
        assert m.get_effective_skill(SKILLID_TACTICS) == 100
        assert m.get_property(CLASSEID_WARRIOR) == 5
        assert m.get_equipped(LAYER_HAND1) is w

    def test_hp_defaults_to_strength(self):
        m = create_mobile_inline(str_=150)
        assert m.hp == 150
        assert m.max_hp == 150

    def test_hp_explicit(self):
        m = create_mobile_inline(str_=100, hp=500)
        assert m.hp == 500
        assert m.max_hp == 500

    def test_mana_defaults_to_intelligence(self):
        m = create_mobile_inline(int_=80)
        assert m.mana == 80

    def test_stamina_defaults_to_dexterity(self):
        m = create_mobile_inline(dex_=90)
        assert m.stamina == 90

    def test_no_weapon(self):
        m = create_mobile_inline()
        assert m.get_equipped(LAYER_HAND1) is None

    def test_armor_equipped(self):
        armor = [
            Armor(name="Helm", ar=10, coverage=["Head"]),
            Armor(name="Plate", ar=25, coverage=["Body"]),
        ]
        m = create_mobile_inline(armor_pieces=armor)
        equip = m.list_equipment()
        assert len(equip) >= 2
        total_ar = sum(a.ar for a in equip.values() if isinstance(a, Armor))
        assert total_ar == 35

    def test_is_player_by_default(self):
        m = create_mobile_inline()
        assert not m.is_npc
        assert m.isa(POLCLASS_MOBILE)

    def test_is_npc(self):
        m = create_mobile_inline(is_npc=True)
        assert m.is_npc
        assert m.isa(POLCLASS_NPC)

    def test_skills_stored_internally(self):
        m = create_mobile_inline(skills={SKILLID_SWORDSMANSHIP: 120})
        # Internal storage is x10
        assert m.get_skill(SKILLID_SWORDSMANSHIP) == 1200
        assert m.get_effective_skill(SKILLID_SWORDSMANSHIP) == 120
