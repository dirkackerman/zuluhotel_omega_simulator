# Changelog to V1

## M0 + M1 — Project Scaffolding & Logging Framework

**Date**: 2026-03-10

### Summary

Established the project foundation: Python package structure, dependency management with `uv`, and a structured logging framework designed for sink-agnostic output.

**Project setup**:
- Installed `uv` 0.10.9 as the package manager
- Created `pyproject.toml` with hatchling build backend, pytest dev dependency, optional notebook dependencies (jupyterlab, matplotlib, numpy)
- Laid out `src/omega/` package with subpackages for each subsystem: parser, config, model, interpreter, runtime, simulation, reporting
- Created `tests/`, `notebooks/`, `.gitignore`
- Removed legacy `src/requirements.txt`

**Logging framework** (`src/omega/logging.py`):
- `get_logger(name)` — cached named loggers wrapping stdlib `logging.Logger`, with `**kwargs` on all log methods for structured key-value data
- `setup_logging(level, subsystem_levels)` — single entry point for configuring handlers and formatters; the only place sink/format changes are needed
- `log_context(**kw)` — context manager using `contextvars.ContextVar` to attach metadata (hit number, combatant names, etc.) to all nested log calls without threading through function signatures
- `@trace` — opt-in decorator logging ENTER/EXIT with args and return values at DEBUG level
- `OmegaFormatter` — human-readable console formatter; swappable for JSON or other formats by changing only `setup_logging()`, not call sites

### Test Criteria

- [ ] `uv sync --extra dev` completes without error
- [ ] `uv run python -c "import omega"` succeeds
- [ ] `uv run pytest -v` — all 23 tests pass:
  - `TestGetLogger` (4 tests) — logger creation, caching, naming
  - `TestOmegaLogger` (7 tests) — log levels, kwargs in output, level filtering
  - `TestLogContext` (5 tests) — context attachment, nesting, no leakage, override
  - `TestTrace` (4 tests) — entry/exit logging, exception logging, name preservation
  - `TestSetupLogging` (3 tests) — root config, subsystem levels, handler cleanup on re-setup
- [ ] Log output format matches: `YYYY-MM-DD HH:MM:SS [logger.name] LEVEL   message  [key=value ...]`
- [ ] Structured kwargs from `log_context()` and logger calls both appear in formatted output

---

## M2 — eScript Parser

**Date**: 2026-03-10

### Summary

Built a complete eScript parser using ANTLR4 with Python target, capable of parsing all 53 files in the shard's combat include chain with zero errors.

**Approach**: Used the existing ANTLR4 grammar from `submodules/escript-antlr4/`, generated Python lexer/parser, and patched 7 embedded JavaScript actions (`this.` → `self.`) plus 2 indentation fixes in the generated code.

**Files created**:
- `src/omega/parser/grammar/` — copied `.g4` files with Python-compatible patches
- `src/omega/parser/gen/` — generated ANTLR4 Python lexer, parser, visitor, listener
- `src/omega/parser/case_insensitive_stream.py` — `CaseInsensitiveInputStream` wrapping `antlr4.InputStream`, overrides `LA()` to lowercase for case-insensitive keyword matching while preserving original identifier text
- `src/omega/parser/include_resolver.py` — resolves `include "path"` (relative to `scripts/`) and `include ":pkg:file"` (via package map from `pkg.cfg`). Deduplicates includes, detects missing files
- `src/omega/parser/parser.py` — public API: `parse_text()`, `parse_file()`, `parse_with_includes()`. Collects errors via custom error listener, logs via `omega.parser` logger
- `scripts/generate_parser.sh` — regeneration script for when grammar changes

**Dependencies added**: `antlr4-python3-runtime>=4.13.2`

### Key decisions
- ANTLR4 over Lark: grammar exists and is tested, only minor patches needed
- Generated code checked into git: no ANTLR4 tooling required at runtime
- Parse tree walked directly by interpreter (no intermediate AST transformation)
- Include resolver uses `PackageMap` protocol: M3 will provide the real implementation, tests use `DictPackageMap`

### Test Criteria

- [ ] `uv run pytest -v` — all 109 tests pass (23 logging + 86 parser):
  - `TestVariables` (7 tests) — var/const declarations, array/struct/dict initializers
  - `TestControlFlow` (15 tests) — if/while/for/foreach/repeat/case/break/continue/return/exit
  - `TestFunctions` (7 tests) — function/program/exported/byref/default/unused params
  - `TestExpressions` (20 tests) — arithmetic, comparison, logical, member access, method calls, scoped calls, bitwise, .isa(), elvis, in, function references
  - `TestModules` (4 tests) — use/include declarations
  - `TestEnum` (1 test) — enum definition
  - `TestComposite` (3 tests) — real-world shard script patterns
  - `TestCaseInsensitiveKeywords` (8 tests) — IF/if/If, VAR/var, FUNCTION/function, etc.
  - `TestCasePreservation` (1 test) — identifier original case preserved in parse tree
  - `TestRelativePaths` (4 tests) — include resolution with .inc extension, missing file error
  - `TestPackagePaths` (3 tests) — `:combat:hitscriptinc` resolution, unknown package error
  - `TestDeduplication` (3 tests) — mark_included/is_included cycle detection
  - `TestSingleFileParse` (6 tests) — mainhit.src, hitscriptinc.inc, damages.inc, classes.inc, attributes.inc, client.inc
  - `TestParseWithIncludes` (4 tests) — full 53-file include chain, specific files present in results
- [ ] `parse_with_includes("mainhit.src")` parses 53 files with zero errors
- [ ] Case-insensitive: `IF`, `if`, `If` all parse identically
- [ ] `:combat:hitscriptinc` resolves to `pkg/systems/combat/include/hitscriptinc.inc`

---

## M3 — Config File Parsers

**Date**: 2026-03-10

### Summary

Built POL config file parsers, package path resolver, dice notation parser, and runtime-compatible config accessors. All shard config files parse correctly — 748 NPC templates from `npcdesc.cfg`, 129 packages discovered, weapon damage dice parsed and rollable.

**Files created**:
- `src/omega/config/cfg_parser.py` — `ConfigElement` (property bag with `get()`, `get_int()`, `get_float()`, `get_all()` for multi-value keys, `get_cprop()` for type-prefixed CProps, `__getattr__` for dot access) and `ConfigFile` (element container with `__getitem__` supporting string names and int objtypes). `parse_config_file(path)` auto-detects flat key=value vs block-based formats
- `src/omega/config/package_resolver.py` — `PackageResolver` scans all `pkg.cfg` files, builds `name → Path` map, resolves `:combat:settings` → filesystem path, handles `:*:itemdesc` wildcard search across all packages. Implements `PackageMap` protocol for include resolver
- `src/omega/config/dice.py` — `DiceSpec` frozen dataclass with `min_value`, `max_value`, `mean_value` properties. `parse_dice("3d5+2")` → `DiceSpec(3, 5, 2)`. `roll_dice(spec, rng)` for deterministic simulation
- `src/omega/config/accessor.py` — `RuntimeConfigFile` and `RuntimeConfigElement` wrappers matching POL's `ReadConfigFile()` API: `cfg["Weapons"].WearChance` dot-style access
- `src/omega/config/__init__.py` — public API exports

**Config formats handled**:
- Flat key=value (`combat.cfg`) — `#` line comments
- Block-based (`npcdesc.cfg`, `equip.cfg`, `itemdesc.cfg`, `settings.cfg`, `hitscriptdesc.cfg`) — `//` line and inline comments, tab/space separators, multi-value keys, CProp entries with `i`/`s` type prefixes, hex objtype names (e.g., `0x13BB`)

### Key decisions
- Auto-detection over explicit format flag: scans for `{` outside comments to choose parser
- `ConfigFile.__getitem__` accepts both string names and int objtypes, enabling `cfg[0x13BB]` for weapon/armor lookup matching eScript patterns
- `PackageResolver` reads `Name` field from `pkg.cfg` (not directory name), matching POL's behavior
- CProps stored raw with type prefix stripped; `get_cprop()` handles `i`→int, `s`→str conversion

### Test Criteria

- [ ] `uv run pytest -v` — all 167 tests pass (23 logging + 86 parser + 58 config):
  - `TestFlatFormat` (2 tests) — combat.cfg parsing, key presence
  - `TestBlockFormat` (5 tests) — npcdesc.cfg parsing, property access, multi-value keys, CProps, specific NPC lookup
  - `TestItemdescFormat` (5 tests) — itemdesc.cfg parsing, objtype int/string lookup, coverage multi-value, armor CProps
  - `TestSettingsFormat` (3 tests) — settings.cfg parsing, element access, wear chance values
  - `TestEquipFormat` (2 tests) — equip.cfg parsing, nazgul equipment chain
  - `TestHitscriptdescFormat` (2 tests) — hitscriptdesc.cfg parsing, enchantment access
  - `TestConfigElement` (3 tests) — get_int, get_float, contains
  - `TestPackageDiscovery` (4 tests) — finds 100+ packages, combat/karmafame/spells present
  - `TestPackageResolve` (3 tests) — resolve combat, case-insensitive, unknown returns None
  - `TestConfigPathResolve` (4 tests) — `:combat:settings`, `:combat:hitscriptdesc`, `:*:itemdesc` wildcard, unknown package
  - `TestPackageMapProtocol` (1 test) — protocol compliance
  - `TestParseDice` (8 tests) — all notation formats, whitespace handling, invalid input errors
  - `TestDiceSpecProperties` (5 tests) — min/max/mean values, flat damage, string representation
  - `TestRollDice` (4 tests) — deterministic seeded rolls, flat damage, bounds checking
  - `TestNpcLookupChain` (1 test) — NPC → equip template resolution
  - `TestRuntimeAccessorPatterns` (5 tests) — combat settings, armor settings, objtype lookup, package resolver path, wildcard resolution
  - `TestWeaponDamageParsing` (1 test) — weapon damage dice parse and validate
- [ ] 748 NPC templates parsed from `npcdesc.cfg`
- [ ] 129 packages discovered from shard `pkg/` directories
- [ ] `cfg[0x13BB].Name == "ChainmailCoif"` — int objtype lookup works
- [ ] `cfg["Weapons"].WearChance.startswith("8")` — runtime accessor dot access works

---

## M4 — Game Object Model

**Date**: 2026-03-10

### Summary

Built the in-memory game object model: base `GameObject` with property bag, `Mobile` with stats/skills/vitals/equipment, `Weapon` and `Armor` items, factory functions for creating objects from config or inline specs, and snapshot/restore for stateless simulation iterations.

**Files created**:
- `src/omega/model/constants.py` — All POL constants: POLCLASS types, 24 equipment layers, 10 class IDs with bonus constants, 49 skill IDs, attribute name strings, SKILLID↔ATTRIBUTE bidirectional maps, vital IDs, caps, 12 damage type bitflags
- `src/omega/model/game_object.py` — `GameObject` base class with auto-incrementing serial, intrinsic fields (objtype, graphic, name, color), property bag (get/set/erase/has), `.isa()` type checking
- `src/omega/model/items.py` — `Weapon` (damage DiceSpec, speed, attribute skill ID, two_handed, quality, hitscript, durability) and `Armor` (AR, coverage zones, layer, durability). Both extend `GameObject` with correct POLCLASS tuples
- `src/omega/model/mobile.py` — `Mobile` with base stats + mods (STR/INT/DEX), vitals (HP/Mana/Stamina), skill storage (internal ×10 representation), equipment slots by layer, computed `.ar` from equipped armor, `get_attribute()` supporting both stat names and skill names, dynamic `_polclasses` for NPC vs player
- `src/omega/model/factories.py` — `create_mobile_from_template()` (full NPC chain: npcdesc→equip→itemdesc), `create_mobile_inline()` (direct spec), `create_weapon_from_config()`, `create_armor_from_config()`, `equip_from_template()`. Handles skill name normalization, CProp transfer, CustomHitsLevel override
- `src/omega/model/snapshot.py` — `MobileSnapshot` frozen dataclass capturing vitals, stat mods, property bag (deep copy), equipment HP. `snapshot()` and `restore()` for stateless iteration reset
- `src/omega/model/__init__.py` — Public API exports

### Key decisions
- Property bag is separate from member access — matches POL's distinction between `obj.field` and `GetObjProperty(obj, "name")`
- Skills stored internally at ×10 precision (0-2000), display values 0-200, matching POL's `GetEffectiveSkill` behavior
- Class levels stored in property bag (e.g., `"IsWarrior" → 5`), not as typed fields — matches eScript's `GetObjProperty(mob, CLASSEID_WARRIOR)` pattern
- Stat mods stored in tenths (matching POL precision), effective stat = base + mod/10
- `_polclasses` is a property on Mobile (dynamic based on `is_npc`) vs a class attribute on items
- Equipment auto-layer assignment from armor coverage zones (Head→HELM, Body→CHEST, etc.)
- Snapshot deep-copies the property bag to prevent shared state between iterations

### Test Criteria

- [ ] `uv run pytest -v` — all 256 tests pass (23 logging + 86 parser + 58 config + 89 model):
  - `TestSerialAssignment` (2 tests) — unique serials, positive values
  - `TestIntrinsicFields` (3 tests) — defaults, custom values, graphic fallback
  - `TestPropertyBag` (7 tests) — CRUD, overwrite, any type support
  - `TestIsa` (4 tests) — Item/Weapon/Mobile checks, IsA alias
  - `TestRepr` (1 test) — string representation
  - `TestWeapon` (6 tests) — defaults, custom, isa, desc, property bag, durability
  - `TestArmor` (6 tests) — defaults, custom, isa, desc, property bag, layer
  - `TestMobileBasics` (2 tests) — player vs NPC defaults
  - `TestMobileIsa` (3 tests) — player/NPC POLCLASS checks
  - `TestMobileStats` (4 tests) — defaults, custom, positive/negative mods
  - `TestMobileVitals` (2 tests) — defaults, modify
  - `TestMobileSkills` (7 tests) — set/get, effective skill, attribute by name, case insensitive
  - `TestMobileEquipment` (4 tests) — equip, unequip, list
  - `TestMobileAR` (4 tests) — no armor, single, sum, weapon excluded
  - `TestMobileClassLevels` (2 tests) — via property bag
  - `TestCreateMobileInline` (10 tests) — warrior creation, HP/mana/stamina defaults, armor equip, NPC flag, skill storage
  - `TestWeaponFromConfig` (2 tests) — WispWeapon from itemdesc, hitscript detection
  - `TestArmorFromConfig` (2 tests) — ChainmailCoif AR/coverage, CProps carried
  - `TestMobileFromTemplate` (5 tests) — beckon NPC stats/skills/equipment, CProps, unknown template error
  - `TestSnapshotWithRealNPC` (1 test) — snapshot→damage→restore cycle
  - `TestSnapshot` (5 tests) — captures vitals, stat mods, properties, equipment HP, frozen
  - `TestRestore` (7 tests) — restores vitals/mods/dead/properties/equipment HP, independence from snapshot
- [ ] `create_mobile_from_template("beckon")` → STR 200, INT 200, DEX 175, skills populated
- [ ] `Weapon.isa(POLCLASS_WEAPON)` → True, `Mobile.isa(POLCLASS_NPC)` → True for NPCs
- [ ] Snapshot→modify→restore cycle preserves original state

---

## M6 — POL Runtime Stubs

**Date**: 2026-03-10

### Summary

Implemented ~60 POL built-in function stubs organized in 3 batches, plus a deterministic RNG, simulation context with side effect tracking, and a decorator-based registry with case-insensitive dispatch. 158 total registry entries (many functions registered under both bare and module-scoped names).

**Files created**:
- `src/omega/runtime/rng.py` — `SimulationRNG` wrapping `random.Random` with seed. `random(max)` for [1,max], `random_int(max)` for [0,max-1]. Stored in `contextvars.ContextVar` for per-iteration isolation
- `src/omega/runtime/context.py` — `SimulationContext` with attacker/defender/weapon refs, side effect recording (`SideEffect` dataclass), damage tracking, object registry for serial lookup, config file cache, `reset_hit()` for iteration reset
- `src/omega/runtime/registry.py` — `@pol_function(module, name)` decorator, `call_builtin(module, name, args)` dispatch with case-insensitive lookup, bare-name fallback for unscoped calls, WARNING log for unknown functions (returns None, doesn't crash)
- `src/omega/runtime/basic_stubs.py` — Batch 1 (~25 functions): CInt/CDbl/CStr/Hex, Max/Min, TypeOf/Len, Pow/Abs/Sqrt/Sin/Cos, Random/RandomInt (deterministic via RNG), SplitWords/Lower/Upper/SubStr, ReadGameClock, SendSysMessage/PrintTextAbove (DEBUG_MODE aware via `omega.runtime.messaging` logger), PerformAction/PlaySoundEffect/IncRevision/Sleepms/Distance (no-ops)
- `src/omega/runtime/object_stubs.py` — Batch 2 (~20 functions): GetObjProperty/SetObjProperty/EraseObjProperty → property bag, GetStrength/GetDexterity/GetIntelligence + mod setters, GetHP/GetMaxHP/GetMana/GetStamina + setters, GetEffectiveSkill/GetAttribute/GetAttributeBaseValue/GetBaseSkill/SetBaseSkill/GetAttributeIdBySkillId, GetEquipmentByLayer/ListEquippedItems
- `src/omega/runtime/structural_stubs.py` — Batch 3 (~15 functions): ReadConfigFile (with caching + RuntimeConfigFile wrapper), FindConfigElem/GetConfigInt/GetConfigString/GetConfigStringKeys, ApplyRawDamage (HP reduction + side effect), SystemFindObjectBySerial/FindMobile, FindGuild (stub with IsEnemyGuild/IsAllyGuild → False), start_script (WARNING + None), SetPoisoned/SetParalyzed/DestroyItem (side effect recording), GetGlobalProperty (sensible defaults)
- `src/omega/runtime/__init__.py` — imports all stub modules to trigger registration on `import omega.runtime`

### Key decisions
- Unknown functions return None instead of raising — maximizes script coverage without crashes; gaps logged at WARNING
- Side effects recorded but not executed — `SetPoisoned` records "poison applied" for stats but doesn't simulate ticks
- Config file caching per simulation context — `ReadConfigFile` is called per-hit in combat scripts
- RNG via `contextvars.ContextVar` — each iteration gets its own seeded instance without threading state
- DEBUG_MODE messaging — `SendSysMessage` silent by default, logs at INFO when `debug_mode=True` in scenario
- Functions registered under both bare (`""`, `"CInt"`) and module-scoped (`"util"`, `"CInt"`) for flexible lookup

### Test Criteria

- [ ] `uv run pytest -v` — all 372 tests pass (23 logging + 86 parser + 58 config + 89 model + 116 runtime):
  - `TestRegistration` (6 tests) — registration, case-insensitive lookup, many stubs present
  - `TestDispatch` (5 tests) — CInt dispatch, module/bare, case-insensitive, unknown → None, bare fallback
  - `TestSimulationRNG` (6 tests) — deterministic seeds, bounds, zero max
  - `TestRNGContext` (1 test) — set_rng_seed reproducibility
  - `TestSimulationContext` (6 tests) — defaults, side effects, damage, absorption, reset, cache preservation
  - `TestObjectRegistry` (2 tests) — register/find, missing serial
  - `TestConfigCache` (2 tests) — cache hit/miss
  - `TestTypeCasts` (11 tests) — CInt/CDbl/CStr/Hex/Max/Min with edge cases
  - `TestTypeQueries` (9 tests) — TypeOf for all types, Len
  - `TestMathOps` (6 tests) — Pow, Abs, Sqrt with edge cases
  - `TestRandom` (3 tests) — deterministic, bounds for Random and RandomInt
  - `TestStringOps` (6 tests) — SplitWords, Lower, Upper, SubStr
  - `TestTime` (1 test) — ReadGameClock from context
  - `TestMessaging` (2 tests) — silent by default, debug mode
  - `TestNoOps` (6 tests) — PerformAction, PlaySoundEffect, IncRevision, set_critical, Sleepms, Distance
  - `TestPropertySystem` (5 tests) — get/set/erase roundtrip, weapon properties, null safety
  - `TestStatAccessors` (6 tests) — STR/DEX/INT, mods, null safety
  - `TestVitalAccessors` (6 tests) — HP/Mana/Stamina get/set
  - `TestSkillAccessors` (4 tests) — GetEffectiveSkill, GetAttribute by name, GetAttributeIdBySkillId
  - `TestEquipmentAccessors` (3 tests) — GetEquipmentByLayer, empty layer, ListEquippedItems
  - `TestApplyRawDamage` (5 tests) — HP reduction, damage recording, side effect, lethal, zero ignored
  - `TestGuildStubs` (3 tests) — FindGuild, IsEnemyGuild/IsAllyGuild → False
  - `TestScriptControl` (2 tests) — start_script → None
  - `TestSideEffectRecording` (3 tests) — poison, item_destroyed, paralyze
  - `TestObjectLookup` (2 tests) — registered object, missing serial
  - `TestMiscStubs` (5 tests) — GetGlobalProperty, EnumerateOnlineCharacters, no-op stubs
- [ ] 158 registry entries covering ~60 distinct POL built-in functions
- [ ] `ApplyRawDamage(mob, 50)` → HP decreases by 50, side effect recorded
- [ ] `Random`/`RandomInt` produce identical sequences for same seed
- [ ] Unknown function → WARNING log, returns None (no crash)
