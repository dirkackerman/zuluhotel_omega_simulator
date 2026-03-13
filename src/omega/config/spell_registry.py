"""Spell registry — parses spells.cfg and circles.cfg into lookup tables.

Provides :class:`CircleConfig` and :class:`SpellEntry` frozen dataclasses,
:data:`DAMAGE_SPELL_IDS` constant, and :class:`SpellRegistry` for lookup.

Usage::

    from omega.config.spell_registry import SpellRegistry, DAMAGE_SPELL_IDS
    from omega.config.spells import Spell

    registry = SpellRegistry.from_cfg(
        spell_cfg_paths=[(Path("pkg/std/spells/spells.cfg"), "Standard"), ...],
        circles_path=Path("config/circles.cfg"),
    )
    entry = registry.by_id(Spell.FIREBALL)
    circle = registry.circle(3)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omega.config.cfg_parser import ConfigElement, parse_config_file
from omega.config.spells import Spell
from omega.logging import get_logger

logger = get_logger("omega.config.spell_registry")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CircleConfig:
    """A single circle parsed from circles.cfg."""

    circle: int
    mana: int
    difficulty: int
    point_value: int
    delay: int
    use_circle: int = 0  # 0 = no remapping


@dataclass(frozen=True)
class SpellEntry:
    """A single spell parsed from spells.cfg."""

    id: int
    name: str
    script: str  # bare script name from cfg (e.g., "fireball")
    circle: int
    power_words: str
    reagents: tuple[str, ...]
    school: str  # "Standard", "Necromancy", "Earth", "Holy", "Song"
    point_value: int = 0


# ---------------------------------------------------------------------------
# Spell ID sets
# ---------------------------------------------------------------------------

# CASTABLE_SPELL_IDS — all 29 spells with executable scripts in the V3 set.
# Includes non-damage spells (buffs, debuffs, CC) that have scripts we can run.
CASTABLE_SPELL_IDS: frozenset[Spell] = frozenset({
    # Standard (11)
    Spell.MAGIC_ARROW, Spell.HARM, Spell.FIREBALL, Spell.LIGHTNING,
    Spell.MIND_BLAST, Spell.ENERGY_BOLT, Spell.EXPLOSION,
    Spell.CHAIN_LIGHTNING, Spell.FLAME_STRIKE, Spell.METEOR_SWARM,
    Spell.EARTHQUAKE,
    # Necromancy (8)
    Spell.DECAYING_RAY, Spell.SPECTRES_TOUCH, Spell.ABYSSAL_FLAME,
    Spell.SACRIFICE, Spell.WRAITHS_BREATH, Spell.SORCERERS_BANE,
    Spell.WYVERN_STRIKE, Spell.KILL,
    # Earth (5)
    Spell.SHIFTING_EARTH, Spell.CALL_LIGHTNING, Spell.GUST_OF_AIR,
    Spell.RISING_FIRE, Spell.ICE_STRIKE,
    # Holy (5)
    Spell.HOLY_BOLT, Spell.WRATH_OF_GOD, Spell.DIVINE_FURY,
    Spell.ASTRAL_STORM, Spell.APOCALYPSE,
})

# NON_DAMAGE_SPELL_IDS — spells in CASTABLE_SPELL_IDS that don't deal direct
# damage.  Decaying Ray is an AR debuff, Wraith's Breath is paralysis/CC,
# Sacrifice is a pet sacrifice mechanic.
NON_DAMAGE_SPELL_IDS: frozenset[Spell] = frozenset({
    Spell.DECAYING_RAY,
    Spell.WRAITHS_BREATH,
    Spell.SACRIFICE,
})

# DAMAGE_SPELL_IDS — the 26 spells that deal direct damage (used for damage
# analysis).  Excludes the 3 non-damage spells above.
DAMAGE_SPELL_IDS: frozenset[Spell] = CASTABLE_SPELL_IDS - NON_DAMAGE_SPELL_IDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_ci(elem: ConfigElement, *keys: str) -> str | None:
    """Case-insensitive config element lookup, trying multiple key variants."""
    for key in keys:
        val = elem.get(key)
        if val is not None:
            return val
    return None


def _get_int_ci(elem: ConfigElement, *keys: str, default: int = 0) -> int:
    """Case-insensitive integer config element lookup."""
    val = _get_ci(elem, *keys)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_circle(elem: ConfigElement, circle_num: int) -> CircleConfig:
    """Parse a single Circle block from circles.cfg."""
    return CircleConfig(
        circle=circle_num,
        mana=elem.get_int("Mana"),
        difficulty=elem.get_int("Difficulty"),
        point_value=_get_int_ci(elem, "PointValue", "Pointvalue"),
        delay=elem.get_int("Delay"),
        use_circle=_get_int_ci(elem, "UseCircle"),
    )


def _parse_spell(elem: ConfigElement, block_id: int, school: str) -> SpellEntry:
    """Parse a single Spell block from spells.cfg."""
    spell_id = _get_int_ci(elem, "SpellId", "SpellID", default=block_id)
    reagents = tuple(r.strip() for r in elem.get_all("Reagent") if r.strip())
    return SpellEntry(
        id=spell_id,
        name=elem.get("Name", "") or "",
        script=elem.get("Script", "") or "",
        circle=elem.get_int("Circle"),
        power_words=_get_ci(elem, "PowerWords", "Powerwords") or "",
        reagents=reagents,
        school=school,
        point_value=_get_int_ci(elem, "PointValue", "Pointvalue"),
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class SpellRegistry:
    """Lookup table of spells and circles from shard config files.

    An empty registry (no entries) is valid — :meth:`by_id` just returns None.
    """

    def __init__(
        self,
        spells: list[SpellEntry] | None = None,
        circles: list[CircleConfig] | None = None,
    ) -> None:
        self._by_id: dict[int, SpellEntry] = {}
        self._by_lower: dict[str, SpellEntry] = {}
        self._circles: dict[int, CircleConfig] = {}

        for entry in spells or []:
            self._by_id[entry.id] = entry
            if entry.name:
                self._by_lower[entry.name.lower().strip()] = entry

        for circ in circles or []:
            self._circles[circ.circle] = circ

    @classmethod
    def from_cfg(
        cls,
        spell_cfg_paths: list[tuple[Path, str]],
        circles_path: Path,
    ) -> SpellRegistry:
        """Parse spells.cfg files + circles.cfg into a registry.

        Parameters
        ----------
        spell_cfg_paths:
            List of ``(path, school_name)`` tuples — one per spells.cfg file.
        circles_path:
            Path to ``circles.cfg``.
        """
        # Parse circles
        circles: list[CircleConfig] = []
        cfg = parse_config_file(circles_path)
        for elem in cfg:
            if elem.block_type != "Circle":
                continue
            try:
                circle_num = int(elem.name)
            except ValueError:
                continue
            circles.append(_parse_circle(elem, circle_num))
        logger.debug("loaded circles", count=len(circles), path=str(circles_path))

        # Parse spells from each cfg
        spells: list[SpellEntry] = []
        for path, school in spell_cfg_paths:
            cfg = parse_config_file(path)
            for elem in cfg:
                if elem.block_type != "Spell":
                    continue
                try:
                    block_id = int(elem.name)
                except ValueError:
                    continue
                spells.append(_parse_spell(elem, block_id, school))
            logger.debug("loaded spells", school=school, count=len([s for s in spells if s.school == school]), path=str(path))

        return cls(spells=spells, circles=circles)

    def by_id(self, spell_id: int) -> SpellEntry | None:
        """Look up a spell by its numeric ID (or Spell enum member)."""
        return self._by_id.get(spell_id)

    def find(self, query: str) -> SpellEntry | None:
        """Find a spell by name or numeric ID string.

        Matching is case-insensitive. Tries numeric ID first, then name.
        """
        try:
            entry_id = int(query)
            entry = self._by_id.get(entry_id)
            if entry is not None:
                return entry
        except ValueError:
            pass
        return self._by_lower.get(query.lower().strip())

    def circle(self, circle_num: int) -> CircleConfig | None:
        """Look up a circle by its number."""
        return self._circles.get(circle_num)

    def effective_circle(self, circle_num: int) -> int:
        """Resolve UseCircle remapping.

        If the circle has ``use_circle > 0``, returns that value.
        Otherwise returns ``circle_num`` unchanged.
        """
        circ = self._circles.get(circle_num)
        if circ and circ.use_circle > 0:
            return circ.use_circle
        return circle_num

    def damage_spells(self) -> list[SpellEntry]:
        """Return all damage-dealing spells, sorted by ID."""
        return sorted(
            (e for e in self._by_id.values() if e.id in DAMAGE_SPELL_IDS),
            key=lambda e: e.id,
        )

    def by_school(self, school: str) -> list[SpellEntry]:
        """Return all spells for a school, sorted by ID."""
        return sorted(
            (e for e in self._by_id.values() if e.school == school),
            key=lambda e: e.id,
        )

    def all_entries(self) -> list[SpellEntry]:
        """Return all spell entries sorted by ID."""
        return sorted(self._by_id.values(), key=lambda e: e.id)

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"SpellRegistry(spells={len(self._by_id)}, circles={len(self._circles)})"
