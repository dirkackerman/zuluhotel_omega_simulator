# Zuluhotel Omega Combat Simulator

An eScript interpreter and combat simulator for the [Zuluhotel Omega](https://zuluhotelomega.com/) UO shard. Parses and executes POL eScript combat scripts to model damage scenarios (physical hits, resistance, mitigation) without running a full POL server. Built for game designers iterating on balance.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Getting Started

```bash
# Clone with submodules
git clone --recurse-submodules <repo-url>
cd zuluhotel_omega_simulator

# Install dependencies
uv sync --extra notebook --extra dev

# Run tests to verify everything works
uv run pytest

# Launch Jupyter
uv run jupyter lab
```

Open any notebook in `notebooks/` to run a simulation:

| Notebook | Description |
|---|---|
| `01_basic_damage` | Single scenario (Warrior vs NPC), damage distribution |
| `02_skill_sweep` | Sweep Tactics 50-120, damage scaling curve |
| `03_class_comparison` | Side-by-side class damage comparison |
| `04_weapon_comparison` | Compare two weapons on the same character |

## Updating

When new changes are published:

```bash
git pull --recurse-submodules
uv sync --extra notebook --extra dev
```

If shard balance scripts were updated, run `uv run pytest -m shard` to check which tests need attention.
