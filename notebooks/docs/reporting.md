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
| `"errors"` | `error_count` | Number of failed iterations |

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
