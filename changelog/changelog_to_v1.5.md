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
