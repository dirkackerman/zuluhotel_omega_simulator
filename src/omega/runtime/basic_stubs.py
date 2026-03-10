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
    """Send system message. Logs when debug_mode is enabled."""
    ctx = get_context()
    if ctx.debug_mode:
        name = getattr(mobile, "name", "?")
        msg_logger.info("SendSysMessage", target=name, text=str(text))


@pol_function("uo", "PrintTextAbove")
@pol_function("", "PrintTextAbove")
def print_text_above(mobile: Any = None, text: Any = "") -> None:
    """Display text above character. Logs when debug_mode is enabled."""
    ctx = get_context()
    if ctx.debug_mode:
        name = getattr(mobile, "name", "?")
        msg_logger.info("PrintTextAbove", target=name, text=str(text))


@pol_function("uo", "PrintTextAbovePrivate")
@pol_function("", "PrintTextAbovePrivate")
def print_text_above_private(
    mobile: Any = None, text: Any = "", viewer: Any = None
) -> None:
    """Display text visible only to viewer. Logs when debug_mode is enabled."""
    ctx = get_context()
    if ctx.debug_mode:
        name = getattr(mobile, "name", "?")
        msg_logger.info("PrintTextAbovePrivate", target=name, text=str(text))


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


@pol_function("", "SetWarMode")
@pol_function("uo", "SetWarMode")
def set_war_mode(mobile: Any = None, mode: Any = None) -> None:
    logger.debug("SetWarMode (no-op)", mode=mode)


@pol_function("", "RevokePrivilege")
@pol_function("uo", "RevokePrivilege")
def revoke_privilege(mobile: Any = None, priv: Any = None) -> None:
    logger.debug("RevokePrivilege (no-op)", privilege=priv)
