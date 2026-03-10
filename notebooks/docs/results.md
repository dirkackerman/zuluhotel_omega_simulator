# Results

This page documents the result objects returned by `run_scenario()` and `run_sweep()`, and how to interpret the statistics.

**Import path:**
```python
from omega.simulation import CellResult, DamageStats, RatioStats, SimulationResult
from omega.combat.result import HitResult
```

## HitResult

The output of a single hit iteration. You rarely work with these directly — they're aggregated into `CellResult` — but they're available for deep inspection.

```python
@dataclass
class HitResult:
    base_damage: int = 0
    raw_damage: int = 0
    final_damage: float = 0.0
    absorbed: float = 0.0

    attacker_name: str = ""
    defender_name: str = ""
    defender_hp_before: int = 0
    defender_hp_after: int = 0

    side_effects: list[SideEffect] = []
    hit_log: list[str] = []

    success: bool = True
    error: str | None = None
```

### Fields

| Field | Description |
|-------|-------------|
| `base_damage` | Weapon dice roll before any modifiers. For `3d6+2`, this is 5–20. |
| `raw_damage` | Damage value passed to `mainhit.src` (equals `base_damage` at entry). |
| `final_damage` | Total damage actually applied to the defender via `ApplyRawDamage()`. This is the post-pipeline number after slayer bonuses, class bonuses, skill scaling, and armor absorption. |
| `absorbed` | Damage absorbed by armor, as reported by the `__RecordSimulatorMetric("absorbed", ...)` call in the script. See [Messages and Metrics](messages-and-metrics.md). |
| `attacker_name` | Attacker's display name. |
| `defender_name` | Defender's display name. |
| `defender_hp_before` | Defender's HP before the hit. |
| `defender_hp_after` | Defender's HP after the hit. |
| `side_effects` | List of `SideEffect` events recorded during execution. See [Side effects](#side-effects). |
| `hit_log` | Reserved for future use (per-hit debug log). |
| `success` | `True` if the script executed without errors. |
| `error` | Error message if `success` is `False`. |

### Side effects

Each `SideEffect` records an event from a POL stub call:

```python
@dataclass
class SideEffect:
    kind: str              # Event type
    target_serial: int     # Which object was affected
    value: Any = None      # Numeric or boolean payload
    detail: str = ""       # Human-readable description
```

| `kind` | Source | `value` | Meaning |
|--------|--------|---------|---------|
| `"damage"` | `ApplyRawDamage()` | damage amount | HP reduced on target |
| `"poison_applied"` | `SetPoisoned()` | poison level | Poison was applied |
| `"paralyze"` | `SetParalyzed()` | `True`/`False` | Paralyze toggled |
| `"item_destroyed"` | `DestroyItem()` | — | Item was destroyed |
| `"equipment_damaged"` | Equipment stub | — | Equipment took durability damage |

### Inspecting individual hits

```python
result = run_scenario(scenario, shard=shard)

# Access raw results
for hit in result.raw_results[:5]:
    print(f"base={hit.base_damage}, final={hit.final_damage:.1f}, "
          f"absorbed={hit.absorbed:.1f}, success={hit.success}")

# Find hits with side effects
poisoned = [h for h in result.raw_results if any(se.kind == "poison_applied" for se in h.side_effects)]
print(f"Poison applied in {len(poisoned)} / {len(result.raw_results)} hits")
```

## DamageStats

Statistical summary computed from a list of damage values.

```python
@dataclass(slots=True)
class DamageStats:
    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    min: float = 0.0
    max: float = 0.0
    std_dev: float = 0.0
    p5: float = 0.0
    p25: float = 0.0
    p75: float = 0.0
    p95: float = 0.0
```

### Fields

| Field | Description |
|-------|-------------|
| `count` | Number of samples (successful iterations) |
| `mean` | Arithmetic mean — the "expected" damage per hit |
| `median` | Middle value — less sensitive to outliers than mean |
| `min` | Lowest damage observed |
| `max` | Highest damage observed |
| `std_dev` | Standard deviation — measures spread. Low = consistent, high = swingy. |
| `p5` | 5th percentile — "bad luck" floor (95% of hits deal more than this) |
| `p25` | 25th percentile — lower quartile |
| `p75` | 75th percentile — upper quartile |
| `p95` | 95th percentile — "good luck" ceiling (only 5% of hits exceed this) |

### Interpreting the stats

**Mean vs Median**: If mean >> median, the distribution is right-skewed (rare big hits pulling the average up). If they're close, the distribution is roughly symmetric.

**Std dev**: A useful rule of thumb — about 68% of hits fall within `mean +/- std_dev`. Low std dev means predictable damage, high means swingy.

**p5–p95 range**: The "realistic" damage range, excluding extreme outliers. Useful for understanding what a player actually experiences most of the time.

```python
ds = result.damage_stats
print(f"Average: {ds.mean:.1f} +/- {ds.std_dev:.1f}")
print(f"Typical range: {ds.p5:.0f} – {ds.p95:.0f}")
print(f"Full range: {ds.min:.0f} – {ds.max:.0f}")
```

## RatioStats

Event frequency ratios (0.0–1.0) computed from side effect counts.

```python
@dataclass(slots=True)
class RatioStats:
    hit_rate: float = 0.0
    poison_rate: float = 0.0
    equipment_break_rate: float = 0.0
```

| Field | Description |
|-------|-------------|
| `hit_rate` | Fraction of iterations where `final_damage > 0`. Usually 1.0 unless armor fully absorbs. |
| `poison_rate` | Fraction of iterations where poison was applied (from weapon charges etc.) |
| `equipment_break_rate` | Fraction of iterations where equipment took durability damage (~8% in the shard) |

```python
r = result.ratios
print(f"Hit rate: {r.hit_rate:.1%}")
print(f"Poison: {r.poison_rate:.1%}")
print(f"Equip break: {r.equipment_break_rate:.1%}")
```

## CellResult

Results for a single scenario — one cell in a sweep grid, or the direct output of `run_scenario()`.

```python
@dataclass
class CellResult:
    variable_values: dict[str, Any] = {}
    damage_stats: DamageStats = DamageStats()
    base_damage_stats: DamageStats = DamageStats()
    absorbed_stats: DamageStats = DamageStats()
    ratios: RatioStats = RatioStats()
    raw_results: list[HitResult] = []
    iteration_count: int = 0
    success_count: int = 0
    error_count: int = 0
```

### Fields

| Field | Description |
|-------|-------------|
| `variable_values` | The swept parameter values for this cell (empty for non-sweep runs). Example: `{"attacker.skills.27": 100}` |
| `damage_stats` | Statistics over **final damage** values (post-pipeline). |
| `base_damage_stats` | Statistics over **base damage** values (weapon dice rolls). |
| `absorbed_stats` | Statistics over **absorbed damage** values (armor reduction). |
| `ratios` | Event frequency ratios. |
| `raw_results` | All individual `HitResult` objects. Available for deep inspection. |
| `iteration_count` | Total iterations attempted. |
| `success_count` | Iterations that completed without error. |
| `error_count` | Iterations that failed (script execution errors). |

### Three damage distributions

A `CellResult` provides three separate statistical summaries:

| Distribution | What it measures | Useful for |
|-------------|-----------------|------------|
| `damage_stats` | Final damage applied | Primary balance metric |
| `base_damage_stats` | Weapon dice rolls | Checking weapon damage range |
| `absorbed_stats` | Armor absorption | Evaluating armor effectiveness |

The relationship: `base_damage ≈ final_damage + absorbed` (approximately, before multipliers).

```python
result = run_scenario(scenario, shard=shard)
print(f"Base:     {result.base_damage_stats.mean:.1f}")
print(f"Absorbed: {result.absorbed_stats.mean:.1f}")
print(f"Final:    {result.damage_stats.mean:.1f}")
```

## SimulationResult

Output of `run_sweep()` — contains all cells from a parameter sweep.

```python
@dataclass
class SimulationResult:
    cells: list[CellResult] = []
    total_time: float = 0.0
```

### Fields

| Field | Description |
|-------|-------------|
| `cells` | One `CellResult` per grid point, in Cartesian product order. |
| `total_time` | Wall-clock time for the entire sweep, in seconds. |

### Methods

#### `get_cell(**variable_values) -> CellResult | None`

Look up a specific cell by its variable values:

```python
result = run_sweep(sweep, shard=shard)

# Find the cell where Tactics = 100
cell = result.get_cell(**{f"attacker.skills.{SKILLID_TACTICS}": 100})
if cell:
    print(f"Mean damage at Tactics 100: {cell.damage_stats.mean:.1f}")
```

#### `damage_curve(variable_name) -> list[tuple[Any, DamageStats]]`

Extract `(value, DamageStats)` pairs for a single swept variable. Useful for manual plotting or data extraction:

```python
curve = result.damage_curve(f"attacker.skills.{SKILLID_TACTICS}")
for value, stats in curve:
    print(f"Tactics {value}: mean={stats.mean:.1f}, p5={stats.p5:.1f}, p95={stats.p95:.1f}")
```

### Iterating cells

```python
# Print all cells
for cell in result.cells:
    vals = ", ".join(f"{k}={v}" for k, v in cell.variable_values.items())
    print(f"[{vals}] mean={cell.damage_stats.mean:.1f} ({cell.success_count}/{cell.iteration_count} ok)")

# Filter to cells with errors
bad = [c for c in result.cells if c.error_count > 0]
```

## Error handling

When a script execution fails (interpreter error, unimplemented built-in, etc.), the iteration is recorded with `success=False` and the error message is captured. The iteration still counts toward `iteration_count` but is excluded from statistical aggregation.

```python
result = run_scenario(scenario, shard=shard)

if result.error_count > 0:
    print(f"Errors: {result.error_count}/{result.iteration_count}")
    # Inspect individual errors
    errors = [h for h in result.raw_results if not h.success]
    for e in errors[:3]:
        print(f"  {e.error}")
```

A high error count may indicate an unimplemented POL built-in on the code path. See [Runtime](runtime.md) for details on the stub system.
