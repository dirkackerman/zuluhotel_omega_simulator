# Runtime

This page explains how the simulator executes the shard's eScript combat scripts. Understanding this layer is useful when debugging unexpected results, interpreting log output, or extending the simulator with new stubs.

## Architecture overview

The simulator doesn't run a POL server. Instead, it:

1. **Parses** the shard's `.src` and `.inc` files into syntax trees (ANTLR4-based)
2. **Walks** the syntax trees with a Python interpreter (`Executor`)
3. **Stubs** POL engine functions (`SendSysMessage`, `ApplyRawDamage`, etc.) with Python implementations
4. **Records** results in a `SimulationContext` that's accessible from all stubs

```
┌──────────────────────────────────────────────────────────────────┐
│  Notebook: run_scenario(scenario, shard=shard)                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Runner (runner.py)                                        │  │
│  │    For each iteration:                                     │  │
│  │      1. Reset combatant state (snapshot/restore)           │  │
│  │      2. Set RNG seed (base_seed XOR iteration)             │  │
│  │      3. Call execute_hit()                                 │  │
│  │      4. Collect HitResult                                  │  │
│  │    Aggregate into CellResult                               │  │
│  └────────────────┬───────────────────────────────────────────┘  │
│                   │                                              │
│  ┌────────────────▼───────────────────────────────────────────┐  │
│  │  execute_hit() (hit.py)                                    │  │
│  │    1. Roll base damage (or use override)                   │  │
│  │    2. Create SimulationContext (attacker, defender, weapon) │  │
│  │    3. Register objects (serial-based lookup)               │  │
│  │    4. Inject __RecordSimulatorMetric override              │  │
│  │    5. executor.run_program({attacker, defender, weapon,    │  │
│  │         armor, basedamage, rawdamage})                     │  │
│  │    6. Collect: final_damage, absorbed, side_effects        │  │
│  └────────────────┬───────────────────────────────────────────┘  │
│                   │                                              │
│  ┌────────────────▼───────────────────────────────────────────┐  │
│  │  Executor (executor.py)                                    │  │
│  │    - Holds parsed syntax trees for all files               │  │
│  │    - Manages ScopeStack (global + function-local scopes)   │  │
│  │    - Manages FunctionRegistry (user + override + builtin)  │  │
│  │    - Runs mainhit.src program block                        │  │
│  │                                                            │  │
│  │  EscriptInterpreter (evaluator.py)                         │  │
│  │    - Tree-walking visitor for all eScript constructs       │  │
│  │    - Dispatches function calls through 3-tier resolution   │  │
│  └────────────────┬───────────────────────────────────────────┘  │
│                   │                                              │
│  ┌────────────────▼───────────────────────────────────────────┐  │
│  │  POL Built-in Stubs (runtime/)                             │  │
│  │    basic_stubs.py     — CInt, Random, SendSysMessage, ...  │  │
│  │    object_stubs.py    — GetObjProperty, GetEffectiveSkill  │  │
│  │    structural_stubs.py — ReadConfigFile, ApplyRawDamage    │  │
│  │                                                            │  │
│  │  SimulationContext (context.py)                             │  │
│  │    - Central state: attacker, defender, weapon              │  │
│  │    - Side effects, damage counters, metrics dict            │  │
│  │    - Accessed via contextvars (thread-safe, no param pass)  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Executor lifecycle

The `Executor` is the top-level orchestrator for script execution.

### Construction (once per scenario)

```python
executor = Executor(parse_results, em_modules_dir=em_modules_dir)
```

On construction, the Executor:

1. Registers all user-defined functions from all parsed files into the `FunctionRegistry`
2. Processes `use` declarations (e.g., `use uo;`, `use vitals;`) to know which modules are available
3. Evaluates top-level constants (e.g., `const FOO := 42;`)
4. Locates the `program` block (in `mainhit.src`)
5. Takes a **snapshot** of the global scope state

### Per-iteration reset

```python
executor.reset()
```

Restores global scope variables to the snapshot taken at construction. This is much cheaper than re-parsing and re-building the executor.

### Program execution

```python
executor.run_program({
    "attacker": attacker_mobile,
    "defender": defender_mobile,
    "weapon": weapon_obj,
    "armor": armor_obj,
    "basedamage": 15,
    "rawdamage": 15,
})
```

Binds the program arguments to the parameter names declared in `program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)`, then executes the program block.

## Function call dispatch

When the interpreter encounters a function call, it follows a three-tier resolution order:

### 1. Python callable overrides (highest priority)

Registered via `executor.functions.set_override(name, callable)`. Used for injecting Python functions that replace eScript functions. The primary use case is `__RecordSimulatorMetric` — see [Messages and Metrics](messages-and-metrics.md).

```python
# In execute_hit():
executor.functions.set_override("__RecordSimulatorMetric", _record_metric)
```

When the eScript calls `__RecordSimulatorMetric(...)`, the interpreter calls the Python function instead.

### 2. User-defined eScript functions

Functions declared in the shard's `.src` and `.inc` files (e.g., `function RecalcDmg(...)`) are registered in the `FunctionRegistry` during Executor construction. These are regular eScript functions executed by the tree-walker.

### 3. POL built-in stubs (lowest priority)

Functions provided by the POL engine (e.g., `SendSysMessage`, `GetObjProperty`, `ApplyRawDamage`) are implemented as Python stubs. The interpreter dispatches these via `call_builtin(module, name, args)`.

### Scoped vs bare calls

eScript supports both scoped and bare function calls:

```escript
// Scoped call — module prefix
uo::SendSysMessage(who, "hello");

// Bare call — no module prefix
SendSysMessage(who, "hello");
```

The dispatcher handles both:
- Scoped: looks up `(module, name)` directly
- Bare: tries user-defined functions first, then falls back to `("", name)` in the stub registry
- If a scoped lookup fails, it falls back to the bare lookup as well

## POL built-in stub system

### How stubs are registered

Stubs use the `@pol_function(module, name)` decorator:

```python
from omega.runtime.registry import pol_function

@pol_function("uo", "GetObjProperty")
@pol_function("", "GetObjProperty")    # Also register for bare calls
def get_obj_property(obj, name):
    return obj.get_property(name)
```

A single Python function can be registered under multiple `(module, name)` pairs — this is common for functions that scripts call both scoped (`uo::GetObjProperty`) and bare (`GetObjProperty`).

### Stub categories

The stubs are organized into three files by complexity:

**`basic_stubs.py`** — ~30 trivial stubs:
- Type casts: `CInt()`, `CDbl()`, `CStr()`, `Hex()`
- Math: `Random()`, `RandomInt()`, `Pow()`, `Max()`, `Min()`, `Abs()`, `Sqrt()`
- String: `SplitWords()`, `Lower()`, `Upper()`, `SubStr()`
- Messaging: `SendSysMessage()`, `PrintTextAbove()`, `PrintTextAbovePrivate()` — log to `omega.runtime.messaging` when `debug_mode=True`
- Time: `ReadGameClock()` — returns simulated clock from context
- No-ops: `PerformAction()`, `PlaySoundEffect()`, `SetWarMode()`, etc.

**`object_stubs.py`** — ~20 object model stubs:
- Property bags: `GetObjProperty()`, `SetObjProperty()`, `EraseObjProperty()`
- Stats: `GetStrength()`, `GetDexterity()`, `GetIntelligence()`
- Vitals: `GetHP()`, `GetMaxHP()`, `GetMana()`, `GetStamina()`, `SetMana()`, `SetStamina()`
- Skills: `GetEffectiveSkill()`, `GetAttribute()`, `GetBaseSkill()`
- Equipment: `GetEquipmentByLayer()`, `ListEquippedItems()`

**`structural_stubs.py`** — ~10 structural stubs:
- Config: `ReadConfigFile()`, `FindConfigElem()`, `GetConfigInt()`, `GetConfigString()`
- Damage: `ApplyRawDamage()` — the critical stub that modifies HP and records damage
- Side effects: `SetPoisoned()`, `SetParalyzed()`, `DestroyItem()`
- Lookup: `SystemFindObjectBySerial()`, `FindGuild()`
- Script control: `start_script()` — logs a warning and returns `None` (V1: skipped)

### Unimplemented functions

When the interpreter encounters a function with no matching stub, it:

1. Logs at DEBUG level: `"Unimplemented built-in: module::function(... N args)"`
2. Returns `None`

This doesn't raise an error — the script continues executing with `None` as the return value. This is intentional: many POL functions are called on the combat path but their return values aren't used (e.g., sound effects, visual effects).

To see which built-in functions are being called but not implemented:

```python
import logging
logging.getLogger("omega.runtime").setLevel(logging.DEBUG)
```

### Listing registered stubs

```python
from omega.runtime.registry import list_registered

for module, name in sorted(list_registered()):
    print(f"{module}::{name}" if module else name)
```

## SimulationContext

The `SimulationContext` is the central state container for each hit execution. All stubs access it via `get_context()` from `contextvars` — no parameter threading required.

### Key fields

| Field | Type | Description |
|-------|------|-------------|
| `attacker` | `Mobile` | The attacking mobile |
| `defender` | `Mobile` | The defending mobile |
| `weapon` | `Weapon` | The weapon used |
| `debug_mode` | `bool` | Enables verbose logging from messaging stubs |
| `game_clock` | `int` | Simulated clock (increments each iteration) |
| `side_effects` | `list[SideEffect]` | Events recorded during this hit |
| `total_damage_dealt` | `float` | Cumulative damage from `ApplyRawDamage()` calls |
| `damage_absorbed` | `float` | Cumulative armor absorption |
| `metrics` | `dict[str, Any]` | Custom metrics from `__RecordSimulatorMetric` |
| `executor` | `Executor \| None` | The script executor (used by `start_script()` for sub-scripts) |
| `_object_registry` | `dict[int, Any]` | Objects by serial (for `SystemFindObjectBySerial`) |
| `_config_cache` | `dict[str, Any]` | Cached parsed config files |
| `_config_resolver` | callable | Resolves `:pkg:name` config paths to filesystem paths |

### Per-iteration reset

Between iterations, `reset_hit()` clears:
- `side_effects` list
- `total_damage_dealt` and `damage_absorbed` counters
- `metrics` dictionary

It preserves:
- `_config_cache` (configs don't change between iterations)
- `_object_registry` (same objects, restored to original state by snapshot/restore)

### Context access pattern

```python
from omega.runtime.context import get_context

# Inside any POL stub:
ctx = get_context()
defender = ctx.defender
ctx.record_damage(25.0)
ctx.record_side_effect("poison_applied", defender.serial, value=3)
```

This pattern means stubs don't need the context passed as a parameter — they retrieve it from the thread-local `contextvars.ContextVar`.

## Deterministic RNG

The simulator provides a seeded RNG that replaces POL's `Random()` and `RandomInt()` functions.

```python
from omega.runtime.rng import SimulationRNG, set_rng_seed, get_rng

rng = set_rng_seed(42)  # Set seed, store in contextvars
```

| eScript function | POL semantics | Python stub |
|-----------------|---------------|-------------|
| `Random(n)` | Returns `[1, n]` inclusive | `rng.random(n)` |
| `RandomInt(n)` | Returns `[0, n-1]` inclusive | `rng.random_int(n)` |

The RNG is seeded per iteration with `base_seed XOR iteration_index`. This guarantees:
- **Reproducibility**: Same seed + same inputs = identical results
- **Independence**: Different iterations get different random sequences
- **Isolation**: Each iteration's randomness is unaffected by how many prior iterations ran

## State model: how eScript resolves values

When eScript accesses combatant properties, the call chain is:

### Stats (STR, DEX, INT)

```escript
// eScript:
var str := GetStrength(attacker);
```
```
→ object_stubs.py: get_strength(mobile)
  → mobile.str_base + mobile.str_mod
  → returns integer (e.g., 100)
```

### Skills

```escript
// eScript:
var skill := GetEffectiveSkill(attacker, SKILLID_TACTICS);
```
```
→ object_stubs.py: get_effective_skill(mobile, skill_id)
  → mobile.get_skill(skill_id)
  → returns internal value (0–1300), where 1000 = display 100.0
```

### Object properties

```escript
// eScript:
var slaytype := GetObjProperty(weapon, "SlayType");
```
```
→ object_stubs.py: get_obj_property(obj, name)
  → obj.get_property("SlayType")
  → returns the property value, or None if not set
```

Properties are a key-value store on every game object. The class system uses them (e.g., `GetObjProperty(mobile, "IsWarrior")` returns the class level), as do weapon enchantments (`"SlayType"`, `"DamageType"`, etc.).

### Config files

```escript
// eScript:
var cfg := ReadConfigFile(":combat:settings");
var elem := FindConfigElem(cfg, "General");
var val := GetConfigInt(elem, "SomeKey");
```
```
→ structural_stubs.py: read_config_file(path)
  → ctx._config_resolver(":combat:settings") → filesystem Path
  → parse_config_file(path) → ConfigFile
  → cached in ctx._config_cache
```

Config files are parsed once and cached per scenario. The resolver maps POL package paths (`:combat:settings`) to actual filesystem paths.

### Damage application

```escript
// eScript:
ApplyRawDamage(defender, damage);
```
```
→ structural_stubs.py: apply_raw_damage(mobile, amount)
  → mobile.hp -= int(amount)
  → if mobile.hp <= 0: mobile._dead = True
  → ctx.record_damage(amount)
  → ctx.record_side_effect("damage", mobile.serial, value=amount)
```

This is the critical stub — it's where damage is finalized. The `final_damage` in `HitResult` comes from `ctx.total_damage_dealt`, which accumulates all `ApplyRawDamage()` calls within one hit execution. In practice, `mainhit.src` calls `ApplyRawDamage()` exactly once per hit.

## Sub-script execution (`start_script()`)

The shard's combat scripts call `start_script()` to launch sub-scripts for enchantments, reactive armor, and on-hit effects. As of V1.5, these are fully executed by the simulator.

### How it works

When the interpreter encounters `start_script(":combat:spellstrikescript", attacker, defender, weapon)`, it:

1. Resolves the package path to a parsed script file
2. Creates a nested `Executor` with the sub-script's syntax tree
3. Binds the arguments to the sub-script's program parameters
4. Executes the sub-script in the same `SimulationContext` (shared state, same RNG)
5. Records any side effects (spell damage, drains, reactive armor hits)

### Supported sub-scripts

| Script | Enchantment type | What it does |
|--------|-----------------|--------------|
| `spellstrikescript` | Spell (1–18) | Casts a spell on hit (e.g., Fireball, Lightning) |
| `slayerscript` | Slayer (19–35) | Bonus damage vs matching creature type |
| `piercingscript` | Effect | Ignores armor |
| `banishscript` | Effect | Banishes summoned creatures |
| `poisonhit` | Effect | Applies poison |
| `lifedrainscript` | Effect | Drains HP |
| `manadrainscript` | Effect | Drains mana |
| `staminadrainscript` | Effect | Drains stamina |
| `blindingscript` | Effect | Blinds target |
| `dualplanarscript` | Greater | Dual-element damage |
| `voidscript` | Greater | Void damage |
| `trielementalscript` | Greater | Tri-element damage |
| `reactivearmor` | Reactive | Reflects physical damage to attacker |

### V1.5 stubs added for sub-scripts

The following POL stubs were added to support sub-script execution:

- `GetVital(mobile, vital_name)` / `SetVital(mobile, vital_name, value)` — read/write vitals by name
- `SetHP(mobile, value)` — direct HP setter
- `GetMaxMana(mobile)` / `GetMaxStamina(mobile)` — max vital accessors
- `MoveObjectToLocation(obj, x, y, z)` — no-op (visual effect)
- `Find(type, objtype, flags)` — returns empty array (no world search in simulation)
- `PlayLightningBoltEffect(mobile)` — no-op (visual effect)
- `send_attack(mobile, target)` — no-op (combat state)
