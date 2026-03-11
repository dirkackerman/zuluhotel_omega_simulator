# Path to V1.5 — Elemental & Enchanted Weapons

## Goal

Extend the simulator to handle elemental weapon damage (inline calculations in hitscriptinc.inc) and weapon enchantment sub-scripts (hitscript/controlscript system via `start_script()`). This includes reactive armor.

## Dependency on V1

V1.5 builds on the complete V1 foundation: eScript interpreter, POL stubs, simulation runner, reporting, and submodule-independent test fixtures.

## Phase 1: Elemental Damage (inline path, no start_script)

Elemental damage flows inline through `RecalcPhysicalDmg()` in hitscriptinc.inc. The shard code parses weapon `ElementalDamage` properties, splits damage by element type, and applies each portion through `ApplyElementalDamageNoResist()`. No sub-script execution is needed — only POL stubs are missing.

### M12 — Elemental Protection Stubs

**Goal**: Implement the protection/resistance lookup functions so elemental damage reduction can be calculated.

**Deliverables**:
- [x] `GetProtLevel(target, element)` — maps element bitflags to target properties (`FireProtection`, `AirProtection`, etc.) and returns protection percentage (0–100+)
- [x] `GetResultingElementalProt(target, element)` — wrapper that returns effective protection (currently delegates to `GetProtLevel`; future: complementary element cancellation)
- [x] `IsImmunedFromThisDamageType(target, element)` — immunity check from damages.inc
- [x] Unit tests for each protection level (0%, 50%, 100%, >100% healing case)
- [x] Test the "over-protection heals" mechanic (protection > 100%)

**Key files**: `damages.inc`, `spelldata.inc`, `structural_stubs.py`

**Acceptance**: Protection stubs return correct values for all 11 element types. Over-protection healing path is verified.

### M13 — Elemental Damage Application

**Goal**: Implement `ApplyElementalDamageNoResist()` and update `ApplyTheDamage()` to track damage type.

**Deliverables**:
- [x] Elemental damage flows end-to-end: `RecalcPhysicalDmg` → element loop → `ApplyElementalDamageNoResist` → `ApplyTheDamage`
- [x] `__RecordSimulatorMetric` calls added to shard scripts using the `list:` protocol:
  - `list:elemental` — per-element base damage, percentage, element ID (hitscriptinc.inc)
  - `list:elemental_applied` — per-element net damage after protection or healed amount (spelldata.inc)
  - `list:damage_applied` — per-ApplyTheDamage call: attack type + amount (damages.inc)
- [x] `_record_metric` override in `hit.py` updated to detect `list:` prefix and accumulate structs into named lists in `ctx.metrics`
- [x] Integration tests: elemental weapon split, protection reduction, pure physical regression, over-protection healing, `list:` protocol verification

**Key files**: `structural_stubs.py`, `context.py`, `hitscriptinc.inc`

**Depends on**: M12

**Acceptance**: A weapon with mixed elemental damage deals the correct proportional damage, reduced by target protection. Pure physical weapons are unaffected. All elemental pipeline values are recorded via `__RecordSimulatorMetric` and accessible in `HitResult.metrics`.

### M14 — Elemental Damage Reporting

**Goal**: Surface per-element damage breakdown in results and reporting.

**Deliverables**:
- [x] `HitResult.metrics` — propagates all `ctx.metrics` (including `elemental_applied`) to the result layer
- [x] `ElementDamage` dataclass — per-element struct with `gross`, `net`, `prot`, `healed`, `absorbed` fields
- [x] `ElementalBreakdown` dataclass — holds `dict[str, ElementDamage]` with `total_net`, `total_gross`, `net_dict()`, `gross_dict()`, `prot_dict()` accessors
- [x] `elemental_breakdown` field on `CellResult`
- [x] `aggregate_cell()` computes mean gross/net/prot/healed per element from `HitResult.metrics`
- [x] `elemental_breakdown_chart()` — horizontal stacked bar showing net damage by element
- [x] `elemental_vs_parameter()` — stacked bar chart of element breakdown across a sweep
- [x] Element stat columns in `summary_table()` — `elem_<name>`, `elem_<name>_net`, `elem_<name>_gross`, `elem_<name>_prot`, `elem_<name>_absorbed`, `elem_total_net`, `elem_total_gross`
- [x] `dmg_gross` added to `elemental_applied` metric (spelldata.inc) — captures pre-protection damage

**Depends on**: M13

**Acceptance**: Notebooks can visualize which portion of total damage comes from each element, including gross vs net and protection percentage. Sweep tables include elemental columns when requested.

## Phase 2: Sub-Script Execution (start_script infrastructure)

Weapon enchantments and reactive armor are launched via `start_script()`. This requires the interpreter to execute separate program blocks as sub-scripts with argument passing and isolated scope.

### M15 — Sub-Script Executor

**Goal**: Extend the `Executor` to find and run sub-scripts by path.

**Deliverables**:
- [x] Parse enchantment/reactive armor `.src` files and add their program blocks to the executor's program registry
- [x] Implement `run_sub_program(script_path, args)` on `Executor` — binds arguments, executes program block, returns result
- [x] Isolated scope for sub-scripts (push/pop on `ScopeStack`, don't pollute main script globals)
- [x] Script path resolution: map `:combat:scriptname` to the parsed program block
- [x] Update `start_script()` stub to dispatch to `run_sub_program()` instead of returning None
- [x] Unit tests: sub-script runs, receives arguments, returns value
- [x] Unit tests: sub-script scope is isolated (doesn't leak variables)
- [x] Unit tests: sub-script can call the same user-defined functions as the main script

**Key files**: `executor.py`, `structural_stubs.py`, `context.py`, `hit.py`, `runner.py`

**Acceptance**: `start_script(":combat:somescript", {arg1, arg2})` parses and executes the referenced program with correct argument binding.

### M16 — Fixture Sync for Enchantment Scripts

**Goal**: Add enchantment sub-scripts to the test fixture set.

**Deliverables**:
- [x] Identify all `.src` files referenced by hitscriptdesc.cfg entries (12 unique scripts across 4 categories)
- [x] Determine which scripts are reachable from the combat path and required for testing (all 12 + reactivearmoronhit = 13)
- [x] Update `scripts/sync_fixtures.py` to discover and copy enchantment scripts and their includes
- [x] Re-run sync: `python scripts/sync_fixtures.py` (222 files, 891 KB)
- [x] Verify fixture completeness: all referenced enchantment scripts are present
- [x] Update CLAUDE.md fixture count (209 → 222)

**Key files**: `scripts/sync_fixtures.py`, `tests/fixtures/shard/`

**Depends on**: M15

**Acceptance**: All enchantment scripts referenced by hitscriptdesc.cfg are in the fixture set. `sync_fixtures.py` discovers them automatically.

### M17 — Reactive Armor

**Goal**: Implement the reactive armor on-hit script.

**Deliverables**:
- [x] Stub `Print()` as a debug-mode logger (like `SendSysMessage`/`PrintTextAbovePrivate`) — needed by enchantment scripts
- [x] Parse and include `:combat:reactivearmoronhit.src` in the combat script set
- [x] Verify the reactive armor script executes through the sub-script executor
- [x] Handle the reactive armor flow: read `ReactiveArmor` property from defender → calculate return damage → apply to attacker
- [x] Record reactive damage metrics via `__RecordSimulatorMetric`: retaliation, reduction, damage, additional_damage
- [x] Add `CombatantSpec.properties` for setting mobile-level properties (e.g., ReactiveArmor)
- [x] Add `reactive_rate` to `RatioStats`
- [x] Integration test: defender with ReactiveArmor property reflects damage to attacker (player + NPC paths)
- [x] Integration test: defender without ReactiveArmor property — no reactive metrics
- [x] Integration test: ReactiveArmor consumed after trigger
- [x] Integration test: reactive_rate aggregation

**Depends on**: M15, M16

**Acceptance**: Reactive armor returns damage to attacker. The reflected amount is tracked in results and metrics.

### M18 — Spell Strike Enchantments

**Goal**: Implement the spell strike hitscript system (18 spell enchantments).

**Deliverables**:
- [x] Parse and execute `:combat:spellstrikescript.src`
- [x] Implement spell effect application stubs as needed (damage-only for V1.5 — skip visual/sound effects)
- [x] Handle `ChanceOfEffect` modifier from hitscriptdesc.cfg (probabilistic trigger)
- [x] Handle `AsCircleMod` (spell power scaling — all 18 entries have AsCircleMod 0; EffectCircle on weapon controls circle)
- [x] Record spell strike metrics via `__RecordSimulatorMetric`: `spell_strike_triggered`, `spell_strike_spellid`, `spell_strike_circle`, `spell_strike_chance`
- [x] Add `spell_strike_rate` to `RatioStats`
- [x] Integration test: weapon with spell strike enchantment triggers at expected rate
- [x] Integration test: spell strike damage is tracked (spell strike hit >= plain hit)
- [x] Integration test: spell strike metrics recorded in `ctx.metrics`
- [x] Integration test: cursed weapon reverses caster/target (spell damages attacker)
- [x] Integration test: powerplayer 0.9 multiplier vs warrior 0.8
- [x] Integration test: multiple spell types (fireball, magic arrow, lightning, harm)

**Depends on**: M15, M16, M12 (elemental stubs needed for spell damage)

**Acceptance**: Weapons with spell strike enchantments trigger spells at the configured chance, dealing additional spell damage. Pipeline values are captured in metrics.

### M19 — Effect Enchantments

**Goal**: Implement the 7 effect-type enchantments (piercing, poison, lifedrain, manadrain, staminadrain, blinding, banishing).

**Deliverables**:
- [x] Parse and execute each effect script:
  - `:combat:piercingscript` — armor penetration
  - `:combat:poisonhit` — applies poison
  - `:combat:lifedrainscript` — lifesteal (attacker heals)
  - `:combat:manadrainscript` — mana drain
  - `:combat:staminadrainscript` — stamina drain
  - `:combat:blindingscript` — blinding effect
  - `:combat:banishscript` — banish effect
- [x] Record each effect type via `__RecordSimulatorMetric` (categorical info only: effect_type, cursed, target_type, triggered)
- [x] Track balancing values through POL stubs (hp_set, mana_changed, stamina_changed, damage_applied) — not duplicated in metrics
- [x] New POL stubs: GetVital, GetVitalMaximumValue, SetVital (hundredths conversion), SetHP, GetMaxMana, GetMaxStamina, MoveObjectToLocation
- [x] Extended SetMana/SetStamina stubs with side effect recording (delta tracking)
- [x] Mobile model: setlightlevel(), x/y/z/realm attributes
- [x] Graceful start_script error handling (fire-and-forget — POL async semantics)
- [x] Fixture sync: added processpoisonmod.src to extra runtime scripts
- [x] Integration tests: 21 tests covering all 7 effects + dispatch verification
- [x] 818 tests passing, 0 skipped

**Depends on**: M15, M16

**Acceptance**: Each effect enchantment runs without errors and records its effect as a side effect. Effect values are captured in metrics.

### M20 — Greater Enchantments

**Goal**: Implement the 3 greater enchantment types.

**Deliverables**:
- [x] `:combat:dualplanarscript` — chance-based HOLY + NECRO planar damage via `ApplyPlanarDamage()`
- [x] `:combat:voidscript` — +15 base damage bonus, cursed halving, random drain (hp/mana/stamina)
- [x] `:combat:trielementalscript` — chance-based FIRE + AIR + WATER elemental damage via `ApplyElementalDamage()`
- [x] `__RecordSimulatorMetric` instrumentation:
  - `Resisted()` — `list:resisted` with dmg_before, dmg_after, chance, did_resist, circle, evalint, resist
  - `ApplyPlanarDamage()` — `list:planar_applied` with attack_type, prot, dmg_gross, dmg_net (mirrors `elemental_applied`)
  - `dualplanarscript` — effect_type, effect_triggered, cursed, spelldmg_base, spelldmg, class_nerf
  - `voidscript` — effect_type, cursed, base_bonus, rawdmg_before_curse, rawdmg, drain_type, drain_amount
  - `trielementalscript` — effect_type, effect_triggered, cursed, spelldmg_base, spelldmg, class_nerf
- [x] Integration tests: 25 tests covering all 3 greater enchantments
- [x] No new POL stubs needed — all infrastructure from M12–M19 was sufficient
- [x] 886 tests passing, 0 skipped
- [x] POL stub unit tests: 43 new unit tests for all POL stubs (GetVital, SetVital, GetVitalMaximumValue, SetHP, GetMaxMana, GetMaxStamina, SetMana, SetStamina, MoveObjectToLocation, HealDamage, ApplyRawDamage) validating current behaviour — return values, clamping, side effect recording, hundredths conversion, null handling. These lock in stub semantics so the future POL audit (M22) can detect regressions.

**Depends on**: M15, M16, M12, M13

**Acceptance**: Greater enchantments execute and deal damage through the correct elemental paths.

## Phase 3: Polish

### M21 — Enchantment Reporting & WeaponSpec Integration

**Goal**: Surface enchantment data in the simulation API and reporting layer.

**Deliverables**:
- [x] Add `hitscript` field to `WeaponSpec` for specifying enchantments declaratively
- [x] Add enchantment lookup from hitscriptdesc.cfg by name/ID — `EnchantmentRegistry` with `find()`, `by_id()`, `by_type()`
- [x] Update `build_weapon()` to configure hitscript properties on the weapon — resolves enchantment names via registry
- [x] Add enchantment effect columns to `summary_table()` — `spell_strike_rate`, `reactive_rate`, `effect_rate`
- [x] Add enchantment comparison plots — `enchantment_comparison()` with physical/elemental split + total line
- [x] Update `damage_breakdown()` to show elemental + enchantment components — optional 4th bar when elemental data present
- [x] Aggregate `planar_applied` metrics alongside `elemental_applied` into `ElementalBreakdown`
- [x] Auto-load `EnchantmentRegistry` from shard in `run_scenario()`/`run_sweep()`
- [x] `Enchantment` IntEnum (45 members) and `Spell` IntEnum (132 members) for type-safe weapon configuration
- [x] `WeaponSpec.enchant_with(Enchantment)` convenience method
- [x] Fixed `SlayType` (not `SlayerType`), spell enchantments only set `HitWithSpell` (not EffectCircle/ChanceOfEffect)
- [x] 964 tests passing, 0 skipped

**Depends on**: M14, M17–M20

**Acceptance**: Notebook authors can specify enchantments via `WeaponSpec(hitscript="Fireball")` and see enchantment effects in reports.

### M22 — Test Fixture Independence & Documentation

**Goal**: Ensure all new tests use fixtures (not live submodule), and update documentation.

**Deliverables**:
- [x] Run `python scripts/sync_fixtures.py` to capture any new shard files needed
- [x] Verify all 964 tests pass with fixture set
- [x] Update `notebooks/docs/combatant-specs.md` — document `ElementalDamage` weapon property, enchantment configuration, `enchant_with()`, Spell/Enchantment enums, `CombatantSpec.properties`
- [x] Update `notebooks/docs/concepts.md` — add elemental damage pipeline and enchantment system to damage flow diagram
- [x] Update `notebooks/docs/results.md` — document elemental breakdown fields, new side effect types, RatioStats fields, metrics dict
- [x] Update `notebooks/docs/reporting.md` — document new plot functions (elemental_breakdown_chart, elemental_vs_parameter, enchantment_comparison)
- [x] Update `notebooks/docs/constants-reference.md` — add Enchantment enum (45 members), Spell enum (132 members), elemental protection properties
- [x] Update `notebooks/docs/examples.md` — add recipes: "Elemental weapon comparison", "Enchantment effectiveness", "Reactive armor test"
- [x] Update `notebooks/docs/runtime.md` — document sub-script execution, new stubs, SimulationContext executor field
- [x] Update `notebooks/docs/messages-and-metrics.md` — document `list:` protocol, V1.5 metric keys
- [x] Update `notebooks/docs/README.md` — V1.5 features in "What can you do?"
- [x] Update `notebooks/docs/scenarios.md` — `properties.<name>` variable path, enchantment performance note
- [x] Update `CLAUDE.md` with V1.5 status → Complete
- [x] Update `changelog/changelog_to_v1.5.md` with M22 entry
- [x] **UNINIT silent-fallthrough audit**: Added `logger.warning` to 10 locations in evaluator.py (7) and structural_stubs.py (3) that silently returned UNINIT/None
- [x] Enrich notebooks 01–04 with V1.5 sections (enchantments, elemental sweeps, reactive armor)
- [x] Create `05_enchantments.ipynb` — comprehensive V1.5 enchantment showcase (7 sections)

**Depends on**: All prior milestones

**Acceptance**: All tests pass without submodule. Documentation covers elemental damage, enchantments, and new API surface. Notebooks demonstrate all V1.5 features with rich examples.

## Milestone Summary

| ID | Milestone | Phase | Depends on | Status |
|----|-----------|-------|------------|--------|
| M12 | Elemental Protection Stubs | 1 | — | **Done** |
| M13 | Elemental Damage Application | 1 | M12 | **Done** |
| M14 | Elemental Damage Reporting | 1 | M13 | **Done** |
| M15 | Sub-Script Executor | 2 | — | **Done** |
| M16 | Fixture Sync for Enchantment Scripts | 2 | M15 | **Done** |
| M17 | Reactive Armor | 2 | M15, M16 | **Done** |
| M18 | Spell Strike Enchantments | 2 | M15, M16, M12 | **Done** |
| M19 | Effect Enchantments | 2 | M15, M16 | **Done** |
| M20 | Greater Enchantments | 2 | M15, M16, M12, M13 | **Done** |
| M21 | Enchantment Reporting & WeaponSpec Integration | 3 | M14, M17–M20 | **Done** |
| M22 | Test Fixture Independence & Documentation | 3 | All | **Done** |

## Dependency Graph

```
Phase 1 (Elemental)        Phase 2 (Enchantments)         Phase 3 (Polish)

M12 Protection Stubs ──┐   M15 Sub-Script Executor ──┐
         │             │            │                 │
         ▼             │            ▼                 │
M13 Elemental Apply ───┤   M16 Fixture Sync ─────────┤
         │             │            │                 │
         ▼             │            ├─► M17 Reactive  │
M14 Elemental Report ──┤            │      Armor ─────┤
                       │            ├─► M18 Spell ────┤──► M21 Reporting
                       │            │      Strike     │        & API
                       └────────────┤                 │         │
                                    ├─► M19 Effect ───┤         ▼
                                    │      Enchants   │    M22 Fixtures
                                    │                 │        & Docs
                                    └─► M20 Greater ──┘
                                           Enchants
```

## Notes

- **Phase 1 can be implemented independently of Phase 2.** Elemental damage is inline in the combat scripts; no `start_script()` needed.
- **Phase 2 is the larger architectural change.** The sub-script executor is new infrastructure. Budget accordingly.
- **M15 is the critical path for Phase 2.** All enchantment milestones depend on it.
- **Slayer bonus is already working in V1.** The slayerscript in hitscriptdesc.cfg exists for the general enchantment framework, but the actual slayer multiplier is applied inline in `RecalcPhysicalDmg()`.
- **Astral damage path** (Spirit Speak → meditation resistance → astral armor → 50% reduction) is NOT in V1.5 scope. It's a separate combat path that would be V2.
