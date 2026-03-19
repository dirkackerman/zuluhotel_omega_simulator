"""Armor enchantment registry — parses onhitscriptdesc.cfg into lookup tables.

Provides :class:`ArmorEnchantment` IntEnum for specifying armor enchantments,
:class:`ArmorEnchantmentEntry` dataclasses with full metadata, and
:class:`ArmorEnchantmentRegistry` for lookup.

Usage::

    from omega.config.armor_enchantments import ArmorEnchantment

    # Apply an enchantment to an armor spec:
    ArmorSpec(ar=30).enchant_with(ArmorEnchantment.OF_BUNGLING)

    # Registry for detailed metadata:
    registry = ArmorEnchantmentRegistry.from_cfg(Path("config/onhitscriptdesc.cfg"))
    entry = registry.by_id(ArmorEnchantment.OF_BUNGLING)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

from omega.config.cfg_parser import ConfigElement, parse_config_file
from omega.config.combat_scripts import CombatScript
from omega.config.creature_types import CreatureType
from omega.config.spells import Spell
from omega.logging import get_logger

logger = get_logger("omega.config.armor_enchantments")


# ---------------------------------------------------------------------------
# ArmorEnchantment enum — named constants for onhitscriptdesc.cfg IDs
# ---------------------------------------------------------------------------


class ArmorEnchantment(IntEnum):
    """Armor enchantment IDs from onhitscriptdesc.cfg.

    Each member corresponds to an enchantment that can be applied to armor.
    Use with :meth:`ArmorSpec.enchant_with` to configure armor::

        ArmorSpec(ar=30).enchant_with(ArmorEnchantment.OF_BUNGLING)
        ArmorSpec(ar=20).enchant_with(ArmorEnchantment.UNDEAD_HUNTER)
    """

    # -- Spells (1-18) -- spellonhit enchantments
    OF_BUNGLING = 1           # Clumsy
    OF_SENILITY = 2           # Feeblemind
    OF_BURNING = 3            # Magic Arrow
    OF_WEAKENING = 4          # Weaken
    OF_WOUNDING = 5           # Harm
    OF_DAEMONS_BREATH = 6     # Fireball
    OF_EVIL = 7               # Curse
    OF_THUNDER = 8            # Lightning
    OF_MAGES_BANE = 9         # Mana Drain
    OF_MENTAL_STRIKE = 10     # Mind Blast
    OF_ENTRAPMENT = 11        # Paralyze
    OF_DISRUPTION = 12        # Energy Bolt
    OF_CONFLAGRATION = 13     # Explosion
    OF_CORRUPTION = 14        # Mass Curse
    OF_HEAVENS_WRATH = 15     # Chain Lightning
    OF_HELLFIRE = 16          # Flame Strike
    OF_CELESTIAL_FURY = 17    # Meteor Swarm
    OF_GAIAS_WRATH = 18       # Earthquake

    # -- Race-Resistant (19-35) -- raceresistonhit enchantments
    SLIME_HUNTER = 19
    RAT_HUNTER = 20
    PLANT_HUNTER = 21
    ANIMAL_HUNTER = 22
    BEHOLDER_HUNTER = 23
    ORC_HUNTER = 24
    TERATHAN_HUNTER = 25
    OPHIDIAN_HUNTER = 26
    BEWITCHED_HUNTER = 27     # Type: Animated
    GARGOYLE_HUNTER = 28
    TROLL_HUNTER = 29
    GIANT_HUNTER = 30         # Type: Giantkin
    ELEMENTAL_HUNTER = 31
    UNDEAD_HUNTER = 32
    DAEMON_HUNTER = 33
    DRAGON_HUNTER = 34        # Type: Dragonkin
    BOUNTY_HUNTER = 35        # Type: Human

    # -- Effects (36-42) -- various effect scripts
    REINFORCED = 36           # piercingonhit
    SUNDERING = 37            # banishonhit
    VENOMOUS = 38             # poisononhit
    DISPLACING = 39           # bouncingonhit
    BLACKROCK_STUDDED = 40    # manadrainonhit
    STICKY = 41               # staminadrainonhit
    BLINDINGLY_BRIGHT = 42    # blindingonhit

    # -- Greaters (43-47) -- greater enchantment scripts
    OF_ELEMENTAL_FURY = 43    # trielementalonhit
    SHIFTING = 44             # deflectiononhit
    AVENGING = 45             # avengingonhit
    SHADOWS_CLOAK = 46        # invisibleonhit
    WINDS_BREATH = 47         # dualplanaronhit


# Maps ArmorEnchantment ID → (onhitscript_path, armor_properties).
# Source: onhitscriptdesc.cfg — kept in sync via sync_fixtures.py.
#
# Notes on what each enchantment type defines:
# - Spells: only HitWithSpell (the spell ID). EffectCircle and ChanceOfEffect
#   are per-armor customisations set separately.
# - Race-Resistant: ProtectedType (the race matched by raceresistonhit).
# - Effects/Greaters: CProp + value where defined in the cfg.
_ARMOR_ENCHANTMENT_META: dict[int, tuple[str, dict[str, Any]]] = {
    # Spells — spellonhit + HitWithSpell only
    1:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.CLUMSY}),
    2:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.FEEBLEMIND}),
    3:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.MAGIC_ARROW}),
    4:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.WEAKEN}),
    5:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.HARM}),
    6:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.FIREBALL}),
    7:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.CURSE}),
    8:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.LIGHTNING}),
    9:  (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.MANA_DRAIN}),
    10: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.MIND_BLAST}),
    11: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.PARALYZE}),
    12: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.ENERGY_BOLT}),
    13: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.EXPLOSION}),
    14: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.MASS_CURSE}),
    15: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.CHAIN_LIGHTNING}),
    16: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.FLAME_STRIKE}),
    17: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.METEOR_SWARM}),
    18: (CombatScript.SPELLONHIT, {"HitWithSpell": Spell.EARTHQUAKE}),
    # Race-Resistant — raceresistonhit + ProtectedType
    19: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.SLIME}),
    20: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.RATKIN}),
    21: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.PLANT}),
    22: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.ANIMAL}),
    23: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.BEHOLDER}),
    24: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.ORC}),
    25: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.TERATHAN}),
    26: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.OPHIDIAN}),
    27: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.ANIMATED}),
    28: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.GARGOYLE}),
    29: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.TROLL}),
    30: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.GIANTKIN}),
    31: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.ELEMENTAL}),
    32: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.UNDEAD}),
    33: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.DAEMON}),
    34: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.DRAGONKIN}),
    35: (CombatScript.RACERESISTONHIT, {"ProtectedType": CreatureType.HUMAN}),
    # Effects
    36: (CombatScript.PIERCINGONHIT, {}),
    37: (CombatScript.BANISHONHIT, {}),
    38: (CombatScript.POISONONHIT, {"Poisonlvl": 0}),
    39: (CombatScript.BOUNCINGONHIT, {"ChanceOfEffect": 10}),
    40: (CombatScript.MANADRAINONHIT, {}),
    41: (CombatScript.STAMINADRAINONHIT, {}),
    42: (CombatScript.BLINDINGONHIT, {"ChanceOfEffect": 10}),
    # Greaters
    43: (CombatScript.TRIELEMENTALONHIT, {"ChanceOfEffect": 7}),
    44: (CombatScript.DEFLECTIONONHIT, {"ChanceOfEffect": 5}),
    45: (CombatScript.AVENGINGONHIT, {"Powerlevel": 10}),
    46: (CombatScript.INVISIBLEONHIT, {"ChanceOfEffect": 5}),
    47: (CombatScript.DUALPLANARONHIT, {"ChanceOfEffect": 6}),
}


def armor_enchantment_onhitscript(enchantment: ArmorEnchantment) -> str:
    """Return the OnHitScript package path for an armor enchantment."""
    return _ARMOR_ENCHANTMENT_META[int(enchantment)][0]


def armor_enchantment_properties(enchantment: ArmorEnchantment) -> dict[str, Any]:
    """Return the armor CProps for an enchantment."""
    return dict(_ARMOR_ENCHANTMENT_META[int(enchantment)][1])


@dataclass(frozen=True)
class ArmorEnchantmentEntry:
    """A single enchantment parsed from onhitscriptdesc.cfg."""

    id: int
    onhitscript_type: str  # "Spell", "RaceResistant", "Effect", "Greater"
    onhitscript: str  # package path, e.g. CombatScript.SPELLONHIT
    name: str  # display name, e.g. "of Bungling"
    cursed_name: str = ""
    color: int = 0
    cursed_color: int = 0
    place: int = 0  # 1=prefix, 2=suffix

    # Spell-specific fields
    spell_id: int = 0
    spell_name: str = ""
    spell_script: str = ""
    as_circle_mod: int = 0
    chance_of_effect_mod: int = 0

    # Race-Resistant specific
    race_type: str = ""

    # Effect/Greater CProp and multiplier
    cprop: str = ""
    multiplier: float = 0.0

    @property
    def armor_properties(self) -> dict[str, Any]:
        """Return the properties that should be set on armor for this enchantment.

        These are the CProps the shard scripts read from the armor at runtime.
        Note: ``EffectCircle`` and ``ChanceOfEffect`` for spell enchantments
        are per-armor customisations, not part of the enchantment definition.
        """
        props: dict[str, Any] = {}

        if self.onhitscript_type == "Spell":
            props["HitWithSpell"] = self.spell_id
        elif self.onhitscript_type == "RaceResistant":
            props["ProtectedType"] = self.race_type
        elif self.onhitscript_type in ("Effect", "Greater"):
            if self.cprop:
                props[self.cprop] = int(self.multiplier) if self.multiplier else 1

        return props

    @property
    def clean_name(self) -> str:
        """Display name with 'of ' prefix stripped for matching."""
        n = self.name.strip()
        if n.lower().startswith("of "):
            return n[3:]
        return n


def _parse_entry(elem: ConfigElement, entry_id: int) -> ArmorEnchantmentEntry:
    """Parse a single Enchantment block from onhitscriptdesc.cfg."""
    color_str = elem.get("Color", "").strip()
    ccolor_str = elem.get("CColor", "").strip()

    cprop_name = ""
    cprops = elem.cprops
    if cprops:
        cprop_name = next(iter(cprops))

    return ArmorEnchantmentEntry(
        id=entry_id,
        onhitscript_type=elem.get("OnHitscriptType", ""),
        onhitscript=elem.get("OnHitscript", ""),
        name=elem.get("Name", ""),
        cursed_name=elem.get("CName", ""),
        color=int(color_str) if color_str else 0,
        cursed_color=int(ccolor_str) if ccolor_str else 0,
        place=elem.get_int("Place"),
        spell_id=elem.get_int("Spellid"),
        spell_name=elem.get("SpellName", ""),
        spell_script=elem.get("Script", ""),
        as_circle_mod=elem.get_int("AsCircleMod"),
        chance_of_effect_mod=elem.get_int("ChanceofEffectMod"),
        race_type=elem.get("Type", ""),
        cprop=cprop_name,
        multiplier=elem.get_float("Multiplier"),
    )


class ArmorEnchantmentRegistry:
    """Lookup table of armor enchantments from onhitscriptdesc.cfg.

    An empty registry (no entries) is valid — :meth:`find` just returns None.
    """

    def __init__(self, entries: list[ArmorEnchantmentEntry] | None = None) -> None:
        self._by_id: dict[int, ArmorEnchantmentEntry] = {}
        self._by_lower: dict[str, ArmorEnchantmentEntry] = {}
        for entry in entries or []:
            self._by_id[entry.id] = entry
            # Index by several name variants for flexible lookup
            self._by_lower[entry.name.lower().strip()] = entry
            self._by_lower[entry.clean_name.lower().strip()] = entry
            if entry.spell_name:
                self._by_lower[entry.spell_name.lower().strip()] = entry
            if entry.race_type:
                self._by_lower[entry.race_type.lower().strip()] = entry

    @classmethod
    def from_cfg(cls, path: Path) -> ArmorEnchantmentRegistry:
        """Parse an onhitscriptdesc.cfg file into a registry."""
        cfg = parse_config_file(path)
        entries: list[ArmorEnchantmentEntry] = []
        for elem in cfg:
            if elem.block_type != "Enchantment":
                continue
            try:
                entry_id = int(elem.name)
            except ValueError:
                continue
            entries.append(_parse_entry(elem, entry_id))
        logger.debug("loaded armor enchantment registry", count=len(entries), path=str(path))
        return cls(entries)

    def by_id(self, enchantment_id: int) -> ArmorEnchantmentEntry | None:
        """Look up an enchantment by its numeric ID."""
        return self._by_id.get(enchantment_id)

    def find(self, query: str) -> ArmorEnchantmentEntry | None:
        """Find an enchantment by name, spell name, ID, or display name.

        Matching is case-insensitive.  Tries (in order):
        1. Numeric ID (e.g. ``"6"``)
        2. Exact name match (e.g. ``"of Daemon's Breath"``)
        3. Clean name match (e.g. ``"Daemon's Breath"``)
        4. Spell name match (e.g. ``"Fireball"``)
        5. Race type match (e.g. ``"Undead"``)
        """
        # Try numeric ID
        try:
            entry_id = int(query)
            entry = self._by_id.get(entry_id)
            if entry is not None:
                return entry
        except ValueError:
            pass

        return self._by_lower.get(query.lower().strip())

    def all_entries(self) -> list[ArmorEnchantmentEntry]:
        """Return all entries sorted by ID."""
        return sorted(self._by_id.values(), key=lambda e: e.id)

    def by_type(self, onhitscript_type: str) -> list[ArmorEnchantmentEntry]:
        """Return all entries of a given type (Spell, RaceResistant, Effect, Greater)."""
        return [e for e in self._by_id.values() if e.onhitscript_type == onhitscript_type]

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"ArmorEnchantmentRegistry(entries={len(self._by_id)})"
