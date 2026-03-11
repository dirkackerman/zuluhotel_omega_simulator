"""Batch 3 — Structural POL built-in stubs.

Config file access, damage application, guild lookups, script control,
and object creation/destruction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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


@pol_function("", "GetConfigStringKeys")
@pol_function("cfgfile", "GetConfigStringKeys")
def get_config_string_keys(cfg: Any = None) -> list[str]:
    """Get all element names/keys from a config file."""
    if cfg is None:
        return []
    if hasattr(cfg, "_cfg"):
        # RuntimeConfigFile wrapping a ConfigFile
        inner = cfg._cfg
        return [e.name for e in inner]
    return []


# ---------------------------------------------------------------------------
# Damage application
# ---------------------------------------------------------------------------


@pol_function("uo", "ApplyRawDamage")
@pol_function("", "ApplyRawDamage")
def apply_raw_damage(mobile: Any = None, amount: Any = 0) -> None:
    """Apply raw damage to a mobile.

    Subtracts from HP and records in simulation context.
    """
    if mobile is None:
        return

    dmg = int(amount) if amount is not None else 0
    if dmg <= 0:
        return

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

    def IsEnemyGuild(self, other: Any = None) -> bool:  # noqa: N802
        return False

    def IsAllyGuild(self, other: Any = None) -> bool:  # noqa: N802
        return False


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
            script=str(path),
            arg_count=len(args),
        )
        return None

    # Convert args to a list for the sub-program.
    # POL passes the array as the first positional argument.
    args_list = list(args)

    logger.info(
        "start_script dispatching",
        script=str(path),
        arg_count=len(args_list),
    )

    # POL's start_script is async (fire-and-forget).  We run sub-scripts
    # synchronously where possible, but failures in the spawned script
    # must not crash the calling hitscript.
    try:
        return ctx.executor.run_sub_program(str(path), args_list)
    except Exception as exc:
        logger.warning(
            "start_script sub-program failed (non-fatal)",
            script=str(path),
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
        kind="poison",
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
def destroy_item(item: Any = None) -> None:
    """Destroy an item. Records as side effect."""
    if item is None:
        return
    ctx = get_context()
    ctx.record_side_effect(
        kind="item_destroyed",
        target_serial=getattr(item, "serial", 0),
        detail=getattr(item, "name", "unknown"),
    )
    logger.debug("DestroyItem", item=getattr(item, "name", "?"))


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
