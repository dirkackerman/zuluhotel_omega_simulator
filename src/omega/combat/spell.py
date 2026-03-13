"""Spell execution — run a spell .src file through the interpreter.

This is the spell-casting counterpart to :func:`execute_hit`, running a
damage spell script through the eScript interpreter and returning a
structured :class:`SpellResult`.

Usage::

    from omega.combat import execute_spell
    from omega.config.spells import Spell
    from omega.shard import ShardData

    shard = ShardData.from_path(Path("submodules/zuluhotel_omega_2.5"))
    result = execute_spell(shard, caster, target, Spell.FIREBALL)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omega.combat.spell_result import SpellResult
from omega.interpreter.executor import Executor
from omega.interpreter.types import EStruct
from omega.logging import get_logger
from omega.model.mobile import Mobile
from omega.parser.parser import ParseResult
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.rng import set_rng_seed

logger = get_logger("omega.combat")


def _resolve_spell_script(spell_id: int, script_name: str) -> str:
    """Map a spell ID + script name to its package path.

    Mirrors the ``GetScript()`` logic in spelldata.inc.
    """
    if spell_id <= 64:
        return f":spells:{script_name}"
    elif spell_id <= 80:
        return f":Necro:{script_name}"
    elif spell_id <= 96:
        return f":Earth:{script_name}"
    elif 166 <= spell_id <= 181:
        return f":holybook:{script_name}"
    elif 182 <= spell_id <= 197:
        return f":songbook:{script_name}"
    # Fallback — try standard spells package
    return f":spells:{script_name}"


def execute_spell(
    parse_results: dict[Path, ParseResult],
    caster: Mobile,
    target: Mobile | list[Mobile],
    spell_id: int,
    *,
    rng_seed: int = 0,
    debug: bool = False,
    config_resolver: Any = None,
    em_modules_dir: Path | None = None,
    executor: Executor | None = None,
    shard_root: Path | None = None,
    package_map: Any = None,
    npc_mode: bool = False,
    circle_override: int = 0,
    main_target_index: int = 0,
    spell_registry: Any = None,
) -> SpellResult:
    """Execute a single spell through the eScript interpreter.

    Parameters
    ----------
    parse_results:
        Pre-parsed spell scripts and includes.
    caster:
        The casting mobile.
    target:
        Single defender or list of defenders for AoE spells.
    spell_id:
        Spell ID from :class:`Spell` enum.
    rng_seed:
        Seed for deterministic RNG.
    debug:
        Enable debug logging and metric recording.
    config_resolver:
        Resolves package config paths to filesystem Paths.
    executor:
        Pre-built :class:`Executor` to reuse.
    shard_root:
        Root directory of the shard.
    package_map:
        Package name → directory mapping.
    npc_mode:
        If True, bypass TryToCast (NPC direct-damage mode).
    circle_override:
        Override spell circle (for NPC mode).
    main_target_index:
        Index into target list for primary target (default 0).
    spell_registry:
        SpellRegistry for looking up spell metadata.

    Returns
    -------
    SpellResult:
        Structured result with damage values, metrics, and side effects.
    """
    import omega.runtime  # noqa: F401 — ensure stubs are registered

    # Resolve defenders list
    if isinstance(target, list):
        defenders = target
    else:
        defenders = [target]

    primary_target = defenders[main_target_index] if defenders else None

    result = SpellResult(
        spell_id=int(spell_id),
        caster_name=caster.name,
        target_name=getattr(primary_target, "name", "") if primary_target else "",
        target_hp_before=getattr(primary_target, "hp", 0) if primary_target else 0,
    )

    # Look up spell metadata
    spell_name = ""
    spell_script = ""
    spell_circle = circle_override

    if spell_registry is not None:
        entry = spell_registry.by_id(int(spell_id))
        if entry is not None:
            spell_name = entry.name
            spell_script = entry.script
            spell_circle = spell_circle or entry.circle
            result.spell_name = spell_name
            result.circle = spell_circle

    # Set up RNG
    rng = set_rng_seed(rng_seed)

    # Set up simulation context
    ctx = SimulationContext(
        attacker=caster,
        defenders=defenders,
        main_target_index=main_target_index,
        debug_mode=debug,
    )
    ctx._config_resolver = config_resolver

    # Seed the shard's eScript RNG
    ctx.global_properties["randomeroseed"] = rng_seed if rng_seed else 12345
    # Note: DEBUG_MODE is forced to 1 in the executor scope below (after
    # executor.reset()), not here.  global_properties is for GetGlobalProperty/
    # SetGlobalProperty stubs, not eScript variable resolution.

    # Register objects for serial-based lookup
    ctx.register_object(caster)
    for d in defenders:
        ctx.register_object(d)

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

        # Force DEBUG_MODE=1 in the eScript scope so all __RecordSimulatorMetric
        # calls in the shard scripts are always active.  The shard may or may not
        # declare ``const DEBUG_MODE := 1`` — we override unconditionally.
        executor.scopes.define_global("DEBUG_MODE", 1)

        # Inject __RecordSimulatorMetric override (same 3 protocols as execute_hit)
        def _record_metric(key_or_metrics: Any = "", value: Any = 0) -> None:
            key_str = str(key_or_metrics) if not isinstance(key_or_metrics, (EStruct, dict)) else ""

            if key_str.startswith("list:"):
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
                items = (
                    {str(k): key_or_metrics.get_member(k) for k in key_or_metrics.keys()}
                    if isinstance(key_or_metrics, EStruct)
                    else {str(k): v for k, v in key_or_metrics.items()}
                )
                ctx.metrics.update(items)
            else:
                ctx.metrics[key_str] = value

        executor.functions.set_override("__RecordSimulatorMetric", _record_metric)

        # Resolve spell script path
        if not spell_script:
            # Fallback: try to derive script name from spell ID
            logger.warning(
                "No spell script name from registry, cannot resolve path",
                spell_id=int(spell_id),
            )
            result.success = False
            result.error = f"No script found for spell ID {spell_id}"
            return result

        script_path = _resolve_spell_script(int(spell_id), spell_script)

        # Build parms based on mode
        if npc_mode:
            # NPC mode: parms = ["#MOB", caster, target, circle, fromhit_flag]
            parms = ["#MOB", caster, primary_target, spell_circle, 0]
        else:
            # Player mode: parms = caster (TryToCast handles everything)
            parms = caster

        # Run the spell script
        executor.run_sub_program(script_path, [parms, int(spell_id)])

        # Collect results from context
        result.final_damage = ctx.total_damage_dealt
        result.casting_delay_ms = float(ctx._virtual_time_ms)
        result.metrics = dict(ctx.metrics)
        result.side_effects = list(ctx.side_effects)

        # Populate fields from metrics
        result.base_damage = int(ctx.metrics.get("spell_base_damage", 0))

        # Check if resisted
        resisted_list = ctx.metrics.get("resisted", [])
        if resisted_list:
            result.resisted = any(
                r.get("did_resist", 0) for r in resisted_list
                if isinstance(r, dict)
            )

        # Check spell protection / immunity
        prot_list = ctx.metrics.get("spell_protection", [])
        if prot_list:
            # IMMUNED constant is 1 in the shard scripts
            result.immuned = any(
                r.get("result", 0) == 1 for r in prot_list
                if isinstance(r, dict)
            )

        # Check fizzle (CheckSkill failure)
        if ctx.metrics.get("spell_skill_check") == 0:
            result.fizzled = True

        # Check mana consumption
        if ctx.metrics.get("spell_mana_consumed") == 0:
            result.fizzled = True  # No mana = effective fizzle

        # Fallback fizzle detection for player mode:
        # When TryToCast fails (skill check or mana), the script returns early
        # without entering the damage pipeline — no metrics are recorded.
        # Detect this by checking for 0 damage with no damage pipeline metrics.
        if (
            not npc_mode
            and not result.fizzled
            and not result.immuned
            and result.base_damage == 0
            and result.final_damage == 0
            and "spell_base_damage" not in ctx.metrics
        ):
            result.fizzled = True

        # Cast success: damage was applied or script completed without fizzle
        result.cast_success = (
            not result.fizzled
            and not result.immuned
            and result.final_damage > 0
        )

        if primary_target is not None:
            result.target_hp_after = primary_target.hp

    except Exception as e:
        result.success = False
        result.error = f"{type(e).__name__}: {e}"
        if primary_target is not None:
            result.target_hp_after = getattr(primary_target, "hp", 0)
        logger.error("Spell execution failed", error=str(e), exc_info=True)

    return result


def execute_spell_from_shard(
    shard: Any,
    caster: Mobile,
    target: Mobile | list[Mobile],
    spell_id: int,
    **kwargs: Any,
) -> SpellResult:
    """Convenience: parse spell scripts from shard and execute a spell.

    Parameters
    ----------
    shard:
        A ``ShardData`` instance.
    caster, target:
        Combat participants.
    spell_id:
        Spell ID to cast.
    **kwargs:
        Passed to ``execute_spell()``.
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

    if "spell_registry" not in kwargs and hasattr(shard, "spell_registry"):
        kwargs["spell_registry"] = shard.spell_registry

    return execute_spell(parse_results, caster, target, spell_id, **kwargs)
