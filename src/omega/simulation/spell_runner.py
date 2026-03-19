"""Spell simulation execution engine.

Runs N iterations of ``execute_spell()`` per spell scenario, optionally
across a parameter sweep grid, and returns aggregated statistical results.

Usage::

    from omega.simulation import run_spell_scenario, run_spell_sweep
    from omega.config.spells import Spell

    result = run_spell_scenario(scenario, shard=shard)
    sweep_result = run_spell_sweep(sweep, shard=shard)
"""

from __future__ import annotations

import dataclasses
import itertools
import time
from pathlib import Path
from typing import Any

from omega.combat.spell import execute_spell
from omega.combat.spell_result import SpellResult
from omega.config.spell_registry import SpellRegistry
from omega.interpreter.executor import Executor
from omega.logging import get_logger
from omega.model.snapshot import restore, snapshot
from omega.parser.parser import ParseResult
from omega.simulation.scenario import (
    CombatantSpec,
    SpellParameterSweep,
    SpellScenario,
    Variable,
    apply_variable,
    build_combatant,
)
from omega.simulation.stats import CellResult, SimulationResult, aggregate_spell_cell

logger = get_logger("omega.simulation.spell")


def _normalize_targets(
    target: CombatantSpec | list[CombatantSpec],
) -> list[CombatantSpec]:
    """Ensure target is always a list of CombatantSpec."""
    if isinstance(target, list):
        return target
    return [target]


def run_spell_scenario(
    scenario: SpellScenario,
    *,
    parse_results: dict[Path, ParseResult] | None = None,
    config_resolver: Any = None,
    em_modules_dir: Path | None = None,
    shard: Any = None,
    _executor: Executor | None = None,
    spell_registry: SpellRegistry | None = None,
) -> CellResult:
    """Run a single spell scenario (N iterations) and return aggregated results.

    Parameters
    ----------
    scenario:
        The spell scenario to execute.
    parse_results:
        Pre-parsed spell script trees.  If ``None`` and ``shard`` is
        provided, scripts are parsed from the shard.
    config_resolver:
        Callable resolving package config paths to filesystem paths.
    em_modules_dir:
        Directory containing ``.em`` module files.
    shard:
        A :class:`~omega.shard.ShardData` instance.  Used to derive
        ``parse_results``, ``config_resolver``, ``em_modules_dir``,
        and ``spell_registry`` when not provided explicitly.
    _executor:
        Pre-built :class:`Executor` to reuse across calls.
    spell_registry:
        Spell metadata lookup.  Auto-loaded from shard if not provided.
    """
    # Derive shard-based defaults
    shard_root: Path | None = None
    package_map: Any = None
    if shard is not None:
        if parse_results is None:
            parse_results = shard.parse_combat_scripts()
        if config_resolver is None:
            config_resolver = shard.resolve_config_path
        if em_modules_dir is None:
            em_modules_dir = shard.root / "scripts" / "modules"
        shard_root = shard.root
        package_map = shard.package_map

    if parse_results is None:
        raise ValueError(
            "Either parse_results or shard must be provided"
        )

    # Auto-load spell registry from shard if needed
    if spell_registry is None and shard is not None:
        if hasattr(shard, "spell_registry"):
            spell_registry = shard.spell_registry

    # Build caster from spec (weapon/armor not used for spells but
    # build_combatant returns them — they may carry MagicPenalty).
    # Enchantment registries not needed: spell execution doesn't trigger
    # weapon hitscripts or armor OnHitScripts.
    caster, _, _ = build_combatant(scenario.caster)

    # Build target(s) from spec(s)
    target_specs = _normalize_targets(scenario.target)
    targets = []
    for tspec in target_specs:
        mob, _, _ = build_combatant(tspec)
        targets.append(mob)

    # Build executor once — reused across all iterations
    cached_executor = _executor or Executor(
        parse_results,
        em_modules_dir=em_modules_dir,
        shard_root=shard_root,
        package_map=package_map,
    )

    # Snapshot for per-iteration reset
    caster_snap = snapshot(caster)
    target_snaps = [snapshot(t) for t in targets]

    # Run iterations
    results: list[SpellResult] = []
    target_arg = targets if len(targets) > 1 else targets[0] if targets else targets
    for i in range(scenario.iterations):
        seed = scenario.base_seed ^ i

        result = execute_spell(
            parse_results,
            caster,
            target_arg,
            scenario.spell_id,
            rng_seed=seed,
            debug=scenario.debug_mode,
            config_resolver=config_resolver,
            executor=cached_executor,
            shard_root=shard_root,
            package_map=package_map,
            npc_mode=scenario.npc_mode,
            circle_override=scenario.circle_override,
            spell_registry=spell_registry,
        )
        results.append(result)

        # Reset state for next iteration
        restore(caster, caster_snap)
        for t, snap in zip(targets, target_snaps):
            restore(t, snap)

    return aggregate_spell_cell(results)


def _apply_spell_variable(
    scenario: SpellScenario,
    var: Variable,
    val: Any,
) -> SpellScenario:
    """Apply a single variable to a spell scenario, returning a new scenario."""
    if var.target == "caster":
        new_caster = apply_variable(scenario.caster, var.parameter, val)
        return dataclasses.replace(scenario, caster=new_caster)
    elif var.target == "target":
        # Apply to all targets (or the single target)
        if isinstance(scenario.target, list):
            new_targets = [
                apply_variable(tspec, var.parameter, val)
                for tspec in scenario.target
            ]
            return dataclasses.replace(scenario, target=new_targets)
        else:
            new_target = apply_variable(scenario.target, var.parameter, val)
            return dataclasses.replace(scenario, target=new_target)
    elif var.target == "spell" and var.parameter == "spell_id":
        return dataclasses.replace(scenario, spell_id=int(val))
    else:
        raise ValueError(
            f"Unknown variable target for spell scenario: {var.target!r}. "
            f"Use 'caster', 'target', or 'spell'."
        )


def run_spell_sweep(
    sweep: SpellParameterSweep,
    *,
    parse_results: dict[Path, ParseResult] | None = None,
    config_resolver: Any = None,
    em_modules_dir: Path | None = None,
    shard: Any = None,
    spell_registry: SpellRegistry | None = None,
) -> SimulationResult:
    """Run a full spell parameter sweep and return results for all cells.

    Parameters
    ----------
    sweep:
        The spell parameter sweep definition.
    parse_results, config_resolver, em_modules_dir, shard, spell_registry:
        See :func:`run_spell_scenario`.
    """
    # Derive shard-based defaults once for all cells
    shard_root: Path | None = None
    package_map: Any = None
    if shard is not None:
        if parse_results is None:
            parse_results = shard.parse_combat_scripts()
        if config_resolver is None:
            config_resolver = shard.resolve_config_path
        if em_modules_dir is None:
            em_modules_dir = shard.root / "scripts" / "modules"
        shard_root = shard.root
        package_map = shard.package_map

    if parse_results is None:
        raise ValueError(
            "Either parse_results or shard must be provided"
        )

    # Auto-load spell registry
    if spell_registry is None and shard is not None:
        if hasattr(shard, "spell_registry"):
            spell_registry = shard.spell_registry

    # Build executor once for all cells in the sweep
    shared_executor = Executor(
        parse_results,
        em_modules_dir=em_modules_dir,
        shard_root=shard_root,
        package_map=package_map,
    )

    # Build the Cartesian product grid
    if not sweep.variables:
        # No variables — just run the base scenario
        start = time.monotonic()
        cell = run_spell_scenario(
            sweep.scenario,
            parse_results=parse_results,
            config_resolver=config_resolver,
            em_modules_dir=em_modules_dir,
            _executor=shared_executor,
            spell_registry=spell_registry,
        )
        elapsed = time.monotonic() - start
        return SimulationResult(cells=[cell], total_time=elapsed)

    var_names = []
    for v in sweep.variables:
        if v.target == "spell":
            var_names.append(v.parameter)
        else:
            var_names.append(f"{v.target}.{v.parameter}")
    var_value_lists = [v.values for v in sweep.variables]
    combos = list(itertools.product(*var_value_lists))
    total_cells = len(combos)

    logger.info(
        "Starting spell parameter sweep",
        variables=len(sweep.variables),
        cells=total_cells,
        iterations_per_cell=sweep.scenario.iterations,
    )

    cells: list[CellResult] = []
    start = time.monotonic()

    for cell_idx, combo in enumerate(combos):
        # Apply variables to the base scenario
        scenario = sweep.scenario
        for var, val in zip(sweep.variables, combo):
            scenario = _apply_spell_variable(scenario, var, val)

        # Progress logging
        elapsed = time.monotonic() - start
        if cell_idx > 0 and elapsed > 0:
            rate = cell_idx / elapsed
            remaining = (total_cells - cell_idx) / rate
            logger.info(
                "Spell sweep progress",
                cell=cell_idx + 1,
                total=total_cells,
                elapsed_s=round(elapsed, 1),
                eta_s=round(remaining, 1),
            )

        cell = run_spell_scenario(
            scenario,
            parse_results=parse_results,
            config_resolver=config_resolver,
            em_modules_dir=em_modules_dir,
            _executor=shared_executor,
            spell_registry=spell_registry,
        )
        cell.variable_values = dict(zip(var_names, combo))
        cells.append(cell)

    total_time = time.monotonic() - start
    logger.info(
        "Spell sweep complete",
        cells=total_cells,
        total_time_s=round(total_time, 1),
    )

    return SimulationResult(cells=cells, total_time=total_time)
