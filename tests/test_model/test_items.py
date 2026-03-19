"""Tests for Weapon and Armor game objects."""

from omega.config.dice import DiceSpec
from omega.model.constants import (
    ATTRIBUTEID_SWORDSMANSHIP,
    POLCLASS_ARMOR,
    POLCLASS_ITEM,
    POLCLASS_WEAPON,
    POLCLASS_MOBILE,
    SKILLID_SWORDSMANSHIP,
)
from omega.model.items import Armor, Weapon


class TestWeapon:
    def test_default_weapon(self):
        w = Weapon()
        assert w.damage == DiceSpec(count=1, sides=4, bonus=0)
        assert w.speed == 50
        assert w.attribute == ""
        assert not w.two_handed
        assert w.quality == 1.0
        assert w.hitscript is None

    def test_custom_weapon(self):
        damage = DiceSpec(count=3, sides=5, bonus=2)
        w = Weapon(
            name="Broadsword",
            objtype=0x0F5E,
            damage=damage,
            speed=35,
            attribute=SKILLID_SWORDSMANSHIP,
            two_handed=False,
            hp=100,
            max_hp=100,
        )
        assert w.name == "Broadsword"
        assert w.damage == damage
        assert w.speed == 35
        assert w.attribute == ATTRIBUTEID_SWORDSMANSHIP
        assert w.hp == 100
        assert w.max_hp == 100

    def test_weapon_isa(self):
        w = Weapon()
        assert w.isa(POLCLASS_WEAPON)
        assert w.isa(POLCLASS_ITEM)
        assert not w.isa(POLCLASS_ARMOR)
        assert not w.isa(POLCLASS_MOBILE)

    def test_weapon_desc(self):
        w = Weapon(name="Halberd")
        assert w.desc == "Halberd"

    def test_weapon_property_bag(self):
        w = Weapon(name="Slayer Sword")
        w.set_property("SlayType", "Undead")
        w.set_property("Astral", 1)
        assert w.get_property("SlayType") == "Undead"
        assert w.get_property("Astral") == 1

    def test_weapon_durability(self):
        w = Weapon(hp=50, max_hp=50)
        w.hp -= 1
        assert w.hp == 49
        assert w.max_hp == 50

    def test_set_blocks_casting_false(self):
        w = Weapon(name="Fist")
        w.set_blocks_casting(False)
        assert w.get_property("BlocksCastingIfInHand") == 0

    def test_set_blocks_casting_true(self):
        w = Weapon(name="Shield")
        w.set_blocks_casting(True)
        assert w.get_property("BlocksCastingIfInHand") == 1

    def test_set_blocks_casting_toggle(self):
        w = Weapon(name="Staff")
        w.set_blocks_casting(True)
        assert w.get_property("BlocksCastingIfInHand") == 1
        w.set_blocks_casting(False)
        assert w.get_property("BlocksCastingIfInHand") == 0


class TestArmor:
    def test_default_armor(self):
        a = Armor()
        assert a.ar == 0
        assert a.coverage == []
        assert a.hp == 70
        assert a.max_hp == 70

    def test_custom_armor(self):
        a = Armor(
            name="ChainmailCoif",
            objtype=0x13BB,
            ar=16,
            coverage=["Head", "Neck"],
            hp=70,
            max_hp=70,
        )
        assert a.name == "ChainmailCoif"
        assert a.ar == 16
        assert a.coverage == ["Head", "Neck"]

    def test_armor_isa(self):
        a = Armor()
        assert a.isa(POLCLASS_ARMOR)
        assert a.isa(POLCLASS_ITEM)
        assert not a.isa(POLCLASS_WEAPON)
        assert not a.isa(POLCLASS_MOBILE)

    def test_armor_desc(self):
        a = Armor(name="Plate Helm")
        assert a.desc == "Plate Helm"

    def test_armor_property_bag(self):
        a = Armor(name="Enchanted Shield")
        a.set_property("DefaultDex", -2)
        a.set_property("MagicPenalty", 8)
        assert a.get_property("DefaultDex") == -2
        assert a.get_property("MagicPenalty") == 8

    def test_armor_layer(self):
        a = Armor(layer=0x06)
        assert a.layer == 0x06
