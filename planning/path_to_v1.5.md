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
- [ ] `GetProtLevel(target, element)` — maps element bitflags to target properties (`FireProtection`, `AirProtection`, etc.) and returns protection percentage (0–100+)
- [ ] `GetResultingElementalProt(target, element)` — wrapper that returns effective protection (currently delegates to `GetProtLevel`; future: complementary element cancellation)
- [ ] `IsImmunedFromThisDamageType(target, element)` — immunity check from damages.inc
- [ ] Unit tests for each protection level (0%, 50%, 100%, >100% healing case)
- [ ] Test the "over-protection heals" mechanic (protection > 100%)

**Key files**: `damages.inc`, `spelldata.inc`, `structural_stubs.py`

**Acceptance**: Protection stubs return correct values for all 11 element types. Over-protection healing path is verified.

### M13 — Elemental Damage Application

**Goal**: Implement `ApplyElementalDamageNoResist()` and update `ApplyTheDamage()` to track damage type.

**Deliverables**:
- [ ] `ApplyElementalDamageNoResist(defender, attacker, dmg, element_ID)` stub — applies elemental damage after protection reduction
- [ ] Update `ApplyTheDamage()` stub to accept and record the `attack_type` (4th parameter) in `SimulationContext`
- [ ] Record per-element damage in `SimulationContext.metrics` (e.g., `fire_damage`, `air_damage`)
- [ ] Add `__RecordSimulatorMetric` calls to track elemental damage pipeline values:
  - `ElementalDamageBase` — total elemental damage before protection reduction
  - `ElementalDamageReduction` — amount reduced by elemental protection per element
  - `ElementalDamageNet` — net elemental damage after protection
  - Per-element base/net values (e.g., `FireDamageBase`, `FireDamageNet`, `AirDamageBase`, etc.)
  - `ElementalProtLevel` — protection level applied per element type
  - `PhysicalPortion` / `ElementalPortion` — the damage split ratio from weapon properties
- [ ] Integration test: weapon with `ElementalDamage` property (e.g., `"FIRE:50 PHYSICAL:50"`) produces correct split
- [ ] Integration test: elemental damage reduced by matching protection
- [ ] Integration test: pure physical weapon (no `ElementalDamage` prop) still works as before
- [ ] Integration test: `__RecordSimulatorMetric` captures elemental pipeline values in `ctx.metrics`

**Key files**: `structural_stubs.py`, `context.py`, `hitscriptinc.inc`

**Depends on**: M12

**Acceptance**: A weapon with mixed elemental damage deals the correct proportional damage, reduced by target protection. Pure physical weapons are unaffected. All elemental pipeline values are recorded via `__RecordSimulatorMetric` and accessible in `HitResult.metrics`.

### M14 — Elemental Damage Reporting

**Goal**: Surface per-element damage breakdown in results and reporting.

**Deliverables**:
- [ ] Add elemental damage fields to `HitResult` (or collect from metrics)
- [ ] Add `ElementalBreakdown` dataclass: per-element mean damage (fire, air, earth, water, necro, holy, poison, acid, physical, magic, astral)
- [ ] Add `elemental_breakdown` field to `CellResult`
- [ ] Aggregate per-element stats across iterations in `aggregate_cell()`
- [ ] Add `elemental_breakdown_chart()` plot function — stacked bar or pie showing damage by element
- [ ] Add element columns to `summary_table()` (opt-in via stats list)
- [ ] Test: sweep with mixed-element weapon shows correct per-element breakdown

**Depends on**: M13

**Acceptance**: Notebooks can visualize which portion of total damage comes from each element. Sweep tables include elemental columns when requested.

## Phase 2: Sub-Script Execution (start_script infrastructure)

Weapon enchantments and reactive armor are launched via `start_script()`. This requires the interpreter to execute separate program blocks as sub-scripts with argument passing and isolated scope.

### M15 — Sub-Script Executor

**Goal**: Extend the `Executor` to find and run sub-scripts by path.

**Deliverables**:
- [ ] Parse enchantment/reactive armor `.src` files and add their program blocks to the executor's program registry
- [ ] Implement `run_sub_program(script_path, args)` on `Executor` — binds arguments, executes program block, returns result
- [ ] Isolated scope for sub-scripts (push/pop on `ScopeStack`, don't pollute main script globals)
- [ ] Script path resolution: map `:combat:scriptname` to the parsed program block
- [ ] Update `start_script()` stub to dispatch to `run_sub_program()` instead of returning None
- [ ] Unit tests: sub-script runs, receives arguments, returns value
- [ ] Unit tests: sub-script scope is isolated (doesn't leak variables)
- [ ] Unit tests: sub-script can call the same user-defined functions as the main script

**Key files**: `executor.py`, `structural_stubs.py`, `parser.py`

**Acceptance**: `start_script(":combat:somescript", {arg1, arg2})` parses and executes the referenced program with correct argument binding.

### M16 — Fixture Sync for Enchantment Scripts

**Goal**: Add enchantment sub-scripts to the test fixture set.

**Deliverables**:
- [ ] Identify all `.src` files referenced by hitscriptdesc.cfg entries (up to 45 scripts across categories)
- [ ] Determine which scripts are reachable from the combat path and required for testing
- [ ] Update `scripts/sync_fixtures.py` to discover and copy enchantment scripts and their includes
- [ ] Re-run sync: `python scripts/sync_fixtures.py`
- [ ] Verify fixture completeness: all referenced enchantment scripts are present
- [ ] Update `FIXTURE_SHARD_ROOT` test count if fixture file count changes

**Key files**: `scripts/sync_fixtures.py`, `tests/fixtures/shard/`

**Depends on**: M15

**Acceptance**: All enchantment scripts referenced by hitscriptdesc.cfg are in the fixture set. `sync_fixtures.py` discovers them automatically.

### M17 — Reactive Armor

**Goal**: Implement the reactive armor on-hit script.

**Deliverables**:
- [ ] Parse and include `:combat:reactivearmoronhit.src` in the combat script set
- [ ] Verify the reactive armor script executes through the sub-script executor
- [ ] Handle the reactive armor flow: read `ReactiveArmor` property from defender → calculate return damage → apply to attacker
- [ ] Record reactive damage as a side effect (`"reactive_damage"` kind)
- [ ] Add `__RecordSimulatorMetric` calls: `ReactiveArmorDamage` (damage reflected), `ReactiveArmorLevel` (property value)
- [ ] Add `reactive_rate` to `RatioStats`
- [ ] Integration test: defender with ReactiveArmor property reflects damage to attacker
- [ ] Integration test: defender without ReactiveArmor property — no change from V1

**Depends on**: M15, M16

**Acceptance**: Reactive armor returns damage to attacker. The reflected amount is tracked in results and metrics.

### M18 — Spell Strike Enchantments

**Goal**: Implement the spell strike hitscript system (18 spell enchantments).

**Deliverables**:
- [ ] Parse and execute `:combat:spellstrikescript.src`
- [ ] Implement spell effect application stubs as needed (damage-only for V1.5 — skip visual/sound effects)
- [ ] Handle `ChanceOfEffect` modifier from hitscriptdesc.cfg (probabilistic trigger)
- [ ] Handle `AsCircleMod` (spell power scaling)
- [ ] Record spell strikes as side effects (`"spell_strike"` kind with spell name)
- [ ] Add `__RecordSimulatorMetric` calls: `SpellStrikeDamage` (damage dealt), `SpellStrikeSpell` (spell name), `SpellStrikeChance` (configured chance), `SpellStrikeCircle` (effective circle from AsCircleMod)
- [ ] Add `spell_strike_rate` to `RatioStats`
- [ ] Integration test: weapon with spell strike enchantment triggers at expected rate
- [ ] Integration test: spell strike damage is tracked separately
- [ ] Integration test: spell strike metrics recorded in `ctx.metrics`

**Depends on**: M15, M16, M12 (elemental stubs needed for spell damage)

**Acceptance**: Weapons with spell strike enchantments trigger spells at the configured chance, dealing additional spell damage. Pipeline values are captured in metrics.

### M19 — Effect Enchantments

**Goal**: Implement the 7 effect-type enchantments (piercing, poison, lifedrain, manadrain, staminadrain, blinding, banishing).

**Deliverables**:
- [ ] Parse and execute each effect script:
  - `:combat:piercingscript` — armor penetration
  - `:combat:poisonhit` — applies poison
  - `:combat:lifedrainscript` — lifesteal (attacker heals)
  - `:combat:manadrainscript` — mana drain
  - `:combat:staminadrainscript` — stamina drain
  - `:combat:blindingscript` — blinding effect
  - `:combat:banishscript` — banish effect
- [ ] Record each effect type as a side effect
- [ ] Add `__RecordSimulatorMetric` calls per effect: `LifeDrainAmount`, `ManaDrainAmount`, `StaminaDrainAmount`, `PiercingArmorReduction`, `PoisonLevel`, `BlindDuration`, `BanishDuration`
- [ ] Integration test per effect type
- [ ] Integration test: effect metrics recorded in `ctx.metrics`
- [ ] Stub any additional POL functions needed by the effect scripts

**Depends on**: M15, M16

**Acceptance**: Each effect enchantment runs without errors and records its effect as a side effect. Effect values are captured in metrics.

### M20 — Greater Enchantments

**Goal**: Implement the 3 greater enchantment types.

**Deliverables**:
- [ ] `:combat:dualplanarscript` — splits damage between physical and astral paths
- [ ] `:combat:voidscript` — void damage
- [ ] `:combat:trielementalscript` — combines 3 elemental damage types
- [ ] Add `__RecordSimulatorMetric` calls: `DualPlanarPhysical`/`DualPlanarAstral` (split amounts), `VoidDamage`, `TriElementalFire`/`TriElementalAir`/`TriElementalEarth` (per-element amounts)
- [ ] Integration tests for each
- [ ] Integration test: greater enchantment metrics recorded in `ctx.metrics`
- [ ] These scripts likely depend on elemental damage stubs (M12–M13) and potentially astral damage path

**Depends on**: M15, M16, M12, M13

**Acceptance**: Greater enchantments execute and deal damage through the correct elemental paths.

## Phase 3: Polish

### M21 — Enchantment Reporting & WeaponSpec Integration

**Goal**: Surface enchantment data in the simulation API and reporting layer.

**Deliverables**:
- [ ] Add `hitscript` field to `WeaponSpec` for specifying enchantments declaratively
- [ ] Add enchantment lookup from hitscriptdesc.cfg by name/ID
- [ ] Update `build_weapon()` to configure hitscript properties on the weapon
- [ ] Add enchantment effect columns to `summary_table()` (spell strike rate, lifesteal amount, etc.)
- [ ] Add enchantment comparison plots (e.g., "Normal vs Piercing vs Spell Strike" overlay)
- [ ] Update `damage_breakdown()` to show elemental + enchantment components

**Depends on**: M14, M17–M20

**Acceptance**: Notebook authors can specify enchantments via `WeaponSpec(hitscript="spellstrike:fireball")` and see enchantment effects in reports.

### M22 — Test Fixture Independence & Documentation

**Goal**: Ensure all new tests use fixtures (not live submodule), and update documentation.

**Deliverables**:
- [ ] Run `python scripts/sync_fixtures.py` to capture any new shard files needed
- [ ] Verify all tests pass with submodule working directory deleted
- [ ] Update `notebooks/docs/combatant-specs.md` — document `ElementalDamage` weapon property, enchantment configuration
- [ ] Update `notebooks/docs/concepts.md` — add elemental damage pipeline and enchantment system to damage flow diagram
- [ ] Update `notebooks/docs/results.md` — document elemental breakdown fields, new side effect types
- [ ] Update `notebooks/docs/reporting.md` — document new plot functions
- [ ] Update `notebooks/docs/constants-reference.md` — add elemental protection property names
- [ ] Update `notebooks/docs/examples.md` — add recipes: "Elemental weapon comparison", "Enchantment effectiveness", "Reactive armor test"
- [ ] Update `notebooks/docs/runtime.md` — document sub-script execution, new stubs
- [ ] Update `CLAUDE.md` with V1.5 status
- [ ] Update `changelog/changelog_to_v1.5.md` with final summary

**Depends on**: All prior milestones

**Acceptance**: All tests pass without submodule. Documentation covers elemental damage, enchantments, and new API surface.

## Milestone Summary

| ID | Milestone | Phase | Depends on | Status |
|----|-----------|-------|------------|--------|
| M12 | Elemental Protection Stubs | 1 | — | Not started |
| M13 | Elemental Damage Application | 1 | M12 | Not started |
| M14 | Elemental Damage Reporting | 1 | M13 | Not started |
| M15 | Sub-Script Executor | 2 | — | Not started |
| M16 | Fixture Sync for Enchantment Scripts | 2 | M15 | Not started |
| M17 | Reactive Armor | 2 | M15, M16 | Not started |
| M18 | Spell Strike Enchantments | 2 | M15, M16, M12 | Not started |
| M19 | Effect Enchantments | 2 | M15, M16 | Not started |
| M20 | Greater Enchantments | 2 | M15, M16, M12, M13 | Not started |
| M21 | Enchantment Reporting & WeaponSpec Integration | 3 | M14, M17–M20 | Not started |
| M22 | Test Fixture Independence & Documentation | 3 | All | Not started |

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
