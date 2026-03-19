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

from omega.config.cfg_parser import ConfigFile
from omega.config.dice import DiceSpec, parse_dice
from omega.config.combat_scripts import CombatScript  # noqa: F401 — used in docstrings
from omega.config.armor_enchantments import (
    ArmorEnchantment,
    ArmorEnchantmentRegistry,
    armor_enchantment_onhitscript,
    armor_enchantment_properties,
)
from omega.config.enchantments import (
    Enchantment,
    EnchantmentRegistry,
    enchantment_hitscript,
    enchantment_properties,
)
from omega.model.constants import LAYER_CHEST, LAYER_HAND1, SKILLID_SWORDSMANSHIP
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile


# ---------------------------------------------------------------------------
# Spec dataclasses (immutable descriptions)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeaponSpec:
    """Declarative weapon description.

    Use :meth:`enchant_with` to apply a hitscriptdesc.cfg enchantment::

        WeaponSpec(damage="3d6+2").enchant_with(Enchantment.OF_DAEMONS_BREATH)

    Or set ``hitscript`` and ``properties`` directly for full control::

        WeaponSpec(
            hitscript=CombatScript.SPELLSTRIKESCRIPT,
            properties={"HitWithSpell": Spell.ANGELIC_AURA, "EffectCircle": 9},
        )
    """

    name: str = "Weapon"
    damage: str = "3d6+2"
    speed: int = 50
    delay: int = 0
    attribute: int | str = SKILLID_SWORDSMANSHIP
    two_handed: bool = False
    quality: float = 1.0
    hp: int = 50
    max_hp: int = 50
    hitscript: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, name: str, itemdesc: ConfigFile) -> WeaponSpec:
        """Create a WeaponSpec by looking up a weapon in itemdesc.cfg.

        Parameters
        ----------
        name:
            The ``Name`` property value (e.g., ``"KatanaOfKieri"``) or hex
            objtype (e.g., ``"0x757d"``).
        itemdesc:
            Parsed itemdesc.cfg (from :meth:`ShardData.get_config` or
            :func:`parse_config_file`).

        Raises
        ------
        KeyError
            If no weapon with the given name/objtype is found.

        Example::

            itemdesc = shard.get_config("itemdesc")
            katana = WeaponSpec.from_config("KatanaOfKieri", itemdesc)
        """
        from omega.model.factories import create_weapon_from_config

        # Try by Name property first, then by block key (objtype string)
        elem = itemdesc.find_by_name(name)
        if elem is None:
            elem = itemdesc[name]
        if elem is None or getattr(elem, "block_type", None) != "Weapon":
            raise KeyError(f"Weapon {name!r} not found in itemdesc")

        w = create_weapon_from_config(elem)
        return cls(
            name=w.name,
            damage=str(w.damage),
            speed=w.speed,
            delay=w.delay,
            attribute=w.attribute,
            two_handed=w.two_handed,
            quality=w.quality,
            hp=w.hp,
            max_hp=w.max_hp,
            hitscript=w.hitscript,
            properties={k: v for k, v in w._properties.items()},
        )

    def enchant_with(self, enchantment: Enchantment) -> WeaponSpec:
        """Return a new WeaponSpec with the given enchantment applied.

        Sets ``hitscript`` and merges the enchantment's weapon properties
        into ``properties``.  Existing properties take precedence (so you
        can override defaults like ``EffectCircle`` or ``ChanceOfEffect``
        before or after calling this method).
        """
        hs = enchantment_hitscript(enchantment)
        props = enchantment_properties(enchantment)
        # Enchantment defaults first, then existing properties override
        merged = {**props, **self.properties}
        return dataclasses.replace(self, hitscript=hs, properties=merged)


@dataclass(frozen=True)
class ArmorSpec:
    """Declarative armor description.

    Use :meth:`enchant_with` to apply an onhitscriptdesc.cfg enchantment::

        ArmorSpec(ar=30).enchant_with(ArmorEnchantment.OF_BUNGLING)

    Or set ``onhitscript`` and ``properties`` directly for full control::

        ArmorSpec(
            ar=30,
            onhitscript=CombatScript.SPELLONHIT,
            properties={"HitWithSpell": 18, "EffectCircle": 5, "ChanceOfEffect": 30},
        )
    """

    name: str = "Armor"
    ar: int = 0
    coverage: tuple[str, ...] = ()
    hp: int = 70
    max_hp: int = 70
    layer: int = 0
    onhitscript: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, name: str, itemdesc: ConfigFile) -> ArmorSpec:
        """Create an ArmorSpec by looking up armor in itemdesc.cfg.

        Parameters
        ----------
        name:
            The ``Name`` property value or hex objtype string.
        itemdesc:
            Parsed itemdesc.cfg.

        Raises
        ------
        KeyError
            If no armor with the given name/objtype is found.
        """
        from omega.model.factories import create_armor_from_config

        elem = itemdesc.find_by_name(name)
        if elem is None:
            elem = itemdesc[name]
        if elem is None or getattr(elem, "block_type", None) != "Armor":
            raise KeyError(f"Armor {name!r} not found in itemdesc")

        a = create_armor_from_config(elem)
        return cls(
            name=a.name,
            ar=a.ar,
            coverage=tuple(a.coverage),
            hp=a.hp,
            max_hp=a.max_hp,
            layer=a.layer,
            properties={k: v for k, v in a._properties.items()},
        )

    def enchant_with(self, enchantment: ArmorEnchantment) -> ArmorSpec:
        """Return a new ArmorSpec with the given armor enchantment applied.

        Sets ``onhitscript`` and merges the enchantment's armor properties
        into ``properties``.  Existing properties take precedence (so you
        can override defaults like ``EffectCircle`` or ``ChanceOfEffect``
        before or after calling this method).
        """
        hs = armor_enchantment_onhitscript(enchantment)
        props = armor_enchantment_properties(enchantment)
        # Enchantment defaults first, then existing properties override
        merged = {**props, **self.properties}
        return dataclasses.replace(self, onhitscript=hs, properties=merged)


@dataclass(frozen=True)
class CombatantSpec:
    """Defines a combatant with stats, skills, and equipment.

    Two creation paths:

    - **Inline**: Set fields directly (``str_``, ``skills``, ``weapon``, etc.).
    - **From config**: Use :meth:`from_config` to populate all fields from
      an NPC template in npcdesc.cfg (resolves equipment chain automatically).

    Both produce a fully self-contained, frozen spec that :func:`build_combatant`
    materialises into game objects without needing config files.

    Armor priority: if ``armor_pieces`` is populated (from :meth:`from_config`),
    individual pieces are equipped to their layers and ``armor`` is ignored.
    If only ``armor`` is set (inline specs), it is used as a single piece.
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
    armor_pieces: dict[int, ArmorSpec] = field(default_factory=dict)
    npc_template: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(
        cls,
        template_name: str,
        npcdesc: ConfigFile,
        equip_cfg: ConfigFile,
        itemdesc: ConfigFile,
    ) -> CombatantSpec:
        """Create a CombatantSpec from an NPC template in npcdesc.cfg.

        Resolves the full equipment chain (npcdesc → equip → itemdesc) and
        extracts all stats, skills, equipment, and properties into an
        immutable spec.

        Parameters
        ----------
        template_name:
            NPC template name (e.g., ``"nazgul"``) from npcdesc.cfg.
        npcdesc:
            Parsed npcdesc.cfg.
        equip_cfg:
            Parsed equip.cfg.
        itemdesc:
            Parsed itemdesc.cfg (combat package).

        Raises
        ------
        ValueError
            If the template is not found.

        Example::

            shard = ShardData.from_path(shard_root)
            npcdesc = shard.get_config("npcdesc")
            equip = shard.get_config("equip")
            itemdesc = shard.get_config("itemdesc")
            orc = CombatantSpec.from_config("orc", npcdesc, equip, itemdesc)
        """
        from omega.model.constants import ALL_CLASS_IDS, LAYER_HAND1
        from omega.model.factories import create_mobile_from_template
        from omega.model.items import Armor as ArmorObj
        from omega.model.items import Weapon as WeaponObj

        mob = create_mobile_from_template(template_name, npcdesc, equip_cfg, itemdesc)

        # Extract skills (internal → display: divide by 10)
        skills = {sid: val // 10 for sid, val in mob._skills.items() if val > 0}

        # Extract class levels from properties
        class_levels = {}
        for cid in ALL_CLASS_IDS:
            lvl = mob.get_property(cid)
            if lvl is not None:
                class_levels[cid] = int(lvl)

        # Extract weapon
        weapon_spec: WeaponSpec | None = None
        hand1 = mob.get_equipped(LAYER_HAND1)
        if isinstance(hand1, WeaponObj):
            weapon_spec = WeaponSpec(
                name=hand1.name,
                damage=str(hand1.damage),
                speed=hand1.speed,
                delay=hand1.delay,
                attribute=hand1.attribute,
                two_handed=hand1.two_handed,
                quality=hand1.quality,
                hp=hand1.hp,
                max_hp=hand1.max_hp,
                hitscript=hand1.hitscript,
                properties={k: v for k, v in hand1._properties.items()},
            )

        # Extract armor — preserve individual pieces for zone-based selection,
        # and also create an aggregated ArmorSpec for backwards compatibility.
        armor_spec: ArmorSpec | None = None
        armor_pieces: dict[int, ArmorSpec] = {}
        total_ar = 0
        all_coverage: list[str] = []
        armor_props: dict[str, Any] = {}
        armor_count = 0
        for layer, item in mob.list_equipment().items():
            if isinstance(item, ArmorObj):
                total_ar += item.ar
                all_coverage.extend(item.coverage)
                armor_props.update(item._properties)
                armor_count += 1
                armor_pieces[layer] = ArmorSpec(
                    name=item.name,
                    ar=item.ar,
                    coverage=tuple(item.coverage),
                    hp=item.hp,
                    max_hp=item.max_hp,
                    layer=layer,
                    properties={k: v for k, v in item._properties.items()},
                )
        if armor_count > 0:
            armor_spec = ArmorSpec(
                name=f"{mob.name}_armor",
                ar=total_ar,
                coverage=tuple(all_coverage),
                properties=armor_props,
            )

        # Extract non-class properties
        mob_props = {}
        for k, v in mob._properties.items():
            if k not in ALL_CLASS_IDS:
                mob_props[k] = v

        return cls(
            name=mob.name,
            is_npc=True,
            str_=mob.str_base,
            int_=mob.int_base,
            dex_=mob.dex_base,
            hp=mob.max_hp,
            mana=mob.max_mana,
            stamina=mob.max_stamina,
            skills=skills,
            class_levels=class_levels,
            weapon=weapon_spec,
            armor=armor_spec,
            armor_pieces=armor_pieces,
            npc_template=template_name,
            properties=mob_props,
        )


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


@dataclass(frozen=True)
class SpellScenario:
    """A spell simulation scenario — caster vs target(s) for N casts.

    Variable targets for sweeps use ``"caster"`` and ``"target"``
    (mapped to ``caster`` and ``target`` fields respectively).
    """

    caster: CombatantSpec
    target: CombatantSpec | list[CombatantSpec]
    spell_id: int
    iterations: int = 1000
    base_seed: int = 0
    debug_mode: bool = False
    npc_mode: bool = False
    circle_override: int = 0


@dataclass(frozen=True)
class SpellParameterSweep:
    """A spell scenario with one or more swept variables.

    Variable targets: ``"caster"`` applies to the caster spec,
    ``"target"`` applies to the target spec(s), ``"spell"`` with
    ``parameter="spell_id"`` sweeps across spell IDs.
    """

    scenario: SpellScenario
    variables: tuple[Variable, ...] = ()


# ---------------------------------------------------------------------------
# Materialization — specs → game objects
# ---------------------------------------------------------------------------


def build_weapon(
    spec: WeaponSpec,
    *,
    enchantment_registry: EnchantmentRegistry | None = None,
) -> Weapon:
    """Create a :class:`Weapon` from a :class:`WeaponSpec`.

    If ``spec.hitscript`` is set, the weapon is configured with the
    enchantment.  If it looks like a package path (starts with ``:``) it
    is used directly.  Otherwise it is treated as an enchantment name and
    resolved via *enchantment_registry*.
    """
    w = Weapon(
        name=spec.name,
        damage=parse_dice(spec.damage),
        speed=spec.speed,
        delay=spec.delay,
        attribute=spec.attribute,
        two_handed=spec.two_handed,
        quality=spec.quality,
        hp=spec.hp,
        max_hp=spec.max_hp,
    )
    for k, v in spec.properties.items():
        w.set_property(k, v)

    # Enchantment configuration
    if spec.hitscript is not None:
        if spec.hitscript.startswith(":"):
            # Raw package path — just set the hitscript
            w.hitscript = spec.hitscript
        else:
            # Enchantment name — resolve via registry
            registry = enchantment_registry or EnchantmentRegistry()
            entry = registry.find(spec.hitscript)
            if entry is not None:
                w.hitscript = entry.hitscript
                for pk, pv in entry.weapon_properties.items():
                    w.set_property(pk, pv)
            else:
                raise ValueError(
                    f"Unknown enchantment name: {spec.hitscript!r}. "
                    f"Use a package path (e.g. ':combat:spellstrikescript') "
                    f"or load an EnchantmentRegistry from hitscriptdesc.cfg."
                )
    return w


def build_armor(
    spec: ArmorSpec,
    *,
    armor_enchantment_registry: ArmorEnchantmentRegistry | None = None,
) -> Armor:
    """Create an :class:`Armor` from an :class:`ArmorSpec`.

    If ``spec.onhitscript`` is set, the armor is configured with the
    enchantment.  If it looks like a package path (starts with ``:``) it
    is used directly.  Otherwise it is treated as an enchantment name and
    resolved via *armor_enchantment_registry*.
    """
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

    # Armor enchantment configuration
    if spec.onhitscript is not None:
        if spec.onhitscript.startswith(":"):
            # Raw package path — set directly as OnHitScript property
            a.set_property("OnHitScript", spec.onhitscript)
        else:
            # Enchantment name — resolve via registry
            registry = armor_enchantment_registry or ArmorEnchantmentRegistry()
            entry = registry.find(spec.onhitscript)
            if entry is not None:
                a.set_property("OnHitScript", entry.onhitscript)
                for pk, pv in entry.armor_properties.items():
                    a.set_property(pk, pv)
            else:
                raise ValueError(
                    f"Unknown armor enchantment name: {spec.onhitscript!r}. "
                    f"Use a package path (e.g. ':combat:spellonhit') "
                    f"or load an ArmorEnchantmentRegistry from onhitscriptdesc.cfg."
                )
    return a


def build_combatant(
    spec: CombatantSpec,
    *,
    enchantment_registry: EnchantmentRegistry | None = None,
    armor_enchantment_registry: ArmorEnchantmentRegistry | None = None,
) -> tuple[Mobile, Weapon, Armor]:
    """Build a Mobile, Weapon, and Armor from a :class:`CombatantSpec`.

    Returns ``(mobile, weapon, armor)`` ready for ``execute_hit()``.
    """
    mob = Mobile(
        name=spec.name,
        is_npc=spec.is_npc,
        npctemplate=spec.npc_template or (spec.name if spec.is_npc else ""),
    )
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

    # Weapon — only equip if specified.  In POL, bare hands means no item
    # in LAYER_HAND1, so GetEquipmentByLayer returns nothing and TryToCast's
    # BlocksCastingIfInHand check is skipped entirely.
    if spec.weapon is not None:
        weapon = build_weapon(spec.weapon, enchantment_registry=enchantment_registry)
        mob.equip(LAYER_HAND1, weapon)
    else:
        weapon = Weapon(name="Fist")

    # Armor — equip individual pieces if available (for zone-based selection),
    # otherwise fall back to the single aggregated ArmorSpec.
    if spec.armor_pieces:
        # Multi-piece: equip each piece to its layer.  The ``armor`` return
        # value is a placeholder — actual selection happens per-hit via
        # ArmorZoneConfig.choose_armor() in execute_hit().
        first_armor: Armor | None = None
        for layer, aspec in spec.armor_pieces.items():
            piece = build_armor(aspec, armor_enchantment_registry=armor_enchantment_registry)
            mob.equip(layer, piece)
            if first_armor is None:
                first_armor = piece
        armor = first_armor or Armor(name="None", ar=0)
    elif spec.armor is not None:
        armor = build_armor(spec.armor, armor_enchantment_registry=armor_enchantment_registry)
        armor_layer = spec.armor.layer if spec.armor.layer else LAYER_CHEST
        mob.equip(armor_layer, armor)
    else:
        armor = Armor(name="None", ar=0)

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
