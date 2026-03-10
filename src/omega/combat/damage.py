"""Base damage rolling for combat hits."""

from __future__ import annotations

from random import Random

from omega.config.dice import DiceSpec, roll_dice
from omega.model.items import Weapon


def roll_base_damage(weapon: Weapon, rng: Random | None = None) -> int:
    """Roll base damage from a weapon's dice spec.

    In POL, basedamage and rawdamage both start as the same weapon roll.
    The mainhit script then applies modifiers to rawdamage.

    Parameters
    ----------
    weapon:
        Weapon with a damage DiceSpec.
    rng:
        Random instance for deterministic rolls. If None, uses default.

    Returns
    -------
    int:
        The rolled damage value (minimum 1).
    """
    dmg = roll_dice(weapon.damage, rng)
    return max(1, dmg)
