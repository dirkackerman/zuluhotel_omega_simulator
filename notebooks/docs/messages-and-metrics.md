# Messages and Metrics

The simulator provides three channels for collecting data from eScript execution:

1. **Messages** — debug output from `SendSysMessage()` and similar calls
2. **Metrics** — custom numeric values recorded via `__RecordSimulatorMetric()`
3. **Side effects** — structured events from `ApplyRawDamage()`, `SetPoisoned()`, etc.

This page explains how each channel works, how to enable them, and how to access the collected data.

## 1. Messages: capturing eScript debug output

The shard's combat scripts use `SendSysMessage()` to send debug information to the attacker or defender during execution. In the live game, these appear as floating text. In the simulator, they're routed to Python's logging system.

### The messaging stubs

Three POL messaging functions are stubbed:

| eScript function | Description |
|-----------------|-------------|
| `SendSysMessage(mobile, text, font, color)` | System message to a specific mobile |
| `PrintTextAbove(mobile, text)` | Floating text above a mobile |
| `PrintTextAbovePrivate(mobile, text, viewer)` | Floating text visible only to viewer |

All three behave the same way in the simulator: when `debug_mode` is enabled, they log the message text to the `omega.runtime.messaging` Python logger.

### Enabling message capture

There are two things you need:

1. **`debug_mode=True`** on the `Scenario` — tells the stubs to actually log
2. **A logging handler** at the right level — captures the log output

#### Method A: Scenario debug mode (recommended)

```python
scenario = Scenario(
    attacker=warrior,
    defender=target,
    iterations=5,          # Keep low when debugging
    base_seed=42,
    debug_mode=True,       # Enable message capture
)

result = run_scenario(scenario, shard=shard)
```

With `debug_mode=True`, every `SendSysMessage()` call in the eScript logs to `omega.runtime.messaging` at INFO level. You'll see output like:

```
INFO omega.runtime.messaging: SendSysMessage [target=Warrior, text=Damage before AR: 45]
INFO omega.runtime.messaging: SendSysMessage [target=Warrior, text=AR absorption: 12]
```

#### Method B: Configure logging level for more control

```python
import logging

# See all messaging output
logging.getLogger("omega.runtime.messaging").setLevel(logging.INFO)

# See all runtime activity (includes unimplemented stubs)
logging.getLogger("omega.runtime").setLevel(logging.DEBUG)

# See interpreter-level tracing
logging.getLogger("omega.interpreter").setLevel(logging.DEBUG)
```

#### Method C: Capture to a string buffer

```python
import logging
import io

# Create a string handler
buffer = io.StringIO()
handler = logging.StreamHandler(buffer)
handler.setLevel(logging.INFO)

msg_logger = logging.getLogger("omega.runtime.messaging")
msg_logger.addHandler(handler)
msg_logger.setLevel(logging.INFO)

# Run with debug mode
result = run_scenario(
    Scenario(attacker=warrior, defender=target, iterations=1, debug_mode=True),
    shard=shard,
)

# Read captured messages
messages = buffer.getvalue()
print(messages)

# Clean up
msg_logger.removeHandler(handler)
```

### What gets logged

The shard's combat scripts use `SendSysMessage()` extensively for debug output. Typical messages include:

- Damage calculation steps: `"Damage before AR: 45"`, `"AR absorption: 12"`
- Class bonus application: `"Warrior bonus: 1.5x"`
- Skill checks: `"Tactics check: 100"`
- Final damage: `"Final damage dealt: 33"`

The exact messages depend on the shard scripts. When the scripts change, the messages change.

### Print and other output functions

In addition to `SendSysMessage`, the shard scripts may use:

| Function | Behavior in simulator |
|----------|----------------------|
| `SendSysMessage()` | Logs to `omega.runtime.messaging` when `debug_mode=True` |
| `PrintTextAbove()` | Same — logs to `omega.runtime.messaging` when `debug_mode=True` |
| `PrintTextAbovePrivate()` | Same — logs to `omega.runtime.messaging` when `debug_mode=True` |
| `print()` (eScript) | Handled as a bare function call, dispatched to the `print` stub which logs at DEBUG level |

All messaging output goes through the same logger (`omega.runtime.messaging`), regardless of which specific function the script uses.

## 2. Metrics: `__RecordSimulatorMetric`

The simulator injects a Python function override called `__RecordSimulatorMetric` into the eScript function registry. This provides a way for eScript code to pass structured data back to the Python side.

### How it works

In `execute_hit()`, before running the script, the simulator registers a Python callable:

```python
def _record_metric(key_or_metrics="", value=0):
    if isinstance(key_or_metrics, EStruct):
        # Unpack struct fields
        for k in key_or_metrics.keys():
            ctx.metrics[str(k)] = key_or_metrics.get_member(k)
    elif isinstance(key_or_metrics, dict):
        # Unpack dict
        for k, v in key_or_metrics.items():
            ctx.metrics[str(k)] = v
    else:
        # Single key-value pair
        ctx.metrics[str(key_or_metrics)] = value

executor.functions.set_override("__RecordSimulatorMetric", _record_metric)
```

This override takes highest priority in the [function dispatch chain](runtime.md). When the eScript calls `__RecordSimulatorMetric(...)`, the Python function runs instead of any eScript function of the same name.

### Call patterns from eScript

The metric function supports three calling conventions:

```escript
// Single key-value pair
__RecordSimulatorMetric("absorbed", 12);

// Struct (all fields become metrics)
var metrics := struct{ absorbed := 12, bonus := 1.5 };
__RecordSimulatorMetric(metrics);

// List append — "list:" prefix appends to a list in ctx.metrics
__RecordSimulatorMetric("list:elemental_applied", struct{ type := "fire", gross := 10, net := 7 });
// Result: ctx.metrics["elemental_applied"] = [struct{type, gross, net}, ...]

// The eScript function can be a no-op in the shard code:
function __RecordSimulatorMetric(key := "", value := 0)
    // No-op in production — override active in simulator
endfunction
```

### Accessing metrics

Metrics are stored in `SimulationContext.metrics` (a `dict[str, Any]`). The `execute_hit()` function reads specific metrics after script execution:

```python
# In execute_hit(), after script runs:
result.absorbed = float(ctx.metrics.get("absorbed", 0.0))
```

Metrics are surfaced in `HitResult.metrics` — a dict containing all recorded values for that hit iteration.

### Built-in V1.5 metric keys

These metrics are recorded by the instrumented shard scripts:

| Metric key | Type | Description |
|-----------|------|-------------|
| `"absorbed"` | `float` | Total armor absorption |
| `"elemental_applied"` | `list[struct]` | Per-element damage breakdown (via `list:` prefix) |
| `"planar_applied"` | `list[struct]` | Per-element planar damage breakdown |
| `"resisted"` | `list[struct]` | Resistance application details |
| `"damage_applied"` | `list[struct]` | Per-damage-type final amounts |
| `"effect_type"` | `str` | Enchantment effect type that fired |
| `"spell_strike_spell"` | `int` | Spell ID of spell strike that fired |
| `"spell_strike_damage"` | `float` | Damage dealt by spell strike |
| `"reactive_damage"` | `float` | Damage reflected by reactive armor |

### Accessing metrics per hit

```python
result = run_scenario(scenario, shard=shard)

for hit in result.raw_results[:3]:
    print(f"Absorbed: {hit.metrics.get('absorbed', 0)}")
    # Elemental breakdown (list of per-element records)
    for elem in hit.metrics.get("elemental_applied", []):
        print(f"  {elem.get_member('type')}: {elem.get_member('net')} net")
```

### Adding custom metrics

Add `__RecordSimulatorMetric("your_key", value)` calls to the shard's eScript (inside `if(DEBUG_MODE)` guards). Values appear in `hit.metrics["your_key"]` on the Python side.

### Override mechanism details

The override is registered via `FunctionRegistry.set_override()`:

```python
class FunctionRegistry:
    def set_override(self, name: str, func: Callable) -> None:
        """Register a Python callable that replaces an eScript function."""
        self._overrides[name.lower()] = func

    def get_override(self, name: str) -> Callable | None:
        """Look up a Python override (case-insensitive)."""
        return self._overrides.get(name.lower())
```

The interpreter checks for overrides **first** in its dispatch chain:

```
Function call: __RecordSimulatorMetric(...)
  1. Check Python overrides → FOUND → call Python function
  2. (skipped) Check user-defined eScript functions
  3. (skipped) Check POL built-in stubs
```

This means the override completely replaces any eScript function of the same name. The eScript function can exist (as a no-op fallback for production) but will never run in the simulator.

## 3. Side effects: structured event recording

Side effects are structured events recorded by specific POL stubs during script execution. Unlike messages (text) and metrics (key-value), side effects have a typed schema.

### How stubs record side effects

When a POL stub with side effects runs, it calls methods on `SimulationContext`:

```python
# In structural_stubs.py — ApplyRawDamage:
ctx = get_context()
mobile.hp -= int(amount)
ctx.record_damage(amount)                              # Updates total_damage_dealt
ctx.record_side_effect("damage", mobile.serial,        # Structured event
                       value=amount)

# SetPoisoned:
ctx.record_side_effect("poison_applied", mobile.serial,
                       value=poison_level)

# SetParalyzed:
ctx.record_side_effect("paralyze", mobile.serial,
                       value=bool(flag))

# DestroyItem:
ctx.record_side_effect("item_destroyed", item.serial,
                       detail=item.name)
```

### Side effect flow

```
eScript: ApplyRawDamage(defender, 33)
    │
    ▼
structural_stubs.py: apply_raw_damage()
    ├─ defender.hp -= 33
    ├─ ctx.record_damage(33)           → ctx.total_damage_dealt += 33
    └─ ctx.record_side_effect(...)     → ctx.side_effects.append(SideEffect(...))
    │
    ▼
execute_hit() collects:
    ├─ result.final_damage = ctx.total_damage_dealt     (33.0)
    └─ result.side_effects = list(ctx.side_effects)     ([SideEffect(kind="damage", ...)])
    │
    ▼
aggregate_cell() computes:
    ├─ damage_stats from [hit.final_damage for hit in results]
    └─ ratios from side_effect kind counts:
         hit_rate          = count(final_damage > 0) / N
         poison_rate       = count("poison_applied" in side_effects) / N
         equip_break       = count("equipment_damaged" in side_effects) / N
         reactive_rate     = count("reactive" in side_effects) / N
         spell_strike_rate = count("spell_strike" in metrics) / N
         effect_rate       = count("effect_type" in metrics) / N
```

### Accessing side effects

**Per-hit (via HitResult):**
```python
result = run_scenario(scenario, shard=shard)

for hit in result.raw_results[:5]:
    for se in hit.side_effects:
        print(f"  {se.kind}: value={se.value}, detail={se.detail}")
```

**Aggregated (via RatioStats):**
```python
r = result.ratios
print(f"Hit rate:     {r.hit_rate:.1%}")
print(f"Poison rate:  {r.poison_rate:.1%}")
print(f"Equip break:  {r.equipment_break_rate:.1%}")
```

### SideEffect schema

```python
@dataclass
class SideEffect:
    kind: str              # Event type identifier
    target_serial: int     # Serial number of affected object
    value: Any = None      # Numeric or boolean payload
    detail: str = ""       # Human-readable description
```

### Per-iteration reset

All three channels are reset between iterations:

| Channel | Reset mechanism |
|---------|----------------|
| Messages | Logging output is stateless (no reset needed) |
| Metrics | `ctx.metrics.clear()` in `SimulationContext.reset_hit()` |
| Side effects | `ctx.side_effects.clear()` in `SimulationContext.reset_hit()` |

Damage counters are also reset:
- `ctx.total_damage_dealt = 0.0`
- `ctx.damage_absorbed = 0.0`

This ensures each iteration is an independent observation.

## Logging subsystem overview

The simulator uses Python's `logging` module with named loggers per subsystem:

| Logger | Level | What it logs |
|--------|-------|-------------|
| `omega.parser` | INFO | Parse errors, include resolution |
| `omega.interpreter` | DEBUG | Function calls, control flow (verbose) |
| `omega.runtime` | DEBUG | All stub calls, unimplemented functions |
| `omega.runtime.messaging` | INFO | `SendSysMessage`, `PrintTextAbove` content |
| `omega.simulation` | INFO | Sweep progress, timing |
| `omega.combat` | ERROR | Hit execution failures |
| `omega.config` | INFO | Config file parsing |

### Quick logging setup for notebooks

```python
import logging

# Minimal — just see simulation progress
logging.basicConfig(level=logging.WARNING)

# Moderate — see stub calls and messages
logging.getLogger("omega.runtime").setLevel(logging.INFO)

# Verbose — full interpreter trace (very noisy)
logging.getLogger("omega").setLevel(logging.DEBUG)
```

All loggers use structured kwargs: `logger.info("message", key=value)` which appear as `[key=value]` in the log output.
