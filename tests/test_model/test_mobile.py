"""Tests for Mobile game object — stats, skills, vitals, equipment, AR."""

from omega.config.dice import DiceSpec
from omega.model.constants import (
    CLASSEID_WARRIOR,
    LAYER_CHEST,
    LAYER_HAND1,
    LAYER_HELM,
    POLCLASS_MOBILE,
    POLCLASS_NPC,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile


class TestMobileBasics:
    def test_default_mobile_is_player(self):
        m = Mobile()
        assert not m.is_npc
        assert m.npctemplate == ""
        assert m.cmdlevel == 0
        assert not m.dead

    def test_npc_mobile(self):
        m = Mobile(is_npc=True, npctemplate="nazgul", name="Nazgul")
        assert m.is_npc
        assert m.npctemplate == "nazgul"
        assert m.name == "Nazgul"


class TestMobileIsa:
    def test_player_is_mobile(self):
        m = Mobile()
        assert m.isa(POLCLASS_MOBILE)

    def test_player_is_not_npc(self):
        m = Mobile()
        assert not m.isa(POLCLASS_NPC)

    def test_npc_is_mobile_and_npc(self):
        m = Mobile(is_npc=True)
        assert m.isa(POLCLASS_MOBILE)
        assert m.isa(POLCLASS_NPC)


class TestMobileStats:
    def test_default_stats(self):
        m = Mobile()
        assert m.strength == 10
        assert m.intelligence == 10
        assert m.dexterity == 10

    def test_custom_stats(self):
        m = Mobile()
        m.str_base = 100
        m.int_base = 50
        m.dex_base = 75
        assert m.strength == 100
        assert m.intelligence == 50
        assert m.dexterity == 75

    def test_stat_mods(self):
        m = Mobile()
        m.str_base = 100
        m.str_mod = 50  # +5 effective
        assert m.strength == 105

    def test_negative_stat_mod(self):
        m = Mobile()
        m.str_base = 100
        m.str_mod = -30  # -3 effective
        assert m.strength == 97


class TestMobileVitals:
    def test_default_vitals(self):
        m = Mobile()
        assert m.hp == 10
        assert m.max_hp == 10
        assert m.mana == 10
        assert m.max_mana == 10
        assert m.stamina == 10
        assert m.max_stamina == 10

    def test_modify_vitals(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        m.mana = 200
        assert m.hp == 50
        assert m.max_hp == 100
        assert m.mana == 200


class TestMobileSkills:
    def test_set_and_get_skill(self):
        m = Mobile()
        m.set_skill(SKILLID_SWORDSMANSHIP, 1000)  # 100.0 display
        assert m.get_skill(SKILLID_SWORDSMANSHIP) == 1000

    def test_get_effective_skill(self):
        m = Mobile()
        m.set_skill(SKILLID_SWORDSMANSHIP, 1000)
        assert m.get_effective_skill(SKILLID_SWORDSMANSHIP) == 100

    def test_missing_skill_is_zero(self):
        m = Mobile()
        assert m.get_skill(SKILLID_TACTICS) == 0
        assert m.get_effective_skill(SKILLID_TACTICS) == 0

    def test_get_attribute_by_name_stat(self):
        m = Mobile()
        m.str_base = 100
        m.str_mod = 50
        # GetAttribute returns tenths: base*10 + mod
        assert m.get_attribute("strength") == 1050

    def test_get_attribute_by_name_skill(self):
        m = Mobile()
        m.set_skill(SKILLID_SWORDSMANSHIP, 1200)
        assert m.get_attribute("Swordsmanship") == 1200

    def test_get_attribute_case_insensitive_stat(self):
        m = Mobile()
        m.dex_base = 80
        assert m.get_attribute("Dexterity") == 800
        assert m.get_attribute("dexterity") == 800

    def test_get_attribute_unknown_returns_zero(self):
        m = Mobile()
        assert m.get_attribute("Nonexistent") == 0


class TestMobileEquipment:
    def test_equip_weapon(self):
        m = Mobile()
        w = Weapon(name="Sword", damage=DiceSpec(3, 5, 2))
        m.equip(LAYER_HAND1, w)
        assert m.get_equipped(LAYER_HAND1) is w

    def test_unequip(self):
        m = Mobile()
        w = Weapon(name="Sword")
        m.equip(LAYER_HAND1, w)
        removed = m.unequip(LAYER_HAND1)
        assert removed is w
        assert m.get_equipped(LAYER_HAND1) is None

    def test_unequip_empty_returns_none(self):
        m = Mobile()
        assert m.unequip(LAYER_HAND1) is None

    def test_list_equipment(self):
        m = Mobile()
        w = Weapon(name="Sword")
        a = Armor(name="Helm", ar=10)
        m.equip(LAYER_HAND1, w)
        m.equip(LAYER_HELM, a)
        equip = m.list_equipment()
        assert len(equip) == 2
        assert equip[LAYER_HAND1] is w
        assert equip[LAYER_HELM] is a


class TestMobileAR:
    def test_no_armor_ar_is_zero(self):
        m = Mobile()
        assert m.ar == 0

    def test_single_armor(self):
        m = Mobile()
        a = Armor(name="Plate", ar=25)
        m.equip(LAYER_CHEST, a)
        assert m.ar == 25

    def test_multiple_armor_sums(self):
        m = Mobile()
        m.equip(LAYER_CHEST, Armor(name="Plate", ar=25))
        m.equip(LAYER_HELM, Armor(name="Helm", ar=10))
        assert m.ar == 35

    def test_weapon_does_not_add_to_ar(self):
        m = Mobile()
        m.equip(LAYER_HAND1, Weapon(name="Sword"))
        m.equip(LAYER_CHEST, Armor(name="Plate", ar=25))
        assert m.ar == 25


class TestMobileClassLevels:
    def test_class_via_property_bag(self):
        m = Mobile()
        m.set_property(CLASSEID_WARRIOR, 5)
        assert m.get_property(CLASSEID_WARRIOR) == 5

    def test_no_class_returns_none(self):
        m = Mobile()
        assert m.get_property(CLASSEID_WARRIOR) is None
