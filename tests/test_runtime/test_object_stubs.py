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
from omega.runtime.context import SimulationContext, set_context
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


class TestSetHP:
    """SetHP: clamping to [0, max_hp], side effect recording."""

    def test_set_hp_basic(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetHP", [m, 75])
        assert m.hp == 75

    def test_set_hp_clamps_to_max(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetHP", [m, 200])
        assert m.hp == 100

    def test_set_hp_clamps_to_zero(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetHP", [m, -10])
        assert m.hp == 0

    def test_set_hp_records_side_effect(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetHP", [m, 75])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "hp_set"
        assert ctx.side_effects[0].value == 25  # delta: 75 - 50

    def test_set_hp_null_mobile(self):
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetHP", [None, 50])
        assert len(ctx.side_effects) == 0


class TestSetManaSideEffects:
    """SetMana: side effect recording with delta tracking."""

    def test_set_mana_records_side_effect(self):
        m = Mobile()
        m.mana = 80
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, 50])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "mana_changed"
        assert ctx.side_effects[0].value == -30  # delta: 50 - 80

    def test_set_mana_increase(self):
        m = Mobile()
        m.mana = 50
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, 80])
        assert ctx.side_effects[0].value == 30

    def test_set_mana_null_mobile(self):
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [None, 50])
        assert len(ctx.side_effects) == 0


class TestSetStaminaSideEffects:
    """SetStamina: side effect recording with delta tracking."""

    def test_set_stamina_records_side_effect(self):
        m = Mobile()
        m.stamina = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetStamina", [m, 60])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "stamina_changed"
        assert ctx.side_effects[0].value == -40  # delta: 60 - 100

    def test_set_stamina_increase(self):
        m = Mobile()
        m.stamina = 50
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetStamina", [m, 80])
        assert ctx.side_effects[0].value == 30


class TestGetMaxManaStamina:
    """GetMaxMana/GetMaxStamina: return values, null handling."""

    def test_get_max_mana(self):
        m = Mobile()
        m.max_mana = 150
        assert call_builtin("uo", "GetMaxMana", [m]) == 150

    def test_get_max_stamina(self):
        m = Mobile()
        m.max_stamina = 200
        assert call_builtin("uo", "GetMaxStamina", [m]) == 200

    def test_get_max_mana_null(self):
        assert call_builtin("uo", "GetMaxMana", [None]) == 0

    def test_get_max_stamina_null(self):
        assert call_builtin("uo", "GetMaxStamina", [None]) == 0


class TestGetVital:
    """GetVital: hundredths conversion, vital mapping."""

    def test_get_vital_life(self):
        m = Mobile()
        m.hp = 75
        result = call_builtin("vitals", "GetVital", [m, "life"])
        assert result == 7500  # hundredths

    def test_get_vital_mana(self):
        m = Mobile()
        m.mana = 50
        result = call_builtin("vitals", "GetVital", [m, "mana"])
        assert result == 5000

    def test_get_vital_stamina(self):
        m = Mobile()
        m.stamina = 30
        result = call_builtin("vitals", "GetVital", [m, "stamina"])
        assert result == 3000

    def test_get_vital_unknown(self):
        m = Mobile()
        assert call_builtin("vitals", "GetVital", [m, "unknown"]) == 0

    def test_get_vital_null_mobile(self):
        assert call_builtin("vitals", "GetVital", [None, "life"]) == 0


class TestGetVitalMaximumValue:
    """GetVitalMaximumValue: hundredths conversion."""

    def test_max_life(self):
        m = Mobile()
        m.max_hp = 200
        result = call_builtin("vitals", "GetVitalMaximumValue", [m, "life"])
        assert result == 20000

    def test_max_mana(self):
        m = Mobile()
        m.max_mana = 100
        result = call_builtin("vitals", "GetVitalMaximumValue", [m, "mana"])
        assert result == 10000

    def test_max_stamina(self):
        m = Mobile()
        m.max_stamina = 80
        result = call_builtin("vitals", "GetVitalMaximumValue", [m, "stamina"])
        assert result == 8000

    def test_max_unknown(self):
        m = Mobile()
        assert call_builtin("vitals", "GetVitalMaximumValue", [m, "unknown"]) == 0

    def test_max_null_mobile(self):
        assert call_builtin("vitals", "GetVitalMaximumValue", [None, "life"]) == 0


class TestSetVital:
    """SetVital: hundredths conversion, clamping, side effect recording."""

    def test_set_vital_life_hundredths(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 200
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "SetVital", [m, "life", 15000])
        assert m.hp == 150  # 15000 // 100

    def test_set_vital_clamps_to_max(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "SetVital", [m, "life", 30000])
        assert m.hp == 100  # clamped to max_hp

    def test_set_vital_clamps_to_zero(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "SetVital", [m, "life", -500])
        assert m.hp == 0

    def test_set_vital_records_hp_set_side_effect(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 200
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "SetVital", [m, "life", 10000])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "hp_set"
        assert ctx.side_effects[0].value == 50  # delta: 100 - 50

    def test_set_vital_records_mana_changed(self):
        m = Mobile()
        m.mana = 80
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "SetVital", [m, "mana", 5000])
        assert m.mana == 50
        assert ctx.side_effects[0].kind == "mana_changed"
        assert ctx.side_effects[0].value == -30

    def test_set_vital_records_stamina_changed(self):
        m = Mobile()
        m.stamina = 60
        m.max_stamina = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "SetVital", [m, "stamina", 9000])
        assert m.stamina == 90
        assert ctx.side_effects[0].kind == "stamina_changed"
        assert ctx.side_effects[0].value == 30

    def test_set_vital_returns_1_on_success(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("vitals", "SetVital", [m, "life", 8000])
        assert result == 1

    def test_set_vital_unknown_returns_0(self):
        m = Mobile()
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("vitals", "SetVital", [m, "unknown", 5000])
        assert result == 0

    def test_set_vital_null_mobile_returns_0(self):
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("vitals", "SetVital", [None, "life", 5000])
        assert result == 0


class TestHealDamage:
    """HealDamage: HP restoration, capping, side effects."""

    def test_heals_hp(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "HealDamage", [m, 30])
        assert m.hp == 80

    def test_caps_at_max_hp(self):
        m = Mobile()
        m.hp = 90
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "HealDamage", [m, 50])
        assert m.hp == 100

    def test_records_heal_side_effect(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "HealDamage", [m, 20])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "heal"
        assert ctx.side_effects[0].value == 20

    def test_zero_amount_no_effect(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "HealDamage", [m, 0])
        assert m.hp == 50
        assert len(ctx.side_effects) == 0

    def test_negative_amount_no_effect(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "HealDamage", [m, -10])
        assert m.hp == 50
        assert len(ctx.side_effects) == 0

    def test_null_mobile_no_crash(self):
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "HealDamage", [None, 20])
        assert len(ctx.side_effects) == 0


class TestSkillAccessors:
    def test_get_effective_skill(self):
        m = Mobile()
        m.set_skill(SKILLID_SWORDSMANSHIP, 1000)  # 100.0
        result = call_builtin("", "GetEffectiveSkill", [m, SKILLID_SWORDSMANSHIP])
        assert result == 100

    def test_get_attribute_by_name(self):
        m = Mobile()
        m.str_base = 100
        # Default precision=0 (ATTRIBUTE_PRECISION_NORMAL) → display value
        result = call_builtin("", "GetAttribute", [m, "strength"])
        assert result == 100

    def test_get_attribute_by_name_tenths(self):
        m = Mobile()
        m.str_base = 100
        # precision=1 (ATTRIBUTE_PRECISION_TENTHS) → tenths
        result = call_builtin("", "GetAttribute", [m, "strength", 1])
        assert result == 1000

    def test_get_attribute_skill(self):
        m = Mobile()
        m.set_skill(SKILLID_TACTICS, 800)  # internal: 800 (display: 80)
        # Default precision → display value
        result = call_builtin("", "GetAttribute", [m, "Tactics"])
        assert result == 80

    def test_get_attribute_skill_tenths(self):
        m = Mobile()
        m.set_skill(SKILLID_TACTICS, 800)
        # precision=1 → tenths (raw internal)
        result = call_builtin("", "GetAttribute", [m, "Tactics", 1])
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
