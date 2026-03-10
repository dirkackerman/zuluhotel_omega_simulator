# Getting Started

This guide walks you through setting up your environment, launching JupyterLab, and running your first combat simulation.

## 1. Install Python 3.14

The simulator requires Python 3.14 or later. Verify your version:

```bash
python --version   # Should print Python 3.14.x
```

## 2. Clone and set up the project

```bash
git clone <repo-url>
cd zuluhotel_omega_simulator

# Initialize submodules (needed for shard scripts)
git submodule update --init --recursive
```

## 3. Install dependencies

Using `uv` (recommended):

```bash
uv pip install -e ".[notebook]"
```

Or plain pip:

```bash
pip install -e ".[notebook]"
```

The `[notebook]` extra installs JupyterLab, matplotlib, and numpy — everything needed for the analysis notebooks.

For development (adds pytest):

```bash
pip install -e ".[dev,notebook]"
```

## 4. Launch JupyterLab

From the project root:

```bash
jupyter lab
```

Navigate to the `notebooks/` directory in the file browser. The existing notebooks (`01_basic_damage.ipynb`, `02_skill_sweep.ipynb`, etc.) are ready to run.

## 5. Your first simulation

Create a new notebook or open an existing one. The standard preamble for any simulation notebook looks like this:

```python
from pathlib import Path
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.shard import ShardData
from omega.simulation import (
    ArmorSpec, CombatantSpec, Scenario, WeaponSpec, run_scenario,
)

# Load shard data — parses package structure, builds config resolver
shard = ShardData.from_path(Path("../submodules/zuluhotel_omega_2.5"))
```

> **Path note**: Notebooks live in `notebooks/`, so the relative path to the shard submodule is `../submodules/zuluhotel_omega_2.5`. Adjust if your notebook is elsewhere.

### Define a scenario

A [Scenario](scenarios.md) pairs an attacker with a defender and specifies how many hit iterations to run:

```python
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
```

See [Combatant Specs](combatant-specs.md) for the full field reference.

### Run it

```python
result = run_scenario(scenario, shard=shard)

print(f"Mean damage:  {result.damage_stats.mean:.1f}")
print(f"Median:       {result.damage_stats.median:.1f}")
print(f"Std dev:      {result.damage_stats.std_dev:.1f}")
print(f"Range:        {result.damage_stats.min:.0f} – {result.damage_stats.max:.0f}")
print(f"Hit rate:     {result.ratios.hit_rate:.1%}")
```

### Visualize

```python
from omega.reporting.plots import damage_histogram, damage_breakdown

# Damage distribution histogram
damage_histogram(result, title="Warrior vs Target Dummy")

# Base / absorbed / final breakdown
damage_breakdown(result)
```

### Tabulate

```python
from omega.reporting.tables import summary_table, format_table_html
from IPython.display import HTML

# Works for sweep results too — one row per cell
rows = summary_table(result)  # result can be wrapped in SimulationResult
HTML(format_table_html(rows))
```

## 6. Next steps

- [Concepts](concepts.md) — Understand the domain model and damage pipeline
- [Scenarios](scenarios.md) — Run parameter sweeps and multi-variable grids
- [Reporting](reporting.md) — All available plots and table functions
- [Examples](examples.md) — Copy-paste recipes for common balancing tasks

## Troubleshooting

**`ModuleNotFoundError: No module named 'omega'`**
The package isn't installed. Run `pip install -e "."` from the project root.

**`FileNotFoundError: mainhit.src not found in combat package`**
The shard submodule isn't initialized. Run `git submodule update --init --recursive`.

**`ImportError: matplotlib is required for plotting`**
Install the notebook extras: `pip install -e ".[notebook]"`.

**Shard path doesn't exist**
Check that the relative path from your notebook to `submodules/zuluhotel_omega_2.5` is correct. Use `Path("../submodules/zuluhotel_omega_2.5").resolve()` to debug.
