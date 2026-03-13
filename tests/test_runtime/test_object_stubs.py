"""Tests for Batch 2 — object model POL built-in stubs.

M-V2.2 Property & Stat Accessor Audit: comprehensive coverage of property,
stat, vital, skill, and equipment stubs with edge cases and UNINIT handling.
"""

import omega.runtime  # noqa: F401
from omega.interpreter.types import UNINIT
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


# ===================================================================
# Property system
# ===================================================================


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


class TestPropertySystemExtended:
    """Extended property system tests: return values, UNINIT, edge cases."""

    def test_erase_obj_property_returns_1(self):
        """POL returns BLong(1) on success."""
        m = Mobile()
        call_builtin("uo", "SetObjProperty", [m, "key", "value"])
        result = call_builtin("uo", "EraseObjProperty", [m, "key"])
        assert result == 1

    def test_erase_nonexistent_property_returns_1(self):
        """EraseObjProperty on missing key still returns 1 (no error)."""
        m = Mobile()
        result = call_builtin("uo", "EraseObjProperty", [m, "nonexistent"])
        assert result == 1

    def test_get_obj_property_uninit_obj(self):
        """GetObjProperty(UNINIT, "x") → None (no crash)."""
        result = call_builtin("uo", "GetObjProperty", [UNINIT, "x"])
        assert result is None

    def test_set_obj_property_uninit_obj(self):
        """SetObjProperty(UNINIT, "x", 1) → no crash."""
        call_builtin("uo", "SetObjProperty", [UNINIT, "x", 1])

    def test_erase_obj_property_uninit_obj(self):
        """EraseObjProperty(UNINIT, "x") → no crash."""
        result = call_builtin("uo", "EraseObjProperty", [UNINIT, "x"])
        assert result == 1

    def test_get_obj_property_uninit_name(self):
        """GetObjProperty(m, UNINIT) → str(UNINIT) lookup, returns None."""
        m = Mobile()
        result = call_builtin("uo", "GetObjProperty", [m, UNINIT])
        assert result is None

    def test_set_obj_property_uninit_name(self):
        """SetObjProperty(m, UNINIT, 1) → works (str(UNINIT) as key)."""
        m = Mobile()
        call_builtin("uo", "SetObjProperty", [m, UNINIT, 1])
        # str(UNINIT) is the key — should be retrievable
        result = call_builtin("uo", "GetObjProperty", [m, UNINIT])
        assert result == 1

    def test_property_stores_any_type(self):
        """Property bag stores any type: list, dict, int, string, None."""
        m = Mobile()
        for val in [[1, 2, 3], {"a": 1}, 42, "hello", None]:
            call_builtin("uo", "SetObjProperty", [m, "test", val])
            assert call_builtin("uo", "GetObjProperty", [m, "test"]) == val

    def test_property_overwrite(self):
        """Set twice, get returns latest."""
        m = Mobile()
        call_builtin("uo", "SetObjProperty", [m, "key", "first"])
        call_builtin("uo", "SetObjProperty", [m, "key", "second"])
        assert call_builtin("uo", "GetObjProperty", [m, "key"]) == "second"

    def test_property_none_value(self):
        """SetObjProperty(m, "k", None) → stores None, get returns None."""
        m = Mobile()
        call_builtin("uo", "SetObjProperty", [m, "k", None])
        # None value is distinct from missing property (both return None)
        assert m.has_property("k") is True
        assert call_builtin("uo", "GetObjProperty", [m, "k"]) is None


# ===================================================================
# Stat accessors
# ===================================================================


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


class TestStatAccessorsExtended:
    """Extended stat accessor tests: mods, type coercion, UNINIT."""

    def test_get_strength_with_mod(self):
        """str_base=100, str_mod=50 → 105 (100 + 50//10)."""
        m = Mobile()
        m.str_base = 100
        m.str_mod = 50
        assert call_builtin("", "GetStrength", [m]) == 105

    def test_get_strength_negative_mod(self):
        """str_base=100, str_mod=-30 → 97 (100 + -30//10 = 100 + -3)."""
        m = Mobile()
        m.str_base = 100
        m.str_mod = -30
        assert call_builtin("", "GetStrength", [m]) == 97

    def test_set_strength_mod_float(self):
        """SetStrengthMod(m, 50.7) → int(50.7) = 50."""
        m = Mobile()
        call_builtin("", "SetStrengthMod", [m, 50.7])
        assert m.str_mod == 50

    def test_set_strength_mod_string(self):
        """SetStrengthMod(m, "100") → 100."""
        m = Mobile()
        call_builtin("", "SetStrengthMod", [m, "100"])
        assert m.str_mod == 100

    def test_set_strength_mod_uninit(self):
        """SetStrengthMod(m, UNINIT) → no crash, mod unchanged."""
        m = Mobile()
        m.str_mod = 42
        call_builtin("", "SetStrengthMod", [m, UNINIT])
        assert m.str_mod == 42  # unchanged

    def test_set_dexterity_mod_uninit(self):
        """SetDexterityMod(m, UNINIT) → no crash."""
        m = Mobile()
        m.dex_mod = 10
        call_builtin("", "SetDexterityMod", [m, UNINIT])
        assert m.dex_mod == 10

    def test_set_intelligence_mod_uninit(self):
        """SetIntelligenceMod(m, UNINIT) → no crash."""
        m = Mobile()
        m.int_mod = 20
        call_builtin("", "SetIntelligenceMod", [m, UNINIT])
        assert m.int_mod == 20

    def test_get_strength_uninit_mobile(self):
        """GetStrength(UNINIT) → 0 (getattr safe)."""
        assert call_builtin("", "GetStrength", [UNINIT]) == 0

    def test_get_dexterity_uninit_mobile(self):
        """GetDexterity(UNINIT) → 0."""
        assert call_builtin("", "GetDexterity", [UNINIT]) == 0

    def test_get_intelligence_uninit_mobile(self):
        """GetIntelligence(UNINIT) → 0."""
        assert call_builtin("", "GetIntelligence", [UNINIT]) == 0


# ===================================================================
# Vital accessors
# ===================================================================


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
        m.max_mana = 100
        call_builtin("uo", "SetMana", [m, 50])
        assert m.mana == 50

    def test_get_stamina(self):
        m = Mobile()
        m.stamina = 60
        assert call_builtin("uo", "GetStamina", [m]) == 60

    def test_set_stamina(self):
        m = Mobile()
        m.max_stamina = 100
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

    def test_set_hp_uninit_value(self):
        """SetHP(m, UNINIT) → no crash, hp unchanged."""
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetHP", [m, UNINIT])
        assert m.hp == 50

    def test_set_hp_string_value(self):
        """SetHP(m, "75") → hp=75 (int coercion)."""
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetHP", [m, "75"])
        assert m.hp == 75

    def test_set_hp_float_value(self):
        """SetHP(m, 75.6) → hp=75 (int truncation, not round)."""
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetHP", [m, 75.6])
        assert m.hp == 75


class TestSetManaSideEffects:
    """SetMana: clamping, side effect recording with delta tracking."""

    def test_set_mana_records_side_effect(self):
        m = Mobile()
        m.mana = 80
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, 50])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "mana_changed"
        assert ctx.side_effects[0].value == -30  # delta: 50 - 80

    def test_set_mana_increase(self):
        m = Mobile()
        m.mana = 50
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, 80])
        assert ctx.side_effects[0].value == 30

    def test_set_mana_null_mobile(self):
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [None, 50])
        assert len(ctx.side_effects) == 0

    def test_set_mana_clamps_to_max(self):
        """SetMana above max_mana clamps to max_mana."""
        m = Mobile()
        m.mana = 50
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, 200])
        assert m.mana == 100

    def test_set_mana_clamps_to_zero(self):
        """SetMana below 0 clamps to 0."""
        m = Mobile()
        m.mana = 50
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, -10])
        assert m.mana == 0

    def test_set_mana_uninit_value(self):
        """SetMana(m, UNINIT) → no crash, mana unchanged."""
        m = Mobile()
        m.mana = 50
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, UNINIT])
        assert m.mana == 50

    def test_set_mana_string_value(self):
        """SetMana(m, "50") → mana=50 (int coercion)."""
        m = Mobile()
        m.mana = 80
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, "50"])
        assert m.mana == 50


class TestSetStaminaSideEffects:
    """SetStamina: clamping, side effect recording with delta tracking."""

    def test_set_stamina_records_side_effect(self):
        m = Mobile()
        m.stamina = 100
        m.max_stamina = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetStamina", [m, 60])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "stamina_changed"
        assert ctx.side_effects[0].value == -40  # delta: 60 - 100

    def test_set_stamina_increase(self):
        m = Mobile()
        m.stamina = 50
        m.max_stamina = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetStamina", [m, 80])
        assert ctx.side_effects[0].value == 30

    def test_set_stamina_clamps_to_max(self):
        """SetStamina above max_stamina clamps to max_stamina."""
        m = Mobile()
        m.stamina = 50
        m.max_stamina = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetStamina", [m, 200])
        assert m.stamina == 100

    def test_set_stamina_clamps_to_zero(self):
        """SetStamina below 0 clamps to 0."""
        m = Mobile()
        m.stamina = 50
        m.max_stamina = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetStamina", [m, -10])
        assert m.stamina == 0

    def test_set_stamina_uninit_value(self):
        """SetStamina(m, UNINIT) → no crash, stamina unchanged."""
        m = Mobile()
        m.stamina = 50
        m.max_stamina = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetStamina", [m, UNINIT])
        assert m.stamina == 50


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


# ===================================================================
# GetVital / SetVital
# ===================================================================


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

    def test_get_vital_uninit_mobile(self):
        """GetVital(UNINIT, "life") → 0 (no crash)."""
        assert call_builtin("vitals", "GetVital", [UNINIT, "life"]) == 0

    def test_get_vital_uninit_vital_id(self):
        """GetVital(m, UNINIT) → 0 (str(UNINIT) not in vital map)."""
        m = Mobile()
        assert call_builtin("vitals", "GetVital", [m, UNINIT]) == 0


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

    def test_max_uninit_mobile(self):
        """GetVitalMaximumValue(UNINIT, "life") → 0."""
        assert call_builtin("vitals", "GetVitalMaximumValue", [UNINIT, "life"]) == 0


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

    def test_set_vital_uninit_value(self):
        """SetVital(m, "life", UNINIT) → no crash, returns 0."""
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("vitals", "SetVital", [m, "life", UNINIT])
        assert result == 0
        assert m.hp == 50  # unchanged

    def test_set_vital_string_value(self):
        """SetVital(m, "life", "5000") → hp=50."""
        m = Mobile()
        m.hp = 10
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "SetVital", [m, "life", "5000"])
        assert m.hp == 50


# ===================================================================
# HealDamage
# ===================================================================


class TestHealDamage:
    """HealDamage: HP restoration, capping, side effects, return value."""

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

    def test_heal_damage_returns_1(self):
        """POL returns BLong(1) on success."""
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("vitals", "HealDamage", [m, 10])
        assert result == 1

    def test_heal_damage_uninit_amount(self):
        """HealDamage(m, UNINIT) → no crash, hp unchanged."""
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("vitals", "HealDamage", [m, UNINIT])
        assert m.hp == 50
        assert result is None

    def test_heal_damage_string_amount(self):
        """HealDamage(m, "20") → heals 20."""
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "HealDamage", [m, "20"])
        assert m.hp == 70

    def test_heal_damage_float_amount(self):
        """HealDamage(m, 15.7) → heals 15 (int truncation)."""
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "HealDamage", [m, 15.7])
        assert m.hp == 65


# ===================================================================
# Skill accessors
# ===================================================================


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


class TestSkillAccessorsExtended:
    """Extended skill accessor tests: edge cases, UNINIT, GetAttributeBaseValue."""

    def test_get_effective_skill_missing(self):
        """Skill not set → 0."""
        m = Mobile()
        result = call_builtin("", "GetEffectiveSkill", [m, SKILLID_SWORDSMANSHIP])
        assert result == 0

    def test_get_effective_skill_uninit_mobile(self):
        """GetEffectiveSkill(UNINIT, 1) → 0."""
        result = call_builtin("", "GetEffectiveSkill", [UNINIT, SKILLID_SWORDSMANSHIP])
        assert result == 0

    def test_get_effective_skill_uninit_skill_id(self):
        """GetEffectiveSkill(m, UNINIT) → no crash, returns 0."""
        m = Mobile()
        result = call_builtin("", "GetEffectiveSkill", [m, UNINIT])
        assert result == 0

    def test_get_effective_skill_string_id(self):
        """GetEffectiveSkill(m, "41") → works (int coercion)."""
        m = Mobile()
        m.set_skill(SKILLID_SWORDSMANSHIP, 1000)
        result = call_builtin("", "GetEffectiveSkill", [m, str(SKILLID_SWORDSMANSHIP)])
        assert result == 100

    def test_get_attribute_base_value_returns_tenths(self):
        """POL GetAttributeBaseValue returns raw tenths, not display value."""
        m = Mobile()
        m.set_skill(SKILLID_SWORDSMANSHIP, 1000)
        result = call_builtin("", "GetAttributeBaseValue", [m, "Swordsmanship"])
        assert result == 1000  # tenths, not 100 display

    def test_get_attribute_base_value_stat(self):
        """str_base=100 → GetAttributeBaseValue("strength") returns 1000 tenths."""
        m = Mobile()
        m.str_base = 100
        result = call_builtin("", "GetAttributeBaseValue", [m, "strength"])
        assert result == 1000

    def test_get_attribute_uninit_mobile(self):
        """GetAttribute(UNINIT, "strength") → 0."""
        result = call_builtin("", "GetAttribute", [UNINIT, "strength"])
        assert result == 0

    def test_get_attribute_uninit_name(self):
        """GetAttribute(m, UNINIT) → 0."""
        m = Mobile()
        result = call_builtin("", "GetAttribute", [m, UNINIT])
        assert result == 0

    def test_get_attribute_uninit_precision(self):
        """GetAttribute(m, "strength", UNINIT) → no crash, uses default precision."""
        m = Mobile()
        m.str_base = 100
        result = call_builtin("", "GetAttribute", [m, "strength", UNINIT])
        # UNINIT → int() fails → defaults to precision 0
        assert result == 100

    def test_get_base_skill_delegates(self):
        """GetBaseSkill returns same as GetEffectiveSkill."""
        m = Mobile()
        m.set_skill(SKILLID_SWORDSMANSHIP, 1000)
        result = call_builtin("", "GetBaseSkill", [m, SKILLID_SWORDSMANSHIP])
        assert result == 100

    def test_set_base_skill_sets_value(self):
        """SetBaseSkill(m, skill_id, 1000) → GetEffectiveSkill returns 100."""
        m = Mobile()
        call_builtin("", "SetBaseSkill", [m, SKILLID_SWORDSMANSHIP, 1000])
        assert call_builtin("", "GetEffectiveSkill", [m, SKILLID_SWORDSMANSHIP]) == 100

    def test_set_base_skill_uninit_value(self):
        """SetBaseSkill(m, 1, UNINIT) → no crash."""
        m = Mobile()
        call_builtin("", "SetBaseSkill", [m, SKILLID_SWORDSMANSHIP, UNINIT])
        assert m.get_skill(SKILLID_SWORDSMANSHIP) == 0  # unchanged

    def test_set_base_skill_uninit_skill_id(self):
        """SetBaseSkill(m, UNINIT, 100) → no crash."""
        m = Mobile()
        call_builtin("", "SetBaseSkill", [m, UNINIT, 100])

    def test_get_attribute_id_by_skill_id_invalid(self):
        """Unknown skill ID → empty string."""
        result = call_builtin("", "GetAttributeIdBySkillId", [99999])
        assert result == ""

    def test_get_attribute_id_by_skill_id_uninit(self):
        """UNINIT → no crash, returns empty string."""
        result = call_builtin("", "GetAttributeIdBySkillId", [UNINIT])
        assert result == ""


# ===================================================================
# Equipment accessors
# ===================================================================


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


class TestEquipmentAccessorsExtended:
    """Extended equipment accessor tests: UNINIT, edge cases."""

    def test_get_equipment_uninit_mobile(self):
        """GetEquipmentByLayer(UNINIT, 1) → None."""
        result = call_builtin("uo", "GetEquipmentByLayer", [UNINIT, LAYER_HAND1])
        assert result is None

    def test_get_equipment_uninit_layer(self):
        """GetEquipmentByLayer(m, UNINIT) → no crash, returns None."""
        m = Mobile()
        result = call_builtin("uo", "GetEquipmentByLayer", [m, UNINIT])
        assert result is None

    def test_get_equipment_string_layer(self):
        """GetEquipmentByLayer(m, "1") → works (int coercion)."""
        m = Mobile()
        w = Weapon(name="Sword")
        m.equip(LAYER_HAND1, w)
        result = call_builtin("uo", "GetEquipmentByLayer", [m, str(LAYER_HAND1)])
        assert result is w

    def test_list_equipped_uninit_mobile(self):
        """ListEquippedItems(UNINIT) → []."""
        result = call_builtin("uo", "ListEquippedItems", [UNINIT])
        assert result == []

    def test_list_equipped_empty(self):
        """No items equipped → []."""
        m = Mobile()
        result = call_builtin("uo", "ListEquippedItems", [m])
        assert result == []

    def test_get_karma_uninit_mobile(self):
        """GetKarma(UNINIT) → 0."""
        result = call_builtin("uo", "GetKarma", [UNINIT])
        assert result == 0

    def test_get_karma_returns_zero(self):
        """GetKarma(m) → 0 (default in simulation)."""
        m = Mobile()
        result = call_builtin("uo", "GetKarma", [m])
        assert result == 0


# ===================================================================
# Vital Unit Consistency
#
# Mobile stores vitals in display units (e.g. mob.mana = 100 means
# 100 mana points).  POL's internal API uses hundredths (100 * 100 =
# 10000).  These tests verify the conversion chain is correct so that
# a //100 or *100 mistake in any stub is caught immediately.
# ===================================================================


class TestVitalUnitConsistency:
    """Round-trip tests verifying display ↔ hundredths conversions."""

    def test_getmana_returns_display_units(self):
        """GetMana(mob) must return the same value as mob.mana (display)."""
        m = Mobile()
        m.mana = 75
        assert call_builtin("uo", "GetMana", [m]) == 75

    def test_getvital_mana_returns_hundredths(self):
        """GetVital(mob, 'mana') must return mob.mana * 100."""
        m = Mobile()
        m.mana = 75
        assert call_builtin("vitals", "GetVital", [m, "mana"]) == 7500

    def test_getmana_getvital_roundtrip(self):
        """GetMana(mob) == GetVital(mob, 'mana') / 100."""
        m = Mobile()
        m.mana = 42
        mana_display = call_builtin("uo", "GetMana", [m])
        mana_hundredths = call_builtin("vitals", "GetVital", [m, "mana"])
        assert mana_display == mana_hundredths // 100

    def test_setmana_uses_display_units(self):
        """SetMana(mob, 60) should set mob.mana to 60 (display)."""
        m = Mobile()
        m.mana = 100
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "SetMana", [m, 60])
        assert m.mana == 60

    def test_setvital_mana_uses_hundredths(self):
        """SetVital(mob, 'mana', 6000) should set mob.mana to 60 (display)."""
        m = Mobile()
        m.mana = 100
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("vitals", "SetVital", [m, "mana", 6000])
        assert m.mana == 60

    def test_setmana_setvital_consistency(self):
        """SetMana(mob, X) and SetVital(mob, 'mana', X*100) produce same result."""
        m1 = Mobile()
        m1.mana = 100
        m1.max_mana = 100
        ctx1 = SimulationContext()
        set_context(ctx1)
        call_builtin("uo", "SetMana", [m1, 60])

        m2 = Mobile()
        m2.mana = 100
        m2.max_mana = 100
        ctx2 = SimulationContext()
        set_context(ctx2)
        call_builtin("vitals", "SetVital", [m2, "mana", 6000])

        assert m1.mana == m2.mana == 60

    def test_gethp_returns_display_units(self):
        """GetHP(mob) must return mob.hp (display)."""
        m = Mobile()
        m.hp = 150
        assert call_builtin("uo", "GetHP", [m]) == 150

    def test_getvital_life_returns_hundredths(self):
        """GetVital(mob, 'life') must return mob.hp * 100."""
        m = Mobile()
        m.hp = 150
        assert call_builtin("vitals", "GetVital", [m, "life"]) == 15000

    def test_sethp_setvital_life_consistency(self):
        """SetHP(mob, X) and SetVital(mob, 'life', X*100) produce same result."""
        m1 = Mobile()
        m1.hp = 100
        m1.max_hp = 200
        ctx1 = SimulationContext()
        set_context(ctx1)
        call_builtin("uo", "SetHP", [m1, 80])

        m2 = Mobile()
        m2.hp = 100
        m2.max_hp = 200
        ctx2 = SimulationContext()
        set_context(ctx2)
        call_builtin("vitals", "SetVital", [m2, "life", 8000])

        assert m1.hp == m2.hp == 80

    def test_getstamina_returns_display_units(self):
        """GetStamina(mob) must return mob.stamina (display)."""
        m = Mobile()
        m.stamina = 90
        assert call_builtin("uo", "GetStamina", [m]) == 90

    def test_getvital_stamina_returns_hundredths(self):
        """GetVital(mob, 'stamina') must return mob.stamina * 100."""
        m = Mobile()
        m.stamina = 90
        assert call_builtin("vitals", "GetVital", [m, "stamina"]) == 9000

    def test_setstamina_setvital_consistency(self):
        """SetStamina(mob, X) and SetVital(mob, 'stamina', X*100) produce same result."""
        m1 = Mobile()
        m1.stamina = 100
        m1.max_stamina = 100
        ctx1 = SimulationContext()
        set_context(ctx1)
        call_builtin("uo", "SetStamina", [m1, 70])

        m2 = Mobile()
        m2.stamina = 100
        m2.max_stamina = 100
        ctx2 = SimulationContext()
        set_context(ctx2)
        call_builtin("vitals", "SetVital", [m2, "stamina", 7000])

        assert m1.stamina == m2.stamina == 70

    def test_escript_getmana_pattern(self):
        """Verify the shard's eScript GetMana() pattern: GetVital(mob,'mana')/100.

        This is what the shard scripts call.  If our GetVital returns
        hundredths correctly, dividing by 100 must yield display units.
        """
        m = Mobile()
        m.mana = 83
        hundredths = call_builtin("vitals", "GetVital", [m, "mana"])
        display = hundredths // 100  # eScript integer division
        assert display == 83

    def test_escript_setmana_pattern(self):
        """Verify the shard's eScript SetMana() pattern: SetVital(mob,'mana', val*100).

        TryToCast does SetMana(caster, GetMana(caster)+manacost) for
        the mana refund.  GetMana returns display, manacost is display,
        SetMana sets display.  Verify no unit confusion.
        """
        m = Mobile()
        m.mana = 50
        m.max_mana = 100
        ctx = SimulationContext()
        set_context(ctx)
        # Simulate shard's refund: SetMana(caster, GetMana(caster) + manacost)
        current = call_builtin("uo", "GetMana", [m])
        manacost = 11  # circle 5 mana cost
        call_builtin("uo", "SetMana", [m, current + manacost])
        assert m.mana == 61  # 50 + 11

    def test_small_mana_values_no_truncation(self):
        """Mana values < 100 must NOT be divided by 100.

        Regression: old ConsumeMana had a heuristic that divided values
        >= 100 by 100.  With mob.mana=5 (a valid low mana), the stub
        must treat it as 5 display mana, not 0.
        """
        m = Mobile()
        m.mana = 5
        assert call_builtin("uo", "GetMana", [m]) == 5

    def test_large_mana_values_no_double_conversion(self):
        """Mana value of 200 must NOT be treated as hundredths.

        Regression: old ConsumeMana had `//100 if >= 100`.  mob.mana=200
        (e.g., a high-INT mage) must be treated as 200 display mana, not 2.
        """
        m = Mobile()
        m.mana = 200
        assert call_builtin("uo", "GetMana", [m]) == 200
        assert call_builtin("vitals", "GetVital", [m, "mana"]) == 20000
