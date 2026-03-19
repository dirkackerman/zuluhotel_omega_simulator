"""Enchantment registry — parses hitscriptdesc.cfg into lookup tables.

Provides :class:`Enchantment` IntEnum for specifying weapon enchantments,
:class:`EnchantmentEntry` dataclasses with full metadata, and
:class:`EnchantmentRegistry` for lookup.

Usage::

    from omega.config.enchantments import Enchantment

    # Apply an enchantment to a weapon spec:
    WeaponSpec(damage="3d6+2").enchant_with(Enchantment.OF_DAEMONS_BREATH)

    # Registry for detailed metadata:
    registry = EnchantmentRegistry.from_cfg(Path("config/hitscriptdesc.cfg"))
    entry = registry.by_id(Enchantment.OF_DAEMONS_BREATH)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

from omega.config.cfg_parser import ConfigElement, parse_config_file
from omega.config.combat_scripts import CombatScript
from omega.config.creature_types import CreatureType
from omega.config.spells import Spell
from omega.logging import get_logger

logger = get_logger("omega.config.enchantments")


# ---------------------------------------------------------------------------
# Enchantment enum — named constants for hitscriptdesc.cfg IDs
# ---------------------------------------------------------------------------


class Enchantment(IntEnum):
    """Weapon enchantment IDs from hitscriptdesc.cfg.

    Each member corresponds to an enchantment that can be applied to a weapon.
    Use with :meth:`WeaponSpec.enchant_with` to configure a weapon::

        WeaponSpec(damage="3d6+2").enchant_with(Enchantment.OF_DAEMONS_BREATH)
        WeaponSpec(damage="1d20+35").enchant_with(Enchantment.SILVER)
    """

    # -- Spells (1-18) -- spellstrikescript enchantments
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

    # -- Slayers (19-35) -- slayerscript enchantments
    SLIME_SLAYER = 19
    RATKIN_SLAYER = 20
    PLANT_SLAYER = 21
    ANIMAL_SLAYER = 22
    BEHOLDER_SLAYER = 23
    ORC_SLAYER = 24
    TERATHAN_SLAYER = 25
    OPHIDIAN_SLAYER = 26
    BEWITCHED_SLAYER = 27     # Type: Animated
    GARGOYLE_SLAYER = 28
    TROLL_SLAYER = 29
    GIANT_SLAYER = 30         # Type: Giantkin
    ELEMENTAL_SLAYER = 31
    SILVER = 32               # Type: Undead
    HOLY = 33                 # Type: Daemon
    DRAGON_SLAYER = 34        # Type: Dragonkin
    ASSASSINS = 35            # Type: Human

    # -- Effects (36-42) -- various effect scripts
    OF_PIERCING = 36          # piercingscript
    BANISHING = 37            # banishscript
    POISONED = 38             # poisonhit
    BLOODY = 39               # lifedrainscript
    VAMPIRIC = 40             # manadrainscript
    LEECH = 41                # staminadrainscript
    BLINDING = 42             # blindingscript

    # -- Greaters (43-45) -- greater enchantment scripts
    OF_PLANAR_FURY = 43       # dualplanarscript
    OF_THE_VOID = 44          # voidscript
    OF_ELEMENTAL_FURY = 45    # trielementalscript


# Maps Enchantment ID → (hitscript_path, weapon_properties).
# Source: hitscriptdesc.cfg — kept in sync via sync_fixtures.py.
#
# Notes on what each enchantment type defines:
# - Spells: only HitWithSpell (the spell ID). EffectCircle and ChanceOfEffect
#   are per-weapon customisations set separately.
# - Slayers: SlayType (the CProp name read by slayerscript).
# - Effects/Greaters: CProp + value where defined in the cfg.
_ENCHANTMENT_META: dict[int, tuple[str, dict[str, Any]]] = {
    # Spells — spellstrikescript + HitWithSpell only
    1:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.CLUMSY}),
    2:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.FEEBLEMIND}),
    3:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.MAGIC_ARROW}),
    4:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.WEAKEN}),
    5:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.HARM}),
    6:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.FIREBALL}),
    7:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.CURSE}),
    8:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.LIGHTNING}),
    9:  (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.MANA_DRAIN}),
    10: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.MIND_BLAST}),
    11: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.PARALYZE}),
    12: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.ENERGY_BOLT}),
    13: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.EXPLOSION}),
    14: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.MASS_CURSE}),
    15: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.CHAIN_LIGHTNING}),
    16: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.FLAME_STRIKE}),
    17: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.METEOR_SWARM}),
    18: (CombatScript.SPELLSTRIKESCRIPT, {"HitWithSpell": Spell.EARTHQUAKE}),
    # Slayers — slayerscript + SlayType
    19: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.SLIME}),
    20: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.RATKIN}),
    21: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.PLANT}),
    22: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.ANIMAL}),
    23: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.BEHOLDER}),
    24: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.ORC}),
    25: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.TERATHAN}),
    26: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.OPHIDIAN}),
    27: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.ANIMATED}),
    28: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.GARGOYLE}),
    29: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.TROLL}),
    30: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.GIANTKIN}),
    31: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.ELEMENTAL}),
    32: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.UNDEAD}),
    33: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.DAEMON}),
    34: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.DRAGONKIN}),
    35: (CombatScript.SLAYERSCRIPT, {"SlayType": CreatureType.HUMAN}),
    # Effects
    36: (CombatScript.PIERCINGSCRIPT, {}),
    37: (CombatScript.BANISHSCRIPT, {}),
    38: (CombatScript.POISONHIT, {"Poisonlvl": 0}),
    39: (CombatScript.LIFEDRAINSCRIPT, {}),
    40: (CombatScript.MANADRAINSCRIPT, {}),
    41: (CombatScript.STAMINADRAINSCRIPT, {}),
    42: (CombatScript.BLINDINGSCRIPT, {"ChanceOfEffect": 10}),
    # Greaters
    43: (CombatScript.DUALPLANARSCRIPT, {"ChanceOfEffect": 7}),
    44: (CombatScript.VOIDSCRIPT, {}),
    45: (CombatScript.TRIELEMENTALSCRIPT, {"ChanceOfEffect": 7}),
}


def enchantment_hitscript(enchantment: Enchantment) -> str:
    """Return the hitscript package path for an enchantment."""
    return _ENCHANTMENT_META[int(enchantment)][0]


def enchantment_properties(enchantment: Enchantment) -> dict[str, Any]:
    """Return the weapon CProps for an enchantment."""
    return dict(_ENCHANTMENT_META[int(enchantment)][1])


@dataclass(frozen=True)
class EnchantmentEntry:
    """A single enchantment parsed from hitscriptdesc.cfg."""

    id: int
    hitscript_type: str  # "Spell", "Slayer", "Effect", "Greater"
    hitscript: str  # package path, e.g. CombatScript.SPELLSTRIKESCRIPT
    name: str  # display name, e.g. "of Daemon's Breath"
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

    # Slayer-specific
    slayer_type: str = ""

    # Effect/Greater CProp and multiplier
    cprop: str = ""
    multiplier: float = 0.0

    @property
    def weapon_properties(self) -> dict[str, Any]:
        """Return the properties that should be set on a weapon for this enchantment.

        These are the CProps the shard scripts read from the weapon at runtime.
        Note: ``EffectCircle`` and ``ChanceOfEffect`` for spell enchantments
        are per-weapon customisations, not part of the enchantment definition.
        """
        props: dict[str, Any] = {}

        if self.hitscript_type == "Spell":
            props["HitWithSpell"] = self.spell_id
        elif self.hitscript_type == "Slayer":
            props["SlayType"] = self.slayer_type
        elif self.hitscript_type in ("Effect", "Greater"):
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


def _parse_entry(elem: ConfigElement, entry_id: int) -> EnchantmentEntry:
    """Parse a single Enchantment block into an EnchantmentEntry."""
    color_str = elem.get("Color", "").strip()
    ccolor_str = elem.get("CColor", "").strip()

    # The cfg parser intercepts "CProp <Name>" lines and stores them as
    # cprops.  In hitscriptdesc.cfg, "CProp ChanceOfEffect" means the
    # enchantment's weapon property is named "ChanceOfEffect".  We
    # extract the first cprop name as the property name.
    cprop_name = ""
    cprops = elem.cprops
    if cprops:
        cprop_name = next(iter(cprops))

    return EnchantmentEntry(
        id=entry_id,
        hitscript_type=elem.get("HitscriptType", ""),
        hitscript=elem.get("Hitscript", ""),
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
        slayer_type=elem.get("Type", ""),
        cprop=cprop_name,
        multiplier=elem.get_float("Multiplier"),
    )


class EnchantmentRegistry:
    """Lookup table of enchantments from hitscriptdesc.cfg.

    An empty registry (no entries) is valid — :meth:`find` just returns None.
    """

    def __init__(self, entries: list[EnchantmentEntry] | None = None) -> None:
        self._by_id: dict[int, EnchantmentEntry] = {}
        self._by_lower: dict[str, EnchantmentEntry] = {}
        for entry in entries or []:
            self._by_id[entry.id] = entry
            # Index by several name variants for flexible lookup
            self._by_lower[entry.name.lower().strip()] = entry
            self._by_lower[entry.clean_name.lower().strip()] = entry
            if entry.spell_name:
                self._by_lower[entry.spell_name.lower().strip()] = entry
            if entry.slayer_type:
                self._by_lower[entry.slayer_type.lower().strip()] = entry

    @classmethod
    def from_cfg(cls, path: Path) -> EnchantmentRegistry:
        """Parse a hitscriptdesc.cfg file into a registry."""
        cfg = parse_config_file(path)
        entries: list[EnchantmentEntry] = []
        for elem in cfg:
            if elem.block_type != "Enchantment":
                continue
            try:
                entry_id = int(elem.name)
            except ValueError:
                continue
            entries.append(_parse_entry(elem, entry_id))
        logger.debug("loaded enchantment registry", count=len(entries), path=str(path))
        return cls(entries)

    def by_id(self, enchantment_id: int) -> EnchantmentEntry | None:
        """Look up an enchantment by its numeric ID."""
        return self._by_id.get(enchantment_id)

    def find(self, query: str) -> EnchantmentEntry | None:
        """Find an enchantment by name, spell name, ID, or display name.

        Matching is case-insensitive.  Tries (in order):
        1. Numeric ID (e.g. ``"6"``)
        2. Exact name match (e.g. ``"of Daemon's Breath"``)
        3. Clean name match (e.g. ``"Daemon's Breath"``)
        4. Spell name match (e.g. ``"Fireball"``)
        5. Slayer type match (e.g. ``"Undead"``)
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

    def all_entries(self) -> list[EnchantmentEntry]:
        """Return all entries sorted by ID."""
        return sorted(self._by_id.values(), key=lambda e: e.id)

    def by_type(self, hitscript_type: str) -> list[EnchantmentEntry]:
        """Return all entries of a given type (Spell, Slayer, Effect, Greater)."""
        return [e for e in self._by_id.values() if e.hitscript_type == hitscript_type]

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"EnchantmentRegistry(entries={len(self._by_id)})"
