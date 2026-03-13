"""Batch 2 — Object model POL built-in stubs.

Property bag access, stat/vital/skill accessors, equipment layer lookup.
These delegate directly to the game object model from M4.
"""

from __future__ import annotations

from typing import Any

from omega.logging import get_logger
from omega.model.constants import ATTRIBUTE_TO_SKILLID, SKILLID_TO_ATTRIBUTE
from omega.runtime.registry import pol_function

logger = get_logger("omega.runtime")

# ---------------------------------------------------------------------------
# Property system (uo module)
# ---------------------------------------------------------------------------


@pol_function("uo", "GetObjProperty")
@pol_function("", "GetObjProperty")
def get_obj_property(obj: Any = None, name: Any = None) -> Any:
    """Get a custom property from a game object."""
    if obj is None or name is None:
        return None
    if hasattr(obj, "get_property"):
        return obj.get_property(str(name))
    return None


@pol_function("uo", "SetObjProperty")
@pol_function("", "SetObjProperty")
def set_obj_property(obj: Any = None, name: Any = None, value: Any = None) -> None:
    """Set a custom property on a game object."""
    if obj is None or name is None:
        return
    if hasattr(obj, "set_property"):
        obj.set_property(str(name), value)


@pol_function("uo", "EraseObjProperty")
@pol_function("", "EraseObjProperty")
def erase_obj_property(obj: Any = None, name: Any = None) -> Any:
    """Erase a custom property from a game object.

    POL returns BLong(1) on success.
    """
    if obj is None or name is None:
        return 1
    if hasattr(obj, "erase_property"):
        obj.erase_property(str(name))
    return 1


# ---------------------------------------------------------------------------
# Stats (vitals module)
# ---------------------------------------------------------------------------


@pol_function("vitals", "GetStrength")
@pol_function("", "GetStrength")
def get_strength(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "strength", 0)


@pol_function("vitals", "GetDexterity")
@pol_function("", "GetDexterity")
def get_dexterity(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "dexterity", 0)


@pol_function("vitals", "GetIntelligence")
@pol_function("", "GetIntelligence")
def get_intelligence(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "intelligence", 0)


@pol_function("vitals", "GetStrengthMod")
@pol_function("", "GetStrengthMod")
def get_strength_mod(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "str_mod", 0)


@pol_function("vitals", "GetDexterityMod")
@pol_function("", "GetDexterityMod")
def get_dexterity_mod(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "dex_mod", 0)


@pol_function("vitals", "GetIntelligenceMod")
@pol_function("", "GetIntelligenceMod")
def get_intelligence_mod(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "int_mod", 0)


@pol_function("vitals", "SetStrengthMod")
@pol_function("", "SetStrengthMod")
def set_strength_mod(mobile: Any = None, value: Any = 0) -> None:
    if mobile is not None:
        try:
            mobile.str_mod = int(value)
        except (TypeError, ValueError):
            return


@pol_function("vitals", "SetDexterityMod")
@pol_function("", "SetDexterityMod")
def set_dexterity_mod(mobile: Any = None, value: Any = 0) -> None:
    if mobile is not None:
        try:
            mobile.dex_mod = int(value)
        except (TypeError, ValueError):
            return


@pol_function("vitals", "SetIntelligenceMod")
@pol_function("", "SetIntelligenceMod")
def set_intelligence_mod(mobile: Any = None, value: Any = 0) -> None:
    if mobile is not None:
        try:
            mobile.int_mod = int(value)
        except (TypeError, ValueError):
            return


# ---------------------------------------------------------------------------
# Vitals (uo module — HP, Mana, Stamina)
# ---------------------------------------------------------------------------


@pol_function("uo", "GetHP")
@pol_function("", "GetHP")
def get_hp(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "hp", 0)


@pol_function("uo", "GetMaxHP")
@pol_function("", "GetMaxHP")
def get_max_hp(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "max_hp", 0)


@pol_function("uo", "GetMana")
@pol_function("", "GetMana")
def get_mana(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "mana", 0)


@pol_function("uo", "GetStamina")
@pol_function("", "GetStamina")
def get_stamina(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "stamina", 0)


@pol_function("uo", "SetHP")
@pol_function("vitals", "SetHP")
@pol_function("", "SetHP")
def set_hp(mobile: Any = None, value: Any = 0) -> None:
    """Set HP on a mobile, clamped to [0, max_hp]. Records side effect."""
    if mobile is None:
        return
    try:
        new_val = int(value)
    except (TypeError, ValueError):
        return
    max_hp = getattr(mobile, "max_hp", new_val)
    new_val = max(0, min(new_val, max_hp))
    old_hp = mobile.hp
    mobile.hp = new_val
    delta = new_val - old_hp

    from omega.runtime.context import get_context

    ctx = get_context()
    ctx.record_side_effect(
        kind="hp_set",
        target_serial=getattr(mobile, "serial", 0),
        value=delta,
    )
    logger.debug("SetHP", target=getattr(mobile, "name", "?"), old=old_hp, new=new_val, delta=delta)


@pol_function("uo", "SetMana")
@pol_function("", "SetMana")
def set_mana(mobile: Any = None, value: Any = 0) -> None:
    """Set mana on a mobile, clamped to [0, max_mana]. Records side effect with delta."""
    if mobile is None:
        return
    try:
        new_val = int(value)
    except (TypeError, ValueError):
        return
    max_mana = getattr(mobile, "max_mana", new_val)
    new_val = max(0, min(new_val, max_mana))
    old_mana = mobile.mana
    mobile.mana = new_val
    delta = new_val - old_mana

    from omega.runtime.context import get_context

    ctx = get_context()
    ctx.record_side_effect(
        kind="mana_changed",
        target_serial=getattr(mobile, "serial", 0),
        value=delta,
    )
    logger.debug("SetMana", target=getattr(mobile, "name", "?"), old=old_mana, new=new_val, delta=delta)


@pol_function("uo", "SetStamina")
@pol_function("", "SetStamina")
def set_stamina(mobile: Any = None, value: Any = 0) -> None:
    """Set stamina on a mobile, clamped to [0, max_stamina]. Records side effect with delta."""
    if mobile is None:
        return
    try:
        new_val = int(value)
    except (TypeError, ValueError):
        return
    max_stamina = getattr(mobile, "max_stamina", new_val)
    new_val = max(0, min(new_val, max_stamina))
    old_stamina = mobile.stamina
    mobile.stamina = new_val
    delta = new_val - old_stamina

    from omega.runtime.context import get_context

    ctx = get_context()
    ctx.record_side_effect(
        kind="stamina_changed",
        target_serial=getattr(mobile, "serial", 0),
        value=delta,
    )
    logger.debug("SetStamina", target=getattr(mobile, "name", "?"), old=old_stamina, new=new_val, delta=delta)


@pol_function("uo", "GetMaxMana")
@pol_function("", "GetMaxMana")
def get_max_mana(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "max_mana", 0)


@pol_function("uo", "GetMaxStamina")
@pol_function("", "GetMaxStamina")
def get_max_stamina(mobile: Any = None) -> int:
    if mobile is None:
        return 0
    return getattr(mobile, "max_stamina", 0)


# ---------------------------------------------------------------------------
# Vitals (vitals module — GetVital / GetVitalMaximumValue)
#
# POL stores vitals in hundredths internally:
#   GetVital(mob, "life") returns mob.hp * 100
#   GetVitalMaximumValue(mob, "life") returns mob.max_hp * 100
# The shard's eScript wrappers (GetHP, GetMana, etc.) divide by 100.
# ---------------------------------------------------------------------------

_VITAL_MAP = {
    "life": ("hp", "max_hp"),
    "mana": ("mana", "max_mana"),
    "stamina": ("stamina", "max_stamina"),
}


@pol_function("vitals", "GetVital")
@pol_function("", "GetVital")
def get_vital(mobile: Any = None, vital_id: Any = None) -> int:
    """Get current vital value in hundredths (POL internal format)."""
    if mobile is None or vital_id is None:
        return 0
    attrs = _VITAL_MAP.get(str(vital_id))
    if attrs is None:
        return 0
    return getattr(mobile, attrs[0], 0) * 100


@pol_function("vitals", "GetVitalMaximumValue")
@pol_function("", "GetVitalMaximumValue")
def get_vital_maximum_value(mobile: Any = None, vital_id: Any = None) -> int:
    """Get maximum vital value in hundredths (POL internal format)."""
    if mobile is None or vital_id is None:
        return 0
    attrs = _VITAL_MAP.get(str(vital_id))
    if attrs is None:
        return 0
    return getattr(mobile, attrs[1], 0) * 100


@pol_function("vitals", "SetVital")
@pol_function("", "SetVital")
def set_vital(mobile: Any = None, vital_id: Any = None, value: Any = 0) -> int:
    """Set vital value in hundredths (POL internal format).

    Records side effect with the delta for tracking drain/heal amounts.
    Returns 1 on success.
    """
    if mobile is None or vital_id is None:
        return 0
    attrs = _VITAL_MAP.get(str(vital_id))
    if attrs is None:
        return 0
    current_attr = attrs[0]  # e.g. "hp", "mana", "stamina"
    max_attr = attrs[1]      # e.g. "max_hp", "max_mana", "max_stamina"
    old_val = getattr(mobile, current_attr, 0)
    # POL stores in hundredths; convert back to display units
    try:
        new_val = max(0, int(value) // 100)
    except (TypeError, ValueError):
        return 0
    max_val = getattr(mobile, max_attr, new_val)
    new_val = min(new_val, max_val)
    setattr(mobile, current_attr, new_val)
    delta = new_val - old_val

    from omega.runtime.context import get_context

    kind_map = {"hp": "hp_set", "mana": "mana_changed", "stamina": "stamina_changed"}
    ctx = get_context()
    ctx.record_side_effect(
        kind=kind_map.get(current_attr, f"{current_attr}_changed"),
        target_serial=getattr(mobile, "serial", 0),
        value=delta,
    )
    logger.debug(
        "SetVital", vital=str(vital_id),
        target=getattr(mobile, "name", "?"),
        old=old_val, new=new_val, delta=delta,
    )
    return 1


@pol_function("vitals", "HealDamage")
@pol_function("uo", "HealDamage")
@pol_function("", "HealDamage")
def heal_damage(mobile: Any = None, amount: Any = 0) -> Any:
    """Heal a mobile by restoring HP, capped at max_hp.

    Records as a side effect for tracking over-protection healing.
    POL returns BLong(1) on success.
    """
    if mobile is None:
        return None
    try:
        amt = int(amount) if amount is not None else 0
    except (TypeError, ValueError):
        return None
    if amt <= 0:
        return None
    old_hp = mobile.hp
    mobile.hp = min(getattr(mobile, "max_hp", mobile.hp + amt), mobile.hp + amt)

    from omega.runtime.context import get_context

    ctx = get_context()
    ctx.record_side_effect(
        kind="heal",
        target_serial=getattr(mobile, "serial", 0),
        value=amt,
    )
    logger.debug("HealDamage", target=getattr(mobile, "name", "?"), amount=amt, hp=mobile.hp)
    return 1


@pol_function("vitals", "RecalcVitals")
@pol_function("", "RecalcVitals")
def recalc_vitals(character: Any = None, calc_attribute: Any = 0, calc_vital: Any = 0) -> int:
    """No-op — stat recalculation not modeled in simulation."""
    logger.debug("RecalcVitals (no-op in simulation)")
    return 1


@pol_function("vitals", "SetHpRegenRate")
@pol_function("", "SetHpRegenRate")
def set_hp_regen_rate(mobile: Any = None, rate: Any = None) -> None:
    logger.debug("SetHpRegenRate (no-op in simulation)", rate=rate)


# ---------------------------------------------------------------------------
# Skills (attributes module)
# ---------------------------------------------------------------------------


@pol_function("", "GetEffectiveSkill")
@pol_function("attributes", "GetEffectiveSkill")
def get_effective_skill(mobile: Any = None, skill_id: Any = None) -> int:
    """Get effective skill value (display units, 0-200)."""
    if mobile is None or skill_id is None:
        return 0
    try:
        sid = int(skill_id)
    except (TypeError, ValueError):
        return 0
    if hasattr(mobile, "get_effective_skill"):
        return mobile.get_effective_skill(sid)
    return 0


@pol_function("", "GetAttribute")
@pol_function("attributes", "GetAttribute")
def get_attribute(
    mobile: Any = None, attr_name: Any = None, precision: Any = 0
) -> int:
    """Get attribute value by string name.

    Parameters
    ----------
    precision:
        0 = ATTRIBUTE_PRECISION_NORMAL (display value, 0-200 for skills)
        1 = ATTRIBUTE_PRECISION_TENTHS (internal tenths, 0-2000 for skills)
    """
    if mobile is None or attr_name is None:
        return 0
    if hasattr(mobile, "get_attribute"):
        tenths = mobile.get_attribute(str(attr_name))
        try:
            prec = int(precision)
        except (TypeError, ValueError):
            prec = 0
        if prec == 0:
            # ATTRIBUTE_PRECISION_NORMAL: return display value
            return tenths // 10
        # ATTRIBUTE_PRECISION_TENTHS: return raw tenths
        return tenths
    return 0


@pol_function("", "GetAttributeBaseValue")
@pol_function("attributes", "GetAttributeBaseValue")
def get_attribute_base_value(mobile: Any = None, attr_name: Any = None) -> int:
    """Get base attribute value in tenths (POL returns av.base(), raw tenths)."""
    return get_attribute(mobile, attr_name, 1)


@pol_function("", "GetBaseSkill")
@pol_function("attributes", "GetBaseSkill")
def get_base_skill(mobile: Any = None, skill_id: Any = None) -> int:
    """Get base skill (same as effective in V1)."""
    return get_effective_skill(mobile, skill_id)


@pol_function("", "SetBaseSkill")
@pol_function("attributes", "SetBaseSkill")
def set_base_skill(
    mobile: Any = None, skill_id: Any = None, value: Any = None
) -> None:
    """Set base skill value."""
    if mobile is not None and skill_id is not None and value is not None:
        if hasattr(mobile, "set_skill"):
            try:
                mobile.set_skill(int(skill_id), int(value))
            except (TypeError, ValueError):
                return


@pol_function("", "GetAttributeIdBySkillId")
@pol_function("attributes", "GetAttributeIdBySkillId")
def get_attribute_id_by_skill_id(skill_id: Any = None) -> str:
    """Convert a numeric skill ID to an attribute name string."""
    if skill_id is None:
        return ""
    try:
        return SKILLID_TO_ATTRIBUTE.get(int(skill_id), "")
    except (TypeError, ValueError):
        return ""


# ---------------------------------------------------------------------------
# Equipment (uo module)
# ---------------------------------------------------------------------------


@pol_function("uo", "GetEquipmentByLayer")
@pol_function("", "GetEquipmentByLayer")
def get_equipment_by_layer(mobile: Any = None, layer: Any = None) -> Any:
    """Get item equipped at a specific layer.

    Returns the item or None (POL returns error, but None is safer for stubs).
    """
    if mobile is None or layer is None:
        return None
    try:
        layer_int = int(layer)
    except (TypeError, ValueError):
        return None
    if hasattr(mobile, "get_equipped"):
        return mobile.get_equipped(layer_int)
    return None


@pol_function("uo", "ListEquippedItems")
@pol_function("", "ListEquippedItems")
def list_equipped_items(mobile: Any = None) -> Any:
    """Get array of all equipped items. Returns EArray for POL conformance."""
    from omega.interpreter.types import EArray

    if mobile is None:
        return EArray()
    if hasattr(mobile, "list_equipment"):
        return EArray(list(mobile.list_equipment().values()))
    return EArray()


@pol_function("uo", "GetKarma")
@pol_function("", "GetKarma")
def get_karma(mobile: Any = None) -> int:
    """Get karma value. Returns 0 in simulation."""
    if mobile is None:
        return 0
    return getattr(mobile, "karma", 0)
