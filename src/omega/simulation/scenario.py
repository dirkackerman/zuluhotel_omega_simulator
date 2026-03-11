"""Scenario definitions for combat simulation.

Declarative dataclasses describing *what* to simulate — combatants,
weapons, armor, iteration counts, and parameter sweeps.  The runner
(``runner.py``) materialises these specs into live game objects and
executes the simulation.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from omega.config.dice import DiceSpec, parse_dice
from omega.model.constants import LAYER_CHEST, LAYER_HAND1, SKILLID_SWORDSMANSHIP
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile


# ---------------------------------------------------------------------------
# Spec dataclasses (immutable descriptions)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeaponSpec:
    """Declarative weapon description."""

    name: str = "Weapon"
    damage: str = "3d6+2"
    speed: int = 50
    attribute: int = SKILLID_SWORDSMANSHIP
    two_handed: bool = False
    quality: float = 1.0
    hp: int = 50
    max_hp: int = 50
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArmorSpec:
    """Declarative armor description."""

    name: str = "Armor"
    ar: int = 0
    coverage: tuple[str, ...] = ()
    hp: int = 70
    max_hp: int = 70
    layer: int = 0
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CombatantSpec:
    """Defines a combatant either inline or by NPC template reference.

    If ``npc_template`` is set, the inline fields are ignored and the
    combatant is resolved from shard config files instead.
    """

    name: str = "Combatant"
    is_npc: bool = False
    str_: int = 100
    int_: int = 25
    dex_: int = 100
    hp: int | None = None
    mana: int | None = None
    stamina: int | None = None
    skills: dict[int, int] = field(default_factory=dict)
    class_levels: dict[str, int] = field(default_factory=dict)
    weapon: WeaponSpec | None = None
    armor: ArmorSpec | None = None
    npc_template: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Scenario:
    """A single simulation scenario — attacker vs defender for N hits."""

    attacker: CombatantSpec
    defender: CombatantSpec
    iterations: int = 1000
    base_seed: int = 0
    debug_mode: bool = False


@dataclass(frozen=True)
class Variable:
    """A parameter to sweep across multiple values.

    ``target`` is ``"attacker"`` or ``"defender"``.
    ``parameter`` is a dotted path like ``"skills.40"`` or ``"str_"``.
    """

    target: str
    parameter: str
    values: tuple[Any, ...] = ()

    @classmethod
    def from_range(
        cls,
        target: str,
        parameter: str,
        start: int,
        stop: int,
        step: int = 1,
    ) -> Variable:
        """Create a variable from a numeric range (stop is inclusive)."""
        return cls(
            target=target,
            parameter=parameter,
            values=tuple(range(start, stop + 1, step)),
        )


@dataclass(frozen=True)
class ParameterSweep:
    """A scenario with one or more swept variables.

    The simulation grid is the Cartesian product of all variable value
    lists.
    """

    scenario: Scenario
    variables: tuple[Variable, ...] = ()


# ---------------------------------------------------------------------------
# Materialization — specs → game objects
# ---------------------------------------------------------------------------


def build_weapon(spec: WeaponSpec) -> Weapon:
    """Create a :class:`Weapon` from a :class:`WeaponSpec`."""
    w = Weapon(
        name=spec.name,
        damage=parse_dice(spec.damage),
        speed=spec.speed,
        attribute=spec.attribute,
        two_handed=spec.two_handed,
        quality=spec.quality,
        hp=spec.hp,
        max_hp=spec.max_hp,
    )
    for k, v in spec.properties.items():
        w.set_property(k, v)
    return w


def build_armor(spec: ArmorSpec) -> Armor:
    """Create an :class:`Armor` from an :class:`ArmorSpec`."""
    a = Armor(
        name=spec.name,
        ar=spec.ar,
        coverage=list(spec.coverage),
        hp=spec.hp,
        max_hp=spec.max_hp,
        layer=spec.layer,
    )
    for k, v in spec.properties.items():
        a.set_property(k, v)
    return a


def build_combatant(spec: CombatantSpec) -> tuple[Mobile, Weapon, Armor]:
    """Build a Mobile, Weapon, and Armor from a :class:`CombatantSpec`.

    Returns ``(mobile, weapon, armor)`` ready for ``execute_hit()``.
    """
    mob = Mobile(name=spec.name, is_npc=spec.is_npc)
    mob.str_base = spec.str_
    mob.int_base = spec.int_
    mob.dex_base = spec.dex_

    # Vitals — default to stat-derived values if not explicitly set
    mob.hp = spec.hp if spec.hp is not None else spec.str_ * 2
    mob.max_hp = mob.hp
    mob.mana = spec.mana if spec.mana is not None else spec.int_
    mob.max_mana = mob.mana
    mob.stamina = spec.stamina if spec.stamina is not None else spec.dex_
    mob.max_stamina = mob.stamina

    # Skills (display value → internal value: multiply by 10)
    for skill_id, display_val in spec.skills.items():
        mob.set_skill(skill_id, display_val * 10)

    # Class levels stored as object properties (eScript reads via GetObjProperty)
    for class_id, level in spec.class_levels.items():
        mob.set_property(class_id, level)

    # Mobile-level properties (e.g., ReactiveArmor)
    for k, v in spec.properties.items():
        mob.set_property(k, v)

    # Weapon
    weapon = build_weapon(spec.weapon) if spec.weapon is not None else Weapon(name="Fist")
    mob.equip(LAYER_HAND1, weapon)

    # Armor — equip on the mobile so defender.ar works in shard scripts
    armor = build_armor(spec.armor) if spec.armor is not None else Armor(name="None", ar=0)
    armor_layer = spec.armor.layer if spec.armor is not None and spec.armor.layer else LAYER_CHEST
    mob.equip(armor_layer, armor)

    return mob, weapon, armor


# ---------------------------------------------------------------------------
# Variable application
# ---------------------------------------------------------------------------


def apply_variable(spec: CombatantSpec, parameter: str, value: Any) -> CombatantSpec:
    """Return a new CombatantSpec with one parameter changed.

    Supported parameter paths:
    - ``"str_"``, ``"int_"``, ``"dex_"`` — base stats
    - ``"hp"``, ``"mana"``, ``"stamina"`` — vitals
    - ``"skills.<skill_id>"`` — a specific skill (display value)
    - ``"class_levels.<class_id>"`` — a class level
    - ``"weapon.<field>"`` — weapon spec field
    - ``"armor.<field>"`` — armor spec field
    """
    parts = parameter.split(".", 1)
    field_name = parts[0]

    # Direct stat/vital fields
    if field_name in ("str_", "int_", "dex_", "hp", "mana", "stamina"):
        return dataclasses.replace(spec, **{field_name: int(value)})

    if field_name == "is_npc":
        return dataclasses.replace(spec, is_npc=bool(value))

    if field_name == "name":
        return dataclasses.replace(spec, name=str(value))

    # Nested dict fields
    if field_name == "skills" and len(parts) == 2:
        skill_id = int(parts[1])
        new_skills = dict(spec.skills)
        new_skills[skill_id] = int(value)
        return dataclasses.replace(spec, skills=new_skills)

    if field_name == "class_levels" and len(parts) == 2:
        class_id = parts[1]
        new_levels = dict(spec.class_levels)
        new_levels[class_id] = int(value)
        return dataclasses.replace(spec, class_levels=new_levels)

    # Nested weapon spec
    if field_name == "weapon" and len(parts) == 2:
        sub_field = parts[1]
        base = spec.weapon or WeaponSpec()
        return dataclasses.replace(spec, weapon=dataclasses.replace(base, **{sub_field: value}))

    # Nested armor spec
    if field_name == "armor" and len(parts) == 2:
        sub_field = parts[1]
        base = spec.armor or ArmorSpec()
        return dataclasses.replace(spec, armor=dataclasses.replace(base, **{sub_field: value}))

    # Mobile properties (e.g., ReactiveArmor)
    if field_name == "properties" and len(parts) == 2:
        prop_name = parts[1]
        new_props = dict(spec.properties)
        new_props[prop_name] = value
        return dataclasses.replace(spec, properties=new_props)

    raise ValueError(f"Unknown variable parameter: {parameter!r}")
