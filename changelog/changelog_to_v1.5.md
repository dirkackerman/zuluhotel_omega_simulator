# Changelog to V1.5

This changelog tracks progress on V1.5 (Elemental & Enchanted Weapons). See [Path to V1.5](../planning/path_to_v1.5.md) for the full roadmap.

---

## M12 — Elemental Protection Stubs

**Summary**: Verified that the shard's elemental protection functions (`GetProtLevel`, `GetResultingElementalProt`, `IsImmunedFromThisDamageType`) execute correctly through the interpreter. Added missing infrastructure for the elemental damage path.

**Changes**:
- **Interpreter bug fix**: `case`/`break` — `break` inside a `case` branch was propagating as an unhandled `BreakSignal` instead of exiting the matched case. Fixed in `evaluator.py`.
- **Mobile model**: Added `hidden` (bool) and `master` (Any) attributes needed by `ApplyElementalDamageNoResist` in spelldata.inc.
- **Snapshot**: `hidden` is now captured/restored between iterations.
- **HealDamage stub**: New POL built-in stub (`vitals::HealDamage`) for the over-protection healing path (protection > 100% heals instead of damages). Records a `"heal"` side effect.
**Testing**:
- Verify `GetProtLevel` returns the correct property value for each of the 6 mapped elements (FIRE/AIR/EARTH/WATER/NECRO/HOLY) and returns 0 for unmapped elements (POISON, ACID, PHYSICAL, MAGIC, ASTRAL)
- Verify `GetResultingElementalProt` delegates to `GetProtLevel` (dead code after early return on line 645)
- Verify `IsImmunedFromThisDamageType` handles: full immunity, partial immunity (damage reduction), no immunity, and `DMGID_NO_RESIST` bypass
- Verify over-protection (>100%) path reaches `HealDamage` — heals instead of damages
- Verify `hidden` state is preserved across snapshot/restore cycles
- Confirm existing combat tests still pass (the `case`/`break` fix is a behavioral change)

**Key insight**: The protection functions are eScript user-defined functions in spelldata.inc/damages.inc (not POL built-ins). They're already in the parsed include chain (`hitscriptinc.inc → dotempmods.inc → spelldata.inc`). M12 was about verifying they work and filling infrastructure gaps.

---

## M13 — Elemental Damage Application

**Summary**: Verified that the full elemental damage path works end-to-end through the interpreter. Instrumented the shard scripts with `__RecordSimulatorMetric` calls using a new `list:` protocol for per-element metric accumulation. No Python stubs were needed — `ApplyElementalDamageNoResist` and `ApplyTheDamage` are eScript functions already in the include chain.

**Changes**:
- **`list:` metric protocol**: `__RecordSimulatorMetric("list:name", struct{...})` appends the struct to a named list in `ctx.metrics["name"]`. Explicit and self-documenting — controlled from the eScript side, no Python-side prefix detection.
- **Shard instrumentation** (3 locations, all inside `if(DEBUG_MODE)` guards):
  - `hitscriptinc.inc` — `list:elemental`: per-element base damage, pct, element name, element ID
  - `spelldata.inc` — `list:elemental_applied`: net damage after protection (or healed amount for over-protection)
  - `damages.inc` — `list:damage_applied`: per-`ApplyTheDamage` call with attack type and amount
- **`_record_metric` override** (`hit.py`): Updated to detect the `list:` prefix on the key argument and accumulate struct values into named lists. Struct-merge and single-KVP modes unchanged.
- **`client.inc` docstring**: Updated `__RecordSimulatorMetric` comment to document the 3 calling conventions (single KVP, struct merge, list append).

**Testing**:
- Verify a `FIRE:50 PHYSICAL:50` weapon splits damage into both fire and physical portions, with correct proportional base damage
- Verify pure physical weapon (no `ElementalDamage` property) produces no elemental metrics and deals damage as before
- Verify fire protection (30%) reduces total damage compared to no protection
- Verify 100% fire protection blocks all fire damage (net = 0)
- Verify over-protection (150%) causes healing instead of damage, records a `heal` side effect
- Verify `list:` protocol produces actual lists in `ctx.metrics` (not scalar overwrites)
- Verify `damage_applied` list tracks all `ApplyTheDamage` calls with type and amount
- Verify scalar metrics (like `absorbed`) remain unaffected by the `list:` protocol

**Key insight**: Like the protection functions in M12, `ApplyElementalDamageNoResist` and `ApplyTheDamage` are eScript user-defined functions — not POL built-ins. The entire elemental damage path runs through the interpreter without any Python wrapping. The `list:` metric protocol solves the per-element accumulation problem cleanly from the eScript side.

---

## M14 — Elemental Damage Reporting

**Summary**: Surfaced per-element damage breakdown in results and reporting. Each element now tracks gross damage, net damage, protection percentage, healed amount, and absorbed amount. Data flows from `ctx.metrics` through `HitResult.metrics` into `ElementalBreakdown` on `CellResult`.

**Changes**:
- **`HitResult.metrics`** (`result.py`): New `dict[str, Any]` field — all `ctx.metrics` are now propagated to the result layer, making metric data available for aggregation.
- **`ElementDamage` dataclass** (`stats.py`): Per-element struct with `gross`, `net`, `prot`, `healed` fields and a computed `absorbed` property (`gross - net`).
- **`ElementalBreakdown` dataclass** (`stats.py`): Holds `dict[str, ElementDamage]` with accessor methods: `total_net`, `total_gross`, `net_dict()`, `gross_dict()`, `prot_dict()`.
- **`aggregate_cell()`** (`stats.py`): Computes mean gross/net/prot/healed per element from `HitResult.metrics["elemental_applied"]` across iterations.
- **`elemental_breakdown_chart()`** (`plots.py`): Horizontal stacked bar chart showing net damage by element with fixed color mapping.
- **`elemental_vs_parameter()`** (`plots.py`): Stacked bar chart of per-element net damage across a swept parameter.
- **`_get_stat()` extension** (`tables.py`): Dynamic element stat columns — `elem_<name>` (defaults to net), `elem_<name>_net`, `elem_<name>_gross`, `elem_<name>_prot`, `elem_<name>_absorbed`, `elem_total_net`, `elem_total_gross`.
- **`dmg_gross` metric** (`spelldata.inc`): Added pre-protection damage to the `list:elemental_applied` struct so both gross and net are captured per element.

**Testing**:
- Verify `ElementDamage.absorbed` equals `gross - net`
- Verify `ElementalBreakdown` with single/multi elements computes correct totals
- Verify `aggregate_cell` computes mean gross/net/prot across multiple iterations
- Verify pure physical weapon produces empty elemental breakdown
- Verify over-protection entries aggregate healed amounts correctly
- Verify table columns `elem_fire`, `elem_fire_gross`, `elem_fire_prot`, `elem_fire_absorbed` return correct values
- Verify `elem_total_net` sums across all elements
- Verify `elemental_breakdown_chart` and `elemental_vs_parameter` return Figure objects
- Verify empty/missing elemental data handled gracefully in both plots and tables

---

## M15 — Sub-Script Executor

**Summary**: Extended the `Executor` to find, parse, and run sub-scripts (`.src` program files) by path. The `start_script()` POL stub now dispatches to `Executor.run_sub_program()` with scope isolation. Sub-scripts share the main script's function registry and global constants but get an isolated local scope that is cleaned up on return.

**Changes**:
- **`Executor.run_sub_program(script_path, args)`** (`executor.py`): New method — resolves a `:package:name` script path, lazily parses the `.src` file, caches the program block, and executes it with scope isolation (push/pop). Args are passed as positional parameters per POL convention.
- **`Executor._resolve_script_path()`** (`executor.py`): Resolves `:combat:scriptname` → `pkg/.../scriptname.src` using the package map. Tries `.src` extension first, then bare name.
- **`Executor._load_sub_script()`** (`executor.py`): Parses a sub-script `.src` file, extracts its program block, registers any new functions, and caches the result. Shared function registry means sub-scripts can call functions from the main include chain.
- **`Executor` constructor**: New optional `shard_root` and `package_map` parameters for sub-script path resolution.
- **`SimulationContext.executor`** (`context.py`): New field — gives `start_script()` access to the executor for dispatch.
- **`start_script()` stub** (`structural_stubs.py`): Updated from V1 no-op to dispatch via `ctx.executor.run_sub_program()`. Falls back to no-op warning if no executor is set.
- **`execute_hit()`** (`hit.py`): Now passes `shard_root`/`package_map` to the Executor and sets `ctx.executor` before script execution.
- **`run_scenario()`/`run_sweep()`** (`runner.py`): Pass `shard_root`/`package_map` through to `execute_hit()` when a shard is provided.

**Testing**:
- Verify sub-script runs and returns computed values from array arguments
- Verify POL convention: args array passed as single first positional argument, program unpacks via indexing
- Verify named-param programs with `TypeOf(attacker) == "array"` self-unpack pattern
- Verify scope isolation: sub-script variables don't leak to main program
- Verify global constants from main script are accessible in sub-scripts
- Verify scope depth is restored after sub-script returns
- Verify sub-scripts can call shared user-defined functions from the main include chain
- Verify missing shard_root raises RuntimeError
- Verify unknown package raises FileNotFoundError
- Verify missing .src file raises FileNotFoundError
- Verify sub-script program blocks are cached across calls
- Verify `start_script()` stub dispatches to executor and returns result
- Verify `start_script()` with no executor returns None gracefully

**Key insight**: Sub-scripts share the same function registry and global scope as the main program. This is critical because shard sub-scripts (`reactivearmoronhit.src`, `piercingscript.src`, etc.) include the same files as `mainhit.src` and call the same functions (`ApplyTheDamage`, `RecalcDmg`). Parsing just the `.src` file (without re-parsing includes) is sufficient since all functions are already registered.

---

## M16 — Fixture Sync for Enchantment Scripts

**Summary**: Added 13 enchantment sub-scripts to the test fixture set via data-driven discovery from `hitscriptdesc.cfg`. Fixture count increased from 209 to 222 files (891 KB). No new include files needed — all dependencies were already in the fixture tree.

**Changes**:
- **`discover_enchantment_scripts()`** (`sync_fixtures.py`): New function — parses `hitscriptdesc.cfg` with regex to extract unique `Hitscript` values, resolves `:combat:name` → `.src` file paths. Also includes the hardcoded `reactivearmoronhit.src`.
- **`_find_package_dir()`** (`sync_fixtures.py`): Helper to resolve package names to directories by scanning `pkg.cfg` files.
- **`sync_fixtures()`** (`sync_fixtures.py`): New step 2b between include tree copy and pkg.cfg copy — discovers and copies enchantment scripts.

**Scripts added** (13 files under `tests/fixtures/shard/pkg/systems/combat/`):
- Spell type (1): `spellstrikescript.src`
- Slayer type (1): `slayerscript.src`
- Effect type (7): `piercingscript.src`, `banishscript.src`, `poisonhit.src`, `lifedrainscript.src`, `manadrainscript.src`, `staminadrainscript.src`, `blindingscript.src`
- Greater type (3): `dualplanarscript.src`, `voidscript.src`, `trielementalscript.src`
- Hardcoded (1): `reactivearmoronhit.src`

**Testing**:
- Verify `sync_fixtures.py` discovers exactly 13 enchantment scripts
- Verify all 13 `.src` files are present in `tests/fixtures/shard/pkg/systems/combat/`
- Verify no new include files were needed (all 8 unique includes already in fixture tree)
- Verify all existing tests still pass after fixture refresh (777 tests)
- Verify `sync_fixtures.py --dry-run` previews the enchantment scripts

**Key insight**: Discovery is data-driven — `hitscriptdesc.cfg` is the source of truth for which scripts exist. When the shard adds or removes enchantments, `sync_fixtures.py` automatically adapts without code changes.

---

## M17 — Reactive Armor

**Summary**: Implemented the reactive armor on-hit script end-to-end. When a defender has a `ReactiveArmor` property, the combat pipeline calls `start_script(":combat:reactivearmoronhit", ...)` which reflects damage back to the attacker. Player attackers receive 1/8 retaliation; NPC attackers receive full. All pipeline values (retaliation, reduction factor, actual damage, additional damage) are recorded via `__RecordSimulatorMetric`.

**Changes**:
- **`reactivearmoronhit.src` instrumentation** (shard submodule): Added `__RecordSimulatorMetric` struct calls inside `if(DEBUG_MODE)` guards in both branches (player/NPC). Records: `reactive_triggered` (1), `reactive_retaliation` (pre-reduction), `reactive_reduction` (8 for players, 1 for NPCs), `reactive_damage` (actual), `reactive_additional_damage` (same as reactive_damage — explicit additional damage tracking).
- **`CombatantSpec.properties`** (`scenario.py`): New `dict[str, Any]` field — mobile-level properties applied via `set_property()` during `build_combatant()`. Enables setting `ReactiveArmor` on defender specs.
- **`apply_variable()` extension** (`scenario.py`): Added `properties.<name>` parameter path support for sweep variables.
- **`RatioStats.reactive_rate`** (`stats.py`): New field tracking the fraction of hits that triggered reactive armor.
- **`aggregate_cell()`** (`stats.py`): Counts `reactive_triggered` in metrics to compute `reactive_rate`.

**Testing** (8 new tests):
- Verify player attacker receives 1/8 retaliation damage with correct metrics (retaliation=20, reduction=8, damage=2)
- Verify NPC attacker receives full retaliation with correct metrics (reduction=1, damage=20)
- Verify no ReactiveArmor property → no reactive metrics recorded
- Verify ReactiveArmor property is consumed (erased) after triggering
- Verify `reactive_rate` computed correctly from metrics (50% = 2 of 4 hits)
- Verify `reactive_rate` is 0 when no reactive triggers
- Verify `CombatantSpec.properties` flows through to built mobile
- Verify default CombatantSpec has empty properties

**Key insight**: The reactive armor instrumentation captures the full pipeline: pre-reduction retaliation, reduction factor, and post-reduction damage. This lets reporting show both the theoretical damage and the actual damage dealt, with the reduction explicitly visible. No eScript or POL function signatures were modified — only `__RecordSimulatorMetric` calls were added.

---

## M18 — Spell Strike Enchantments

**Summary**: Implemented the spell strike hitscript system end-to-end. The `spellstrikescript.src` reads `ChanceOfEffect`, `HitWithSpell`, and `EffectCircle` properties from the weapon, rolls against chance, resolves the spell script via `GetScript(spellid)` (reads `:*:spells` config files), and dispatches the spell via `Start_Script()`. The spell scripts (fireball, lightning, harm, magic arrow, etc.) execute through the sub-script executor, calling `CalcSpellDamage` and `ApplyElementalDamage` to deal elemental spell damage on top of the physical hit.

**Changes**:
- **Interpreter: `_get_index` fallback** (`evaluator.py`): Added `__getitem__` fallback for objects like `RuntimeConfigFile` that support bracket indexing but aren't EArray/EDict. Logs warning on UNINIT fallback.
- **Interpreter: `_get_member` case sensitivity** (`evaluator.py`): Try original case before lowered case in `_get_member`. Fixes `RuntimeConfigElement` property access where case matters (e.g., `.Script` vs `.script`).
- **Interpreter: string slicing** (`evaluator.py`): `str[start, end]` now returns a 1-based substring (eScript convention) instead of being treated as chained indexing. Used by `RandomDiceStr()` in `random.inc`.
- **`Find()` stub** (`basic_stubs.py`): New POL built-in — 1-based substring search, returns 0 if not found. Used by `RandomDiceStr()` in `random.inc`.
- **`PlayLightningBoltEffect()` stub** (`basic_stubs.py`): Visual effect no-op for lightning spell.
- **`send_attack()` stub** (`basic_stubs.py`): Combat notification no-op used by spell scripts.
- **`spell_strike_rate`** (`stats.py`): Already present from test scaffolding — `RatioStats` field and `aggregate_cell()` counting.
- **`__RecordSimulatorMetric` instrumentation** (`spellstrikescript.src`): Records `spell_strike_triggered`, `spell_strike_spellid`, `spell_strike_circle`, `spell_strike_chance` via struct merge.
- **Unimplemented built-in logging** (`registry.py`): Promoted from `debug` to `warning` level for faster diagnosis of missing stubs.
- **Spell fixture sync** (`sync_fixtures.py`): Added spell script discovery — scans `:*:spells` config files, copies referenced `.src` spell scripts and `spells.cfg` to fixtures. 22 spell scripts added.

**Testing** (10 tests):
- Verify 100% chance triggers spell strike with correct metrics (spellid, circle, chance)
- Verify 0% chance does not trigger spell strike
- Verify spell strike deals additional damage (spell hit >= plain hit)
- Verify different spell types: Magic Arrow (id=5), Lightning (id=30, AIR), Harm (id=12, WATER)
- Verify cursed weapon reverses caster/target (spell damages attacker, attacker HP drops)
- Verify powerplayer gets 0.9 multiplier vs warrior 0.8
- Verify `spell_strike_rate` aggregation (50% = 2 of 4 hits)
- Verify `spell_strike_rate` is 0 when no triggers

---

## M19 — Effect Enchantments

**Summary**: Implemented all 7 effect-type weapon enchantments end-to-end. Each effect script replaces mainhit (per M18's hitscript dispatch). Balancing values flow through POL stubs (SetVital, SetMana, SetStamina, ApplyRawDamage) as side effects — `__RecordSimulatorMetric` records only categorical decisions (which effect fired, cursed status, target type). Added the POL vitals subsystem (GetVital/SetVital/GetVitalMaximumValue with hundredths↔display conversion) to support the shard's wrapper functions in attributes.inc.

**Changes**:
- **POL vitals stubs** (`object_stubs.py`): `GetVital`, `GetVitalMaximumValue`, `SetVital` — POL stores vitals in hundredths internally (e.g., `GetVital(mob, "life")` returns `mob.hp * 100`). The shard's eScript wrappers (`GetMana`, `SetMana`, etc. in `attributes.inc`) call these with divide/multiply by 100. `SetVital` records `hp_set`/`mana_changed`/`stamina_changed` side effects with delta values.
- **Additional stubs** (`object_stubs.py`): `SetHP` (sets hp with clamping + side effect), `GetMaxMana`, `GetMaxStamina`.
- **`MoveObjectToLocation`** (`basic_stubs.py`): No-op stub for banishscript's teleport.
- **Mobile model** (`mobile.py`): Added `x`, `y`, `z` (int), `realm` (str) for banishscript world access; `setlightlevel(level, duration)` no-op for blindingscript.
- **`start_script` error handling** (`structural_stubs.py`): Wrapped `run_sub_program` call in try/except — POL's `start_script` is async (fire-and-forget), so failures in spawned scripts log a warning but don't crash the calling hitscript. Fixes poison test where `processpoisonmod` (a long-running daemon) can't fully execute in the synchronous simulator.
- **Fixture sync** (`sync_fixtures.py`): Added `processpoisonmod.src` to extra runtime scripts list. Fixture count: 246 files, 962 KB.
- **Shard instrumentation** (7 scripts, all inside `if(DEBUG_MODE)` guards):
  - `piercingscript.src` — `effect_type=piercing`, `cursed`
  - `poisonhit.src` — `effect_type=poison`, `effect_poison_level`, `cursed`
  - `lifedrainscript.src` — `effect_type=lifedrain`, `cursed`
  - `manadrainscript.src` — `effect_type=manadrain`, `cursed`
  - `staminadrainscript.src` — `effect_type=staminadrain`, `cursed`
  - `blindingscript.src` — `effect_type=blinding`, `effect_triggered=1`, `cursed`
  - `banishscript.src` — `effect_type=banish`, `effect_target_type=(summoned|animated|normal)`, `cursed`

**Testing** (21 tests):
- Verify piercing executes, bypasses armor (piercing damage >= plain), cursed reversal
- Verify poison executes with poison level metric, cursed reversal
- Verify life drain heals attacker (hp_set side effect, 50% proc across seeds)
- Verify mana drain transfers mana (mana_changed side effects for both drain and gain)
- Verify stamina drain transfers stamina (stamina_changed side effects, 50% proc)
- Verify blinding triggers at 100% chance, doesn't trigger at 0%
- Verify banish: normal target gets regular damage, summoned target insta-killed (max_hp+3), cursed reversal
- Verify no double damage: each effect weapon produces exactly 1 damage_applied entry (hitscript replaces mainhit)

**Key insight**: Three independent interpreter bugs cascaded to produce a single error: (1) `_get_index` didn't handle `RuntimeConfigFile` objects, so `spellcfg[spellid]` returned UNINIT; (2) `_get_member` tried lowered case first, so `.Script` on `RuntimeConfigElement` returned None (wrong case); (3) `RandomDiceStr()` failed because `Find()` wasn't stubbed and eScript string slicing `str[start, end]` wasn't supported. Fixing all three made the full spell strike chain work.

---

## M20 — Greater Enchantments

**Summary**: Implemented all 3 greater-type weapon enchantments end-to-end. No new POL stubs were needed — all infrastructure from M12–M19 was sufficient. Added `Resisted()` and `ApplyPlanarDamage()` instrumentation to spelldata.inc for resistance and planar damage tracking across all spell paths (not just greater enchantments).

**Changes**:
- **`Resisted()` instrumentation** (`spelldata.inc`): Added `list:resisted` metric recording dmg_before, dmg_after, chance, did_resist, circle, evalint, resist. Captures the full resistance pipeline for any spell path that calls `Resisted()` (spell strikes, greater enchantments, elemental damage).
- **`ApplyPlanarDamage()` instrumentation** (`spelldata.inc`): Added `list:planar_applied` metric mirroring the existing `elemental_applied` pattern — records attack_type (plane), prot, dmg_gross, dmg_net (or healed for over-protection). Previously untracked.
- **`dualplanarscript.src` instrumentation**: Records effect_type=dualplanar, effect_triggered, cursed, spelldmg_before_resist, spelldmg (post-resist), class_nerf (0.7 for Mage/Paladin/Mystic Archer, 1.0 otherwise). Applies HOLY + NECRO planar damage via `ApplyPlanarDamage()`.
- **`voidscript.src` instrumentation**: Records effect_type=void, cursed, base_bonus (extracted to variable to avoid metric drift), rawdmg_before_curse, rawdmg, drain_type (hp/mana/stamina), drain_amount. The +15 base damage constant was extracted to a `base_bonus` variable used by both the calculation and the metric.
- **`trielementalscript.src` instrumentation**: Records effect_type=trielemental, effect_triggered, cursed, spelldmg_before_resist, spelldmg, class_nerf (0.7 for Mage/Mystic Archer only — no Paladin nerf unlike dualplanar). Applies FIRE + AIR + WATER elemental damage via `ApplyElementalDamage()`.

**Testing** (25 tests):
- Verify dualplanar triggers at 100% chance with correct metrics (effect_type, triggered, planar_applied)
- Verify dualplanar does not trigger at 0% chance (physical damage still dealt)
- Verify dualplanar deals additional damage over plain weapon
- Verify dualplanar records `list:planar_applied` with HOLY and NECRO entries
- Verify `list:resisted` entries recorded for planar damage resistance rolls
- Verify dualplanar cursed: records cursed flag (note: shard script uses targ as caster, not cast_on — damage still goes to defender)
- Verify dualplanar 0.7 class nerf for Mage and Paladin attackers
- Verify void executes with effect_type=void metric
- Verify void base_bonus is recorded (from variable, not hardcoded constant)
- Verify void deals more damage than plain weapon (+15 bonus)
- Verify void drain types: all 3 (hp, mana, stamina) proc across seeds
- Verify void drain_amount equals rawdamage/2
- Verify void cursed halves rawdamage (rawdmg == int(rawdmg_before_curse / 2))
- Verify void cursed reverses drainer/drained (attacker loses mana/stamina)
- Verify void hitscript replaces mainhit (no double damage)
- Verify trielemental triggers at 100% chance with metrics
- Verify trielemental does not trigger at 0% chance
- Verify trielemental deals additional damage over plain weapon
- Verify trielemental records `list:elemental_applied` with FIRE, AIR, WATER entries
- Verify trielemental `list:resisted` entries recorded
- Verify trielemental cursed targets attacker (ApplyElementalDamage uses targ as cast_on)
- Verify trielemental 0.7 class nerf for Mage attacker
- Verify trielemental no Paladin nerf (unlike dualplanar — class_nerf=1.0)
- Verify trielemental protection reduces damage (FireProtection on defender)

**POL stub unit tests** (43 new tests in `test_object_stubs.py` and `test_structural_stubs.py`):
- `SetHP`: basic set, clamps to max_hp, clamps to 0, records hp_set side effect with delta, null mobile
- `SetMana`: records mana_changed side effect with delta (decrease and increase), null mobile
- `SetStamina`: records stamina_changed side effect with delta (decrease and increase)
- `GetMaxMana`/`GetMaxStamina`: return values, null mobile returns 0
- `GetVital`: hundredths conversion (life→hp*100, mana→mana*100, stamina→stamina*100), unknown vital returns 0, null mobile returns 0
- `GetVitalMaximumValue`: hundredths conversion for all 3 vitals, unknown/null returns 0
- `SetVital`: hundredths→display conversion (15000→150), clamps to max, clamps to 0, records correct side effect kind per vital (hp_set/mana_changed/stamina_changed), returns 1 on success, returns 0 for unknown vital or null mobile
- `HealDamage`: heals HP, caps at max_hp, records heal side effect, zero/negative amount no-ops, null mobile no-ops
- `ApplyRawDamage` (extended): negative damage ignored, null mobile ignored, side effect target serial matches mobile
- `MoveObjectToLocation`: no-op (coordinates unchanged after call)

**Key insight**: Dualplanar and trielemental have asymmetric cursed behavior due to different argument ordering. Dualplanar passes `targ` as the 1st arg (caster) to `ApplyPlanarDamage(targ, defender, ...)`, so damage always goes to defender. Trielemental passes `targ` as the 2nd arg (cast_on) to `ApplyElementalDamage(attacker, targ, ...)`, so cursed correctly redirects damage to attacker. Class nerfs also differ: dualplanar nerfs Mage/Paladin/Mystic Archer; trielemental nerfs only Mage/Mystic Archer.

---

## M21 — Enchantment Reporting & WeaponSpec Integration

**Summary**: Added `EnchantmentRegistry` to parse hitscriptdesc.cfg, `Enchantment` IntEnum (45 members) and `Spell` IntEnum (132 members) for type-safe weapon configuration, and `WeaponSpec.enchant_with()` for declarative enchantment application. Updated the reporting layer with enchantment-specific stats and plots.

### New files
- `src/omega/config/enchantments.py` — `Enchantment` IntEnum, `EnchantmentEntry` dataclass, `EnchantmentRegistry`, `enchantment_hitscript()` / `enchantment_properties()` helpers, `_ENCHANTMENT_META` baked lookup table
- `src/omega/config/spells.py` — `Spell` IntEnum with all 132 spell IDs (standard 1-64, necro 65-80, earth 81-96, holy 166-181, songs 182-197)
- `tests/test_config/test_enchantments.py` — 43 tests for registry, enums, and meta lookup

### Changes

**Enchantment system** (`enchantments.py`):
- `Enchantment` IntEnum — 45 members matching hitscriptdesc.cfg (18 spell, 17 slayer, 7 effect, 3 greater). Names from display names (e.g. `OF_DAEMONS_BREATH`, `SILVER`, `OF_PLANAR_FURY`).
- `_ENCHANTMENT_META` dict — maps each enchantment ID to its hitscript path and weapon CProps. Spell enchantments reference `Spell` enum for `HitWithSpell` values. Slayers use `SlayType` (the actual CProp name, not `SlayerType`). Spell enchantments only set `HitWithSpell` — `EffectCircle` and `ChanceOfEffect` are per-weapon customisations, not part of the enchantment definition.
- `EnchantmentEntry.weapon_properties` — fixed: spell type returns only `HitWithSpell`, slayer type uses `SlayType`

**Simulation API** (`scenario.py`):
- `WeaponSpec.enchant_with(Enchantment)` — returns a new WeaponSpec with hitscript and properties from the enchantment. Existing properties override enchantment defaults.
- `WeaponSpec.hitscript: str | None` — also accepts package paths (`:combat:spellstrikescript`) or enchantment names via `build_weapon()` registry resolution
- `build_weapon()` — resolves enchantment names via `EnchantmentRegistry`, sets weapon properties
- `build_combatant()` — passes registry through to `build_weapon()`

**Runner** (`runner.py`):
- `run_scenario()` / `run_sweep()` accept `enchantment_registry` parameter
- Auto-loads registry from shard's `hitscriptdesc.cfg` when shard is provided

**Stats** (`stats.py`):
- `RatioStats.effect_rate` — tracks enchantment effect trigger rate
- `aggregate_cell()` — counts `effect_triggered` metric for effect_rate
- `aggregate_cell()` — aggregates `planar_applied` metrics (from greater enchantments) alongside `elemental_applied` into unified `ElementalBreakdown`

**Reporting** (`tables.py`):
- `_get_stat()` exposes `spell_strike_rate`, `reactive_rate`, `effect_rate` columns

**Plots** (`plots.py`):
- `damage_breakdown()` — new `show_elemental` parameter adds 4th bar for total elemental/planar damage
- `enchantment_comparison()` — new plot showing physical vs elemental/enchantment damage with total line overlay

### Tests added: 78 new tests (964 total)

**Enum and meta tests** (25):
- `Enchantment` IntEnum: all 45 members, values match IDs, `Enchantment(6)` resolves to `OF_DAEMONS_BREATH`
- `Spell` IntEnum: standard/necro/earth/holy/song spells, `Spell(169)` resolves to `ANGELIC_AURA`
- `enchantment_hitscript()` / `enchantment_properties()`: spell → spellstrikescript + HitWithSpell only, slayer → slayerscript + SlayType, effect → piercingscript, greater → ChanceOfEffect, void → empty

**Registry tests** (24):
- Parsing: total entries (45), type counts (18 spell, 17 slayer, 7 effect, 3 greater)
- Lookup by ID, spell name, display name, clean name, slayer type, string ID
- Case-insensitive matching, missing entries return None
- Weapon properties: spell (HitWithSpell only, no EffectCircle), slayer (SlayType), effect/greater (CProp/Multiplier)
- Empty registry behavior, clean_name stripping

**Scenario tests** (16):
- WeaponSpec.hitscript default None, raw package path, enchantment name resolution (Fireball, Piercing, Planar Fury)
- `enchant_with()`: spell/slayer/effect/greater, preserves existing fields, existing properties override defaults, build_weapon integration
- Unknown name raises ValueError, build_combatant passes registry

**Stats tests** (7):
- effect_rate: all triggered, none, partial
- planar_applied: creates holy/necro elements, combined with elemental_applied, healed path

**Reporting tests** (12):
- summary_table: spell_strike_rate, reactive_rate, effect_rate columns, all combined
- damage_breakdown: elemental bar when data present, no bar without data, show_elemental=False
- enchantment_comparison: basic rendering, custom title, single/three scenarios

### Test criteria
- `WeaponSpec(damage="3d6+2").enchant_with(Enchantment.OF_DAEMONS_BREATH)` → hitscript=`:combat:spellstrikescript`, HitWithSpell=Spell.FIREBALL
- `WeaponSpec().enchant_with(Enchantment.SILVER)` → hitscript=`:combat:slayerscript`, SlayType=`Undead`
- Existing properties override enchantment defaults (e.g. custom EffectCircle/ChanceOfEffect preserved)
- Direct property approach also works: `WeaponSpec(hitscript=":combat:spellstrikescript", properties={"HitWithSpell": Spell.ANGELIC_AURA, "EffectCircle": 9})`
- Planar damage (holy/necro from greater enchantments) appears in elemental breakdown
- All enchantment rate columns accessible in summary_table
- All existing tests continue to pass
