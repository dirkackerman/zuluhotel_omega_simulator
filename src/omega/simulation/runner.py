"""Simulation execution engine.

Runs N iterations of ``execute_hit()`` per scenario, optionally across
a parameter sweep grid, and returns aggregated statistical results.

Usage::

    from omega.simulation import run_scenario, run_sweep

    result = run_scenario(scenario, shard=shard)
    sweep_result = run_sweep(sweep, shard=shard)
"""

from __future__ import annotations

import itertools
import time
from pathlib import Path
from typing import Any

from omega.combat.hit import execute_hit
from omega.combat.result import HitResult
from omega.interpreter.executor import Executor
from omega.logging import get_logger
from omega.model.snapshot import restore, snapshot
from omega.parser.parser import ParseResult
from omega.simulation.scenario import (
    ParameterSweep,
    Scenario,
    Variable,
    apply_variable,
    build_combatant,
)
from omega.simulation.stats import CellResult, SimulationResult, aggregate_cell

logger = get_logger("omega.simulation")


def run_scenario(
    scenario: Scenario,
    *,
    parse_results: dict[Path, ParseResult] | None = None,
    config_resolver: Any = None,
    em_modules_dir: Path | None = None,
    shard: Any = None,
    _executor: Executor | None = None,
) -> CellResult:
    """Run a single scenario (N iterations) and return aggregated results.

    Parameters
    ----------
    scenario:
        The scenario to execute.
    parse_results:
        Pre-parsed combat script trees.  If ``None`` and ``shard`` is
        provided, scripts are parsed from the shard.
    config_resolver:
        Callable resolving package config paths to filesystem paths.
    em_modules_dir:
        Directory containing ``.em`` module files.
    shard:
        A :class:`~omega.shard.ShardData` instance.  Used to derive
        ``parse_results``, ``config_resolver``, and ``em_modules_dir``
        when they are not provided explicitly.
    """
    # Derive shard-based defaults
    if shard is not None:
        if parse_results is None:
            parse_results = shard.parse_combat_scripts()
        if config_resolver is None:
            config_resolver = shard.resolve_config_path
        if em_modules_dir is None:
            em_modules_dir = shard.root / "scripts" / "modules"

    if parse_results is None:
        raise ValueError(
            "Either parse_results or shard must be provided"
        )

    # Build combatants from specs
    attacker, weapon, _atk_armor = build_combatant(scenario.attacker)
    defender, _def_weapon, armor = build_combatant(scenario.defender)

    # Build executor once — reused across all iterations
    cached_executor = _executor or Executor(parse_results, em_modules_dir=em_modules_dir)

    # Snapshot for per-iteration reset
    atk_snap = snapshot(attacker)
    def_snap = snapshot(defender)
    weapon_hp = weapon.hp
    armor_hp = armor.hp

    # Run iterations
    results: list[HitResult] = []
    for i in range(scenario.iterations):
        seed = scenario.base_seed ^ i

        result = execute_hit(
            parse_results,
            attacker,
            defender,
            weapon,
            armor,
            rng_seed=seed,
            debug=scenario.debug_mode,
            config_resolver=config_resolver,
            executor=cached_executor,
        )
        results.append(result)

        # Reset state for next iteration
        restore(attacker, atk_snap)
        restore(defender, def_snap)
        weapon.hp = weapon_hp
        armor.hp = armor_hp

    return aggregate_cell(results)


def run_sweep(
    sweep: ParameterSweep,
    *,
    parse_results: dict[Path, ParseResult] | None = None,
    config_resolver: Any = None,
    em_modules_dir: Path | None = None,
    shard: Any = None,
) -> SimulationResult:
    """Run a full parameter sweep and return results for all cells.

    Parameters
    ----------
    sweep:
        The parameter sweep definition.
    parse_results, config_resolver, em_modules_dir, shard:
        See :func:`run_scenario`.
    """
    # Derive shard-based defaults once for all cells
    if shard is not None:
        if parse_results is None:
            parse_results = shard.parse_combat_scripts()
        if config_resolver is None:
            config_resolver = shard.resolve_config_path
        if em_modules_dir is None:
            em_modules_dir = shard.root / "scripts" / "modules"

    if parse_results is None:
        raise ValueError(
            "Either parse_results or shard must be provided"
        )

    # Build executor once for all cells in the sweep
    shared_executor = Executor(parse_results, em_modules_dir=em_modules_dir)

    # Build the Cartesian product grid
    if not sweep.variables:
        # No variables — just run the base scenario
        start = time.monotonic()
        cell = run_scenario(
            sweep.scenario,
            parse_results=parse_results,
            config_resolver=config_resolver,
            em_modules_dir=em_modules_dir,
            _executor=shared_executor,
        )
        elapsed = time.monotonic() - start
        return SimulationResult(cells=[cell], total_time=elapsed)

    var_names = [f"{v.target}.{v.parameter}" for v in sweep.variables]
    var_value_lists = [v.values for v in sweep.variables]
    combos = list(itertools.product(*var_value_lists))
    total_cells = len(combos)

    logger.info(
        "Starting parameter sweep",
        variables=len(sweep.variables),
        cells=total_cells,
        iterations_per_cell=sweep.scenario.iterations,
    )

    cells: list[CellResult] = []
    start = time.monotonic()

    for cell_idx, combo in enumerate(combos):
        # Apply variables to the base scenario's combatant specs
        scenario = sweep.scenario
        for var, val in zip(sweep.variables, combo):
            if var.target == "attacker":
                new_atk = apply_variable(scenario.attacker, var.parameter, val)
                scenario = Scenario(
                    attacker=new_atk,
                    defender=scenario.defender,
                    iterations=scenario.iterations,
                    base_seed=scenario.base_seed,
                    debug_mode=scenario.debug_mode,
                )
            else:
                new_def = apply_variable(scenario.defender, var.parameter, val)
                scenario = Scenario(
                    attacker=scenario.attacker,
                    defender=new_def,
                    iterations=scenario.iterations,
                    base_seed=scenario.base_seed,
                    debug_mode=scenario.debug_mode,
                )

        # Progress logging
        elapsed = time.monotonic() - start
        if cell_idx > 0 and elapsed > 0:
            rate = cell_idx / elapsed
            remaining = (total_cells - cell_idx) / rate
            logger.info(
                "Sweep progress",
                cell=cell_idx + 1,
                total=total_cells,
                elapsed_s=round(elapsed, 1),
                eta_s=round(remaining, 1),
            )

        cell = run_scenario(
            scenario,
            parse_results=parse_results,
            config_resolver=config_resolver,
            em_modules_dir=em_modules_dir,
            _executor=shared_executor,
        )
        cell.variable_values = dict(zip(var_names, combo))
        cells.append(cell)

    total_time = time.monotonic() - start
    logger.info(
        "Sweep complete",
        cells=total_cells,
        total_time_s=round(total_time, 1),
    )

    return SimulationResult(cells=cells, total_time=total_time)
