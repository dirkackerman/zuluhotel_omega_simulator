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
    metrics: dict[str, Any] = {}

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
| `metrics` | Dictionary of custom metrics from `__RecordSimulatorMetric` calls. See [Messages and Metrics](messages-and-metrics.md). Contains per-hit data like elemental breakdowns, enchantment effects, etc. |
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
| `"hp_set"` | `SetHP()` | new HP value | HP directly set (e.g., reactive armor reflect) |
| `"mana_changed"` | `SetMana()` / drain scripts | delta | Mana changed (e.g., mana drain enchantment) |
| `"stamina_changed"` | `SetStamina()` / drain scripts | delta | Stamina changed (e.g., stamina drain enchantment) |
| `"heal"` | Over-protection healing | heal amount | HP healed via elemental over-protection |
| `"reactive"` | Reactive armor script | damage reflected | Damage reflected back to attacker |

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
    reactive_rate: float = 0.0
    spell_strike_rate: float = 0.0
    effect_rate: float = 0.0
    reactive_rate_on_hit: float = 0.0
    spell_strike_rate_on_hit: float = 0.0
    effect_rate_on_hit: float = 0.0
```

### Overall rates (per swing)

| Field | Description |
|-------|-------------|
| `hit_rate` | Fraction of swings where the attack connected (`final_damage > 0`). Determined by POL's core hit/miss check. |
| `poison_rate` | Fraction of swings where poison was applied |
| `equipment_break_rate` | Fraction of swings where equipment took durability damage (~8% in the shard) |
| `reactive_rate` | Fraction of swings where reactive armor triggered |
| `spell_strike_rate` | Fraction of swings where a spell strike enchantment fired |
| `effect_rate` | Fraction of swings where an effect/greater enchantment fired |

### On-hit rates (per connected swing)

These show the conditional probability given that the swing hit. Misses are excluded from the denominator.

| Field | Description |
|-------|-------------|
| `reactive_rate_on_hit` | Fraction of *hits* where reactive armor triggered |
| `spell_strike_rate_on_hit` | Fraction of *hits* where a spell strike fired |
| `effect_rate_on_hit` | Fraction of *hits* where an effect enchantment fired |

When hit rate is 100%, the overall and on-hit rates are identical.

```python
r = result.ratios
print(f"Hit rate: {r.hit_rate:.1%}")
print(f"Spell strike (overall): {r.spell_strike_rate:.1%}")
print(f"Spell strike (on hit):  {r.spell_strike_rate_on_hit:.1%}")
```

## CellResult

Results for a single scenario — one cell in a sweep grid, or the direct output of `run_scenario()`.

```python
@dataclass
class CellResult:
    variable_values: dict[str, Any] = {}
    damage_stats: DamageStats = DamageStats()          # overall (all swings)
    base_damage_stats: DamageStats = DamageStats()
    absorbed_stats: DamageStats = DamageStats()
    ratios: RatioStats = RatioStats()
    elemental_breakdown: ElementalBreakdown = ElementalBreakdown()
    drain_stats: DamageStats = DamageStats()            # overall drain per swing
    damage_stats_on_hit: DamageStats = DamageStats()    # hits only
    drain_stats_on_hit: DamageStats = DamageStats()     # hits with drain only
    raw_results: list[HitResult] = []
    iteration_count: int = 0
    success_count: int = 0
    error_count: int = 0
```

### Fields

| Field | Description |
|-------|-------------|
| `variable_values` | The swept parameter values for this cell (empty for non-sweep runs). Example: `{"attacker.skills.27": 100}` |
| `damage_stats` | Statistics over **final damage** values, **all swings** (includes 0 for misses). |
| `damage_stats_on_hit` | Statistics over final damage for **hits only** (misses excluded). |
| `base_damage_stats` | Statistics over **base damage** values (weapon dice rolls). |
| `absorbed_stats` | Statistics over **absorbed damage** values (armor reduction). |
| `ratios` | Event frequency ratios — both overall (per swing) and on-hit (per connected swing). |
| `elemental_breakdown` | Per-element damage breakdown (V1.5). Only populated for weapons with `ElementalDamage`. See [Elemental breakdown](#elemental-breakdown). |
| `drain_stats` | Mean drain amount **per swing** (0 for misses and non-drain hits). |
| `drain_stats_on_hit` | Mean drain amount for **hits that drained** only. |
| `raw_results` | All individual `HitResult` objects. Available for deep inspection. |
| `iteration_count` | Total iterations attempted. |
| `success_count` | Iterations that completed without error. |
| `error_count` | Iterations that failed (script execution errors). |

### Overall vs on-hit damage stats

`CellResult` provides two tiers of damage statistics:

| Tier | Field | Includes misses? | Use case |
|------|-------|:-:|---------|
| Overall | `damage_stats` | Yes (0 damage) | Expected damage per swing attempt |
| On-hit | `damage_stats_on_hit` | No | Damage when you connect |

With a 50% hit rate and 20 damage per hit, `damage_stats.mean` ≈ 10, `damage_stats_on_hit.mean` ≈ 20.

### Three damage distributions (overall)

| Distribution | What it measures | Useful for |
|-------------|-----------------|------------|
| `damage_stats` | Final damage applied | Primary balance metric |
| `base_damage_stats` | Weapon dice rolls | Checking weapon damage range |
| `absorbed_stats` | Armor absorption | Evaluating armor effectiveness |

The relationship: `base_damage ≈ final_damage + absorbed` (approximately, before multipliers).

```python
result = run_scenario(scenario, shard=shard)
print(f"Hit rate: {result.ratios.hit_rate:.1%}")
print(f"Overall mean:  {result.damage_stats.mean:.1f}")
print(f"On-hit mean:   {result.damage_stats_on_hit.mean:.1f}")
print(f"Absorbed mean: {result.absorbed_stats.mean:.1f}")
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

## Elemental breakdown (V1.5)

When a weapon has an `ElementalDamage` property, the `CellResult.elemental_breakdown` provides per-element damage statistics.

**Import path:**
```python
from omega.simulation import ElementalBreakdown, ElementDamage
```

### ElementDamage

Per-element statistics (all values are means across iterations):

| Field | Description |
|-------|-------------|
| `gross` | Mean damage before protection reduction |
| `net` | Mean damage after protection reduction |
| `prot` | Mean protection percentage applied |
| `healed` | Mean amount healed via over-protection (>100%) |
| `absorbed` | Computed: `gross - net` |

### ElementalBreakdown

| Method / Property | Description |
|-------------------|-------------|
| `elements` | `dict[str, ElementDamage]` — one entry per active element |
| `total_net` | Sum of net damage across all elements |
| `total_gross` | Sum of gross damage across all elements |
| `net_dict()` | `{element_name: net_damage}` mapping |
| `gross_dict()` | `{element_name: gross_damage}` mapping |
| `prot_dict()` | `{element_name: protection_%}` mapping |

```python
result = run_scenario(scenario, shard=shard)
eb = result.elemental_breakdown

if eb.elements:
    print(f"Total elemental (gross): {eb.total_gross:.1f}")
    print(f"Total elemental (net):   {eb.total_net:.1f}")
    for name, ed in eb.elements.items():
        print(f"  {name}: {ed.gross:.1f} gross → {ed.net:.1f} net ({ed.prot:.0f}% prot)")
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
