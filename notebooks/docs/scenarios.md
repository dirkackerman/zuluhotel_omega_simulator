# Scenarios

This page covers how to define and run simulations — from a single scenario to multi-variable parameter sweeps.

**Import path:**
```python
from omega.simulation import (
    Scenario, Variable, ParameterSweep,
    run_scenario, run_sweep,
)
```

## Scenario

A `Scenario` defines a single simulation: one attacker, one defender, N iterations.

```python
@dataclass(frozen=True)
class Scenario:
    attacker: CombatantSpec       # Required
    defender: CombatantSpec       # Required
    iterations: int = 1000        # Number of independent hits
    base_seed: int = 0            # RNG seed for reproducibility
    debug_mode: bool = False      # Enable verbose script logging
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `attacker` | `CombatantSpec` | — | The attacking combatant. See [Combatant Specs](combatant-specs.md). |
| `defender` | `CombatantSpec` | — | The defending combatant. |
| `iterations` | `int` | `1000` | How many independent hits to simulate. More iterations = tighter confidence on the mean. |
| `base_seed` | `int` | `0` | RNG seed. Per-iteration seed = `base_seed XOR iteration_index`. Same seed = identical results. |
| `debug_mode` | `bool` | `False` | When `True`, enables verbose logging from the eScript interpreter. See [Messages and Metrics](messages-and-metrics.md). |

### How many iterations?

| Goal | Iterations | Notes |
|------|-----------|-------|
| Quick sanity check | 10–50 | Fast, but noisy statistics |
| Exploratory analysis | 200–500 | Good enough for trends and plots |
| Publication-quality results | 1000–5000 | Tight confidence intervals |
| Stress test / performance | 10000+ | Tests throughput (~374 hits/sec) |

## run_scenario()

Executes a single scenario and returns a `CellResult`.

```python
def run_scenario(
    scenario: Scenario,
    *,
    parse_results: dict[Path, ParseResult] | None = None,
    config_resolver: Any = None,
    em_modules_dir: Path | None = None,
    shard: Any = None,
) -> CellResult
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `scenario` | `Scenario` | What to simulate |
| `parse_results` | `dict` or `None` | Pre-parsed eScript trees. Auto-derived from `shard` if not provided. |
| `config_resolver` | callable or `None` | Resolves `:pkg:name` config paths. Auto-derived from `shard`. |
| `em_modules_dir` | `Path` or `None` | Directory with `.em` module definitions. Auto-derived from `shard`. |
| `shard` | `ShardData` or `None` | Convenience — auto-derives the three parameters above. |

### Usage patterns

**Simplest — pass `shard` only:**
```python
from omega.shard import ShardData

shard = ShardData.from_path(Path("../submodules/zuluhotel_omega_2.5"))
result = run_scenario(scenario, shard=shard)
```

**Explicit — for reusing parsed results across multiple calls:**
```python
shard = ShardData.from_path(Path("../submodules/zuluhotel_omega_2.5"))
parse_results = shard.parse_combat_scripts()

# Reuse parse_results across multiple scenarios
r1 = run_scenario(scenario_a, parse_results=parse_results,
                   config_resolver=shard.resolve_config_path,
                   em_modules_dir=shard.root / "scripts" / "modules")
r2 = run_scenario(scenario_b, parse_results=parse_results,
                   config_resolver=shard.resolve_config_path,
                   em_modules_dir=shard.root / "scripts" / "modules")
```

> When you pass `shard=shard`, the function calls `shard.parse_combat_scripts()` internally. If you're running many scenarios, pre-parsing once and passing `parse_results` explicitly avoids redundant parsing.

### Return value

Returns a `CellResult` with aggregated statistics. See [Results](results.md).

## Variable

Defines one axis of a parameter sweep.

```python
@dataclass(frozen=True)
class Variable:
    target: str                   # "attacker" or "defender"
    parameter: str                # Dotted path like "skills.40" or "str_"
    values: tuple[Any, ...] = ()  # Discrete values to test
```

### Supported parameter paths

| Path | Example | What it changes |
|------|---------|-----------------|
| `"str_"` | `100` | Base Strength |
| `"int_"` | `50` | Base Intelligence |
| `"dex_"` | `100` | Base Dexterity |
| `"hp"` | `200` | Hit points |
| `"mana"` | `50` | Mana points |
| `"stamina"` | `100` | Stamina points |
| `"skills.<id>"` | `"skills.40"` = Swordsmanship | Skill display value (0–130) |
| `"class_levels.<id>"` | `"class_levels.IsWarrior"` | Class level (1–5) |
| `"weapon.<field>"` | `"weapon.damage"` | Any WeaponSpec field |
| `"armor.<field>"` | `"armor.ar"` | Any ArmorSpec field |
| `"properties.<name>"` | `"properties.ReactiveArmor"` | Mobile CProps (V1.5) |

### Creating variables

**From a numeric range** (most common):

```python
# Sweep Tactics from 50 to 130, step 10 → [50, 60, 70, 80, 90, 100, 110, 120, 130]
Variable.from_range("attacker", f"skills.{SKILLID_TACTICS}", start=50, stop=130, step=10)
```

The `stop` value is **inclusive** — `from_range(start=50, stop=130, step=10)` includes 130.

**From explicit values** (for non-numeric or irregular sweeps):

```python
# Test specific weapon damages
Variable(
    target="attacker",
    parameter="weapon.damage",
    values=("1d10", "2d6+1", "3d6+2", "4d5+3"),
)

# Test specific AR values
Variable(
    target="defender",
    parameter="armor.ar",
    values=(0, 15, 30, 45, 60),
)
```

## ParameterSweep

Wraps a `Scenario` with one or more `Variable` axes. The sweep runs the Cartesian product of all variable values.

```python
@dataclass(frozen=True)
class ParameterSweep:
    scenario: Scenario                # Base scenario
    variables: tuple[Variable, ...] = ()  # Swept parameters
```

### Single-variable sweep

```python
sweep = ParameterSweep(
    scenario=Scenario(
        attacker=warrior,
        defender=target,
        iterations=500,
        base_seed=42,
    ),
    variables=(
        Variable.from_range("attacker", f"skills.{SKILLID_TACTICS}", 50, 130, 10),
    ),
)
```

This creates 9 cells (50, 60, 70, 80, 90, 100, 110, 120, 130), each running 500 iterations. Total: 4,500 hits.

### Multi-variable sweep (grid)

```python
sweep = ParameterSweep(
    scenario=base_scenario,
    variables=(
        Variable.from_range("attacker", f"skills.{SKILLID_SWORDSMANSHIP}", 50, 100, 25),
        Variable.from_range("defender", "armor.ar", 0, 40, 20),
    ),
)
```

This creates a 3 x 3 = 9 cell grid:

| | AR 0 | AR 20 | AR 40 |
|-|------|-------|-------|
| **Sword 50** | cell | cell | cell |
| **Sword 75** | cell | cell | cell |
| **Sword 100** | cell | cell | cell |

## run_sweep()

Executes a full parameter sweep and returns a `SimulationResult`.

```python
def run_sweep(
    sweep: ParameterSweep,
    *,
    parse_results: dict[Path, ParseResult] | None = None,
    config_resolver: Any = None,
    em_modules_dir: Path | None = None,
    shard: Any = None,
) -> SimulationResult
```

Parameters are the same as `run_scenario()`. Returns a `SimulationResult` with one `CellResult` per grid cell.

```python
result = run_sweep(sweep, shard=shard)

# Access individual cells
for cell in result.cells:
    print(cell.variable_values, f"mean={cell.damage_stats.mean:.1f}")

# Look up a specific cell
cell = result.get_cell(**{f"attacker.skills.{SKILLID_TACTICS}": 100})
```

### Performance

The sweep shares a single `Executor` instance across all cells, avoiding redundant script parsing. Typical throughput is ~374 hits/second for physical-only scenarios. Enchanted weapons with sub-scripts (V1.5) have additional overhead from nested script execution — expect ~200-300 hits/second depending on enchantment complexity. Planning guide:

| Grid | Iterations/cell | Total hits | Estimated time |
|------|----------------|------------|----------------|
| 9 cells | 100 | 900 | ~2s |
| 9 cells | 1000 | 9,000 | ~24s |
| 25 cells | 500 | 12,500 | ~33s |
| 100 cells | 100 | 10,000 | ~27s |

## Spell Scenarios (V3)

Spell scenarios model direct spell casting instead of weapon hits.

**Import path:**
```python
from omega.simulation import (
    SpellScenario, SpellParameterSweep,
    run_spell_scenario, run_spell_sweep,
)
```

### SpellScenario

```python
@dataclass(frozen=True)
class SpellScenario:
    caster: CombatantSpec
    target: CombatantSpec | list[CombatantSpec]
    spell_id: int
    iterations: int = 1000
    base_seed: int = 0
    debug_mode: bool = False
    npc_mode: bool = False
    circle_override: int = 0
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `caster` | `CombatantSpec` | — | The spell caster. Needs Magery and EvalInt skills. |
| `target` | `CombatantSpec` or `list` | — | Single target or list for AoE spells. |
| `spell_id` | `int` | — | Spell ID from `Spell` enum (e.g., `Spell.FIREBALL`). |
| `iterations` | `int` | `1000` | Number of independent casts. |
| `base_seed` | `int` | `0` | RNG seed for reproducibility. |
| `npc_mode` | `bool` | `False` | When `True`, bypasses TryToCast (no fizzle, no mana cost). |
| `circle_override` | `int` | `0` | Override spell circle for damage calculation. |

### run_spell_scenario()

```python
def run_spell_scenario(
    scenario: SpellScenario,
    *,
    shard: Any = None,
    spell_registry: SpellRegistry | None = None,
) -> CellResult
```

Returns a `CellResult` with spell-specific stats: `fizzle_rate`, `resist_rate`, `damage_stats_on_cast`, etc.

### SpellParameterSweep

```python
@dataclass(frozen=True)
class SpellParameterSweep:
    scenario: SpellScenario
    variables: tuple[Variable, ...] = ()
```

Same `Variable` system as weapon sweeps. Targets: `"caster"`, `"target"`.

### run_spell_sweep()

```python
def run_spell_sweep(
    sweep: SpellParameterSweep,
    *,
    shard: Any = None,
    spell_registry: SpellRegistry | None = None,
) -> SimulationResult
```

### Example

```python
from omega.config.spells import Spell

sweep = SpellParameterSweep(
    scenario=SpellScenario(
        caster=CombatantSpec(
            name="Mage",
            skills={SKILLID_MAGERY: 100, SKILLID_EVALINT: 100},
            str_=50, dex_=50, int_=120,
            class_levels={"IsMage": 5},
        ),
        target=CombatantSpec(name="Target", is_npc=True, hp=500),
        spell_id=Spell.FIREBALL,
        iterations=100,
        npc_mode=False,
    ),
    variables=(
        Variable.from_range("caster", f"skills.{SKILLID_MAGERY}", 50, 130, 10),
    ),
)

result = run_spell_sweep(sweep, shard=shard)
```

## Comparing multiple independent scenarios

For scenarios that don't fit a parameter sweep (e.g., different classes, different weapons), run them individually and collect into a dict:

```python
results = {}
for name, scenario in [("Warrior", warrior_scenario), ("Mage", mage_scenario)]:
    results[name] = run_scenario(scenario, shard=shard)

# Use comparison functions
from omega.reporting.plots import comparison_overlay
from omega.reporting.tables import comparison_table

comparison_overlay(results, title="Warrior vs Mage")
comparison_table(results)
```

See [Reporting](reporting.md) for all comparison visualization options and [Examples](examples.md) for complete recipes.

## Reproducibility

Two runs with the same `Scenario` (including the same `base_seed`) produce identical results. This is guaranteed by:

1. Deterministic RNG seeded per iteration (`base_seed XOR iteration_index`)
2. State reset between iterations (snapshot/restore)
3. Single-threaded execution within a scenario

Change the `base_seed` to get a different random sequence:

```python
# Different seeds, same parameters — for checking variance
r1 = run_scenario(Scenario(attacker=..., defender=..., base_seed=42), shard=shard)
r2 = run_scenario(Scenario(attacker=..., defender=..., base_seed=99), shard=shard)
# r1 and r2 will have similar means but different individual results
```
