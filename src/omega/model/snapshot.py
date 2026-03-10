"""State capture and restore for stateless simulation iterations.

Each combat hit in V1 is independent — state resets between iterations.
``snapshot()`` captures a mobile's full mutable state before a hit, and
``restore()`` resets it afterward so the next iteration starts clean.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile


@dataclass(frozen=True, slots=True)
class MobileSnapshot:
    """Frozen state of a mobile for reset between iterations."""

    hp: int
    max_hp: int
    mana: int
    max_mana: int
    stamina: int
    max_stamina: int
    dead: bool
    str_mod: int
    int_mod: int
    dex_mod: int
    properties: dict[str, Any]
    equipment_hp: dict[int, int]  # layer → item.hp


def snapshot(mobile: Mobile) -> MobileSnapshot:
    """Capture the mutable state of a mobile.

    Captures vitals, stat mods, property bag (deep copy), and
    equipment durability. Intrinsic fields like base stats and skills
    are not captured since they don't change during a hit.
    """
    equip_hp: dict[int, int] = {}
    for layer, item in mobile.list_equipment().items():
        equip_hp[layer] = item.hp

    return MobileSnapshot(
        hp=mobile.hp,
        max_hp=mobile.max_hp,
        mana=mobile.mana,
        max_mana=mobile.max_mana,
        stamina=mobile.stamina,
        max_stamina=mobile.max_stamina,
        dead=mobile.dead,
        str_mod=mobile.str_mod,
        int_mod=mobile.int_mod,
        dex_mod=mobile.dex_mod,
        properties=copy.deepcopy(mobile._properties),
        equipment_hp=equip_hp,
    )


def restore(mobile: Mobile, snap: MobileSnapshot) -> None:
    """Restore a mobile to a previously captured state.

    Resets vitals, stat mods, property bag, and equipment durability.
    """
    mobile.hp = snap.hp
    mobile.max_hp = snap.max_hp
    mobile.mana = snap.mana
    mobile.max_mana = snap.max_mana
    mobile.stamina = snap.stamina
    mobile.max_stamina = snap.max_stamina
    mobile.dead = snap.dead
    mobile.str_mod = snap.str_mod
    mobile.int_mod = snap.int_mod
    mobile.dex_mod = snap.dex_mod

    # Restore property bag (deep copy to avoid shared references)
    mobile._properties = copy.deepcopy(snap.properties)

    # Restore equipment HP
    for layer, hp_val in snap.equipment_hp.items():
        item = mobile.get_equipped(layer)
        if item is not None:
            item.hp = hp_val
