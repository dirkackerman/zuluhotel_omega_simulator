# Path to V1 — Physical Damage PoC

## Overview

V1 delivers: a game designer can define an attacker and defender (by class/skills/stats/weapon/armor or by NPC template name), run N simulated physical hits, and get statistical output (mean/median/min/max/distribution/breakdown) in a Jupyter notebook with graphs.

## Dependency Graph

```
M1 (Project Setup)
 ├─► M2 (eScript Parser)
 │    └─► M5 (Interpreter)
 │         └─► M7 (Combat Integration)
 │              └─► M8 (Simulation Runner)
 │                   └─► M9 (Reporting & Notebooks)
 │                        └─► M10 (Validation & Polish)
 ├─► M3 (Config Parsers)
 │    └─► M4 (Game Object Model)
 │         └─► M6 (POL Runtime Stubs)
 │              └─► M7
 └─► M0 (Logging Framework) — used by all milestones
```

M2 and M3/M4 can be developed in parallel. They converge at M7.

---

## M0 — Logging Framework
**Status**: [x] Complete

**Goal**: Establish structured logging as the foundation for all other milestones. Every subsystem will use this from day one.

**Context**: Logging is critical for debugging the interpreter, understanding which POL stubs are hit, and tracing combat calculations. It must be in place before any other code is written.

**Deliverables**:
- Named loggers per subsystem: `omega.parser`, `omega.interpreter`, `omega.runtime`, `omega.config`, `omega.simulation`
- Log levels used consistently:
  - `DEBUG` — interpreter trace (variable assignments, branch decisions, function entry/exit)
  - `INFO` — POL built-in calls with args/return values, simulation progress
  - `WARNING` — NotImplemented stub hits, unexpected state
  - `ERROR` — parse failures, runtime errors
- Structured log format: timestamp, logger name, level, message, optional context dict
- Configurable verbosity per logger (e.g., silence parser noise while debugging runtime)
- Helper decorator for tracing function calls at DEBUG level

**Files**: `src/omega/logging.py`

**Acceptance**: Import and use from any other module. Verify log output at different verbosity levels.

---

## M1 — Project Scaffolding
**Status**: [x] Complete

**Goal**: Set up the Python project structure, dependency management, and dev tooling so all subsequent milestones have a working foundation.

**Context**: Arch Linux, Python 3.14.3 available. No pip/uv currently installed but `ensurepip` exists and `curl` available for uv install. Need ANTLR4 tooling for M2.

**Deliverables**:
- Install `uv` via official installer (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- `pyproject.toml` with project metadata, Python 3.14 requirement, and dependencies:
  - `antlr4-tools` and `antlr4-python3-runtime` (parser generation)
  - `pytest` (testing)
  - `jupyter` / `jupyterlab` (notebooks)
  - `matplotlib` and/or `plotly` (graphing)
  - `numpy` (statistics)
- Package structure:
  ```
  src/
    omega/
      __init__.py
      logging.py          (M0)
      parser/             (M2)
        __init__.py
      config/             (M3)
        __init__.py
      model/              (M4)
        __init__.py
      interpreter/        (M5)
        __init__.py
      runtime/            (M6)
        __init__.py
      simulation/         (M8)
        __init__.py
      reporting/          (M9)
        __init__.py
  tests/
    test_parser/
    test_config/
    test_interpreter/
    test_runtime/
    test_simulation/
  notebooks/
  ```
- `uv sync` works, `uv run pytest` runs (even if no tests yet)
- `.gitignore` for Python, Jupyter, ANTLR4 generated files

**Acceptance**: `uv run python -c "import omega"` succeeds. `uv run pytest` exits 0.

---

## M2 — eScript Parser
**Status**: [x] Complete

**Goal**: Parse eScript `.src` and `.inc` files into an AST we can walk in the interpreter. Must handle all language constructs used by the combat scripts.

**Context**: ANTLR4 grammars exist in `submodules/escript-antlr4/` (`EscriptLexer.g4`, `EscriptParser.g4`). These need a Python target generated. The grammar is case-insensitive (uses CaseChangingStream in the JS target). Alternative approach: write a Lark grammar.

**Approach decision**: Try ANTLR4 Python target first. The grammar is ready and tested. If ANTLR4 Python runtime has compatibility issues with Python 3.14, fall back to Lark.

**Deliverables**:
- ANTLR4 Python target generation script/command (or Lark grammar file)
- Generated lexer and parser (or Lark grammar) in `src/omega/parser/`
- Case-insensitive lexing (eScript keywords are case-insensitive)
- Include resolver:
  - `include "path/file";` → relative to shard root `scripts/` directory
  - `include ":pkgname:file";` → resolves via package path (reads `pkg.cfg` Name field)
  - Circular include detection
- Parse all files in the combat dependency tree without errors:
  - `mainhit.src`, `hitscriptinc.inc`, `damages.inc`, `classes.inc`, `attributes.inc`, `client.inc`, `dotempmods.inc`, `skillpoints.inc`, `math.inc`, `karmafame.inc`, `astralfights.inc`
- Unit tests: parse individual constructs (assignments, if/endif, foreach, function definitions, program blocks)
- Integration test: parse `mainhit.src` with all includes resolved → valid AST

**Key language constructs to verify**:
- `:=` assignment and compound assignments (`+=`, `-=`, etc.)
- `if/elseif/else/endif`, `while/endwhile`, `foreach X in Y ... endforeach`
- `for (init; cond; step) ... endfor` and `for X := start TO end ... endfor`
- `case(expr) ... default: ... endcase`
- `function name(params) ... endfunction`, `program name(params) ... endprogram`
- `use module;`, `include "file";`
- Member access: `obj.prop`, `obj.method(args)`, `obj[index]`
- Scoped calls: `module::function(args)`
- `.isa(CONSTANT)`, `.IsA(CONSTANT)` — case-insensitive method
- `byref` parameter modifier
- String and numeric literals, hex literals (0x...)
- Operators: `and`/`or`/`not` alongside `&&`/`||`/`!`

**Files**: `src/omega/parser/`, potentially `grammar/` for source grammars

**Acceptance**: `parse("mainhit.src")` returns a complete AST with all includes resolved. No parse errors on the combat file set.

---

## M3 — Config File Parsers
**Status**: [ ] Not started

**Goal**: Parse POL `.cfg` files and dice notation so the simulator can load NPC templates, weapon/armor definitions, equipment sets, and combat settings.

**Context**: POL config files use a block-based format (not INI, not YAML). Each block has a type keyword, a name/id, and key-value pairs inside braces. CProps use type prefixes (`i` for int, `s` for string). Weapon damage uses dice notation (`XdY+Z`).

**Deliverables**:
- **POL config parser** (`src/omega/config/cfg_parser.py`):
  - Parse block format: `BlockType Name { Key Value; CProp Name TypeValue; }`
  - Handle multi-line values, comments (// and /* */), nested braces if any
  - Return structured data: `dict[str, list[ConfigBlock]]` keyed by block type
  - Parse these files without error:
    - `config/npcdesc.cfg` (580KB, hundreds of NPC templates)
    - `config/combat.cfg` (simple key=value)
    - `config/equip.cfg` (equipment sets)
    - `pkg/systems/combat/config/itemdesc.cfg` (weapons and armor)
    - `pkg/systems/combat/config/hitscriptdesc.cfg` (enchantments)
    - `pkg/systems/combat/config/settings.cfg` (combat settings)

- **Package path resolver** (`src/omega/config/package_resolver.py`):
  - Scan all `pkg/*/pkg.cfg` and `pkg/*/*/pkg.cfg` for `Name` fields
  - Build map: `{"combat": "pkg/systems/combat", "karmafame": "pkg/systems/karmafame", ...}`
  - Resolve `:pkgname:filepath` → absolute filesystem path
  - Used by both the include resolver (M2) and config loading

- **Dice notation parser** (`src/omega/config/dice.py`):
  - Parse `XdY+Z`, `XdY-Z`, `XdY` formats
  - `roll(dice_str, rng) -> int` function
  - `parse(dice_str) -> DiceSpec(count, sides, bonus)` for analysis

- Unit tests for each parser with sample inputs from the actual shard files

**Files**: `src/omega/config/`

**Acceptance**: Load `npcdesc.cfg`, look up NPC "nazgul", get its stats, skills, and equipment reference. Resolve equipment chain to weapon damage dice and armor AR values.

---

## M4 — Game Object Model
**Status**: [ ] Not started

**Goal**: Define the in-memory data model for combatants, weapons, armor, and the property-bag system that eScript interacts with via GetObjProperty/SetObjProperty.

**Context**: eScript treats game objects as opaque references with properties accessed via `GetObjProperty(obj, "PropName")` and `SetObjProperty(obj, "PropName", value)`. Objects also have intrinsic fields (`.name`, `.hp`, `.maxhp`, `.serial`, `.npctemplate`). Mobiles have stats (STR/INT/DEX) and skills. Weapons have damage dice, speed, skill attribute. Armor has AR and coverage.

**Deliverables**:
- **Base game object** (`src/omega/model/game_object.py`):
  - Property bag: `get_property(name) -> value`, `set_property(name, value)`, `erase_property(name)`
  - Intrinsic fields exposed as properties (`.name`, `.serial`, `.objtype`, `.graphic`)
  - `.isa(polclass)` / `.IsA(polclass)` type checking
  - POLCLASS constants: `POLCLASS_MOBILE`, `POLCLASS_NPC`, `POLCLASS_WEAPON`, `POLCLASS_ARMOR`, `POLCLASS_ITEM`

- **Mobile** (`src/omega/model/mobile.py`):
  - Stats: STR, INT, DEX (with getters matching POL API: `GetStrength()`, etc.)
  - Vitals: HP, Mana, Stamina (current + max)
  - Skills: dict of skill_id → value (0-1300 internally, /10 for display)
  - Class: which class(es) active, class level
  - Equipment slots by layer (LAYER_HAND1, LAYER_HAND2, etc.)
  - `is_player` vs `is_npc` flag
  - `npctemplate` field for NPCs

- **Weapon** (`src/omega/model/items.py`):
  - Damage dice spec (from config)
  - Speed, skill attribute (Swords/Mace/Fencing/Archery/Wrestling)
  - HP / MaxHP (durability)
  - Two-handed flag, range
  - Hitscript reference
  - Property bag for enchantment data (SlayType, ElementalDamage, Astral, etc.)

- **Armor** (`src/omega/model/items.py`):
  - AR value
  - Coverage zones
  - HP / MaxHP
  - Property bag for enchantment data

- **Factory functions** (`src/omega/model/factories.py`):
  - `create_mobile_from_config(npc_template: ConfigBlock, equip_resolver) -> Mobile`
  - `create_mobile_inline(stats, skills, class_id, ...) -> Mobile`
  - `create_weapon_from_config(weapon_block: ConfigBlock) -> Weapon`
  - `create_armor_from_config(armor_block: ConfigBlock) -> Armor`
  - Equipment set resolver: given an equipment template name, resolve and equip all items

- **Snapshot/reset** (`src/omega/model/snapshot.py`):
  - `snapshot(mobile) -> MobileState` — capture full state before a hit
  - `restore(mobile, snapshot)` — reset to pre-hit state for next iteration

**Files**: `src/omega/model/`

**Acceptance**: Create a Warrior with 100 Swords, 100 Tactics, STR 100, a broadsword (3d5+2), and verify all properties are accessible via the same API the eScript runtime will use. Create an NPC from the "nazgul" template. Snapshot and restore a mobile.

---

## M5 — eScript Interpreter
**Status**: [ ] Not started

**Goal**: Walk the parsed AST and execute eScript code. This is the core of the project — a tree-walking interpreter that can run the combat scripts.

**Context**: Standard tree-walking interpreter. eScript has function-level scoping, `byref` parameters, global variables (within a program), and `use`/`include` for module/file imports. The interpreter doesn't need to be fast — correctness and traceability matter more.

**Deliverables**:
- **AST visitor/walker** (`src/omega/interpreter/evaluator.py`):
  - Expression evaluation: arithmetic, comparison, logical, string concatenation
  - Operator precedence (handled by parser, interpreter just evaluates)
  - Type coercion rules matching POL behavior (e.g., string + int, truthiness)

- **Variable & scope management** (`src/omega/interpreter/scope.py`):
  - Global scope (program-level variables and constants)
  - Function-local scope (pushed/popped on function entry/exit)
  - `byref` parameter binding (alias to caller's variable)
  - `var` declaration with optional initializer
  - `const` declaration

- **Control flow** (`src/omega/interpreter/evaluator.py`):
  - `if/elseif/else/endif`
  - `while/endwhile`, `do/dowhile`
  - `for/endfor` (both C-style and BASIC-style `TO`)
  - `foreach/endforeach` with `in` operator
  - `repeat/until`
  - `case/endcase` with integer and string labels, `default`
  - `break`, `continue`, `return`, `exit`

- **Function system** (`src/omega/interpreter/functions.py`):
  - User-defined function registry (from parsed includes)
  - Built-in function dispatch (delegates to runtime stubs, M6)
  - Module-scoped function calls (`module::function`)
  - `program` block as the entry point

- **Data structures**:
  - Arrays (1-indexed as in eScript), with `.append()`, `[]` access
  - Structs (named-field containers)
  - Dictionaries with `.Exists()`, `[]` access, `keys()` iteration
  - ERROR type

- **Member access & method calls**:
  - `obj.property` reads → delegates to game object model
  - `obj.method(args)` → delegates to runtime stubs
  - `obj[index]` → array/dict indexing
  - `.isa()` / `.IsA()` → type checking on game objects

- **Logging integration**:
  - Function entry/exit with args at DEBUG
  - Variable assignments at DEBUG
  - Branch decisions (which if/elseif/case taken) at DEBUG
  - Configurable: can silence per-file or per-function

**Files**: `src/omega/interpreter/`

**Acceptance**: Execute a standalone eScript function that uses variables, loops, conditionals, and function calls. Execute a minimal program block. Pass a suite of unit tests covering each language construct.

---

## M6 — POL Runtime Stubs
**Status**: [ ] Not started

**Goal**: Implement the mock POL built-in functions that the combat scripts call. These bridge the interpreter to the game object model.

**Context**: The combat path calls ~60 distinct POL built-ins. Each `use module;` statement makes that module's functions available. The interpreter dispatches `module::function(args)` or bare `function(args)` calls to these stubs. Stubs operate on the game object model from M4.

**Deliverables**:
- **Stub registry** (`src/omega/runtime/registry.py`):
  - Map of `(module, function_name) -> callable`
  - Auto-registers stubs decorated with `@pol_function("module", "name")`
  - Unknown function calls → log WARNING + raise `NotImplementedError` with full context

- **Batch 1 — trivial stubs** (`src/omega/runtime/basic_stubs.py`):
  - Type casts: `CInt(v)`, `CDbl(v)`, `CStr(v)`, `Hex(v)`
  - Math: `Random(max)`, `RandomInt(max)`, `Pow(b,e)`, `Max(a,b)`, `Min(a,b)`, `Abs(v)`, `Sin/Cos/Sqrt` etc.
  - Type queries: `TypeOf(v)`, `Len(v)`
  - String: `SplitWords(s, delim)`, `Lower(s)`, `Upper(s)`, `SubStr()`
  - Time: `ReadGameClock()` → returns iteration counter or fixed value
  - Messaging (no-ops with logging): `SendSysMessage()`, `PrintTextAbovePrivate()`, `PrintTextAbove()`
  - Actions (no-ops): `PerformAction()`, `PlaySoundEffect()`

- **Batch 2 — object model stubs** (`src/omega/runtime/object_stubs.py`):
  - Property system: `GetObjProperty(obj, name)`, `SetObjProperty(obj, name, val)`, `EraseObjProperty(obj, name)` → delegates to game object property bag
  - Stats: `GetStrength(mob)`, `GetIntelligence(mob)`, `GetDexterity(mob)` → reads from Mobile
  - Vitals: `GetHP(mob)`, `GetMaxHP(mob)`, `GetMana(mob)`, `GetStamina(mob)`, `SetMana(mob,v)`, `SetStamina(mob,v)`
  - Skills: `GetEffectiveSkill(mob, id)`, `GetAttribute(mob, name, precision)`, `GetAttributeBaseValue(mob, name)`
  - Equipment: `GetEquipmentByLayer(mob, layer)` → returns equipped item or error
  - Type check: `.isa(POLCLASS)` → resolved on game objects
  - Revision: `IncRevision(item)` → no-op with logging

- **Batch 3 — structural stubs** (`src/omega/runtime/structural_stubs.py`):
  - `ApplyRawDamage(mob, dmg)` → records damage in simulation context, modifies HP
  - `ReadConfigFile(path)` → delegates to config parser (M3), returns config object stub
  - Config object methods: `FindConfigElem()`, `GetConfigInt()`, `GetConfigString()`, `GetConfigStringKeys()`
  - `SystemFindObjectBySerial(serial)` → lookup from object registry
  - `SetScriptController(mob)` → no-op with logging
  - `start_script(name, args)` → log WARNING, return stub (V1: skip enchantment scripts)
  - `FindGuild(id)` → return stub guild object with `.IsEnemyGuild()` → false, `.IsAllyGuild()` → false
  - `SetPoison()`, `SetWarMode()` → no-ops, logged as side effects

- **Deterministic RNG** (`src/omega/runtime/rng.py`):
  - Seeded RNG wrapper around Python's `random.Random`
  - `Random(max)` and `RandomInt(max)` use this
  - Seed configurable per simulation run (for reproducibility)

- **Simulation context** (`src/omega/runtime/context.py`):
  - Tracks current attacker, defender, weapon, armor references
  - Records side effects per hit: damage dealt, poison applied, equipment damaged, stamina drained
  - Provides state reset between iterations

**Files**: `src/omega/runtime/`

**Acceptance**: All ~60 combat-path built-in calls dispatch without error. `ApplyRawDamage` correctly records damage. `GetObjProperty`/`SetObjProperty` round-trips. Unknown function → clear WARNING log with module, function, args, call site.

---

## M7 — Combat Integration
**Status**: [ ] Not started

**Goal**: Wire everything together: parse `mainhit.src` with all includes, load config files, create combatants, and execute a single hit through the interpreter.

**Context**: This is the convergence point where parser (M2), config (M3), object model (M4), interpreter (M5), and runtime stubs (M6) come together. The first time we actually run the shard's combat code.

**Deliverables**:
- **Shard loader** (`src/omega/shard.py`):
  - Accepts shard root path (e.g., `submodules/zuluhotel_omega_2.5/`)
  - Builds package map from all `pkg.cfg` files
  - Parses combat config files (combat.cfg, settings.cfg, itemdesc.cfg, npcdesc.cfg, equip.cfg)
  - Provides NPC lookup by template name
  - Provides equipment resolution chain (NPC → equip template → weapon/armor)

- **Combat runner** (`src/omega/combat.py`):
  - `execute_hit(attacker: Mobile, defender: Mobile, weapon: Weapon, armor: Armor, rng_seed: int) -> HitResult`
  - Parses `mainhit.src` + all includes (cached after first parse)
  - Sets up interpreter scope with program parameters (attacker, defender, weapon, armor, basedamage, rawdamage)
  - `basedamage` = roll weapon damage dice
  - `rawdamage` = basedamage (initial value before script modifies it)
  - Executes the program
  - Collects `HitResult`: final damage dealt, damage absorbed, hit/miss, crit, side effects

- **HitResult** dataclass:
  - `raw_damage: float` — damage before absorption
  - `final_damage: float` — damage after all reductions
  - `absorbed: float` — total absorbed by armor/shields
  - `is_hit: bool` — did the attack connect
  - `is_crit: bool` — was it a critical hit
  - `side_effects: dict` — poison applied, equipment damaged, stamina drained, etc.

- **Integration tests**:
  - Bare weapon vs unarmored target → damage equals raw dice roll with class/tactics modifiers
  - Weapon vs armored target → AR absorption reduces damage
  - Warrior class bonus → measurably higher damage
  - PvP scenario → 60% damage scaling applied
  - Verify by hand-calculating expected values from the eScript source

**Files**: `src/omega/shard.py`, `src/omega/combat.py`

**Acceptance**: `execute_hit()` runs the actual shard `mainhit.src` through the interpreter and returns a plausible `HitResult`. Logging shows the full execution trace. Hand-calculated test cases pass.

---

## M8 — Simulation Runner
**Status**: [ ] Not started

**Goal**: Run N iterations of `execute_hit()` across parameter variations and collect statistical results.

**Context**: Each hit is independent (state resets between iterations). Designers want to sweep variables (e.g., skill 50→130) and compare scenarios (e.g., Warrior vs Mage attacker). Each cell in the parameter grid runs N iterations with different RNG seeds.

**Deliverables**:
- **Scenario definition** (`src/omega/simulation/scenario.py`):
  - `Combatant` spec: class, skills dict, stats dict, weapon spec, armor spec — OR — NPC template name
  - `Scenario`: attacker spec, defender spec, N iterations (default 1000)
  - `Variable`: parameter name, range (start, stop, step) or list of discrete values
  - `ParameterSweep`: scenario + one or more variables → generates a grid of scenarios

- **Runner** (`src/omega/simulation/runner.py`):
  - Takes a `Scenario` or `ParameterSweep`
  - For each cell: creates combatants, runs N hits via `execute_hit()`, collects `HitResult` list
  - Deterministic: base seed + iteration index → per-hit seed
  - Progress logging: current cell, iteration count, ETA

- **Result aggregation** (`src/omega/simulation/stats.py`):
  - Per cell: mean, median, min, max, std dev, percentiles (5th, 25th, 75th, 95th)
  - Damage breakdown: physical dealt, absorbed, per elemental type
  - Ratio stats: hit rate, crit rate, poison rate, equipment break rate
  - `SimulationResult` dataclass with all stats + raw data access

**Files**: `src/omega/simulation/`

**Acceptance**: Define a sweep of attacker Swordsmanship 50→130, run 1000 iterations per step, get a `SimulationResult` with all stats populated. Total runtime under 60 seconds for the full sweep.

---

## M9 — Reporting & Notebooks
**Status**: [ ] Not started

**Goal**: Visualize simulation results in Jupyter notebooks with publication-quality graphs suitable for game design decisions.

**Context**: The target user is a game designer comparing builds, tuning formulas, and verifying balance. They need clear visual outputs, not raw numbers. Hot reload lets them edit scripts and re-run without restarting.

**Deliverables**:
- **Plotting library** (`src/omega/reporting/plots.py`):
  - Damage distribution histogram (single scenario)
  - Damage vs parameter curve (sweep result) with confidence bands
  - Damage breakdown stacked bar chart (physical / absorbed / elemental)
  - Comparison overlay: multiple scenarios on one chart
  - All plots return matplotlib/plotly figure objects (notebook-friendly)

- **Summary table** (`src/omega/reporting/tables.py`):
  - Formatted table of stats per sweep cell
  - Comparison table: scenario A vs scenario B side by side

- **Example notebooks** (`notebooks/`):
  - `01_basic_damage.ipynb` — single scenario: Warrior vs NPC, histogram + summary
  - `02_skill_sweep.ipynb` — damage vs Swordsmanship skill level curve
  - `03_class_comparison.ipynb` — all classes attacking same defender, side-by-side
  - Each notebook is self-contained with markdown explanation

- **Hot reload utility** (`src/omega/reload.py`):
  - File watcher on shard script directory
  - On change: invalidate parsed script cache, re-parse, optionally re-run last scenario
  - Usable from notebook: `watcher = watch_and_rerun(scenario)` or manual `reload_scripts()`

**Files**: `src/omega/reporting/`, `notebooks/`

**Acceptance**: Run example notebook end-to-end. Graphs render in JupyterLab. Edit a shard script → hot reload → graphs update.

---

## M10 — Validation & Polish
**Status**: [ ] Not started

**Goal**: Verify simulator accuracy against known in-game results and polish the developer experience.

**Context**: Without this milestone, we can't trust the numbers. We need specific test cases verified against the real game.

**Deliverables**:
- **Validation test suite** (`tests/test_validation/`):
  - 3-5 hand-calculated scenarios derived from reading the eScript combat formulas
  - Where possible, verified against in-game observations
  - Test cases:
    1. Plain weapon (3d5+2) vs 0 AR target, no class bonus → expected damage range
    2. Same weapon vs 50 AR target → expected absorption range
    3. Warrior (level 3) class bonus → expected multiplier applied
    4. Slayer weapon vs matching creature type → 2.0x multiplier
    5. PvP scenario → 60% scaling verified
  - Each test documents the formula trace and expected value derivation

- **Error handling review**:
  - All NotImplemented stubs are documented (which ones were hit, which were not)
  - Clear error messages for common user mistakes (wrong NPC name, invalid skill ID)

- **Documentation**:
  - Update CLAUDE.md with any architectural changes discovered during integration
  - Inline docstrings on public APIs
  - Notebook markdown cells explain what each section does

- **Performance check**:
  - Profile 10,000 iteration run — identify bottlenecks
  - If parsing is slow, verify script caching works
  - Target: 1000 hits/second minimum

**Files**: `tests/test_validation/`, updates across codebase

**Acceptance**: All 5 validation scenarios pass. A game designer can follow the example notebooks to set up and run their own scenarios without reading source code.

---

## Milestone Summary

| Milestone | Description | Depends On | Parallelizable With |
|-----------|-------------|------------|---------------------|
| M0 | Logging Framework | — | M1 |
| M1 | Project Scaffolding | — | M0 |
| M2 | eScript Parser | M0, M1 | M3, M4 |
| M3 | Config File Parsers | M0, M1 | M2 |
| M4 | Game Object Model | M0, M1 | M2, M3 |
| M5 | eScript Interpreter | M0, M2 | M6 (partial) |
| M6 | POL Runtime Stubs | M0, M4 | M5 (partial) |
| M7 | Combat Integration | M2-M6 | — |
| M8 | Simulation Runner | M7 | M9 (partial) |
| M9 | Reporting & Notebooks | M8 | — |
| M10 | Validation & Polish | M7-M9 | — |

**Critical path**: M1 → M2 → M5 → M7 → M8 → M9 → M10

**Parallel track**: M1 → M3 → M4 → M6 (converges at M7)
