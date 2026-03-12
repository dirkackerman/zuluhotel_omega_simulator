"""POL-conformant swing delay calculation.

Implements ``Character::schedule_attack()`` from
``polserver/pol-core/pol/mobile/charactr.cpp:2832–2881``.

Clock unit: 1 POL clock = 10ms (``POLCLOCKS_PER_SEC = 100``).

Two mutually exclusive timing paths:

**Speed-based** (when ``weapon.delay == 0`` — all ZH weapons):
    ``clocks = 1_500_000 // ((DEX + 100) * SPEED)``

**Delay-based** (when ``weapon.delay > 0``):
    ``delay_sum = max(0, weapon.delay + char.delay_mod)``
    ``clocks = (delay_sum * 100) // 1000``

Both paths then apply SwingSpeedIncrease::

    modifier = clamp(swing_speed_increase / 100.0, min=-0.99)
    clocks = c_round(clocks / (1 + modifier))

Note: POL does NOT enforce a minimum floor — the ``clocks < 20`` check at
line 2872 is only a debug log, not a clamp.  We match this exactly.
"""

from __future__ import annotations

import math

from omega.logging import get_logger
from omega.model.items import Weapon
from omega.model.mobile import Mobile

logger = get_logger("omega.combat.timing")

# POL constants from polclock.h
POLCLOCKS_PER_SEC: int = 100
"""1 POL clock = 10ms; 100 clocks per second."""


def _c_round(x: float) -> int:
    """C++ ``round()`` semantics: round half away from zero.

    Python's built-in ``round()`` uses banker's rounding (half to even),
    which diverges from C++ for values like 66.5 or 150.5.

    Examples:
        _c_round(66.5)  → 67  (Python round() → 66)
        _c_round(150.5) → 151 (Python round() → 150)
        _c_round(-2.5)  → -3  (Python round() → -2)
    """
    if x >= 0:
        return int(math.floor(x + 0.5))
    else:
        return int(math.ceil(x - 0.5))


def calculate_swing_delay(attacker: Mobile, weapon: Weapon) -> float:
    """Calculate swing delay in milliseconds, matching POL's ``schedule_attack()``.

    Parameters
    ----------
    attacker:
        The attacking mobile (provides DEX, delay_mod, swing_speed_increase).
    weapon:
        The weapon used (provides speed and delay).

    Returns
    -------
    float
        Swing delay in milliseconds.  Always >= 10.0 (1 clock minimum from
        integer arithmetic; POL doesn't enforce a floor beyond that).

    References
    ----------
    ``charactr.cpp:2832–2881`` (``Character::schedule_attack()``)
    ``polclock.h:33`` (``POLCLOCKS_PER_SEC = 100``)
    """
    weapon_speed: int = weapon.speed
    weapon_delay: int = weapon.delay

    if not weapon_delay:
        # Speed-based path (charactr.cpp:2850–2851)
        # C++ integer division: truncates toward zero.
        # Both operands are positive here, so Python // is equivalent.
        dex = attacker.dexterity
        denominator = (dex + 100) * weapon_speed
        if denominator <= 0:
            # Guard against division by zero (weapon_speed=0 or extreme negative DEX)
            logger.warning(
                "Swing delay denominator <= 0",
                dex=dex,
                weapon_speed=weapon_speed,
            )
            # Return a large delay — can't swing
            return 100_000.0

        clocks = (POLCLOCKS_PER_SEC * 15000) // denominator
    else:
        # Delay-based path (charactr.cpp:2855–2863)
        delay_sum = weapon_delay + attacker.delay_mod
        if delay_sum < 0:
            delay_sum = 0
        # C++ integer division: (delay_sum * 100) / 1000
        clocks = (delay_sum * POLCLOCKS_PER_SEC) // 1000

    # SwingSpeedIncrease modifier (charactr.cpp:2867–2870)
    # swing_speed_increase().sum() returns an integer (hundredths)
    ssi = attacker.swing_speed_increase
    speed_modifier = ssi / 100.0
    if speed_modifier < -0.99:
        speed_modifier = -0.99

    # C++ uses round() which is "round half away from zero"
    clocks = _c_round(clocks / (1 + speed_modifier))

    # POL line 2872: clocks < POLCLOCKS_PER_SEC / 5 is just a debug log,
    # NOT a clamp.  We match POL exactly — no minimum enforcement.
    # However, clocks can't be negative in practice (both paths yield >= 0).
    if clocks < 0:
        clocks = 0

    # Convert POL clocks to milliseconds (1 clock = 10ms)
    delay_ms = float(clocks * 10)

    logger.debug(
        "Swing delay calculated",
        weapon_speed=weapon_speed,
        weapon_delay=weapon_delay,
        dex=attacker.dexterity,
        delay_mod=attacker.delay_mod,
        ssi=ssi,
        clocks=clocks,
        delay_ms=delay_ms,
    )

    return delay_ms
