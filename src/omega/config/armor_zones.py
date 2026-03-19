"""Armor zone configuration — POL-conformant probabilistic armor selection.

Parses ``armrzone.cfg`` and provides :meth:`ArmorZoneConfig.choose_armor` to
select one armor piece per combat hit, matching POL's ``Character::choose_armor()``
in ``charactr.cpp:3198``.

POL selects which armor piece is hit using weighted random zone selection.
Each zone covers one or more equipment layers.  For each zone, the highest-AR
piece among equipped items in that zone's layers is the representative piece.
At hit time, a zone is drawn randomly, and that zone's representative piece
is passed to the hitscript as the ``armor`` parameter.

The shard's ``config/armrzone.cfg`` defines 6 zones::

    Body        44%   layers 13, 20, 22, 5, 17
    Arms        14%   layer 19
    Head        14%   layer 6
    Legs/feet   14%   layers 4, 3, 24
    Neck         7%   layer 10
    Hands        7%   layer 7

Usage::

    from omega.config.armor_zones import ArmorZoneConfig

    zones = ArmorZoneConfig.from_cfg(Path("config/armrzone.cfg"))
    armor = zones.choose_armor(defender, rng)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from omega.logging import get_logger
from omega.model.items import Armor

if TYPE_CHECKING:
    from omega.model.mobile import Mobile
    from omega.runtime.rng import SimulationRNG

logger = get_logger("omega.config.armor_zones")


@dataclass(frozen=True)
class ArmorZone:
    """A single armor zone from armrzone.cfg."""

    name: str
    chance: float  # probability weight (0.0–1.0), e.g. 0.44 for Body
    layers: tuple[int, ...]  # equipment layer IDs in this zone


@dataclass
class ArmorZoneConfig:
    """Armor zone hit probability table.

    Loaded from ``armrzone.cfg``.  Provides :meth:`choose_armor` to select
    one armor piece per hit using POL's exact algorithm.
    """

    zones: list[ArmorZone] = field(default_factory=list)
    chance_sum: float = 0.0

    @classmethod
    def from_cfg(cls, path: Path) -> ArmorZoneConfig:
        """Parse an armrzone.cfg file.

        POL loads ``Chance`` as ``ushort / 100.0`` (charactr.cpp:236).
        """
        text = path.read_text(encoding="utf-8", errors="replace")

        zones: list[ArmorZone] = []
        chance_sum = 0.0

        # Parse block format: ArmorZone <id> { ... }
        in_block = False
        name = ""
        chance_raw = 0
        layers: list[int] = []

        for line in text.splitlines():
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("//"):
                continue

            # Block start
            if stripped.startswith("ArmorZone"):
                in_block = False  # reset any previous incomplete block
                name = ""
                chance_raw = 0
                layers = []
                continue

            if stripped == "{":
                in_block = True
                continue

            if stripped == "}":
                if in_block and name:
                    chance = chance_raw / 100.0
                    zones.append(ArmorZone(
                        name=name,
                        chance=chance,
                        layers=tuple(layers),
                    ))
                    chance_sum += chance
                in_block = False
                continue

            if not in_block:
                continue

            # Parse key-value inside block
            m = re.match(r'^\s*(\w+)\s+(.*)', stripped)
            if not m:
                continue

            key = m.group(1)
            val = m.group(2).strip()

            if key == "Name":
                name = val
            elif key == "Chance":
                try:
                    chance_raw = int(val)
                except ValueError:
                    pass
            elif key == "Layer":
                try:
                    layers.append(int(val))
                except ValueError:
                    pass

        config = cls(zones=zones, chance_sum=chance_sum)
        logger.debug(
            "loaded armor zones",
            zone_count=len(zones),
            chance_sum=f"{chance_sum:.2f}",
            path=str(path),
        )
        return config

    def choose_armor(self, mobile: Mobile, rng: SimulationRNG) -> Armor | None:
        """Select one armor piece using POL's zone probability algorithm.

        Matches ``Character::choose_armor()`` in ``charactr.cpp:3198-3210``::

            double f = random_double(armor_zone_chance_sum);
            for (zone in armorzones) {
                f -= zone.chance;
                if (f <= 0.0) return armor_[zone];
            }
            return nullptr;

        For each zone, the highest-AR piece among equipped items in that
        zone's layers is selected (matching POL's ``refresh_ar()``).

        Returns None if no armor covers the selected zone.
        """
        if not self.zones or self.chance_sum <= 0.0:
            return None

        # Build zone → best armor piece mapping
        # POL does this in refresh_ar() during equip; we do it per-hit
        # since equipment doesn't change between hits in V1.
        zone_armor: list[Armor | None] = []
        for zone in self.zones:
            best: Armor | None = None
            for layer in zone.layers:
                item = mobile.get_equipped(layer)
                if isinstance(item, Armor):
                    if best is None or item.ar > best.ar:
                        best = item
            zone_armor.append(best)

        # POL: random_double(chance_sum) — uniform in [0, chance_sum)
        f = rng.random_float() * self.chance_sum
        for i, zone in enumerate(self.zones):
            f -= zone.chance
            if f <= 0.0:
                return zone_armor[i]

        return None
