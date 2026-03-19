"""Batch 3 — Structural POL built-in stubs.

Config file access, damage application, guild lookups, script control,
and object creation/destruction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omega.interpreter.types import EArray
from omega.logging import get_logger
from omega.runtime.context import get_context
from omega.runtime.registry import pol_function

logger = get_logger("omega.runtime")

# ---------------------------------------------------------------------------
# Config file access (cfgfile / uo module)
# ---------------------------------------------------------------------------


@pol_function("", "ReadConfigFile")
@pol_function("cfgfile", "ReadConfigFile")
@pol_function("uo", "ReadConfigFile")
def read_config_file(path: Any = None) -> Any:
    """Read and parse a POL config file, with caching.

    Resolves package paths (e.g., ":combat:settings") and returns
    a RuntimeConfigFile wrapper.  Wildcard paths (":*:name") merge
    configs from all packages.
    """
    if path is None:
        return None

    path_str = str(path)
    ctx = get_context()

    # Check cache first
    cached = ctx.get_cached_config(path_str)
    if cached is not None:
        return cached

    # Lazy import to avoid circular deps
    from omega.config.accessor import RuntimeConfigFile
    from omega.config.cfg_parser import parse_config_file as _parse_cfg

    # Handle wildcard ":*:name" — merge configs from all packages
    if path_str.startswith(":*:") and ctx._config_resolver is not None:
        cfg_name = path_str[3:]
        resolver = ctx._config_resolver
        # Use resolve_config_paths_wildcard if available (ShardData)
        if hasattr(resolver, '__self__') and hasattr(resolver.__self__, 'resolve_config_paths_wildcard'):
            paths = resolver.__self__.resolve_config_paths_wildcard(cfg_name)
        else:
            # Fallback: single file
            fs_path = resolver(path_str)
            paths = [fs_path] if fs_path is not None else []

        if not paths:
            logger.warning("Config path not resolved", path=path_str)
            return None

        # Parse and merge all matching configs
        merged_cfg = _parse_cfg(paths[0])
        for extra_path in paths[1:]:
            extra_cfg = _parse_cfg(extra_path)
            for elem in extra_cfg:
                merged_cfg.add_element(elem)

        result = RuntimeConfigFile(merged_cfg)
        ctx.cache_config(path_str, result)
        return result

    # Try to resolve package paths (":combat:settings") via shard resolver
    resolved = Path(path_str)
    if path_str.startswith(":") and ctx._config_resolver is not None:
        fs_path = ctx._config_resolver(path_str)
        if fs_path is not None:
            resolved = fs_path
        else:
            logger.warning("Config path not resolved", path=path_str)
            return None

    if not resolved.exists():
        logger.warning("Config file not found", path=path_str)
        return None

    try:
        cfg = RuntimeConfigFile.from_path(resolved)
        ctx.cache_config(path_str, cfg)
        return cfg
    except Exception as e:
        logger.warning("Failed to parse config file", path=path_str, error=str(e))
        return None


@pol_function("", "FindConfigElem")
@pol_function("cfgfile", "FindConfigElem")
def find_config_elem(cfg: Any = None, name: Any = None) -> Any:
    """Get a config element by name."""
    if cfg is None or name is None:
        logger.warning("FindConfigElem: cfg or name is None", cfg=repr(cfg), name=repr(name))
        return None
    try:
        return cfg[name]
    except (KeyError, TypeError):
        logger.warning("FindConfigElem: element not found", name=repr(name))
        return None


@pol_function("", "GetConfigInt")
@pol_function("cfgfile", "GetConfigInt")
def get_config_int(elem: Any = None, key: Any = None) -> int:
    """Get an integer value from a config element."""
    if elem is None or key is None:
        return 0
    try:
        val = elem[str(key)]
        return int(val) if val is not None else 0
    except (ValueError, TypeError, KeyError):
        return 0


@pol_function("", "GetConfigString")
@pol_function("cfgfile", "GetConfigString")
def get_config_string(elem: Any = None, key: Any = None) -> str:
    """Get a string value from a config element."""
    if elem is None or key is None:
        return ""
    try:
        val = elem[str(key)]
        return str(val) if val is not None else ""
    except (TypeError, KeyError):
        return ""


@pol_function("", "GetConfigStringArray")
@pol_function("cfgfile", "GetConfigStringArray")
def get_config_string_array(elem: Any = None, key: Any = None) -> EArray:
    """Get all string values for a multi-value config property.

    POL's GetConfigStringArray returns an array of all values for a property
    name that appears multiple times in a config element.
    """
    if elem is None or key is None:
        return EArray()
    # RuntimeConfigElement wraps a ConfigElement that has get_all()
    inner = getattr(elem, "_elem", None)
    if inner is not None and hasattr(inner, "get_all"):
        return EArray(list(inner.get_all(str(key))))
    # Direct ConfigElement
    if hasattr(elem, "get_all"):
        return EArray(list(elem.get_all(str(key))))
    return EArray()


@pol_function("", "GetConfigStringKeys")
@pol_function("cfgfile", "GetConfigStringKeys")
def get_config_string_keys(cfg: Any = None) -> EArray:
    """Get all element names/keys from a config file."""
    if cfg is None:
        return EArray()
    if hasattr(cfg, "_cfg"):
        # RuntimeConfigFile wrapping a ConfigFile
        inner = cfg._cfg
        return EArray([e.name for e in inner])
    return EArray()


# ---------------------------------------------------------------------------
# Damage application
# ---------------------------------------------------------------------------


@pol_function("uo", "ApplyRawDamage")
@pol_function("", "ApplyRawDamage")
def apply_raw_damage(mobile: Any = None, amount: Any = 0) -> None:
    """Apply raw damage to a mobile.

    Matches POL charactr.cpp:1734-1782:
    - Returns immediately if target is already dead
    - Unhides the mobile on damage
    - Removes paralysis on damage
    - Rounds float damage (not truncate)
    - Subtracts from HP and records in simulation context.
    """
    if mobile is None:
        return

    # POL: if (dead()) return;  (charactr.cpp:1738)
    if getattr(mobile, "dead", False):
        return

    try:
        # POL's getParam extracts BLong only (executor.cpp:493-501).
        # If a Double arrives, POL rejects it and returns 0.  In practice
        # eScript always CInt()s damage before this call, so a float here
        # indicates a stub path divergence.  We truncate toward zero (C-style
        # cast) rather than round, matching CInt / static_cast<int> semantics.
        dmg = int(float(amount)) if amount is not None else 0
    except (TypeError, ValueError):
        return
    if dmg <= 0:
        return

    # POL: if (hidden()) unhide();  (charactr.cpp:1762)
    if getattr(mobile, "hidden", False):
        mobile.hidden = False

    # POL: if (paralyzed()) mob_flags_.remove(PARALYZED);  (charactr.cpp:1766)
    if getattr(mobile, "paralyzed", False):
        mobile.paralyzed = False

    mobile.hp = max(0, mobile.hp - dmg)
    if mobile.hp <= 0:
        mobile.dead = True

    ctx = get_context()
    ctx.record_damage(dmg)
    ctx.record_side_effect(
        kind="damage",
        target_serial=getattr(mobile, "serial", 0),
        value=dmg,
    )

    if ctx.debug_mode:
        ctx.metrics["spell_final_applied_damage"] = dmg

    logger.debug("ApplyRawDamage", target=getattr(mobile, "name", "?"), amount=dmg, hp_remaining=mobile.hp)


# ---------------------------------------------------------------------------
# Object lookup
# ---------------------------------------------------------------------------


@pol_function("uo", "SystemFindObjectBySerial")
@pol_function("", "SystemFindObjectBySerial")
def system_find_object_by_serial(serial: Any = None, flags: Any = None) -> Any:
    """Find a game object by serial number."""
    if serial is None:
        return None
    ctx = get_context()
    return ctx.find_object(int(serial))


@pol_function("uo", "FindMobile")
@pol_function("", "FindMobile")
def find_mobile(serial: Any = None) -> Any:
    """Find a mobile by serial number."""
    if serial is None:
        logger.warning("FindMobile: serial is None")
        return None
    ctx = get_context()
    obj = ctx.find_object(int(serial))
    if obj is not None and hasattr(obj, "is_npc"):
        return obj
    logger.warning("FindMobile: object not found or not a mobile", serial=repr(serial))
    return None


# ---------------------------------------------------------------------------
# Guild stubs
# ---------------------------------------------------------------------------


class _GuildStub:
    """Minimal guild object stub for PvP checks."""

    def __init__(self) -> None:
        self.guildid = 0

    def IsEnemyGuild(self, other: Any = None) -> int:  # noqa: N802
        return 0

    def IsAllyGuild(self, other: Any = None) -> int:  # noqa: N802
        return 0


_NULL_GUILD = _GuildStub()


@pol_function("uo", "FindGuild")
@pol_function("", "FindGuild")
def find_guild(guild_id: Any = None) -> Any:
    """Find a guild by ID. Returns stub with IsEnemyGuild → False."""
    return _NULL_GUILD


# ---------------------------------------------------------------------------
# Script control
# ---------------------------------------------------------------------------


@pol_function("os", "start_script")
@pol_function("os", "Start_Script")
@pol_function("", "start_script")
@pol_function("", "Start_Script")
def start_script(path: Any = None, *args: Any) -> Any:
    """Launch a sub-script via the executor.

    POL convention: ``start_script(":combat:script", {arg1, arg2, ...})``
    passes the array as the single first argument to the program.

    Falls back to a no-op warning if no executor is available on the
    simulation context.
    """
    from omega.runtime.context import get_context

    ctx = get_context()
    if ctx.executor is None:
        logger.warning(
            "start_script skipped (no executor on context)",
            script=path.value if hasattr(path, "value") else path,
            arg_count=len(args),
        )
        return None

    # Convert args to a list for the sub-program.
    # POL passes the array as the first positional argument.
    args_list = list(args)

    # Use the raw string value — str(enum) returns the name, not the value.
    # CombatScript is str,Enum so path_str IS the package path string.
    path_str = path.value if hasattr(path, "value") else path

    logger.info(
        "start_script dispatching",
        script=path_str,
        arg_count=len(args_list),
    )

    # POL's start_script is async (fire-and-forget).  We run sub-scripts
    # synchronously where possible, but failures in the spawned script
    # must not crash the calling hitscript.
    try:
        return ctx.executor.run_sub_program(path_str, args_list)
    except Exception as exc:
        logger.warning(
            "start_script sub-program failed (non-fatal)",
            script=path_str,
            error=str(exc),
        )
        return None


# ---------------------------------------------------------------------------
# Object manipulation — side effect recording
# ---------------------------------------------------------------------------


@pol_function("uo", "SetPoisoned")
@pol_function("", "SetPoisoned")
def set_poisoned(mobile: Any = None, level: Any = 0) -> None:
    """Set poison level. Records as side effect."""
    if mobile is None:
        return
    ctx = get_context()
    ctx.record_side_effect(
        kind="poison_applied",
        target_serial=getattr(mobile, "serial", 0),
        value=int(level) if level else 0,
    )
    logger.debug("SetPoisoned", target=getattr(mobile, "name", "?"), level=level)


@pol_function("uo", "SetParalyzed")
@pol_function("", "SetParalyzed")
def set_paralyzed(mobile: Any = None, flag: Any = None) -> None:
    """Set paralyzed state. Records as side effect."""
    if mobile is None:
        return
    ctx = get_context()
    ctx.record_side_effect(
        kind="paralyze",
        target_serial=getattr(mobile, "serial", 0),
        value=bool(flag),
    )


@pol_function("uo", "DestroyItem")
@pol_function("", "DestroyItem")
def destroy_item(item: Any = None) -> Any:
    """Destroy an item. Records as side effect.

    POL returns BLong(1) on success (uomod.cpp:2628).
    """
    if item is None:
        return None
    ctx = get_context()
    ctx.record_side_effect(
        kind="item_destroyed",
        target_serial=getattr(item, "serial", 0),
        detail=getattr(item, "name", "unknown"),
    )
    logger.debug("DestroyItem", item=getattr(item, "name", "?"))
    return 1


@pol_function("uo", "EquipItem")
@pol_function("", "EquipItem")
def equip_item(mobile: Any = None, item: Any = None) -> None:
    """Equip item on mobile. No-op with logging in simulation."""
    logger.debug("EquipItem (no-op)", item=getattr(item, "name", "?"))


@pol_function("uo", "MoveItemToContainer")
@pol_function("", "MoveItemToContainer")
def move_item_to_container(item: Any = None, container: Any = None) -> None:
    """Move item to container. No-op with logging in simulation."""
    logger.debug("MoveItemToContainer (no-op)", item=getattr(item, "name", "?"))


@pol_function("uo", "CreateItemAtLocation")
@pol_function("", "CreateItemAtLocation")
def create_item_at_location(
    x: Any = 0, y: Any = 0, z: Any = 0, objtype: Any = 0, quantity: Any = 1
) -> None:
    """Create item at location. No-op in simulation."""
    logger.debug("CreateItemAtLocation (no-op)", objtype=objtype)
    return None


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


@pol_function("os", "GetGlobalProperty")
@pol_function("", "GetGlobalProperty")
def get_global_property(name: Any = None) -> Any:
    """Get global server property from context store."""
    if name is None:
        logger.warning("GetGlobalProperty: name is None")
        return None
    ctx = get_context()
    key = str(name)
    val = ctx.global_properties.get(key)
    if val is not None:
        return val
    # Sensible defaults for properties not yet set
    defaults = {
        "powerHour": 0,
        "PowerHour": 0,
        "RPer": 0,
    }
    return defaults.get(key, None)


@pol_function("os", "SetGlobalProperty")
@pol_function("", "SetGlobalProperty")
def set_global_property(name: Any = None, value: Any = None) -> None:
    """Set global server property in context store."""
    if name is None:
        return
    ctx = get_context()
    ctx.global_properties[str(name)] = value


@pol_function("uo", "EnumerateOnlineCharacters")
@pol_function("", "EnumerateOnlineCharacters")
def enumerate_online_characters() -> list[Any]:
    """Return online characters. Empty in simulation."""
    return []


# ---------------------------------------------------------------------------
# Spell casting stubs
# ---------------------------------------------------------------------------


@pol_function("attributes", "CheckSkill")
@pol_function("", "CheckSkill")
def check_skill(
    character: Any = None,
    skill_id: Any = None,
    difficulty: Any = None,
    points: Any = None,
) -> int:
    """Simplified skill check for spell casting.

    POL's CheckSkill is hook-driven (attributemod.cpp).  In the shard,
    the hook determines success based on skill vs difficulty.  We use a
    simplified model: ``chance = clamp(skill - difficulty + 50, 0, 100)``
    then roll against it with the context RNG.

    Records wrapper metrics: spell_skill_check, spell_skill_chance,
    spell_difficulty.
    """
    if character is None or skill_id is None:
        return 0

    ctx = get_context()

    try:
        sid = int(skill_id)
        diff = int(difficulty) if difficulty is not None else 0
    except (TypeError, ValueError):
        return 0

    # Get effective skill value (display units 0-200)
    skill_val = 0
    if hasattr(character, "get_effective_skill"):
        skill_val = character.get_effective_skill(sid)

    chance = max(0, min(100, skill_val - diff + 50))

    # Use simulation RNG for determinism
    from omega.runtime.rng import get_rng

    roll = get_rng().random_int(100)  # 0-99
    success = roll < chance

    # Record metrics via wrapper
    if ctx.debug_mode:
        ctx.metrics["spell_skill_check"] = 1 if success else 0
        ctx.metrics["spell_skill_chance"] = chance
        ctx.metrics["spell_difficulty"] = diff

    logger.debug(
        "CheckSkill",
        character=getattr(character, "name", "?"),
        skill_id=sid,
        skill_val=skill_val,
        difficulty=diff,
        chance=chance,
        roll=roll,
        success=success,
    )
    return 1 if success else 0


@pol_function("vitals", "ConsumeMana")
@pol_function("", "ConsumeMana")
def consume_mana(character: Any = None, spell_id: Any = None) -> int:
    """Consume mana for a spell.

    POL's ConsumeMana (vitalmod.cpp) looks up the spell's circle, gets
    the mana cost from circles config, and deducts it.  We replicate this
    by reading the config via ReadConfigFile, matching the shard's logic
    in TryToCast.

    Returns 1 on success (mana consumed), 0 on insufficient mana.
    Records wrapper metrics: spell_mana_cost, spell_mana_before,
    spell_mana_consumed.
    """
    if character is None or spell_id is None:
        return 0

    ctx = get_context()

    try:
        sid = int(spell_id)
    except (TypeError, ValueError):
        return 0

    # Read spell config to get circle, then circle config for mana cost
    # This mirrors TryToCast's config read chain
    spell_cfg = read_config_file(":*:spells")
    if spell_cfg is None:
        logger.warning("ConsumeMana: could not read spells config")
        return 1  # Fail open if no config

    from omega.config.accessor import RuntimeConfigFile

    circle = 0
    if isinstance(spell_cfg, RuntimeConfigFile):
        elem = spell_cfg[sid]
        if elem is not None:
            circle_val = getattr(elem, "Circle", None)
            try:
                circle = int(circle_val) if circle_val is not None else 0
            except (TypeError, ValueError):
                circle = 0

    circles_cfg = read_config_file(":*:circles")
    mana_cost = 0
    if circles_cfg is not None and isinstance(circles_cfg, RuntimeConfigFile):
        circ_elem = circles_cfg[circle]
        if circ_elem is not None:
            mana_val = getattr(circ_elem, "Mana", None)
            try:
                mana_cost = int(mana_val) if mana_val is not None else 0
            except (TypeError, ValueError):
                mana_cost = 0

    # Mobile.mana is in display units (matching POL's current_ones()).
    # POL's check_mana compares current_ones() >= manacost (both display).
    # POL's consume_mana deducts manacost*100 from hundredths internally,
    # which is equivalent to subtracting manacost from display units.
    current_mana = getattr(character, "mana", 0)
    try:
        current_mana = int(current_mana)
    except (TypeError, ValueError):
        current_mana = 0

    # Record metrics
    if ctx.debug_mode:
        ctx.metrics["spell_mana_cost"] = mana_cost
        ctx.metrics["spell_mana_before"] = current_mana

    if current_mana < mana_cost:
        if ctx.debug_mode:
            ctx.metrics["spell_mana_consumed"] = 0
        logger.debug(
            "ConsumeMana: insufficient",
            mana=current_mana,
            cost=mana_cost,
        )
        return 0

    # Deduct mana in display units
    character.mana = current_mana - mana_cost

    if ctx.debug_mode:
        ctx.metrics["spell_mana_consumed"] = 1

    logger.debug(
        "ConsumeMana",
        character=getattr(character, "name", "?"),
        spell_id=sid,
        circle=circle,
        cost=mana_cost,
        mana_before=current_mana,
        mana_after=character.mana,
    )
    return 1


@pol_function("uo", "ConsumeReagents")
@pol_function("", "ConsumeReagents")
def consume_reagents(character: Any = None, spell_id: Any = None) -> int:
    """Consume reagents for a spell. Always succeeds in simulation."""
    return 1


@pol_function("uo", "Target")
@pol_function("", "Target")
def target_stub(character: Any = None, options: Any = None) -> Any:
    """Return the primary defender as the target.

    POL's Target() is a blocking call that suspends the script and waits
    for player input.  In the simulator, we return ctx.defender immediately.
    """
    ctx = get_context()
    result = ctx.defender
    logger.debug("Target", target=getattr(result, "name", "?") if result else "None")
    return result


@pol_function("uo", "TargetCoordinates")
@pol_function("", "TargetCoordinates")
def target_coordinates(character: Any = None) -> Any:
    """Return coordinates of the primary defender.

    POL's TargetCoordinates() is a blocking call.  We return an EStruct
    with the defender's x/y/z.

    Coordinates default to (100, 100, 0) when the defender has no position
    set, because many scripts guard with ``if (!cast_loc.x)`` — returning
    x=0 would be treated as "no target selected" and abort the spell.
    """
    from omega.interpreter.evaluator import EStruct

    # Default to non-zero coords so scripts that check `!cast_loc.x`
    # don't treat the simulated target as "cancelled targeting cursor".
    _DEFAULT_X, _DEFAULT_Y, _DEFAULT_Z = 100, 100, 0

    ctx = get_context()
    defender = ctx.defender
    if defender is None:
        return EStruct({"x": _DEFAULT_X, "y": _DEFAULT_Y, "z": _DEFAULT_Z})
    return EStruct({
        "x": getattr(defender, "x", 0) or _DEFAULT_X,
        "y": getattr(defender, "y", 0) or _DEFAULT_Y,
        "z": getattr(defender, "z", _DEFAULT_Z),
    })


@pol_function("uo", "CheckLineOfSight")
@pol_function("", "CheckLineOfSight")
def check_line_of_sight(src: Any = None, dst: Any = None) -> int:
    """Always returns 1 (LOS exists) in simulation."""
    return 1


@pol_function("uo", "CheckLosAt")
@pol_function("", "CheckLosAt")
def check_los_at(
    src: Any = None, x: Any = None, y: Any = None, z: Any = None
) -> int:
    """Always returns 1 (LOS to coordinates exists) in simulation."""
    return 1


@pol_function("uo", "ListHostiles")
@pol_function("", "ListHostiles")
def list_hostiles(
    character: Any = None, range_val: Any = None, flags: Any = None
) -> EArray:
    """Return empty array — no interruption in simulation."""
    return EArray()


@pol_function("uo", "ListMobilesNearLocationEx")
@pol_function("", "ListMobilesNearLocationEx")
def list_mobiles_near_location_ex(
    x: Any = None,
    y: Any = None,
    z: Any = None,
    range_val: Any = None,
    flags: Any = None,
    realm: Any = None,
) -> EArray:
    """Return all defenders from context for AoE targeting."""
    ctx = get_context()
    result = list(ctx.defenders) if ctx.defenders else []
    if ctx.debug_mode:
        ctx.metrics["aoe_target_count"] = len(result)
    return EArray(result)


@pol_function("uo", "ListMobilesNearLocation")
@pol_function("", "ListMobilesNearLocation")
def list_mobiles_near_location(
    x: Any = None,
    y: Any = None,
    z: Any = None,
    range_val: Any = None,
    realm: Any = None,
) -> EArray:
    """Return all defenders from context for AoE targeting."""
    ctx = get_context()
    result = list(ctx.defenders) if ctx.defenders else []
    return EArray(result)


@pol_function("uo", "ListItemsNearLocation")
@pol_function("", "ListItemsNearLocation")
def list_items_near_location(
    x: Any = None,
    y: Any = None,
    z: Any = None,
    range_val: Any = None,
    realm: Any = None,
) -> EArray:
    """No-op — item search not modeled in simulation."""
    return EArray()


@pol_function("uo", "ListItemsNearLocationOfType")
@pol_function("", "ListItemsNearLocationOfType")
def list_items_near_location_of_type(
    x: Any = None,
    y: Any = None,
    z: Any = None,
    range_val: Any = None,
    objtype: Any = None,
    realm: Any = None,
) -> EArray:
    """No-op — structure/item damage not modeled in simulation."""
    return EArray()
