"""Combat simulation engine — scenario definition, execution, and statistics."""

from omega.simulation.runner import run_scenario, run_sweep
from omega.simulation.scenario import (
    ArmorSpec,
    CombatantSpec,
    ParameterSweep,
    Scenario,
    Variable,
    WeaponSpec,
)
from omega.simulation.stats import CellResult, DamageStats, RatioStats, SimulationResult

__all__ = [
    "ArmorSpec",
    "CellResult",
    "CombatantSpec",
    "DamageStats",
    "ParameterSweep",
    "RatioStats",
    "Scenario",
    "SimulationResult",
    "Variable",
    "WeaponSpec",
    "run_scenario",
    "run_sweep",
]
