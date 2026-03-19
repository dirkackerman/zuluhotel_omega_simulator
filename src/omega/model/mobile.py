"""Mobile game object — players and NPCs.

A Mobile has stats (STR/INT/DEX), vitals (HP/Mana/Stamina), skills,
equipment slots, and class levels stored in the property bag.

eScript accesses mobiles via:
- Member access: ``mob.ar``, ``mob.dead``, ``mob.npctemplate``
- Stat functions: ``GetStrength(mob)``, ``GetDexterity(mob)``
- Skills: ``GetEffectiveSkill(mob, SKILLID_SWORDSMANSHIP)``
- Property bag: ``GetObjProperty(mob, "IsWarrior")``
- Equipment: ``GetEquipmentByLayer(mob, LAYER_HAND1)``
"""

from __future__ import annotations

from typing import Any

from omega.model.constants import (
    LAYER_HAND1,
    LAYER_HAND2,
    POLCLASS_MOBILE,
    POLCLASS_NPC,
    SKILLID__HIGHEST,
    SKILLID_TO_ATTRIBUTE,
)
from omega.model.game_object import GameObject
from omega.model.items import Armor, Weapon

def _wrestling_weapon() -> Weapon:
    """Create a fresh wrestling weapon (POL's intrinsic_weapon).

    Returns a new instance each time to avoid shared mutable state.
    """
    return Weapon(name="Wrestling", attribute="Wrestling", speed=35)


class Mobile(GameObject):
    """A mobile (player or NPC) with stats, skills, vitals, and equipment.

    Parameters
    ----------
    is_npc:
        Whether this is an NPC (vs a player character).
    npctemplate:
        NPC template name from npcdesc.cfg (e.g., "nazgul"), or empty.
    """

    @property
    def _polclasses(self) -> tuple[str, ...]:  # type: ignore[override]
        if self.is_npc:
            return (POLCLASS_MOBILE, POLCLASS_NPC)
        return (POLCLASS_MOBILE,)

    def __init__(
        self,
        *,
        objtype: int = 0x0190,
        graphic: int | None = None,
        name: str = "",
        color: int = 0,
        is_npc: bool = False,
        npctemplate: str = "",
    ) -> None:
        super().__init__(objtype=objtype, graphic=graphic, name=name, color=color)
        self.is_npc: bool = is_npc
        self.npctemplate: str = npctemplate
        self.cmdlevel: int = 0
        self.dead: bool = False
        self.hidden: bool = False
        self.paralyzed: bool = False
        self.frozen: bool = False
        self.master: Any = None

        # World position (used by banishscript etc.)
        self.x: int = 0
        self.y: int = 0
        self.z: int = 0
        self.realm: str = "britannia"

        # Swing timer modifiers
        self.delay_mod: int = 0
        """Delay modifier in milliseconds (for delay-based weapons only).

        Added to ``weapon.delay`` in POL's delay-based swing timer path
        (``charactr.cpp:2855``).  Can be negative.
        """

        # Base stats
        self.str_base: int = 10
        self.int_base: int = 10
        self.dex_base: int = 10

        # Stat mods (temporary + intrinsic, in tenths like POL)
        self.str_mod: int = 0
        self.int_mod: int = 0
        self.dex_mod: int = 0

        # Vitals
        self.hp: int = 10
        self.max_hp: int = 10
        self.mana: int = 10
        self.max_mana: int = 10
        self.stamina: int = 10
        self.max_stamina: int = 10

        # Skills: skill_id → base value (0-2000 internal, /10 for display)
        self._skills: dict[int, int] = {}

        # Equipment: layer → item
        self._equipment: dict[int, Weapon | Armor] = {}

        # Per-instance wrestling weapon cache (avoids creating new objects
        # on repeated .weapon access for unarmed mobiles)
        self._cached_wrestling: Weapon | None = None

    # ------------------------------------------------------------------
    # Stats (effective = base + mod/10, matching POL)
    # ------------------------------------------------------------------

    @property
    def strength(self) -> int:
        return self.str_base + self.str_mod // 10

    @property
    def intelligence(self) -> int:
        return self.int_base + self.int_mod // 10

    @property
    def dexterity(self) -> int:
        return self.dex_base + self.dex_mod // 10

    # ------------------------------------------------------------------
    # Swing speed
    # ------------------------------------------------------------------

    @property
    def swing_speed_increase(self) -> int:
        """Total SwingSpeedIncrease in hundredths (summed from mobile + equipment).

        POL sums ``swing_speed_increase()`` across the character and all
        equipped items (``charactr.cpp:2867``).  The value is in hundredths:
        a value of 25 means 25% faster (modifier = 25/100 = 0.25).
        """
        total = 0
        # Mobile's own SwingSpeedIncrease property
        own = self._properties.get("SwingSpeedIncrease")
        if own is not None:
            try:
                total += int(own)
            except (TypeError, ValueError):
                pass
        # Sum from all equipped items' SwingSpeedIncrease properties
        for item in self._equipment.values():
            item_ssi = item.get_property("SwingSpeedIncrease")
            if item_ssi is not None:
                try:
                    total += int(item_ssi)
                except (TypeError, ValueError):
                    pass
        return total

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def get_skill(self, skill_id: int) -> int:
        """Get raw skill value (internal representation, 0-2000)."""
        return self._skills.get(skill_id, 0)

    def set_skill(self, skill_id: int, value: int) -> None:
        """Set raw skill value."""
        self._skills[skill_id] = value

    def get_effective_skill(self, skill_id: int) -> int:
        """Get effective skill value in display units (0-200).

        This is the base value divided by 10, matching POL's
        ``GetEffectiveSkill`` which returns tenths.
        """
        return self._skills.get(skill_id, 0) // 10

    def get_attribute(self, attribute_name: str) -> int:
        """Get attribute by string name (for GetAttribute() calls).

        Handles both stat names ("strength", "dexterity", "intelligence")
        and skill names ("Swordsmanship", "Tactics", etc.).
        Returns value in tenths (matching POL precision).
        """
        lower = attribute_name.lower()
        if lower == "strength":
            return self.str_base * 10 + self.str_mod
        if lower == "dexterity":
            return self.dex_base * 10 + self.dex_mod
        if lower == "intelligence":
            return self.int_base * 10 + self.int_mod

        # Skill lookup by attribute name
        from omega.model.constants import ATTRIBUTE_TO_SKILLID

        skill_id = ATTRIBUTE_TO_SKILLID.get(lower)
        if skill_id is not None:
            return self._skills.get(skill_id, 0)

        return 0

    # ------------------------------------------------------------------
    # Equipment
    # ------------------------------------------------------------------

    def equip(self, layer: int, item: Weapon | Armor) -> None:
        """Equip an item to a layer slot."""
        self._equipment[layer] = item
        # Invalidate cached wrestling weapon if hand slot changed
        if layer in (LAYER_HAND1, LAYER_HAND2):
            self._cached_wrestling = None

    def unequip(self, layer: int) -> Weapon | Armor | None:
        """Remove and return the item at a layer, or None."""
        item = self._equipment.pop(layer, None)
        if layer in (LAYER_HAND1, LAYER_HAND2):
            self._cached_wrestling = None
        return item

    def get_equipped(self, layer: int) -> Weapon | Armor | None:
        """Get the item equipped at a layer, or None."""
        return self._equipment.get(layer)

    def list_equipment(self) -> dict[int, Weapon | Armor]:
        """Return all equipped items by layer."""
        return dict(self._equipment)

    @property
    def weapon(self) -> Weapon:
        """The weapon in LAYER_HAND1 or LAYER_HAND2, or wrestling if unarmed.

        Matches POL's ``character.weapon`` member: checks both hand slots
        (``charactr.cpp:1399-1402``).  LAYER_HAND1 is checked first.
        Unarmed characters get the intrinsic wrestling weapon
        (``intrinsic_weapon()`` → ``gamestate.wrestling_weapon`` in POL).
        """
        item = self._equipment.get(LAYER_HAND1)
        if isinstance(item, Weapon):
            return item
        item = self._equipment.get(LAYER_HAND2)
        if isinstance(item, Weapon):
            return item
        # Cache per-instance to avoid creating new objects on repeated access
        if self._cached_wrestling is None:
            self._cached_wrestling = _wrestling_weapon()
        return self._cached_wrestling

    @property
    def ar(self) -> int:
        """Total armor rating from all equipped armor pieces."""
        total = 0
        for item in self._equipment.values():
            if isinstance(item, Armor):
                total += item.ar
        return total

    # ------------------------------------------------------------------
    # Visual effects (no-op in simulation)
    # ------------------------------------------------------------------

    def setlightlevel(self, level: int = 0, duration: int = 0) -> None:
        """Set light level on mobile (no-op — visual only)."""
        pass

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        kind = "NPC" if self.is_npc else "Player"
        return (
            f"Mobile({kind}, serial={self.serial}, name={self.name!r}, "
            f"STR={self.strength}/INT={self.intelligence}/DEX={self.dexterity})"
        )
