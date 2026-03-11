"""Batch 1 — Trivial POL built-in stubs.

Type casts, math, string ops, time, messaging, and no-op action stubs.
"""

from __future__ import annotations

import math as pymath
from typing import Any

from omega.logging import get_logger
from omega.runtime.context import get_context
from omega.runtime.registry import pol_function
from omega.runtime.rng import get_rng

msg_logger = get_logger("omega.runtime.messaging")
logger = get_logger("omega.runtime")

# ---------------------------------------------------------------------------
# Type casts (util module)
# ---------------------------------------------------------------------------


@pol_function("", "CInt")
@pol_function("util", "CInt")
def cint(value: Any = None) -> int:
    """Convert to integer. None/error → 0."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


@pol_function("", "CDbl")
@pol_function("util", "CDbl")
def cdbl(value: Any = None) -> float:
    """Convert to double. None/error → 0.0."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


@pol_function("", "CStr")
@pol_function("util", "CStr")
def cstr(value: Any = None) -> str:
    """Convert to string."""
    if value is None:
        return ""
    return str(value)


@pol_function("", "Hex")
@pol_function("util", "Hex")
def hex_func(value: Any = None) -> str:
    """Convert to hex string."""
    try:
        return hex(int(value))
    except (ValueError, TypeError):
        return "0x0"


@pol_function("", "Max")
def max_func(a: Any = 0, b: Any = 0) -> Any:
    """Return the larger of two values."""
    try:
        return max(a, b)
    except TypeError:
        return a


@pol_function("", "Min")
def min_func(a: Any = 0, b: Any = 0) -> Any:
    """Return the smaller of two values."""
    try:
        return min(a, b)
    except TypeError:
        return a


# ---------------------------------------------------------------------------
# Type queries
# ---------------------------------------------------------------------------


@pol_function("", "TypeOf")
@pol_function("basic", "TypeOf")
def type_of(value: Any = None) -> str:
    """Return type string matching POL conventions."""
    if value is None:
        return "Uninit"
    if isinstance(value, bool):
        return "Integer"  # POL treats bools as ints
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Double"
    if isinstance(value, str):
        return "String"
    if isinstance(value, (list, tuple)):
        return "Array"
    if isinstance(value, dict):
        return "Dictionary"

    # Check for game objects by class name
    cls_name = type(value).__name__
    if cls_name == "Mobile":
        return "MobileRef"
    if cls_name in ("Weapon", "Armor"):
        return "ItemRef"

    return "Unknown"


@pol_function("", "Len")
@pol_function("basic", "Len")
def len_func(value: Any = None) -> int:
    """Get length of array, string, or dictionary."""
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 0


# ---------------------------------------------------------------------------
# Math (math module)
# ---------------------------------------------------------------------------


@pol_function("math", "Pow")
@pol_function("", "Pow")
def pow_func(base: Any = 0, exp: Any = 0) -> float:
    """Raise base to exponent."""
    try:
        return float(base) ** float(exp)
    except (ValueError, TypeError, OverflowError):
        return 0.0


@pol_function("math", "Abs")
@pol_function("", "Abs")
def abs_func(value: Any = 0) -> int | float:
    """Absolute value."""
    try:
        return abs(value)
    except TypeError:
        return 0


@pol_function("math", "Sqrt")
@pol_function("math", "Sqr")
def sqrt_func(value: Any = 0) -> float:
    """Square root."""
    try:
        v = float(value)
        if v < 0:
            return 0.0
        return pymath.sqrt(v)
    except (ValueError, TypeError):
        return 0.0


@pol_function("math", "Sin")
def sin_func(value: Any = 0) -> float:
    try:
        return pymath.sin(float(value))
    except (ValueError, TypeError):
        return 0.0


@pol_function("math", "Cos")
def cos_func(value: Any = 0) -> float:
    try:
        return pymath.cos(float(value))
    except (ValueError, TypeError):
        return 0.0


@pol_function("math", "Exp")
def exp_func(base: Any = 0, power: Any = 0) -> float:
    """Exponentiation (alias for Pow in math.inc wrapper)."""
    try:
        return float(base) ** float(power)
    except (ValueError, TypeError, OverflowError):
        return 0.0


# ---------------------------------------------------------------------------
# Random number generation
# ---------------------------------------------------------------------------


@pol_function("", "Random")
@pol_function("uo", "Random")
def random_func(max_val: Any = 1) -> int:
    """Random integer in [1, max_val]. Matches POL's Random()."""
    return get_rng().random(int(max_val))


@pol_function("", "RandomInt")
@pol_function("uo", "RandomInt")
def random_int_func(max_val: Any = 1) -> int:
    """Random integer in [0, max_val-1]. Matches POL's RandomInt()."""
    return get_rng().random_int(int(max_val))


# ---------------------------------------------------------------------------
# String operations (basic module)
# ---------------------------------------------------------------------------


@pol_function("", "SplitWords")
@pol_function("basic", "SplitWords")
def split_words(text: Any = "", delim: Any = None) -> list[str]:
    """Split string into array of words."""
    s = str(text) if text is not None else ""
    if delim is not None:
        return s.split(str(delim))
    return s.split()


@pol_function("", "Lower")
@pol_function("basic", "Lower")
def lower_func(text: Any = "") -> str:
    return str(text).lower() if text is not None else ""


@pol_function("", "Upper")
@pol_function("basic", "Upper")
def upper_func(text: Any = "") -> str:
    return str(text).upper() if text is not None else ""


@pol_function("", "SubStr")
@pol_function("basic", "SubStr")
def substr_func(text: Any = "", start: Any = 1, length: Any = None) -> str:
    """Substring. POL uses 1-based indexing."""
    s = str(text) if text is not None else ""
    idx = int(start) - 1  # convert to 0-based
    if idx < 0:
        idx = 0
    if length is not None:
        return s[idx : idx + int(length)]
    return s[idx:]


@pol_function("", "Find")
@pol_function("basic", "Find")
def find_func(text: Any = "", search: Any = "", start: Any = 1) -> int:
    """Find substring position (1-based). Returns 0 if not found."""
    s = str(text) if text is not None else ""
    needle = str(search) if search is not None else ""
    offset = max(0, int(start) - 1)
    pos = s.find(needle, offset)
    return pos + 1 if pos >= 0 else 0


# ---------------------------------------------------------------------------
# Time (os module)
# ---------------------------------------------------------------------------


@pol_function("os", "ReadGameClock")
@pol_function("", "ReadGameClock")
def read_game_clock() -> int:
    """Return simulated game clock value."""
    return get_context().game_clock


# ---------------------------------------------------------------------------
# Messaging — DEBUG_MODE aware
# ---------------------------------------------------------------------------


@pol_function("uo", "SendSysMessage")
@pol_function("", "SendSysMessage")
def send_sys_message(
    mobile: Any = None, text: Any = "", font: Any = None, color: Any = None
) -> None:
    """Send system message. Logs the message text when debug_mode is enabled."""
    ctx = get_context()
    if ctx.debug_mode:
        name = getattr(mobile, "name", "?")
        msg_logger.info(f"[{name}] {text}")


@pol_function("uo", "PrintTextAbove")
@pol_function("", "PrintTextAbove")
def print_text_above(mobile: Any = None, text: Any = "") -> None:
    """Display text above character. Logs the message text when debug_mode is enabled."""
    ctx = get_context()
    if ctx.debug_mode:
        name = getattr(mobile, "name", "?")
        msg_logger.info(f"[{name}] {text}")


@pol_function("uo", "PrintTextAbovePrivate")
@pol_function("", "PrintTextAbovePrivate")
def print_text_above_private(
    mobile: Any = None, text: Any = "", viewer: Any = None
) -> None:
    """Display text visible only to viewer. Logs the message text when debug_mode is enabled."""
    ctx = get_context()
    if ctx.debug_mode:
        name = getattr(mobile, "name", "?")
        msg_logger.info(f"[{name}] {text}")


@pol_function("basic", "Print")
@pol_function("", "Print")
def print_stub(text: Any = "") -> None:
    """eScript Print() — server console output. Logs the message text when debug_mode is enabled."""
    ctx = get_context()
    if ctx.debug_mode:
        msg_logger.info(f"{text}")


# ---------------------------------------------------------------------------
# No-ops with logging
# ---------------------------------------------------------------------------


@pol_function("uo", "PerformAction")
@pol_function("", "PerformAction")
def perform_action(mobile: Any = None, action: Any = None) -> None:
    logger.debug("PerformAction (no-op)", action=action)


@pol_function("uo", "PlaySoundEffect")
@pol_function("", "PlaySoundEffect")
def play_sound_effect(mobile: Any = None, sound: Any = None) -> None:
    logger.debug("PlaySoundEffect (no-op)", sound=sound)


@pol_function("uo", "PlaySoundEffectPrivate")
@pol_function("", "PlaySoundEffectPrivate")
def play_sound_effect_private(
    mobile: Any = None, sound: Any = None, target: Any = None
) -> None:
    logger.debug("PlaySoundEffectPrivate (no-op)", sound=sound)


@pol_function("uo", "IncRevision")
@pol_function("", "IncRevision")
def inc_revision(item: Any = None) -> None:
    pass  # Pure no-op


@pol_function("os", "set_critical")
@pol_function("", "set_critical")
def set_critical(flag: Any = None) -> None:
    pass  # No threading in simulation


@pol_function("os", "Sleepms")
@pol_function("", "Sleepms")
def sleepms(ms: Any = None) -> None:
    pass  # No delays in simulation


@pol_function("uo", "SetScriptController")
@pol_function("", "SetScriptController")
def set_script_controller(mobile: Any = None) -> None:
    logger.debug("SetScriptController (no-op)")


@pol_function("uo", "Distance")
@pol_function("", "Distance")
def distance(a: Any = None, b: Any = None) -> int:
    """Return distance between two objects. Default 1 (melee range)."""
    return 1


@pol_function("uo", "SendEvent")
@pol_function("", "SendEvent")
def send_event(npc: Any = None, event: Any = None) -> None:
    """Send event to NPC (no-op in simulation)."""
    logger.debug("SendEvent (no-op)")


@pol_function("uo", "PlayMovingEffect")
@pol_function("", "PlayMovingEffect")
def play_moving_effect(
    source: Any = None, target: Any = None, effect: Any = None,
    speed: Any = None, loop: Any = 0, explode: Any = 0,
) -> None:
    """Play moving visual effect (no-op in simulation)."""
    logger.debug("PlayMovingEffect (no-op)")


@pol_function("uo", "PlayMovingEffectEx")
@pol_function("", "PlayMovingEffectEx")
def play_moving_effect_ex(*args: Any, **kwargs: Any) -> None:
    """Play moving visual effect extended (no-op in simulation)."""
    logger.debug("PlayMovingEffectEx (no-op)")


@pol_function("uo", "PlayObjectCenteredEffect")
@pol_function("", "PlayObjectCenteredEffect")
def play_object_centered_effect(
    center: Any = None, effect: Any = None, speed: Any = None, loop: Any = 0,
) -> None:
    """Play centered visual effect (no-op in simulation)."""
    logger.debug("PlayObjectCenteredEffect (no-op)")


@pol_function("uo", "PlayObjectCenteredEffectEx")
@pol_function("", "PlayObjectCenteredEffectEx")
def play_object_centered_effect_ex(*args: Any, **kwargs: Any) -> None:
    """Play centered visual effect extended (no-op in simulation)."""
    logger.debug("PlayObjectCenteredEffectEx (no-op)")


@pol_function("uo", "PlayStationaryEffect")
@pol_function("", "PlayStationaryEffect")
def play_stationary_effect(*args: Any, **kwargs: Any) -> None:
    """Play stationary visual effect (no-op in simulation)."""
    logger.debug("PlayStationaryEffect (no-op)")


@pol_function("uo", "PlayLightningBoltEffect")
@pol_function("", "PlayLightningBoltEffect")
def play_lightning_bolt_effect(mobile: Any = None) -> None:
    """Play lightning bolt visual effect (no-op in simulation)."""
    logger.debug("PlayLightningBoltEffect (no-op)")


@pol_function("uo", "send_attack")
@pol_function("", "send_attack")
def send_attack(target: Any = None, attacker: Any = None, spell_id: Any = None) -> None:
    """Notify combat system of an attack (no-op in simulation)."""
    logger.debug("send_attack (no-op)", spell_id=spell_id)


@pol_function("os", "set_priority")
@pol_function("", "set_priority")
def set_priority(value: Any = None) -> int:
    """Set script priority (no-op in simulation). Returns previous priority."""
    return 0


@pol_function("util", "RandomFloat")
@pol_function("", "RandomFloat")
def random_float(below: Any = 1.0) -> float:
    """Return random float in [0, below)."""
    rng = get_rng()
    limit = float(below) if below is not None else 1.0
    return rng._rng.random() * limit


@pol_function("math", "LogE")
@pol_function("", "LogE")
def log_e(value: Any = None) -> float:
    """Natural logarithm."""
    if value is None or float(value) <= 0:
        return 0.0
    return pymath.log(float(value))


@pol_function("util", "RandomDiceRoll")
@pol_function("", "RandomDiceRoll")
def random_dice_roll(dice_string: Any = None, allow_negatives: Any = 0) -> int:
    """Roll dice from a string like '3d6+4'. Uses our deterministic RNG."""
    if dice_string is None:
        return 0
    ds = str(dice_string).strip().lower()
    # Parse XdY+Z or XdY-Z
    import re
    m = re.match(r'(\d+)d(\d+)([+-]\d+)?', ds)
    if not m:
        try:
            return int(float(ds))
        except (ValueError, TypeError):
            return 0
    num_dice = int(m.group(1))
    faces = int(m.group(2))
    bonus = int(m.group(3)) if m.group(3) else 0
    rng = get_rng()
    total = bonus + num_dice  # base = bonus + num_dice (1 per die minimum)
    for _ in range(num_dice):
        total += rng._rng.randint(0, faces - 1) if faces > 0 else 0
    result = total
    if not allow_negatives and result < 0:
        result = 0
    return result


@pol_function("os", "detach")
@pol_function("", "detach")
def detach() -> None:
    """Detach script from parent (no-op in simulation)."""
    logger.debug("detach (no-op)")


@pol_function("", "SetWarMode")
@pol_function("uo", "SetWarMode")
def set_war_mode(mobile: Any = None, mode: Any = None) -> None:
    logger.debug("SetWarMode (no-op)", mode=mode)


@pol_function("uo", "MoveObjectToLocation")
@pol_function("", "MoveObjectToLocation")
def move_object_to_location(*args: Any, **kwargs: Any) -> None:
    """Move object to world location (no-op in simulation)."""
    logger.debug("MoveObjectToLocation (no-op)")


@pol_function("", "RevokePrivilege")
@pol_function("uo", "RevokePrivilege")
def revoke_privilege(mobile: Any = None, priv: Any = None) -> None:
    logger.debug("RevokePrivilege (no-op)", privilege=priv)
