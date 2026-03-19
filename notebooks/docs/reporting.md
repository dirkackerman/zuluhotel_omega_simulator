# Reporting

This page documents the table and plot functions for visualizing simulation results in Jupyter notebooks.

**Import paths:**
```python
from omega.reporting.tables import summary_table, comparison_table, format_table_html
from omega.reporting.plots import (
    damage_histogram,
    damage_vs_parameter,
    damage_breakdown,
    comparison_breakdown,
    comparison_overlay,
    # V1.5 elemental and enchantment plots
    elemental_breakdown_chart,
    elemental_vs_parameter,
    enchantment_comparison,
    # V2 DPS plots
    dps_vs_parameter,
    dps_comparison,
    # V3 spell plots
    spell_comparison,
    fizzle_rate_vs_parameter,
)
```

## Tables

All table functions return `list[dict[str, Any]]` — a list of row dictionaries. This format works with:

- `IPython.display.HTML(format_table_html(rows))` — rendered HTML in notebooks
- `pandas.DataFrame(rows)` — if you want DataFrame operations
- Direct iteration — `for row in rows: ...`

### summary_table()

One row per cell in a sweep result. Columns are variable values followed by stat columns.

```python
def summary_table(
    result: SimulationResult,
    *,
    stats: list[str] | None = None,
) -> list[dict[str, Any]]
```

| Parameter | Description |
|-----------|-------------|
| `result` | A `SimulationResult` from `run_sweep()` |
| `stats` | Which stat columns to include. Defaults to: `mean`, `median`, `min`, `max`, `std_dev`, `p5`, `p95`, `hit_rate`, `count` |

**Available stat column names:**

| Column | Source | Description |
|--------|--------|-------------|
| `"mean"` | `damage_stats.mean` | Mean final damage |
| `"median"` | `damage_stats.median` | Median final damage |
| `"min"` | `damage_stats.min` | Minimum final damage |
| `"max"` | `damage_stats.max` | Maximum final damage |
| `"std_dev"` | `damage_stats.std_dev` | Standard deviation |
| `"p5"` | `damage_stats.p5` | 5th percentile |
| `"p25"` | `damage_stats.p25` | 25th percentile |
| `"p75"` | `damage_stats.p75` | 75th percentile |
| `"p95"` | `damage_stats.p95` | 95th percentile |
| `"count"` | `damage_stats.count` | Number of successful iterations |
| `"base_mean"` | `base_damage_stats.mean` | Mean base (pre-pipeline) damage |
| `"absorbed_mean"` | `absorbed_stats.mean` | Mean absorbed damage |
| `"total"` | `count * mean` | Total damage across all iterations |
| `"hit_rate"` | `ratios.hit_rate` | Fraction of hits dealing damage |
| `"poison_rate"` | `ratios.poison_rate` | Fraction of hits applying poison |
| `"equipment_break_rate"` | `ratios.equipment_break_rate` | Fraction of hits damaging equipment |
| `"reactive_rate"` | `ratios.reactive_rate` | Fraction of hits triggering reactive armor (V1.5) |
| `"spell_strike_rate"` | `ratios.spell_strike_rate` | Fraction of hits firing a spell strike (V1.5) |
| `"effect_rate"` | `ratios.effect_rate` | Fraction of hits firing an effect/greater enchantment (V1.5) |
| `"elem_total_net"` | `elemental_breakdown.total_net` | Total net elemental damage (V1.5) |
| `"elem_total_gross"` | `elemental_breakdown.total_gross` | Total gross elemental damage (V1.5) |
| `"swing_delay_ms"` | `timing.swing_delay_ms` | Swing delay in milliseconds (V2) |
| `"swings_per_sec"` | `timing.swings_per_second` | Attack rate (V2) |
| `"dps_mean"` | `timing.dps_mean` | Mean DPS including misses (V2) |
| `"dps_on_hit"` | `timing.dps_on_hit` | DPS on connected swings only (V2) |
| `"effective_dps"` | `timing.effective_dps` | Effective DPS accounting for hit rate (V2) |
| `"errors"` | `error_count` | Number of failed iterations |
| `"fizzle_rate"` | `ratios.fizzle_rate` | Fraction of casts that fizzled (V3) |
| `"resist_rate"` | `ratios.resist_rate` | Fraction of casts where target resisted (V3) |
| `"resist_rate_on_cast"` | `ratios.resist_rate_on_cast` | Resist rate among successful casts (V3) |
| `"cast_rate"` | `ratios.hit_rate` | Fraction of successful casts (alias for hit_rate) (V3) |
| `"mean_on_cast"` | `damage_stats_on_cast.mean` | Mean damage on successful cast (V3) |
| `"median_on_cast"` | `damage_stats_on_cast.median` | Median damage on successful cast (V3) |
| `"min_on_cast"` | `damage_stats_on_cast.min` | Min damage on successful cast (V3) |
| `"max_on_cast"` | `damage_stats_on_cast.max` | Max damage on successful cast (V3) |
| `"std_dev_on_cast"` | `damage_stats_on_cast.std_dev` | Std dev on successful cast (V3) |
| `"p5_on_cast"` | `damage_stats_on_cast.p5` | 5th percentile on cast (V3) |
| `"p95_on_cast"` | `damage_stats_on_cast.p95` | 95th percentile on cast (V3) |

**Example:**
```python
from IPython.display import HTML

result = run_sweep(sweep, shard=shard)
rows = summary_table(result, stats=["mean", "std_dev", "p5", "p95", "hit_rate"])
HTML(format_table_html(rows))
```

### comparison_table()

Side-by-side comparison of named scenarios. One row per stat, one column per scenario.

```python
def comparison_table(
    cells: dict[str, CellResult],
    *,
    stats: list[str] | None = None,
) -> list[dict[str, Any]]
```

| Parameter | Description |
|-----------|-------------|
| `cells` | `dict` mapping scenario label to `CellResult` |
| `stats` | Which stats to compare. Same column names as `summary_table()`. |

When exactly 2 scenarios are compared, a `"delta"` column is automatically added showing the difference.

**Example:**
```python
results = {
    "Warrior": run_scenario(warrior_scenario, shard=shard),
    "Mage": run_scenario(mage_scenario, shard=shard),
}
rows = comparison_table(results)
HTML(format_table_html(rows))
```

Output structure:
```
| stat     | Warrior | Mage   | delta  |
|----------|---------|--------|--------|
| mean     | 45.20   | 32.10  | -13.10 |
| median   | 44.00   | 31.00  | -13.00 |
| ...      | ...     | ...    | ...    |
```

### format_table_html()

Renders any `list[dict]` as an HTML table with light/dark mode CSS.

```python
def format_table_html(rows: list[dict[str, Any]]) -> str
```

Returns an HTML string. Use with `IPython.display.HTML()`:

```python
from IPython.display import HTML
HTML(format_table_html(rows))
```

The table automatically formats:
- Floats between 0 and 1 as percentages (e.g., `0.95` → `95.0%`)
- Other floats to 2 decimal places
- Integers as-is

## Plots

All plot functions return `matplotlib.figure.Figure` objects. In Jupyter, they display inline automatically. You can also save them:

```python
fig = damage_histogram(result)
fig.savefig("damage_dist.png", dpi=150, bbox_inches="tight")
```

> Matplotlib is an optional dependency. It's included in the `[notebook]` install extras. If not installed, plot functions raise `ImportError` with install instructions.

### damage_histogram()

Histogram of final damage values for a single cell/scenario.

```python
def damage_histogram(
    cell: CellResult,
    *,
    bins: int = 30,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cell` | — | A `CellResult` with `raw_results` populated |
| `bins` | `30` | Number of histogram bins |
| `title` | `"Damage Distribution"` | Figure title |
| `figsize` | `(8, 5)` | Figure size in inches (width, height) |

The histogram overlays vertical lines for the **mean** (red dashed) and **median** (orange dotted).

```python
result = run_scenario(scenario, shard=shard)
damage_histogram(result, title="Warrior vs Target (AR 30)", bins=40)
```

### damage_vs_parameter()

Line plot of mean damage vs. a swept parameter, with optional p5–p95 shaded range.

```python
def damage_vs_parameter(
    result: SimulationResult,
    variable_name: str,
    *,
    show_range: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `result` | — | A `SimulationResult` from `run_sweep()` |
| `variable_name` | — | The variable to plot on the x-axis, e.g., `"attacker.skills.27"` |
| `show_range` | `True` | Shade the p5–p95 range |
| `title` | auto | Figure title |
| `figsize` | `(8, 5)` | Figure size |

The `variable_name` must match the key format in `CellResult.variable_values`. For a sweep created with `Variable.from_range("attacker", f"skills.{SKILLID_TACTICS}", ...)`, the variable name is `"attacker.skills.27"`.

```python
result = run_sweep(sweep, shard=shard)
damage_vs_parameter(result, f"attacker.skills.{SKILLID_TACTICS}",
                    title="Damage vs Tactics")
```

### damage_breakdown()

Grouped bar chart showing mean base damage, absorbed damage, and final damage for a single cell.

```python
def damage_breakdown(
    cell: CellResult,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (6, 4),
) -> Figure
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cell` | — | A `CellResult` |
| `title` | `"Damage Breakdown"` | Figure title |
| `figsize` | `(6, 4)` | Figure size |

Three bars: **Base** (blue), **Absorbed** (orange), **Final** (green), with value labels above each bar.

```python
result = run_scenario(scenario, shard=shard)
damage_breakdown(result, title="Damage Pipeline Breakdown")
```

### comparison_breakdown()

Grouped bar chart comparing base/absorbed/final damage across multiple named scenarios.

```python
def comparison_breakdown(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cells` | — | `dict` mapping label to `CellResult` |
| `title` | `"Damage Breakdown Comparison"` | Figure title |
| `figsize` | `(8, 5)` | Figure size |

Each scenario gets three side-by-side bars (base, absorbed, final).

```python
results = {
    "Warrior": run_scenario(warrior_scenario, shard=shard),
    "Ranger": run_scenario(ranger_scenario, shard=shard),
    "Mage": run_scenario(mage_scenario, shard=shard),
}
comparison_breakdown(results, title="Class Damage Comparison")
```

### comparison_overlay()

Overlaid histograms comparing damage distributions across multiple scenarios.

```python
def comparison_overlay(
    cells: dict[str, CellResult],
    *,
    bins: int = 30,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cells` | — | `dict` mapping label to `CellResult` |
| `bins` | `30` | Number of histogram bins |
| `title` | `"Damage Comparison"` | Figure title |
| `figsize` | `(8, 5)` | Figure size |

Each scenario is shown as a semi-transparent histogram with its mean in the legend.

```python
comparison_overlay(results, bins=40, title="Warrior vs Ranger vs Mage")
```

### elemental_breakdown_chart() (V1.5)

Stacked bar chart showing per-element damage (gross vs net) for a single cell.

```python
def elemental_breakdown_chart(
    cell: CellResult,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

Shows each active element with gross damage, net damage (after protection), and absorbed amount.

```python
result = run_scenario(fire_weapon_scenario, shard=shard)
elemental_breakdown_chart(result, title="Fire Sword Element Breakdown")
```

### elemental_vs_parameter() (V1.5)

Line plot of per-element net damage vs. a swept parameter.

```python
def elemental_vs_parameter(
    result: SimulationResult,
    variable_name: str,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

Shows how each element's damage changes across the sweep, with one line per element.

```python
result = run_sweep(fire_resistance_sweep, shard=shard)
elemental_vs_parameter(result, "defender.properties.FireProtection",
                       title="Fire Damage vs Fire Resistance")
```

### enchantment_comparison() (V1.5)

Bar chart comparing mean damage across different enchantments.

```python
def enchantment_comparison(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

Each bar represents a named scenario (typically with a different enchantment), showing mean damage with error bars.

```python
from omega.config.enchantments import Enchantment

results = {
    "Plain": run_scenario(plain_scenario, shard=shard),
    "Fireball": run_scenario(fireball_scenario, shard=shard),
    "Silver": run_scenario(silver_scenario, shard=shard),
}
enchantment_comparison(results, title="Enchantment Effectiveness")
```

### armor_enchantment_comparison() (V3.1)

Grouped bar chart comparing armor enchantments by physical damage received plus onhit additional damage, with trigger rate overlay.

```python
def armor_enchantment_comparison(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 6),
) -> Figure
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cells` | -- | `dict` mapping label to `CellResult` |
| `title` | `"Armor Enchantment Comparison"` | Figure title |
| `figsize` | `(10, 6)` | Figure size |

Each bar group shows two stacked components: **Physical damage** (blue) and **OnHit Additional damage** (orange). A secondary y-axis displays the onhit trigger rate as an overlay line (red dashed). This follows the same pattern as `enchantment_comparison()` for weapon enchantments.

```python
from omega.reporting.plots import armor_enchantment_comparison

results = {
    "Plain": run_scenario(plain_armor_scenario, shard=shard),
    "Fire Plate": run_scenario(fire_armor_scenario, shard=shard),
    "Piercing Plate": run_scenario(piercing_armor_scenario, shard=shard),
}
armor_enchantment_comparison(results, title="Armor Enchantment Effectiveness")
```

### dps_vs_parameter() (V2)

Dual-axis line plot of DPS and swing delay vs. a swept parameter.

```python
def dps_vs_parameter(
    result: SimulationResult,
    variable_name: str,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

Left axis shows effective DPS (line), right axis shows swing delay in milliseconds (dashed line). Useful for understanding how DEX or weapon speed affects both attack rate and damage output simultaneously.

```python
result = run_sweep(dex_sweep, shard=shard)
dps_vs_parameter(result, "attacker.dex_", title="DPS vs Dexterity")
```

### dps_comparison() (V2)

Bar chart comparing DPS across named scenarios with delay annotations.

```python
def dps_comparison(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

Each bar shows effective DPS with the swing delay annotated. Useful for comparing weapons with different speeds to see which delivers the best sustained damage output.

```python
results = {
    "Slow Axe (Speed 15)": axe_result,
    "Medium Sword (Speed 50)": sword_result,
    "Fast Bow (Speed 98)": bow_result,
}
dps_comparison(results, title="DPS by Weapon Speed")
```

### spell_comparison() (V3)

Grouped bar chart comparing spells by mean on-cast damage, color-coded by dominant element.

```python
def spell_comparison(
    cells: dict[str, CellResult],
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 6),
    show_fizzle: bool = True,
    show_resist: bool = True,
) -> Figure
```

Each bar shows `damage_stats_on_cast.mean`, colored by the spell's dominant element. Optional annotations show fizzle rate and resist rate below each bar.

```python
from omega.config.spells import Spell
from omega.simulation import SpellScenario, run_spell_scenario

cells = {
    "Fireball": run_spell_scenario(fireball_scenario, shard=shard),
    "Lightning": run_spell_scenario(lightning_scenario, shard=shard),
}
spell_comparison(cells, title="Spell Damage Comparison")
```

### fizzle_rate_vs_parameter() (V3)

Dual-line plot of fizzle rate and resist rate across a swept parameter.

```python
def fizzle_rate_vs_parameter(
    result: SimulationResult,
    variable_name: str,
    *,
    show_resist: bool = True,
    title: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure
```

Shows `ratios.fizzle_rate` (solid line) and optionally `ratios.resist_rate_on_cast` (dashed line) across a parameter sweep. Y-axis is 0--100%.

```python
result = run_spell_sweep(magery_sweep, shard=shard)
fizzle_rate_vs_parameter(result, f"caster.skills.{SKILLID_MAGERY}",
                         title="Fizzle & Resist vs Magery")
```

## Combining tables and plots

A typical analysis cell in a notebook:

```python
from IPython.display import HTML, display

# Run sweep
result = run_sweep(sweep, shard=shard)

# Table
rows = summary_table(result, stats=["mean", "median", "std_dev", "p5", "p95"])
display(HTML(format_table_html(rows)))

# Damage curve
damage_vs_parameter(result, f"attacker.skills.{SKILLID_TACTICS}")

# Histogram for a specific cell
cell_100 = result.get_cell(**{f"attacker.skills.{SKILLID_TACTICS}": 100})
if cell_100:
    damage_histogram(cell_100, title="Tactics = 100")
```
