"""Combat hit execution — run mainhit.src through the interpreter.

This is the main integration point between the shard's eScript combat
scripts and the Python simulation engine.

Usage::

    from omega.combat import execute_hit
    from omega.shard import ShardData

    shard = ShardData.from_path(Path("submodules/zuluhotel_omega_2.5"))
    result = execute_hit(shard, attacker, defender, weapon, armor)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omega.combat.damage import roll_base_damage
from omega.combat.result import HitResult
from omega.combat.timing import calculate_swing_delay
from omega.interpreter.executor import Executor
from omega.interpreter.types import EStruct
from omega.logging import get_logger
from omega.model.constants import LAYER_HAND1, SKILLID_WRESTLING
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.parser.parser import ParseResult
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.rng import SimulationRNG, set_rng_seed

logger = get_logger("omega.combat")


def _weapon_skill(mobile: Mobile, weapon: Weapon | None = None) -> int:
    """Get a mobile's effective skill for their weapon, in display units (0-200).

    POL's ``weapon_attribute()`` returns the effective skill in the weapon's
    primary attribute.  If the mobile has no weapon, Wrestling is used.
    """
    if weapon is None:
        equipped = mobile.get_equipped(LAYER_HAND1)
        if isinstance(equipped, Weapon) and equipped.attribute:
            return mobile.get_effective_skill(equipped.attribute)
        return mobile.get_effective_skill(SKILLID_WRESTLING)
    if weapon.attribute:
        return mobile.get_effective_skill(weapon.attribute)
    return mobile.get_effective_skill(SKILLID_WRESTLING)


def check_hit(
    attacker: Mobile,
    defender: Mobile,
    weapon: Weapon,
    rng: SimulationRNG,
) -> bool:
    """POL-style hit check: does this swing connect?

    Formula (from ``Character::attack()`` in polserver)::

        hit_chance = (attacker_skill + 50) / (2 * (defender_skill + 50))

    Returns True if the attack hits, False if it misses.
    """
    atk_skill = _weapon_skill(attacker, weapon)
    def_skill = _weapon_skill(defender)

    hit_chance = (atk_skill + 50.0) / (2.0 * (def_skill + 50.0))

    # Clamp to [0, 1] — POL doesn't clamp but values outside are fine with
    # the random check (always hit if >= 1, always miss if <= 0).
    roll = rng.random_float()
    return roll < hit_chance


def execute_hit(
    parse_results: dict[Path, ParseResult],
    attacker: Mobile,
    defender: Mobile,
    weapon: Weapon,
    armor: Armor,
    *,
    base_damage: int | None = None,
    rng_seed: int = 0,
    debug: bool = False,
    config_resolver: Any = None,
    em_modules_dir: Path | None = None,
    executor: Executor | None = None,
    shard_root: Path | None = None,
    package_map: Any = None,
    core_hit_check: bool = True,
) -> HitResult:
    """Execute a single combat hit through the eScript interpreter.

    Parameters
    ----------
    parse_results:
        Pre-parsed mainhit.src and all includes (from ``shard.parse_combat_scripts()``
        or ``parse_with_includes()``).
    attacker:
        The attacking mobile.
    defender:
        The defending mobile.
    weapon:
        The weapon used.
    armor:
        The defender's armor (typically chest piece or highest AR piece).
    base_damage:
        Override base damage instead of rolling from weapon dice.
        If None, rolls from weapon.damage using the RNG.
    rng_seed:
        Seed for deterministic RNG.
    debug:
        Enable debug logging from script execution.
    config_resolver:
        Callable that resolves package config paths (e.g., ":combat:settings")
        to filesystem Paths. Typically ``shard.resolve_config_path``.
    executor:
        Pre-built :class:`Executor` to reuse across multiple hits.
        If provided, ``parse_results`` and ``em_modules_dir`` are ignored.
        The executor is reset before each run.
    shard_root:
        Root directory of the shard.  Needed for sub-script path resolution
        (``start_script``).  Passed to :class:`Executor` if creating one.
    package_map:
        Package name → directory mapping for resolving ``:pkg:name`` script
        paths in ``start_script`` calls.
    core_hit_check:
        If True (default), perform POL's core hit/miss check before calling
        the hitscript.  The formula is:
        ``hit_chance = (atk_skill + 50) / (2 * (def_skill + 50))``.
        Misses return immediately with ``final_damage=0``.

    Returns
    -------
    HitResult:
        Structured result with damage values and side effects.
    """
    import omega.runtime  # noqa: F401 — ensure stubs are registered

    # Calculate swing delay (constant for a given attacker+weapon, computed once)
    swing_delay_ms = calculate_swing_delay(attacker, weapon)

    result = HitResult(
        attacker_name=attacker.name,
        defender_name=defender.name,
        defender_hp_before=defender.hp,
        swing_delay_ms=swing_delay_ms,
    )

    # Set up RNG
    rng = set_rng_seed(rng_seed)

    # POL hit check — core performs this BEFORE calling the hitscript.
    # Formula: hit_chance = (atk_skill + 50) / (2 * (def_skill + 50))
    if core_hit_check and not check_hit(attacker, defender, weapon, rng):
        result.final_damage = 0.0
        result.defender_hp_after = defender.hp
        return result

    # Roll or use provided base damage
    if base_damage is not None:
        dmg = base_damage
    else:
        dmg = roll_base_damage(weapon, rng._rng)

    result.base_damage = dmg
    result.raw_damage = dmg  # starts equal, mainhit may modify

    # Set up simulation context
    ctx = SimulationContext(
        attacker=attacker,
        defender=defender,
        weapon=weapon,
        debug_mode=debug,
    )
    ctx._config_resolver = config_resolver

    # Seed the shard's eScript RNG (random.inc uses GetGlobalProperty("randomeroseed"))
    ctx.global_properties["randomeroseed"] = rng_seed if rng_seed else 12345

    # Register objects for serial-based lookup
    ctx.register_object(attacker)
    ctx.register_object(defender)
    ctx.register_object(weapon)
    ctx.register_object(armor)

    set_context(ctx)

    try:
        # Build executor or reuse cached one
        if executor is None:
            executor = Executor(
                parse_results,
                em_modules_dir=em_modules_dir,
                shard_root=shard_root,
                package_map=package_map,
            )
        else:
            executor.reset()

        # Make executor available to start_script() stub
        ctx.executor = executor

        # Inject Python override for __RecordSimulatorMetric so the
        # eScript no-op is replaced with actual metric recording.
        #
        # Protocol:
        #   Single KVP:   __RecordSimulatorMetric("key", value)
        #   Struct merge:  __RecordSimulatorMetric(struct{ ... })
        #   List append:   __RecordSimulatorMetric("list:name", struct{ ... })
        #     → appends the struct dict to ctx.metrics["name"] (a list)

        def _record_metric(key_or_metrics: Any = "", value: Any = 0) -> None:
            key_str = str(key_or_metrics) if not isinstance(key_or_metrics, (EStruct, dict)) else ""

            if key_str.startswith("list:"):
                # List accumulation: append struct/value to a named list
                list_name = key_str[5:]
                entry = (
                    {str(k): value.get_member(k) for k in value.keys()}
                    if isinstance(value, EStruct)
                    else {str(k): v for k, v in value.items()}
                    if isinstance(value, dict)
                    else value
                )
                ctx.metrics.setdefault(list_name, []).append(entry)
            elif isinstance(key_or_metrics, (EStruct, dict)):
                # Struct merge: flatten into metrics dict
                items = (
                    {str(k): key_or_metrics.get_member(k) for k in key_or_metrics.keys()}
                    if isinstance(key_or_metrics, EStruct)
                    else {str(k): v for k, v in key_or_metrics.items()}
                )
                ctx.metrics.update(items)
            else:
                ctx.metrics[key_str] = value

        executor.functions.set_override("__RecordSimulatorMetric", _record_metric)

        # POL behaviour: if the weapon has a hitscript, it REPLACES the
        # default mainhit program — it is NOT run in addition to it.
        # Standard weapons get `:combat:mainhit` as their hitscript via
        # the controlscript `makehitscript.src`.  Enchanted weapons get
        # their own hitscript (e.g., `:combat:spellstrikescript`).
        # Both paths receive (attacker, defender, weapon, armor, basedamage, rawdamage).
        if weapon.hitscript:
            hitscript_args = [attacker, defender, weapon, armor, dmg, dmg]
            executor.run_sub_program(weapon.hitscript, hitscript_args)
        else:
            # No hitscript on weapon — run the default mainhit program.
            program_args = {
                "attacker": attacker,
                "defender": defender,
                "weapon": weapon,
                "armor": armor,
                "basedamage": dmg,
                "rawdamage": dmg,
            }
            executor.run_program(program_args)

        # Collect results from context
        result.final_damage = ctx.total_damage_dealt
        result.absorbed = float(ctx.metrics.get("absorbed", 0.0))
        result.metrics = dict(ctx.metrics)
        result.side_effects = list(ctx.side_effects)
        result.defender_hp_after = defender.hp

    except Exception as e:
        result.success = False
        result.error = f"{type(e).__name__}: {e}"
        result.defender_hp_after = defender.hp
        logger.error("Hit execution failed", error=str(e), exc_info=True)

    return result


def execute_hit_from_shard(
    shard: Any,
    attacker: Mobile,
    defender: Mobile,
    weapon: Weapon,
    armor: Armor,
    **kwargs: Any,
) -> HitResult:
    """Convenience: parse combat scripts from shard and execute a hit.

    Parameters
    ----------
    shard:
        A ``ShardData`` instance with combat scripts available.
    attacker, defender, weapon, armor:
        Combat participants.
    **kwargs:
        Passed to ``execute_hit()`` (base_damage, rng_seed, debug).
    """
    parse_results = shard.parse_combat_scripts()

    if "config_resolver" not in kwargs:
        kwargs["config_resolver"] = shard.resolve_config_path

    if "em_modules_dir" not in kwargs:
        kwargs["em_modules_dir"] = shard.root / "scripts" / "modules"

    if "shard_root" not in kwargs:
        kwargs["shard_root"] = shard.root

    if "package_map" not in kwargs:
        kwargs["package_map"] = shard.package_map

    return execute_hit(parse_results, attacker, defender, weapon, armor, **kwargs)
