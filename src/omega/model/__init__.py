"""Game object model for the Omega combat simulator.

Public API::

    from omega.model import Mobile, Weapon, Armor, GameObject
    from omega.model import create_mobile_inline, create_mobile_from_template
    from omega.model import snapshot, restore
    from omega.model.constants import *
"""

from omega.model.factories import (
    create_armor_from_config,
    create_mobile_from_template,
    create_mobile_inline,
    create_weapon_from_config,
    equip_from_template,
    find_armor_by_name,
    find_weapon_by_name,
)
from omega.model.game_object import GameObject
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.model.snapshot import MobileSnapshot, restore, snapshot

__all__ = [
    "Armor",
    "GameObject",
    "Mobile",
    "MobileSnapshot",
    "Weapon",
    "create_armor_from_config",
    "create_mobile_from_template",
    "create_mobile_inline",
    "create_weapon_from_config",
    "equip_from_template",
    "find_armor_by_name",
    "find_weapon_by_name",
    "restore",
    "snapshot",
]
