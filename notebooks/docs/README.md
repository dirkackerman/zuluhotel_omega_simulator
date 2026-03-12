# Zuluhotel Omega Simulator — Notebook Documentation

The Zuluhotel Omega Simulator runs the shard's real eScript combat scripts through a Python interpreter, letting you simulate thousands of weapon hits and analyze the results — without a running POL server.

This documentation is for **notebook authors and game designers** who want to define combat scenarios, run simulations, and interpret the results for balance tuning.

## Who is this for?

- **Game designers** iterating on weapon damage, armor values, class bonuses, and skill scaling
- **Balance testers** comparing builds, matchups, and edge cases with statistical confidence
- **Notebook authors** building new analysis notebooks on top of the simulation API

## What can you do?

- Define an attacker and defender with stats, skills, class levels, weapons, and armor
- Run N independent hit iterations and get statistical summaries (mean, median, percentiles, std dev)
- Sweep a parameter (e.g., Tactics 50 to 130) and plot damage curves
- Compare scenarios side by side (class vs class, weapon A vs weapon B)
- Inspect the damage pipeline: base roll, armor absorption, final damage
- Simulate elemental weapons with per-element resistance checks (V1.5)
- Apply weapon enchantments (spell strike, slayer, effects, greaters) via `enchant_with()` (V1.5)
- Test reactive armor damage reflection (V1.5)
- Compute DPS metrics with POL-conformant swing timing (V2)
- Simulate astral damage (Spirit Speak, meditation resistance, mana/stamina drain) (V2)
- Analyze spell resistance with class modifiers (Mage, Warrior, Paladin) (V2)
- Capture debug messages from the eScript execution for troubleshooting

## Quick start

```python
from pathlib import Path
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.shard import ShardData
from omega.simulation import (
    ArmorSpec, CombatantSpec, Scenario, WeaponSpec, run_scenario,
)

# Load the shard data (scripts, configs, package map)
shard = ShardData.from_path(Path("../submodules/zuluhotel_omega_2.5"))

# Define a scenario
scenario = Scenario(
    attacker=CombatantSpec(
        name="Warrior",
        skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
        str_=100, dex_=100, int_=25,
        class_levels={"IsWarrior": 5},
        weapon=WeaponSpec(name="Broadsword", damage="3d6+2"),
    ),
    defender=CombatantSpec(
        name="Target Dummy",
        is_npc=True,
        str_=50, dex_=50, int_=50,
        hp=500,
        armor=ArmorSpec(ar=30),
    ),
    iterations=1000,
    base_seed=42,
)

# Run and inspect
result = run_scenario(scenario, shard=shard)
print(f"Mean damage: {result.damage_stats.mean:.1f}")
print(f"Std dev:     {result.damage_stats.std_dev:.1f}")
print(f"Range:       {result.damage_stats.min:.0f} – {result.damage_stats.max:.0f}")
```

## Prerequisites

- Python 3.14
- Install dependencies: `pip install -e ".[notebook]"` (adds JupyterLab, matplotlib, numpy)
- Launch notebooks: `jupyter lab` from the project root

## Documentation pages

| Page | What it covers |
|------|----------------|
| [Getting Started](getting-started.md) | Environment setup, launching JupyterLab, running your first simulation |
| [Concepts](concepts.md) | Domain glossary — hits, iterations, the damage pipeline, state resets, seeds |
| [Combatant Specs](combatant-specs.md) | Defining attackers and defenders: stats, skills, classes, weapons, armor |
| [Scenarios](scenarios.md) | Running simulations: `Scenario`, `Variable`, `ParameterSweep`, `run_scenario`, `run_sweep` |
| [Results](results.md) | Understanding output: `HitResult`, `DamageStats`, `CellResult`, `SimulationResult` |
| [Reporting](reporting.md) | Tables and plots: `summary_table`, `comparison_table`, histogram, damage curves |
| [Runtime](runtime.md) | How eScript executes: the interpreter, POL built-in stubs, context, and RNG |
| [Messages and Metrics](messages-and-metrics.md) | Capturing debug output, recording metrics, and tracking side effects |
| [Constants Reference](constants-reference.md) | Skill IDs, class IDs, damage type flags, stat caps, equipment layers |
| [Examples](examples.md) | Cookbook — copy-paste recipes for common balancing questions |

## Existing notebooks

The `notebooks/` directory ships with working examples:

- `01_basic_damage.ipynb` — Single scenario, damage histogram, breakdown chart
- `02_skill_sweep.ipynb` — Sweep a skill parameter, plot damage curves
- `03_class_comparison.ipynb` — Compare damage output across character classes
- `04_weapon_comparison.ipynb` — Side-by-side weapon comparison
- `05_enchantments.ipynb` — Enchantments & elemental damage deep dive (V1.5)

All notebooks include V2 sections for DPS analysis, astral damage, and spell resistance.
