"""Creature type enum — canonical names for slayer/race-resistant types.

These are the ``Type`` values from hitscriptdesc.cfg (weapon slayers) and
onhitscriptdesc.cfg (armor race-resistant enchantments).  Both config files
use the same set of 17 creature types.

Using a ``str`` enum so that values pass straight through to
``set_property()`` / ``GetObjProperty()`` without conversion::

    from omega.config.creature_types import CreatureType

    weapon.set_property("SlayType", CreatureType.UNDEAD)
    # Equivalent to: weapon.set_property("SlayType", "Undead")

    armor.set_property("ProtectedType", CreatureType.DAEMON)
    # Equivalent to: armor.set_property("ProtectedType", "Daemon")
"""

from __future__ import annotations

from enum import Enum


class CreatureType(str, Enum):
    """Creature types used by slayer weapons and race-resistant armor.

    Each value is the exact string used in the shard config files and
    eScript ``GetObjProperty()`` / ``SetObjProperty()`` calls.
    """

    SLIME = "Slime"
    RATKIN = "Ratkin"
    PLANT = "Plant"
    ANIMAL = "Animal"
    BEHOLDER = "Beholder"
    ORC = "Orc"
    TERATHAN = "Terathan"
    OPHIDIAN = "Ophidian"
    ANIMATED = "Animated"
    GARGOYLE = "Gargoyle"
    TROLL = "Troll"
    GIANTKIN = "Giantkin"
    ELEMENTAL = "Elemental"
    UNDEAD = "Undead"
    DAEMON = "Daemon"
    DRAGONKIN = "Dragonkin"
    HUMAN = "Human"
