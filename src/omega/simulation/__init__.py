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
from omega.simulation.stats import (
    CellResult,
    DamageStats,
    ElementDamage,
    ElementalBreakdown,
    RatioStats,
    SimulationResult,
)

__all__ = [
    "ArmorSpec",
    "CellResult",
    "CombatantSpec",
    "DamageStats",
    "ElementDamage",
    "ElementalBreakdown",
    "ParameterSweep",
    "RatioStats",
    "Scenario",
    "SimulationResult",
    "Variable",
    "WeaponSpec",
    "run_scenario",
    "run_sweep",
]
