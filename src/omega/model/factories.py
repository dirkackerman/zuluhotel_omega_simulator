"""Factory functions for creating game objects from config or inline specs.

Two creation paths:
1. **From config** — NPC template chain: npcdesc.cfg → equip.cfg → itemdesc.cfg
2. **Inline** — Direct specification of stats/skills/equipment for testing

Both paths produce the same ``Mobile``, ``Weapon``, and ``Armor`` objects.
"""

from __future__ import annotations

from typing import Any

from omega.config.cfg_parser import ConfigElement, ConfigFile
from omega.config.dice import DiceSpec, parse_dice
from omega.logging import get_logger
from omega.model.constants import (
    ATTRIBUTE_TO_SKILLID,
    LAYER_HAND1,
    SKILLID__HIGHEST,
    SKILLID_TO_ATTRIBUTE,
)
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile

logger = get_logger("omega.model")

# Skill names as they appear in npcdesc.cfg → SKILLID mapping.
# npcdesc.cfg uses mixed forms: "Swordsmanship", "MaceFighting", "Parry", etc.
_NPCDESC_SKILL_NAMES: dict[str, int] = {}

# Build from SKILLID_TO_ATTRIBUTE (canonical mapping)
for _sid, _aname in SKILLID_TO_ATTRIBUTE.items():
    _NPCDESC_SKILL_NAMES[_aname.lower()] = _sid

# Also add common cfg variants that differ from attribute names
_NPCDESC_SKILL_NAMES.update(
    {
        "evaluatingintelligence": 16,
        "detectinghidden": 14,
        "forensicevaluation": 19,
        "animaltaming": 35,
        "tasteidentification": 36,
        "animallore": 2,
        "magicresistance": 26,
        "macefighting": 41,
        "spiritspeak": 32,
        "battle_defense": 5,
    }
)

# Stat keys in npcdesc.cfg
_STAT_KEYS = {"STR", "INT", "DEX", "HITS", "MANA", "STAM"}

# Weapon attribute name → skill ID (as used in itemdesc.cfg Attribute field)
_WEAPON_ATTRIBUTE_NAMES: dict[str, int] = {
    "swordsmanship": 40,
    "swords": 40,
    "macefighting": 41,
    "mace": 41,
    "fencing": 42,
    "archery": 31,
    "wrestling": 43,
}


def find_weapon_by_name(name: str, itemdesc: ConfigFile) -> Weapon:
    """Look up a weapon by its ``Name`` property in itemdesc.cfg and create it.

    Parameters
    ----------
    name:
        The ``Name`` property value (e.g., ``"TheHeartwood"``).
    itemdesc:
        Parsed itemdesc.cfg.

    Raises
    ------
    KeyError
        If no weapon with the given name is found.
    """
    elem = itemdesc.find_by_name(name)
    if elem is None or elem.block_type != "Weapon":
        raise KeyError(f"Weapon {name!r} not found in itemdesc")
    return create_weapon_from_config(elem)


def find_armor_by_name(name: str, itemdesc: ConfigFile) -> Armor:
    """Look up an armor piece by its ``Name`` property in itemdesc.cfg and create it.

    Parameters
    ----------
    name:
        The ``Name`` property value (e.g., ``"ChainmailCoif"``).
    itemdesc:
        Parsed itemdesc.cfg.

    Raises
    ------
    KeyError
        If no armor with the given name is found.
    """
    elem = itemdesc.find_by_name(name)
    if elem is None or elem.block_type != "Armor":
        raise KeyError(f"Armor {name!r} not found in itemdesc")
    return create_armor_from_config(elem)


def create_weapon_from_config(elem: ConfigElement) -> Weapon:
    """Create a Weapon from an itemdesc.cfg element.

    Parameters
    ----------
    elem:
        A ConfigElement with block_type "Weapon".
    """
    damage_str = elem.get("Damage", "1d4")
    damage = parse_dice(damage_str)

    speed = elem.get_int("Speed", 50)
    attr_name = elem.get("Attribute", "Wrestling")
    # Pass the attribute name string directly — matches POL's weapon.attribute
    # member which returns the attribute name. Weapon.__init__ stores as-is
    # for string inputs.
    attribute: int | str = attr_name

    two_handed = elem.get("TwoHanded", "0") == "1"
    max_hp = elem.get_int("MaxHP", 50)
    hitscript = elem.get("Hitscript")

    # Parse objtype from element name
    objtype = _parse_objtype(elem.name)
    graphic_str = elem.get("Graphic")
    graphic = int(graphic_str, 0) if graphic_str else None

    name = elem.get("Name", elem.name)

    return Weapon(
        objtype=objtype,
        graphic=graphic,
        name=name,
        damage=damage,
        speed=speed,
        attribute=attribute,
        two_handed=two_handed,
        hitscript=hitscript,
        hp=max_hp,
        max_hp=max_hp,
    )


def create_armor_from_config(elem: ConfigElement) -> Armor:
    """Create an Armor from an itemdesc.cfg element.

    Parameters
    ----------
    elem:
        A ConfigElement with block_type "Armor".
    """
    ar = elem.get_int("AR", 0)
    coverage = elem.get_all("Coverage")
    max_hp = elem.get_int("MaxHP", 70)

    objtype = _parse_objtype(elem.name)
    graphic_str = elem.get("Graphic")
    graphic = int(graphic_str, 0) if graphic_str else None

    name = elem.get("Name", elem.name)

    armor = Armor(
        objtype=objtype,
        graphic=graphic,
        name=name,
        ar=ar,
        coverage=coverage,
        hp=max_hp,
        max_hp=max_hp,
    )

    # Copy CProps to property bag (DefaultDex, MagicPenalty, etc.)
    for cprop_name, cprop_raw in elem.cprops.items():
        armor.set_property(cprop_name, elem.get_cprop(cprop_name))

    return armor


def create_mobile_from_template(
    template_name: str,
    npcdesc: ConfigFile,
    equip_cfg: ConfigFile,
    itemdesc: ConfigFile,
) -> Mobile:
    """Create a Mobile from an NPC template, resolving equipment chain.

    Parameters
    ----------
    template_name:
        NPC template name (e.g., "nazgul") from npcdesc.cfg.
    npcdesc:
        Parsed npcdesc.cfg.
    equip_cfg:
        Parsed equip.cfg.
    itemdesc:
        Parsed itemdesc.cfg (combat package).
    """
    npc_elem = npcdesc[template_name]
    if npc_elem is None:
        raise ValueError(f"NPC template {template_name!r} not found in npcdesc.cfg")
    if not isinstance(npc_elem, ConfigElement):
        raise ValueError(f"Expected ConfigElement for {template_name!r}, got {type(npc_elem)}")

    # Parse objtype from element
    objtype_str = npc_elem.get("objtype", "0x0190")
    objtype = int(objtype_str, 0) if objtype_str else 0x0190

    mobile = Mobile(
        objtype=objtype,
        name=npc_elem.get("Name", template_name),
        is_npc=True,
        npctemplate=template_name,
    )

    # Stats
    mobile.str_base = npc_elem.get_int("STR", 10)
    mobile.int_base = npc_elem.get_int("INT", 10)
    mobile.dex_base = npc_elem.get_int("DEX", 10)

    hits = npc_elem.get_int("HITS", mobile.str_base)
    mobile.hp = hits
    mobile.max_hp = hits

    mana = npc_elem.get_int("MANA", mobile.int_base)
    mobile.mana = mana
    mobile.max_mana = mana

    stam = npc_elem.get_int("STAM", mobile.dex_base)
    mobile.stamina = stam
    mobile.max_stamina = stam

    # CustomHitsLevel override — shard uses this CProp to set NPC max HP
    # independently of STR (see regen.src GetLifeMaximumValueExported).
    custom_hp = npc_elem.get_cprop("CustomHitsLevel")
    if custom_hp is not None:
        try:
            hp_val = int(custom_hp)
            mobile.hp = hp_val
            mobile.max_hp = hp_val
        except (ValueError, TypeError):
            logger.warning(
                "CustomHitsLevel CProp ignored — cannot parse as integer",
                npc_template=mobile.npctemplate,
                raw_value=repr(custom_hp),
            )

    # Skills — scan all properties, match known skill names
    for key, values in npc_elem.properties.items():
        skill_id = _NPCDESC_SKILL_NAMES.get(key.lower())
        if skill_id is not None and values:
            try:
                # npcdesc uses display values (0-200), store as internal (×10)
                skill_val = int(float(values[0]))
                mobile.set_skill(skill_id, skill_val * 10)
            except (ValueError, TypeError):
                pass

    # CProps → property bag
    for cprop_name in npc_elem.cprops:
        mobile.set_property(cprop_name, npc_elem.get_cprop(cprop_name))

    # Equipment
    equip_name = npc_elem.get("Equip")
    if equip_name:
        equip_from_template(mobile, equip_name, equip_cfg, itemdesc)

    logger.debug(
        "Created mobile from template",
        template=template_name,
        str=mobile.strength,
        int=mobile.intelligence,
        dex=mobile.dexterity,
        hp=mobile.max_hp,
        skills=len(mobile._skills),
        equipment=len(mobile._equipment),
    )

    return mobile


def create_mobile_inline(
    *,
    name: str = "Combatant",
    is_npc: bool = False,
    str_: int = 100,
    int_: int = 25,
    dex_: int = 100,
    hp: int | None = None,
    mana: int | None = None,
    stamina: int | None = None,
    skills: dict[int, int] | None = None,
    class_levels: dict[str, int] | None = None,
    weapon: Weapon | None = None,
    armor_pieces: list[Armor] | None = None,
) -> Mobile:
    """Create a Mobile from inline parameters (no config files needed).

    Parameters
    ----------
    skills:
        Skill ID → display value (0-200). Stored internally × 10.
    class_levels:
        Class ID string → level (e.g., {"IsWarrior": 5}).
    weapon:
        Weapon to equip in HAND1.
    armor_pieces:
        Armor pieces to equip (auto-assigned to layers if set).
    """
    mobile = Mobile(name=name, is_npc=is_npc)
    mobile.str_base = str_
    mobile.int_base = int_
    mobile.dex_base = dex_

    mobile.hp = hp if hp is not None else str_
    mobile.max_hp = mobile.hp
    mobile.mana = mana if mana is not None else int_
    mobile.max_mana = mobile.mana
    mobile.stamina = stamina if stamina is not None else dex_
    mobile.max_stamina = mobile.stamina

    if skills:
        for skill_id, display_value in skills.items():
            mobile.set_skill(skill_id, display_value * 10)

    if class_levels:
        for class_id, level in class_levels.items():
            mobile.set_property(class_id, level)

    if weapon:
        mobile.equip(LAYER_HAND1, weapon)

    if armor_pieces:
        for armor in armor_pieces:
            layer = _guess_armor_layer(armor)
            mobile.equip(layer, armor)

    return mobile


def equip_from_template(
    mobile: Mobile,
    equip_name: str,
    equip_cfg: ConfigFile,
    itemdesc: ConfigFile,
) -> None:
    """Resolve an equipment template and equip all items on a mobile.

    Equipment templates in equip.cfg have entries like:
    - ``Weapon WeaponName`` → look up by Name in itemdesc
    - ``Armor ArmorName`` → look up by Name in itemdesc
    - ``Equip 0xOBJTYPE [color]`` → look up by objtype in itemdesc
    """
    equip_elem = equip_cfg[equip_name]
    if equip_elem is None or not isinstance(equip_elem, ConfigElement):
        logger.warning("Equipment template not found", template=equip_name)
        return

    # Process Weapon entries (may have trailing color: "0x9azz 0x0493")
    for weapon_ref in equip_elem.get_all("Weapon"):
        parts = weapon_ref.split()
        ref_str = parts[0]
        color = int(parts[1], 0) if len(parts) > 1 else 0
        weapon_item = _resolve_item_ref(ref_str, itemdesc)
        if weapon_item and weapon_item.block_type == "Weapon":
            weapon = create_weapon_from_config(weapon_item)
            weapon.color = color
            mobile.equip(LAYER_HAND1, weapon)

    # Process Armor entries (may have trailing color: "0xf701 1556")
    for armor_ref in equip_elem.get_all("Armor"):
        parts = armor_ref.split()
        ref_str = parts[0]
        color = int(parts[1], 0) if len(parts) > 1 else 0
        armor_item = _resolve_item_ref(ref_str, itemdesc)
        if armor_item and armor_item.block_type == "Armor":
            armor = create_armor_from_config(armor_item)
            armor.color = color
            layer = _guess_armor_layer(armor)
            mobile.equip(layer, armor)

    # Process generic Equip entries (objtype [color])
    for equip_ref in equip_elem.get_all("Equip"):
        parts = equip_ref.split()
        objtype_str = parts[0]
        color = int(parts[1]) if len(parts) > 1 else 0

        item_elem = _resolve_item_ref(objtype_str, itemdesc)
        if item_elem is None:
            continue

        if item_elem.block_type == "Weapon":
            weapon = create_weapon_from_config(item_elem)
            weapon.color = color
            mobile.equip(LAYER_HAND1, weapon)
        elif item_elem.block_type == "Armor":
            armor = create_armor_from_config(item_elem)
            armor.color = color
            layer = _guess_armor_layer(armor)
            mobile.equip(layer, armor)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_objtype(name: str) -> int:
    """Parse an objtype from a config element name (may be hex or decimal)."""
    try:
        return int(name, 0)
    except (ValueError, TypeError):
        return 0


def _resolve_item_ref(ref: str, itemdesc: ConfigFile) -> ConfigElement | None:
    """Resolve a weapon/armor reference to a ConfigElement.

    References can be:
    - A hex objtype: "0x13BB" → lookup by int key
    - A template Name: "Armor5" → scan elements for matching Name property
    """
    ref = ref.strip()

    # Try as objtype first
    try:
        objtype = int(ref, 0)
        result = itemdesc[objtype]
        if isinstance(result, ConfigElement):
            return result
    except (ValueError, TypeError):
        pass

    # Try by element name (direct key)
    result = itemdesc[ref]
    if isinstance(result, ConfigElement):
        return result

    # Try scanning for Name property match
    by_name = itemdesc.find_by_name(ref)
    if by_name is not None:
        return by_name

    logger.debug("Item reference not resolved", ref=ref)
    return None


# Coverage zone → layer mapping for auto-equipping armor
_COVERAGE_TO_LAYER: dict[str, int] = {
    "head": 0x06,       # LAYER_HELM
    "neck": 0x0A,       # LAYER_NECK
    "body": 0x0D,       # LAYER_CHEST
    "arms": 0x13,       # LAYER_ARMS
    "hands": 0x07,      # LAYER_GLOVES
    "legs": 0x18,       # LAYER_LEGS
    "legs/feet": 0x18,  # LAYER_LEGS
    "feet": 0x03,       # LAYER_SHOES
}

# Track which layers have been assigned to avoid collisions
_layer_assignment_counter: int = 0


def _guess_armor_layer(armor: Armor) -> int:
    """Guess the equipment layer for an armor piece based on its coverage.

    If the armor has a layer already set, use that. Otherwise, infer from
    the first coverage zone. Falls back to LAYER_CHEST.
    """
    if armor.layer != 0:
        return armor.layer

    if armor.coverage:
        first = armor.coverage[0].lower()
        layer = _COVERAGE_TO_LAYER.get(first)
        if layer is not None:
            return layer

    # Default to chest
    return 0x0D  # LAYER_CHEST
