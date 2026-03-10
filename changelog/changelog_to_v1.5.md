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
