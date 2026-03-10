"""Base game object with property bag and type checking.

POL game objects have two distinct property systems:
1. **Intrinsic fields** — accessed via member syntax (``obj.name``, ``obj.serial``)
2. **Property bag** — accessed via ``GetObjProperty(obj, "name")`` / ``SetObjProperty()``

This module provides the base class with the property bag and ``.isa()`` support.
Subclasses add their own intrinsic fields as regular Python attributes.
"""

from __future__ import annotations

import itertools
from typing import Any

from omega.logging import get_logger

logger = get_logger("omega.model")

_serial_counter = itertools.count(1)


class GameObject:
    """Base POL game object.

    Parameters
    ----------
    objtype:
        Hex object type (e.g., 0x13BB for ChainmailCoif).
    graphic:
        Visual graphic ID. Defaults to objtype if not provided.
    name:
        Display name.
    color:
        Display color (0 = default).
    """

    _polclasses: tuple[str, ...] = ("Item",)

    def __init__(
        self,
        *,
        objtype: int = 0,
        graphic: int | None = None,
        name: str = "",
        color: int = 0,
    ) -> None:
        self.serial: int = next(_serial_counter)
        self.objtype: int = objtype
        self.graphic: int = graphic if graphic is not None else objtype
        self.name: str = name
        self.color: int = color
        self._properties: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Property bag (GetObjProperty / SetObjProperty / EraseObjProperty)
    # ------------------------------------------------------------------

    def get_property(self, name: str) -> Any:
        """Get a custom property value, or ``None`` if not set."""
        return self._properties.get(name)

    def set_property(self, name: str, value: Any) -> None:
        """Set a custom property value."""
        self._properties[name] = value

    def erase_property(self, name: str) -> bool:
        """Erase a custom property. Returns True if it existed."""
        try:
            del self._properties[name]
            return True
        except KeyError:
            return False

    def has_property(self, name: str) -> bool:
        """Check if a custom property exists."""
        return name in self._properties

    # ------------------------------------------------------------------
    # Type checking (.isa / .IsA)
    # ------------------------------------------------------------------

    # Integer POLCLASS constant → string name mapping
    _POLCLASS_INT_MAP: dict[int, str] = {
        1: "UObject",
        2: "Item",
        3: "Mobile",
        4: "NPC",
        5: "Lockable",
        6: "Container",
        7: "Corpse",
        8: "Door",
        9: "Spellbook",
        10: "Map",
        11: "Multi",
        12: "Boat",
        13: "House",
        14: "Equipment",
        15: "Armor",
        16: "Weapon",
    }

    def isa(self, polclass: str | int) -> bool:
        """Check if this object matches a POLCLASS constant.

        Accepts both string names ("Mobile", "NPC") and integer constants
        (3 for POLCLASS_MOBILE, 4 for POLCLASS_NPC, etc.).
        """
        if isinstance(polclass, int):
            name = self._POLCLASS_INT_MAP.get(polclass)
            if name is None:
                return False
            return name in self._polclasses
        return polclass in self._polclasses

    # Alias matching eScript's case-insensitive method name
    IsA = isa

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(serial={self.serial}, "
            f"objtype=0x{self.objtype:04X}, name={self.name!r})"
        )
