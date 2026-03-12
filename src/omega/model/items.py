"""Weapon and Armor game objects.

Weapons have damage dice, speed, and a combat skill attribute.
Armor has an AR value and body coverage zones.
Both have durability (hp/max_hp) and support the property bag for
enchantment data (SlayType, ElementalDamage, Astral, etc.).
"""

from __future__ import annotations

from omega.config.dice import DiceSpec
from omega.model.game_object import GameObject


class Weapon(GameObject):
    """A weapon with damage, speed, and combat attribute.

    Parameters
    ----------
    damage:
        Dice spec for base damage (e.g., ``DiceSpec(3, 5, 2)`` for 3d5+2).
    speed:
        Attack speed in tenths of a second.
    attribute:
        Skill ID used for this weapon (SKILLID_SWORDSMANSHIP, etc.).
    two_handed:
        Whether the weapon requires both hand slots.
    quality:
        Crafting quality modifier (default 1.0).
    hitscript:
        Package path to hit script (e.g., ``:combat:crithit``), or None.
    """

    _polclasses = ("Item", "Weapon")

    def __init__(
        self,
        *,
        objtype: int = 0,
        graphic: int | None = None,
        name: str = "",
        color: int = 0,
        damage: DiceSpec | None = None,
        speed: int = 50,
        delay: int = 0,
        attribute: int = 0,
        two_handed: bool = False,
        quality: float = 1.0,
        hitscript: str | None = None,
        hp: int = 50,
        max_hp: int = 50,
    ) -> None:
        super().__init__(objtype=objtype, graphic=graphic, name=name, color=color)
        self.damage: DiceSpec = damage or DiceSpec(count=1, sides=4, bonus=0)
        self.speed: int = speed
        self.delay: int = delay
        """Explicit delay in milliseconds (alternative to speed).

        When ``delay > 0``, the delay-based swing timer path is used
        instead of the speed-based path.  Matches POL's ``WeaponDesc::delay``
        (``weapon.cpp:87``).
        """
        self.attribute: int = attribute
        self.two_handed: bool = two_handed
        self.quality: float = quality
        self.hitscript: str | None = hitscript
        self.hp: int = hp
        self.max_hp: int = max_hp

    @property
    def desc(self) -> str:
        """Display description (matches POL's item.desc)."""
        return self.name

    def __repr__(self) -> str:
        return (
            f"Weapon(serial={self.serial}, name={self.name!r}, "
            f"damage={self.damage}, speed={self.speed})"
        )


class Armor(GameObject):
    """An armor piece with AR and body coverage.

    Parameters
    ----------
    ar:
        Armor rating value.
    coverage:
        List of body zones covered (e.g., ["Head", "Neck"]).
    """

    _polclasses = ("Item", "Armor")

    def __init__(
        self,
        *,
        objtype: int = 0,
        graphic: int | None = None,
        name: str = "",
        color: int = 0,
        ar: int = 0,
        coverage: list[str] | None = None,
        hp: int = 70,
        max_hp: int = 70,
        layer: int = 0,
    ) -> None:
        super().__init__(objtype=objtype, graphic=graphic, name=name, color=color)
        self.ar: int = ar
        self.coverage: list[str] = coverage or []
        self.hp: int = hp
        self.max_hp: int = max_hp
        self.layer: int = layer

    @property
    def desc(self) -> str:
        """Display description (matches POL's item.desc)."""
        return self.name

    def __repr__(self) -> str:
        return (
            f"Armor(serial={self.serial}, name={self.name!r}, "
            f"ar={self.ar}, coverage={self.coverage})"
        )
