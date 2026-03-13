# Changelog to V3

This changelog tracks progress on V3 (Damage Spell Casting). See [Path to V3](../planning/path_to_v3.md) for the full roadmap.

---

## M23 — Spell Config Parsing & Fixture Sync

Parsed `spells.cfg` (5 files, 128 spells) and `circles.cfg` (33 circles) into a new `SpellRegistry` with lookup by ID, name, and school. Synced 29 damage spell `.src` scripts to test fixtures. Integrated with the existing `Spell` IntEnum for type-safe lookups.

### New Files

- **`src/omega/config/spell_registry.py`** — `CircleConfig`, `SpellEntry`, `SpellRegistry`, `DAMAGE_SPELL_IDS` (29 spells as `Spell` enum members)
- **`tests/test_config/test_spell_registry.py`** — 51 tests across 7 test classes

### Changes

- **`scripts/sync_fixtures.py`** — Added `circles.cfg` sync, `discover_damage_spell_scripts()` for 29 damage spell `.src` files (Standard/Necro/Earth/Holy)
- **`src/omega/config/__init__.py`** — Exported `CircleConfig`, `SpellEntry`, `SpellRegistry`, `DAMAGE_SPELL_IDS`

### Key Design Decisions

- **`Spell` IntEnum integration**: `DAMAGE_SPELL_IDS` is `frozenset[Spell]` with named members (`Spell.FIREBALL`, not `18`). `SpellRegistry.by_id()` accepts both `int` and `Spell` naturally via IntEnum.
- **Case-insensitive config keys**: `_get_ci()` helper handles `SpellId`/`SpellID` (Standard vs Earth/Holy) and `PointValue`/`Pointvalue` (circles.cfg) differences.
- **UseCircle remapping**: `effective_circle()` resolves special school circles (21-28) to standard circles for damage calculations.
- **School passed explicitly**: `from_cfg()` takes `list[tuple[Path, school_name]]` — more reliable than path inference.

### Test Scenarios

- Circle parsing: 33 circles, standard values, UseCircle remapping, effective_circle resolution
- Spell parsing: 128 spells across 5 schools, field validation for Fireball/Kill/Holy Bolt/Flame Strike
- Damage spells: 29 IDs resolvable, all have circles and scripts, correct school distribution
- Lookup: by_id (int and Spell enum), find by name (case-insensitive), find by ID string
- Edge cases: empty-value keys (Change/Duration), reagent multi-value, double-space "Spell  5", power words, tuple type for reagents
- Construction: empty registry, repr, sorted output

### Stats

- Tests: 1584 (was 1533, +51 new)
- Fixture files: 266 (was 247, +19 — circles.cfg + 18 new damage spell scripts)

---

## M24 — Spell Execution Engine

Created `execute_spell()` — the entry point that runs a spell `.src` file through the interpreter and returns a `SpellResult`. Mirrors `execute_hit()` for weapon combat. Supports both NPC mode (direct damage, bypasses TryToCast) and Player mode (full casting pipeline: delay loop → mana → reagents → skill check → targeting → damage). Fixed a bug in wildcard config resolution that prevented `circles.cfg` and other root-level configs from being found by `:*:name` paths.

### New Files

- **`src/omega/combat/spell_result.py`** — `SpellResult` dataclass with spell_id, circle, element, base_damage, final_damage, fizzled, immuned, cast_success, resisted, metrics, side_effects
- **`src/omega/combat/spell.py`** — `execute_spell()`, `execute_spell_from_shard()`, `_resolve_spell_script()` (maps spell ID ranges to package paths)
- **`tests/test_runtime/test_virtual_time.py`** — 10 tests for Sleepms/Sleep virtual time advancement and ReadGameClock integration
- **`tests/test_runtime/test_multi_defender.py`** — 12 tests for multi-defender context and stub integration
- **`tests/test_combat/test_spell_execution.py`** — 45 tests across 10 test classes covering all spell execution paths

### Changes

- **`src/omega/runtime/context.py`** — Multi-defender support (`defenders` list, `main_target_index`, backward-compatible `defender` property), virtual time (`_virtual_time_ms` field, reset in `reset_hit()`)
- **`src/omega/runtime/basic_stubs.py`** — `Sleepms`/`Sleep` advance virtual time, `ReadGameClock` returns `game_clock + _virtual_time_ms // 1000`, added `SpeakPowerWords` no-op stub
- **`src/omega/runtime/structural_stubs.py`** — Added `CheckSkill` (simplified model with simulation RNG), `ConsumeMana` (reads circle config for mana cost), `ConsumeReagents`, `Target`, `TargetCoordinates`, `CheckLineOfSight`, `CheckLosAt`, `ListHostiles`, `ListMobilesNearLocation`, `ListMobilesNearLocationEx`, `GetConfigStringArray`
- **`src/omega/shard.py`** — Fixed `resolve_config_paths_wildcard` to search root `config/` directory (not just package dirs) — this was preventing `circles.cfg`, `combat.cfg`, etc. from being found by `:*:name` wildcard paths
- **`src/omega/combat/__init__.py`** — Exported `SpellResult`, `execute_spell`, `execute_spell_from_shard`
- **`src/omega/combat/hit.py`** — Updated for multi-defender context API (set `ctx.defender` after construction)
- **`submodules/zuluhotel_omega_2.5/scripts/include/spelldata.inc`** — Uncommented `areas.inc` include, added `__RecordSimulatorMetric` calls in `CalcSpellDamage` (`spell_base_damage`), `IsProtected` (`list:spell_protection`), `ModifyWithMagicEfficiency` (`spell_efficiency_penalty`)

### Key Design Decisions

- **Multi-defender backward compatibility**: `ctx.defender` property wraps `defenders[main_target_index]`, setter creates/updates single-element list. All existing `execute_hit()` code works unchanged.
- **Virtual time for spell delays**: TryToCast's `Sleepms(500)` delay loop now advances `_virtual_time_ms` so `ReadGameClock()` reflects elapsed casting time. Reset between hits.
- **Spell script modes**: NPC mode (`parms = ["#MOB", caster, target, circle, 0]`) bypasses TryToCast entirely. Player mode (`parms = caster`) runs the full casting pipeline.
- **CheckSkill simplified model**: `chance = clamp(skill - difficulty + 50, 0, 100)`, roll via simulation RNG for determinism. POL's hook-driven system is too complex to replicate fully.
- **Root config resolution fix**: `:*:name` wildcard now searches `shard_root/config/` first, then all package dirs. This was a pre-existing bug that prevented `circles.cfg`, which lives in the root config dir, from being found.

### Bug Fixes

- **`resolve_config_paths_wildcard` missing root config dir**: `:*:circles` and `:*:spells` wildcards returned None because the method only searched package directories, not the shard root `config/` directory. This caused TryToCast to read UNINIT for difficulty/mana/delay, making CheckSkill use difficulty=0 (51% chance instead of the correct circle-based difficulty).
- **`ConsumeMana` using `.get()` on `RuntimeConfigElement`**: `RuntimeConfigElement` uses `__getattr__` for property access, not a `.get()` method. Fixed to use `getattr(elem, "Circle", None)`.
- **`ConsumeMana` mana unit confusion** (M24 audit): The stub had `display_mana = current_mana // 100 if current_mana >= 100 else current_mana` — a heuristic that treated `Mobile.mana` (display units) as POL hundredths. With `mob.mana=100` (100 mana), this computed `100//100=1` and failed the cost check. Also deducted `cost * 100` instead of `cost`. Root cause: POL stores vitals in hundredths internally but `Mobile.mana` stores display units. POL C++ `check_mana()` compares `current_ones()` (display) with `manacost` (display), and `consume_mana()` deducts `manacost*100` from hundredths — equivalent to `display -= cost`. Fixed to compare and deduct in display units directly.
- **Dead `_random.seed()` in `execute_spell`**: Seeded Python's `random` module but `CheckSkill` uses `get_rng().random_int()`. Removed.
- **Missing `try/except` in `ConsumeMana` config parsing**: `int(circle_val)` and `int(mana_val)` from config could raise TypeError/ValueError on unexpected values. Added protection.

### Test Scenarios

- Spell execution: Fireball NPC/player mode, deterministic seeds, base_damage metric, circle/name in result, NPC target scaling
- Fizzle mechanics: Low magery fizzles (11% chance at skill 1 vs difficulty 40), high magery succeeds (100% chance at skill 120)
- Resistance: High magic resistance reduces damage, resisted metric populated
- Elemental protection: elemental_applied metric recorded
- CheckSkill stub: returns int, high/low/zero skill, metrics, None character handling, UNINIT difficulty, string coercion, boundary chance values, negative difficulty clamping, debug-off suppression, RNG determinism
- ConsumeMana stub: deducts correct display amount, insufficient/barely-insufficient/exact mana, metrics with display values, None character/spell_id, mana unit consistency (no //100, no *100)
- Mana unit consistency (regression): display values 15/100/200, deduction not multiplied, GetMana round-trip, player mode display values, end-to-end GetVital consistency
- Vital unit consistency: GetMana/GetVital/SetMana/SetVital round-trips for mana/HP/stamina, eScript GetMana and SetMana patterns, small/large value edge cases
- ApplyRawDamage unit consistency: GetHP/GetVital round-trip after damage, no *100 multiplication, HealDamage+ApplyRawDamage round-trip
- No-op stubs: ConsumeReagents, CheckLineOfSight, CheckLosAt
- Sleep UNINIT edge cases: Sleepms(UNINIT), Sleep(UNINIT), negative ms, string coercion, float truncation
- Player mode pipeline: success, mana deduction, zero mana fizzle, NPC bypass, fizzle = 0 damage
- Target stubs: empty defenders, TargetCoordinates with no defender
- Edge cases: dead caster/target, hidden target, minimum damage, invalid spell ID
- Multi-school: Lightning, Harm, Energy Bolt, Flame Strike, Mind Blast, Chain Lightning
- Virtual time: Sleepms advancement, sub-second accumulation, reset between hits, base clock integration, TryToCast delay loop pattern
- Multi-defender: backward compat, setter, direct list, main_target_index, Target/ListMobiles stubs
- End-to-end vital units: damage equals HP delta, GetMana after consume, GetVital mana/life consistency, mana cost range validation

### Stats

- Tests: 1707 (was 1584, +123 new)
- Fixture files: 266 (unchanged — areas.inc already present)

---

## M25 — Single-Target Damage Spells

Extended spell execution coverage to all 4 schools: Standard (7), Necromancy (4), Earth (3), Holy (2). Fixed package name case mismatch that prevented Necro and Earth spells from resolving. Added `RecalcVitals` no-op stub. Classified 3 spells from the original "single-target damage" list as non-damage (Decaying Ray = AR debuff, Wraith's Breath = paralysis/CC, Sacrifice = AoE pet mechanic).

### Bug Fixes

- **Package name case mismatch in `_resolve_spell_script()`**: Returned `:necro:` and `:earth:` but pkg.cfg declares `Name Necro` and `Name Earth`. `DictPackageMap.resolve()` is case-sensitive (correct for Linux filesystem). All Necro and Earth spells failed with "Unknown package". Fixed to use `:Necro:` and `:Earth:`.
- **Missing `RecalcVitals` POL built-in stub**: Called indirectly via `RecalcVitalsIfOnline()` in `attributes.inc` when stat modifications happen (e.g., Decaying Ray's `DotempMod`). Produced "Unimplemented built-in" warning. Added no-op stub returning 1.

### Changes

- **`src/omega/combat/spell.py`** — Fixed `_resolve_spell_script()` to use correct package name case: `:Necro:` and `:Earth:` (was lowercase)
- **`src/omega/runtime/object_stubs.py`** — Added `RecalcVitals` no-op stub (vitals module)

### Spell Classification Corrections

| Spell | ID | Listed As | Actual Type | Reason |
|---|---|---|---|---|
| Decaying Ray | 67 | Single-target damage | AR debuff | Uses `DotempMod("ar", ...)`, no damage calls |
| Wraith's Breath | 72 | Single-target damage | AoE paralysis/CC | Sets `mobile.frozen := 1`, no damage calls |
| Sacrifice | 71 | Single-target damage | AoE pet sacrifice | Kills pet, distributes damage to nearby mobs |

Holy Bolt (170) is alignment-gated: NPC caster → player target deals damage; NPC → NPC or player → good NPC heals instead. Tests cover both paths.

### Test Scenarios

- All 15 single-target damage spells (Standard + Necro + Earth + Holy): execute successfully, deal positive damage, deterministic with seed, have circle metadata
- Holy Bolt alignment: NPC→player damages, NPC→NPC heals, player→player heals
- Non-damage spells: Decaying Ray executes with 0 damage, Wraith's Breath executes with 0 damage, Sacrifice executes
- Damage properties: higher circle → higher damage, NPC target > player target, resistance reduces damage, standard spells increase with circle
- School metrics: Standard spells have elemental_applied, Necro spells have planar_applied, Earth spells have elemental_applied, Divine Fury has planar_applied
- Edge cases: Wyvern Strike poison, Sorcerer's Bane dual damage, Kill massive damage vs low HP, Spectre's Touch, Shifting Earth, Call Lightning, Ice Strike
- Hand-calculated: Fireball damage range across 50 seeds, Flame Strike > Fireball average, Kill > 100 damage, Magic Arrow < 100 damage
- RecalcVitals stub: registered and returns 1, Decaying Ray doesn't error

### Stats

- Tests: 1805 (was 1707, +98 new)
- Fixture files: 266 (unchanged)

---

## M26 — AoE Damage Spells

All 7 AoE damage spells execute correctly against multiple targets across 4 schools: Standard (Explosion, Chain Lightning, Meteor Swarm, Earthquake), Necromancy (Abyssal Flame), Earth (Rising Fire), Holy (Apocalypse). Fixed method call dispatch for POL built-ins used as member functions. Added package-directory search for `start_script()` relative paths. Reclassified 3 spells from AoE to single-target (Gust of Air, Wrath of God) and CC (Astral Storm).

### Bug Fixes

- **Method call dispatch missing POL built-in fallback**: `_call_method` in `evaluator.py` only checked instance methods via `getattr(obj, name)`. When eScript calls `cast_on.SetParalyzed(0)` — a POL built-in invoked as a method call — the dispatch never fell back to the POL function registry. Added fallback: after exhausting instance method lookup, checks the POL function registry with the object as the first argument.
- **`start_script()` relative path resolution**: `start_script("astralstorm_damage", ...)` with a bare name failed because `_resolve_script_path` only searched `scripts/` and shard root, not package directories. In POL, relative paths resolve from the calling script's package. Added search across all registered package directories as fallback.
- **Missing `ListItemsNearLocation` stub**: Earthquake calls `ListItemsNearLocation()` (without OfType) for nearby item search. Was not implemented.

### New Files

- **`tests/fixtures/shard/pkg/opt/holybook/astralstorm_damage.src`** — Astral Storm damage sub-script (5 damage applications at CalcSpellDamage/8 each)

### Changes

- **`src/omega/interpreter/evaluator.py`** — `_call_method` falls back to POL function registry for built-ins called as methods
- **`src/omega/interpreter/executor.py`** — `_resolve_script_path` searches all package directories for relative `start_script()` paths
- **`src/omega/runtime/structural_stubs.py`** — Added `ListItemsNearLocation` and `ListItemsNearLocationOfType` no-op stubs (return empty arrays)
- **`scripts/sync_fixtures.py`** — Added `astralstorm_damage.src` to extra scripts list

### Spell Classification Corrections

| Spell | ID | Listed As | Actual Type | Reason |
|---|---|---|---|---|
| Gust of Air | 89 | AoE damage | Single-target | Uses `CanTargetSpell` not `CanTargetArea`, no foreach loop |
| Wrath of God | 174 | AoE damage | Single-target karma-based | No AoE loop, damage based on Karma difference |
| Astral Storm | 176 | AoE damage | CC + damage sub-script | Main script is paralysis; damage via `start_script("astralstorm_damage")` |

### AoE Spell Patterns

| Pattern | Spells | Description |
|---|---|---|
| Standard AoE | Explosion, Chain Lightning, Earthquake | CanTargetArea → ListMobiles → SmartAoE → foreach → damage |
| Dual-phase | Meteor Swarm (Fire+Earth), Rising Fire (Fire×2) | Two damage passes with sleep between phases |
| Primary + AoE | Abyssal Flame | Primary target at circle/2, then AoE secondary at circle/2 with AREA_EFFECT_SPELL |
| Three-phase | Apocalypse | Chain lightning + earthquake + meteor effects, 24% damage per phase |

### Test Scenarios

- All 7 AoE spells: execute with success, deal positive damage, deterministic with seed
- Multi-target: each of 3+ targets takes HP damage independently
- Meteor Swarm: dual-phase, dual-element, deals more than single-phase Explosion
- Rising Fire: dual-phase half-damage per phase, Fire element
- Abyssal Flame: primary + secondary targets both damaged
- Earthquake: ListItemsNearLocation/OfType no-ops, .multi UNINIT no crash, caster excluded
- Apocalypse: NPC caster mode, player targets, .multi UNINIT no crash
- Circle reduction: AoE per-target damage < equivalent single-target (circle-3)
- Resistance: high resist averaged over 20 seeds ≤ low resist damage
- Reclassified: Gust of Air, Wrath of God execute as single-target with damage
- Wrath of God: karma-based damage, equal karma → 0 damage
- Astral Storm: CC + damage sub-script fires, deals damage via 5× ApplyPlanarDamage
- Method call dispatch: SetParalyzed registered, dispatches via POL fallback, records side effect
- Edge cases: empty defender list, single defender, 5 defenders, dead/hidden targets
- Damage properties: higher circle → more damage, NPC > player targets, target count independent
- Stub tests: ListItemsNearLocation and ListItemsNearLocationOfType registered and return empty

### Stats

- Tests: 1854 (was 1805, +49 new)
- Fixture files: 267 (was 266, +1 astralstorm_damage.src)

---

## M27 — Spell Scenario Runner & Stats

Added `SpellScenario`, `run_spell_scenario()`, `run_spell_sweep()`, and `aggregate_spell_cell()` — the spell simulation runner layer parallel to the existing weapon-hit runner. Spell-specific stats: fizzle rate, resist rate, resist rate on cast, DPS via casting delay. Added lazy `spell_registry` property to `ShardData`. Fixed multiple bugs discovered during comprehensive shard integration testing.

### New Files

- **`src/omega/simulation/spell_runner.py`** — `run_spell_scenario()` (N iterations with snapshot/restore), `run_spell_sweep()` (Cartesian product parameter sweeps), `_apply_spell_variable()`, `_normalize_targets()`
- **`tests/test_simulation/test_spell_stats.py`** — 26 unit tests for `aggregate_spell_cell()`: empty results, fizzle/resist rates, on-cast stats, timing/DPS, elemental breakdown, percentiles, immuned handling, UNINIT safety, regression against weapon-hit `aggregate_cell()`
- **`tests/test_simulation/test_spell_runner.py`** — 16 mock-based runner tests: iteration count, deterministic seeds, state reset, executor reuse, fizzle/resist rate propagation, AoE targets, single target normalization, sweep variables, Cartesian products, shard integration
- **`tests/test_simulation/test_spell_runner_shard.py`** — 82 comprehensive shard integration tests across 15 test classes (C1–C15): per-spell execution (all damage spells), fizzle rate validation (first-principles CheckSkill formula), resistance, damage validation, mana cost, casting delay/DPS, magic efficiency, class bonuses, PvP scaling, elemental protection, skill scaling sweeps, AoE multi-target, edge cases, determinism, sweep acceptance criteria

### Changes

- **`src/omega/simulation/scenario.py`** — Added `SpellScenario` and `SpellParameterSweep` frozen dataclasses; `build_combatant` sets `npctemplate` on NPC mobiles, only equips weapon/armor when specified (bare hands = empty LAYER_HAND1 matching POL behavior)
- **`src/omega/simulation/stats.py`** — Extended `RatioStats` with `fizzle_rate`, `resist_rate`, `resist_rate_on_cast`; extended `CellResult` with `damage_stats_on_cast`; added `aggregate_spell_cell()` with spell-specific aggregation logic
- **`src/omega/simulation/__init__.py`** — Exported new spell symbols
- **`src/omega/reporting/tables.py`** — Added spell stats to `_get_stat()` and `_RATE_STATS`: `fizzle_rate`, `resist_rate`, `resist_rate_on_cast`, `cast_rate`, `mean_on_cast`, `median_on_cast`
- **`src/omega/shard.py`** — Added lazy `spell_registry` property that auto-builds `SpellRegistry` from shard `spells.cfg` and `circles.cfg` files
- **`src/omega/model/items.py`** — Added `Weapon.set_blocks_casting(blocks: bool)` helper method
- **`src/omega/combat/spell.py`** — Added fallback fizzle detection for player mode (TryToCast early return without metrics)
- **`tests/test_model/test_items.py`** — 3 unit tests for `set_blocks_casting`
- **`tests/test_reporting/test_tables.py`** — Updated `_RATE_STATS` assertion to include spell rates

### Bug Fixes

- **`aggregate_spell_cell()` returning None**: Missing `return cell` at end of function — all 42 unit tests failed until fixed.
- **`ShardData` missing `spell_registry`**: `run_spell_scenario(shard=shard)` couldn't auto-load spell metadata. Added lazy property that scans packages for `spells.cfg` files and builds `SpellRegistry`.
- **Player mode fizzle detection**: When TryToCast fails (skill check or mana), the spell script returns early without recording DEBUG_MODE metrics. The existing checks for `spell_skill_check == 0` only triggered when the key exists with value 0, not when absent. Added fallback: if player mode, 0 base/final damage, and no `spell_base_damage` metric → mark as fizzled.
- **Default Fist weapon blocking spell casting**: `build_combatant` always equipped a `Weapon(name="Fist")` with objtype 0 in LAYER_HAND1. TryToCast reads `weapcfg[hand1.objtype].BlocksCastingIfInHand` from config — for unknown objtype 0, config lookup returns None, member access returns UNINIT, and `UNINIT != 0` evaluates True → blocks casting. Fix: don't equip weapon/armor when not specified, matching POL behavior where bare hands means empty LAYER_HAND1.
- **Missing `npctemplate` on NPC mobiles**: `build_combatant` created `Mobile(is_npc=True)` without setting `npctemplate`, causing CalcSpellDamage to not distinguish NPC from player targets (identical PvP scaling applied to both). Fixed by setting `npctemplate` from spec.

### Key Design Decisions

- **Parallel to weapon-hit runner**: `SpellScenario` / `run_spell_scenario()` mirrors `Scenario` / `run_scenario()` exactly — same snapshot/restore, executor reuse, seed XOR pattern.
- **Spell-specific aggregation**: `aggregate_spell_cell()` handles fizzle zeros in `damage_stats` (includes them) vs `damage_stats_on_cast` (excludes them). `hit_rate` = cast success rate (analogous to weapon hit rate).
- **Bare-hands = no equipment**: In POL, an unarmed combatant has no item in LAYER_HAND1, so `GetEquipmentByLayer` returns nothing and TryToCast's equipment check is skipped entirely. The `Weapon(name="Fist")` is still created for API compatibility but not equipped.
- **`set_blocks_casting()` helper**: Wraps the `BlocksCastingIfInHand` config property on `Weapon` for explicit API. Useful for tests where a weapon is equipped but shouldn't block casting.

### Test Scenarios

- **Per-spell execution (C1)**: All damage spells execute without error, deal positive damage (non-fizzled), deterministic with seed
- **Fizzle rate validation (C2)**: CheckSkill formula `chance = clamp(skill - difficulty + 50, 0, 100)` verified at Magery 0/50/80/100 against Circle 3 and 7 difficulties, NPC mode bypass
- **Resistance (C3)**: Zero resist → low rate, high resist (130) → high rate, higher resist → lower mean damage
- **Damage validation (C4)**: Fireball NPC caster range 29–72, Flame Strike > Fireball, Kill > 100 damage, higher circle → higher damage
- **Mana cost (C5)**: Fireball=9, Lightning=11 from circles.cfg
- **Casting delay/DPS (C6)**: Fireball=1500ms, Flame Strike=2000ms from circles.cfg, NPC mode=0 delay, DPS computation
- **Magic efficiency (C7)**: MagicPenalty sweep 0→100 produces monotonically decreasing damage
- **Class bonuses (C8)**: Mage caster > classless, Mage level sweep increasing, Warrior caster < classless, Mage target < classless target damage
- **PvP scaling (C9)**: NPC→NPC > player→NPC (/3), NPC→player < NPC→NPC (/3), player→player < player→NPC (×0.6)
- **Elemental protection (C10)**: FireProtection sweep reduces Fireball damage monotonically
- **Skill scaling (C11)**: Magery sweep increasing damage, EvalInt sweep increasing, Magic Resistance sweep decreasing
- **AoE multi-target (C12)**: Chain Lightning hits all 3 targets, per-target damage < single-target
- **Edge cases (C13)**: Zero Magery (~90% fizzle), zero mana fizzle, dead caster/target, deterministic seeds
- **Determinism (C14)**: Same seed → same CellResult across 2 runs, different seeds → different distributions
- **Sweep acceptance (C15)**: Magery increasing, Resist decreasing, MagicPenalty decreasing — all monotonic

### Stats

- Tests: 1979 (was 1854, +125 new)
- Fixture files: 267 (unchanged)

---

## M28 — Reporting, Notebooks & Documentation

Added spell-specific plot functions, metric tracking enhancements, DEBUG_MODE fixture patching, 3 new notebooks, spell sections in all 5 existing notebooks, and full documentation update for V3 spell casting.

### New Files

- **`notebooks/06_spell_damage.ipynb`** — Primary spell showcase: single spell scenario, fizzle analysis, resist analysis, elemental protection sweep, PvP scaling, pipeline metrics, casting DPS
- **`notebooks/07_spell_comparison.ipynb`** — Spell comparison: circle scaling (C1→C7), school comparison (Standard vs Necro vs Earth vs Holy), AoE vs single-target, NPC vs player mode
- **`notebooks/08_spell_resistance.ipynb`** — Resistance deep-dive: resist vs MagicResistance sweep, EvalInt scaling, class modifiers, protection stacking, over-protection healing
- **`notebooks/docs/spells.md`** — Spell catalog reference (29 damage spells with circle, element, type, school)

### Changes

**Reporting**:
- **`src/omega/reporting/plots.py`** — Added `spell_comparison()` (grouped bar chart by spell, color-coded by element, with fizzle/resist annotations) and `fizzle_rate_vs_parameter()` (dual-line plot of fizzle + resist rates across swept parameter)

**Metric Tracking**:
- **`src/omega/runtime/object_stubs.py`** — `ApplyRawDamage` records `ctx.metrics["spell_final_applied_damage"]` in debug mode
- **`src/omega/runtime/structural_stubs.py`** — `ListMobilesNearLocationEx` records `ctx.metrics["aoe_target_count"]` in debug mode
- **`submodules/zuluhotel_omega_2.5/scripts/include/spelldata.inc`** — Added `__RecordSimulatorMetric("spell_dice_roll", dmg)` in CalcSpellDamage after RandomDiceRoll, inside existing `if(DEBUG_MODE)` guard

**DEBUG_MODE Fixture Patching**:
- **`scripts/sync_fixtures.py`** — Added `_patch_debug_mode()` that replaces `const DEBUG_MODE := 1` with `const DEBUG_MODE := 0` in fixture copies of `client.inc`. This proves the executor's `define_global("DEBUG_MODE", 1)` override works correctly — fixtures have DEBUG_MODE=0 but metrics are still recorded.

**Notebooks (enriched)**:
- **`notebooks/01_basic_damage.ipynb`** — Added "Spell Casting Comparison (V3)" section with Fireball scenario, histogram, comparison table
- **`notebooks/02_skill_sweep.ipynb`** — Added "Spell Damage vs Magery (V3)" section with Magery sweep, fizzle rate plot, summary table
- **`notebooks/03_class_comparison.ipynb`** — Added "Spell Damage by Caster Class (V3)" section with Mage/Paladin/Warrior comparison
- **`notebooks/04_weapon_comparison.ipynb`** — Added "Weapon vs Spell DPS (V3)" section comparing Warrior weapon DPS vs Mage Fireball DPS
- **`notebooks/05_enchantments.ipynb`** — Added "Spell Strike vs Direct Casting (V3)" section

**Documentation**:
- **`notebooks/docs/README.md`** — Updated with V3 capabilities, notebooks 06-08, spells.md reference
- **`notebooks/docs/reporting.md`** — Added `spell_comparison()`, `fizzle_rate_vs_parameter()`, 11 spell stat columns
- **`notebooks/docs/scenarios.md`** — Added `SpellScenario`, `SpellParameterSweep`, `run_spell_scenario`, `run_spell_sweep`
- **`notebooks/docs/results.md`** — Added `SpellResult`, spell `RatioStats`, `damage_stats_on_cast`
- **`notebooks/docs/concepts.md`** — Added spell casting pipeline diagram, V3 additions
- **`notebooks/docs/examples.md`** — Added Recipe 18 (basic spell), Recipe 19 (fizzle sweep), Recipe 20 (school comparison)

### Tests

- **`tests/test_reporting/test_plots.py`** — Tests for `spell_comparison()` and `fizzle_rate_vs_parameter()`: returns figure, custom titles, single/empty cells, show_fizzle/show_resist toggles
- **`tests/test_reporting/test_tables.py`** — Tests for spell stat columns: fizzle_rate, resist_rate, resist_rate_on_cast, cast_rate, mean_on_cast, median_on_cast
- **`tests/test_combat/test_spell_execution.py`** — Tests for `spell_dice_roll` metric, `aoe_target_count` metric, `spell_final_applied_damage` metric, DEBUG_MODE override verification (3 tests proving fixture has DEBUG_MODE=0 but executor override produces metrics)
- **`tests/test_runtime/test_object_stubs.py`** — Tests for ApplyRawDamage metric recording in debug mode
- **`tests/test_simulation/test_spell_runner_shard.py`** — Fixed 2 skipped tests (HOLY_BOLT, WRATH_OF_GOD) by filtering `_ZERO_DAMAGE_SPELLS` from parametrize

### Key Design Decisions

- **DEBUG_MODE patching in sync_fixtures**: Fixtures have `DEBUG_MODE := 0` (matching what a non-simulator environment would see), while the executor always overrides to 1. This validates the override mechanism end-to-end.
- **POL wrapper metrics over `__RecordSimulatorMetric`**: `spell_final_applied_damage` and `aoe_target_count` are recorded in Python POL stub wrappers rather than eScript instrumentation — simpler and doesn't require shard changes.
- **`spell_dice_roll` in shard**: The raw dice roll before cap/efficiency is only available inside CalcSpellDamage in eScript, so `__RecordSimulatorMetric` is the right choice here. Combined with existing `spell_base_damage` (post-cap), analysts can see when the damage cap was reached.

### Test Scenarios

- Plot functions: spell_comparison returns figure, custom title, single spell, empty cells, fizzle/resist annotations, show_fizzle=False; fizzle_rate_vs_parameter returns figure, no data, show_resist=False
- Table stats: all 6 spell stat columns render correctly, comparison table with spell columns + delta, rate formatting as percentages
- Metrics: spell_dice_roll > 0 and present, aoe_target_count matches defender count, spell_final_applied_damage matches final_damage, ApplyRawDamage records in debug mode only
- DEBUG_MODE: fixture has `const DEBUG_MODE := 0`, spell execution still produces spell_dice_roll/spell_base_damage metrics, hit execution still produces damage_applied/damage_before_ar metrics
- Zero-damage spells excluded from damage assertions (HOLY_BOLT, WRATH_OF_GOD)

### Stats

- Tests: 2018 (was 1979, +39 new, 0 skipped)
- Fixture files: 267 (unchanged)

---

## M29 — Test Coverage Review & POL Stub Audit

Comprehensive test coverage audit and POL stub conformance review for the spell-casting pipeline. 178 new tests across 20 test classes covering all M29 requirements: every damage spell has 2+ tests, AoE with 1/3/5 targets, resistance at 0%/50%/100%, class modifiers, PvP scaling, fizzle tests, edge cases. Fixed ApplyRawDamage float→int conversion bug (was rounding, should truncate per POL's C++ `static_cast<int>`).

### Bug Fixes

- **ApplyRawDamage float→int conversion**: Was using `int(round(float(amount)))` (Python banker's rounding: 23.5→24) but POL's `getParam(1, damage)` only accepts BLong (integer) and C++ `static_cast<int>` truncates toward zero (23.7→23). Fixed to `int(float(amount))` in `structural_stubs.py`. In practice, eScript always `CInt()`s damage before calling `ApplyRawDamage`, so the fix is for strict POL conformance.

### New Files

- **`tests/test_m29_coverage_audit.py`** — 178 tests across 20 test classes organized in 7 sections

### Changes

- **`src/omega/runtime/structural_stubs.py`** — Fixed `ApplyRawDamage` to truncate floats instead of rounding
- **`tests/test_runtime/test_structural_stubs.py`** — Updated existing float damage test to expect truncation (77 not 76)

### Test Coverage (20 Test Classes)

**Section 1 — POL Stub Audit (9 classes)**:
- `TestApplyRawDamageAudit` — Truncation conformance, zero/negative/UNINIT damage, dead target, large damage, hundredths precision, damage tracking, context missing
- `TestRandomAudit` — Range [1, max_val], boundary values, large range, single value
- `TestRandomIntAudit` — Range [0, max_val-1], boundary values, large range
- `TestRandomDiceRollAudit` — XdY+Z parsing, known seeds, negative bonus, single die, large rolls, zero faces, dice count bounds
- `TestCheckSkillAudit` — Chance formula validation, boundary skills, UNINIT difficulty, metrics recording, None character
- `TestConsumeManaAudit` — Display unit deduction, insufficient mana, exact mana, zero cost, metrics recording
- `TestGetEffectiveSkillAudit` — Skill retrieval, zero/max skill, missing skill, UNINIT attribute
- `TestGetSetObjPropertyAudit` — Set/get round-trip, overwrite, erase, missing property, UNINIT key, nested values
- `TestReadConfigFileAudit` — Config loading, element access, missing element, key access, missing file

**Section 2 — Resistance at Multiple Skill Levels**:
- `TestResistanceMultipleLevels` — Zero resist (no reduction), mid resist (~50%), max resist (~100%), resist monotonically decreasing damage, parametrized across 5 standard spells

**Section 3 — Resisted() Formula Validation**:
- `TestResistedFormulaValidation` — Chance = max(resist/6, resist - magery/4 - circle*6), resist rate proportional to chance, EvalInt scaling (integer division by 200), high EvalInt advantage, zero EvalInt = no scaling bonus

**Section 4 — Class Modifier Effects**:
- `TestClassModifierEffects` — Mage caster bonus > classless, Warrior caster penalty < classless, Mage target takes less damage, class level scaling, NPC→NPC vs player→NPC mode

**Section 5 — PvP Scaling All Combos**:
- `TestPvPScalingCombos` — NPC→NPC baseline, NPC→player (/3 CalcSpellDamage), player→NPC (/3), player→player (×0.6 ApplyTheDamage), PvP < PvE for all modes

**Section 6 — AoE Spells With Varying Target Counts**:
- `TestAoETargetCounts` — 1/3/5 targets for all 4 AoE spells (Explosion, Chain Lightning, Meteor Swarm, Earthquake), damage dealt to majority of targets

**Section 7 — Edge Cases (4 classes + 3 coverage classes)**:
- `TestOverProtectionHealing` — 100% elemental protection results in 0 or negative damage (healing)
- `TestMaxCircleDamage` — Circle 7 > Circle 1, high-circle spells produce substantial damage
- `TestZeroDamageFloor` — Minimum skill/stats still produces valid results (no negative damage)
- `TestUNINITEdgeCases` — UNINIT resist skill, UNINIT eval int, UNINIT magery, UNINIT element protection, UNINIT class level — all handled gracefully without crashes
- `TestSpellPerSpellCoverage` — Every damage spell in DAMAGE_SPELL_IDS executes successfully and deals positive damage
- `TestFizzleAtVariousMageryLevels` — Fizzle rate at Magery 0 (near 100%), Magery 50 (moderate), Magery 100 (near 0%), NPC bypass, fizzle = 0 damage
- `TestManaCostPerCircle` — Mana cost matches circles.cfg, mana deducted correctly, increasing cost with circle

### Stats

- Tests: 2196 (was 2018, +178 new, 0 skipped)
- Fixture files: 267 (unchanged)
