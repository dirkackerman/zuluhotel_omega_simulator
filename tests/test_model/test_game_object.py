"""Tests for base GameObject: property bag, serial, .isa()."""

from omega.model.game_object import GameObject
from omega.model.constants import POLCLASS_ITEM, POLCLASS_WEAPON, POLCLASS_MOBILE


class TestSerialAssignment:
    def test_unique_serials(self):
        a = GameObject()
        b = GameObject()
        assert a.serial != b.serial

    def test_serial_is_positive(self):
        obj = GameObject()
        assert obj.serial > 0


class TestIntrinsicFields:
    def test_default_values(self):
        obj = GameObject()
        assert obj.objtype == 0
        assert obj.graphic == 0
        assert obj.name == ""
        assert obj.color == 0

    def test_custom_values(self):
        obj = GameObject(objtype=0x13BB, graphic=0x1400, name="TestItem", color=42)
        assert obj.objtype == 0x13BB
        assert obj.graphic == 0x1400
        assert obj.name == "TestItem"
        assert obj.color == 42

    def test_graphic_defaults_to_objtype(self):
        obj = GameObject(objtype=0xFF01)
        assert obj.graphic == 0xFF01


class TestPropertyBag:
    def test_set_and_get(self):
        obj = GameObject()
        obj.set_property("SlayType", "Undead")
        assert obj.get_property("SlayType") == "Undead"

    def test_get_missing_returns_none(self):
        obj = GameObject()
        assert obj.get_property("Nonexistent") is None

    def test_erase_existing(self):
        obj = GameObject()
        obj.set_property("key", "value")
        assert obj.erase_property("key") is True
        assert obj.get_property("key") is None

    def test_erase_missing(self):
        obj = GameObject()
        assert obj.erase_property("nope") is False

    def test_has_property(self):
        obj = GameObject()
        assert not obj.has_property("x")
        obj.set_property("x", 42)
        assert obj.has_property("x")

    def test_overwrite_property(self):
        obj = GameObject()
        obj.set_property("k", 1)
        obj.set_property("k", 2)
        assert obj.get_property("k") == 2

    def test_property_bag_supports_any_type(self):
        obj = GameObject()
        obj.set_property("list", [1, 2, 3])
        obj.set_property("dict", {"a": 1})
        assert obj.get_property("list") == [1, 2, 3]
        assert obj.get_property("dict") == {"a": 1}


class TestIsa:
    def test_base_is_item(self):
        obj = GameObject()
        assert obj.isa(POLCLASS_ITEM)

    def test_base_is_not_weapon(self):
        obj = GameObject()
        assert not obj.isa(POLCLASS_WEAPON)

    def test_base_is_not_mobile(self):
        obj = GameObject()
        assert not obj.isa(POLCLASS_MOBILE)

    def test_isa_alias(self):
        obj = GameObject()
        assert obj.IsA(POLCLASS_ITEM) == obj.isa(POLCLASS_ITEM)


class TestRepr:
    def test_repr_contains_name(self):
        obj = GameObject(name="Sword")
        r = repr(obj)
        assert "Sword" in r
        assert "GameObject" in r
