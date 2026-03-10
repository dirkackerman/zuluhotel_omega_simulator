"""Tests for Batch 2 — object model POL built-in stubs."""

import omega.runtime  # noqa: F401
from omega.model.constants import (
    LAYER_HAND1,
    LAYER_HELM,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.runtime.registry import call_builtin


class TestPropertySystem:
    def test_get_set_roundtrip(self):
        m = Mobile(name="Test")
        call_builtin("uo", "SetObjProperty", [m, "SlayType", "Undead"])
        result = call_builtin("uo", "GetObjProperty", [m, "SlayType"])
        assert result == "Undead"

    def test_get_missing_property(self):
        m = Mobile(name="Test")
        result = call_builtin("uo", "GetObjProperty", [m, "Nonexistent"])
        assert result is None

    def test_erase_property(self):
        m = Mobile(name="Test")
        call_builtin("uo", "SetObjProperty", [m, "key", "value"])
        call_builtin("uo", "EraseObjProperty", [m, "key"])
        assert call_builtin("uo", "GetObjProperty", [m, "key"]) is None

    def test_property_on_weapon(self):
        w = Weapon(name="Sword")
        call_builtin("uo", "SetObjProperty", [w, "Astral", 1])
        assert call_builtin("uo", "GetObjProperty", [w, "Astral"]) == 1

    def test_null_obj(self):
        assert call_builtin("uo", "GetObjProperty", [None, "x"]) is None


class TestStatAccessors:
    def test_get_strength(self):
        m = Mobile()
        m.str_base = 100
        assert call_builtin("", "GetStrength", [m]) == 100

    def test_get_dexterity(self):
        m = Mobile()
        m.dex_base = 75
        assert call_builtin("", "GetDexterity", [m]) == 75

    def test_get_intelligence(self):
        m = Mobile()
        m.int_base = 50
        assert call_builtin("", "GetIntelligence", [m]) == 50

    def test_stat_mods(self):
        m = Mobile()
        m.str_mod = 50
        assert call_builtin("", "GetStrengthMod", [m]) == 50

    def test_set_stat_mod(self):
        m = Mobile()
        call_builtin("", "SetStrengthMod", [m, 100])
        assert m.str_mod == 100

    def test_null_mobile(self):
        assert call_builtin("", "GetStrength", [None]) == 0


class TestVitalAccessors:
    def test_get_hp(self):
        m = Mobile()
        m.hp = 42
        assert call_builtin("uo", "GetHP", [m]) == 42

    def test_get_max_hp(self):
        m = Mobile()
        m.max_hp = 100
        assert call_builtin("uo", "GetMaxHP", [m]) == 100

    def test_get_mana(self):
        m = Mobile()
        m.mana = 30
        assert call_builtin("uo", "GetMana", [m]) == 30

    def test_set_mana(self):
        m = Mobile()
        call_builtin("uo", "SetMana", [m, 50])
        assert m.mana == 50

    def test_get_stamina(self):
        m = Mobile()
        m.stamina = 60
        assert call_builtin("uo", "GetStamina", [m]) == 60

    def test_set_stamina(self):
        m = Mobile()
        call_builtin("uo", "SetStamina", [m, 80])
        assert m.stamina == 80


class TestSkillAccessors:
    def test_get_effective_skill(self):
        m = Mobile()
        m.set_skill(SKILLID_SWORDSMANSHIP, 1000)  # 100.0
        result = call_builtin("", "GetEffectiveSkill", [m, SKILLID_SWORDSMANSHIP])
        assert result == 100

    def test_get_attribute_by_name(self):
        m = Mobile()
        m.str_base = 100
        result = call_builtin("", "GetAttribute", [m, "strength"])
        assert result == 1000  # tenths

    def test_get_attribute_skill(self):
        m = Mobile()
        m.set_skill(SKILLID_TACTICS, 800)
        result = call_builtin("", "GetAttribute", [m, "Tactics"])
        assert result == 800

    def test_get_attribute_id_by_skill_id(self):
        result = call_builtin("", "GetAttributeIdBySkillId", [SKILLID_SWORDSMANSHIP])
        assert result == "Swordsmanship"


class TestEquipmentAccessors:
    def test_get_equipment_by_layer(self):
        m = Mobile()
        w = Weapon(name="Sword")
        m.equip(LAYER_HAND1, w)
        result = call_builtin("uo", "GetEquipmentByLayer", [m, LAYER_HAND1])
        assert result is w

    def test_get_equipment_empty_layer(self):
        m = Mobile()
        result = call_builtin("uo", "GetEquipmentByLayer", [m, LAYER_HELM])
        assert result is None

    def test_list_equipped_items(self):
        m = Mobile()
        w = Weapon(name="Sword")
        a = Armor(name="Helm", ar=10)
        m.equip(LAYER_HAND1, w)
        m.equip(LAYER_HELM, a)
        items = call_builtin("uo", "ListEquippedItems", [m])
        assert len(items) == 2
