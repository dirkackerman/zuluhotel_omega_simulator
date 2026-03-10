"""Dice notation parser for weapon damage specifications.

POL weapon configs use dice notation like ``3d5+2`` meaning:
roll 3 dice with 5 sides each, then add 2.

Usage::

    spec = parse_dice("3d5+2")
    # DiceSpec(count=3, sides=5, bonus=2)

    damage = roll_dice(spec, rng)
    # Random value between 5 and 17
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from random import Random

# Matches: "3d5+2", "3d5-1", "3d5", "5" (flat damage)
_DICE_RE = re.compile(
    r"^(\d+)(?:d(\d+))?([+-]\d+)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class DiceSpec:
    """Parsed dice notation."""

    count: int
    """Number of dice to roll (0 if flat damage)."""

    sides: int
    """Sides per die (0 if flat damage)."""

    bonus: int
    """Flat modifier added after rolling."""

    @property
    def min_value(self) -> int:
        """Minimum possible roll."""
        if self.sides == 0:
            return self.bonus
        return self.count + self.bonus

    @property
    def max_value(self) -> int:
        """Maximum possible roll."""
        if self.sides == 0:
            return self.bonus
        return self.count * self.sides + self.bonus

    @property
    def mean_value(self) -> float:
        """Expected average roll."""
        if self.sides == 0:
            return float(self.bonus)
        return self.count * (self.sides + 1) / 2.0 + self.bonus

    def __str__(self) -> str:
        if self.sides == 0:
            return str(self.bonus)
        result = f"{self.count}d{self.sides}"
        if self.bonus > 0:
            result += f"+{self.bonus}"
        elif self.bonus < 0:
            result += str(self.bonus)
        return result


def parse_dice(notation: str) -> DiceSpec:
    """Parse dice notation string into a DiceSpec.

    Supported formats:
    - ``"3d5+2"`` — 3 dice, 5 sides, +2 bonus
    - ``"2d6-1"`` — 2 dice, 6 sides, -1 penalty
    - ``"1d4"``   — 1 die, 4 sides, no bonus
    - ``"5"``     — flat damage of 5

    Raises
    ------
    ValueError:
        If the notation is not a valid dice format.
    """
    notation = notation.strip()
    m = _DICE_RE.match(notation)
    if not m:
        raise ValueError(f"Invalid dice notation: {notation!r}")

    first = int(m.group(1))
    sides_str = m.group(2)
    bonus_str = m.group(3)

    if sides_str is None:
        # Flat damage: "5"
        return DiceSpec(count=0, sides=0, bonus=first)

    sides = int(sides_str)
    bonus = int(bonus_str) if bonus_str else 0

    return DiceSpec(count=first, sides=sides, bonus=bonus)


def roll_dice(spec: DiceSpec, rng: Random | None = None) -> int:
    """Roll dice according to a DiceSpec.

    Parameters
    ----------
    spec:
        The dice specification.
    rng:
        Random number generator. If None, uses a default Random instance.

    Returns
    -------
    int:
        The total rolled value.
    """
    if rng is None:
        rng = Random()

    if spec.sides == 0:
        return spec.bonus

    total = sum(rng.randint(1, spec.sides) for _ in range(spec.count))
    return total + spec.bonus
