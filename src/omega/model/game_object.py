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

    def isa(self, polclass: str) -> bool:
        """Check if this object matches a POLCLASS constant."""
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
