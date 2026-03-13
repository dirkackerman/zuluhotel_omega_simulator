"""Combat simulation engine — scenario definition, execution, and statistics."""

from omega.simulation.runner import run_scenario, run_sweep
from omega.simulation.scenario import (
    ArmorSpec,
    CombatantSpec,
    ParameterSweep,
    Scenario,
    SpellParameterSweep,
    SpellScenario,
    Variable,
    WeaponSpec,
)
from omega.simulation.spell_runner import run_spell_scenario, run_spell_sweep
from omega.simulation.stats import (
    CellResult,
    DamageStats,
    ElementDamage,
    ElementalBreakdown,
    RatioStats,
    SimulationResult,
    aggregate_spell_cell,
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
    "SpellParameterSweep",
    "SpellScenario",
    "Variable",
    "WeaponSpec",
    "aggregate_spell_cell",
    "run_scenario",
    "run_spell_scenario",
    "run_spell_sweep",
    "run_sweep",
]
