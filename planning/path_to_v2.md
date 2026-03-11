# Path to V2 — Spell & Resistance Flows

## Goal

Harden the simulator's POL built-in stubs against the actual POL C++ source code, validate the astral damage path, and ensure all spell resistance and reactive armor interactions are thoroughly tested. V1.5 delivered the features (elemental damage, enchantments, spell resistance, reactive armor); V2 ensures they're **correct** by auditing every stub against POL's C++ implementation.

## Dependency on V1.5

V1.5 delivered:
- Elemental damage pipeline with 11 element types
- Sub-script executor for weapon enchantments
- Spell strike (18 spells), effect (7 types), greater (3 types) enchantments
- Reactive armor with damage reflection
- `Resisted()` function with class modifiers and `list:resisted` metrics
- `ApplyElementalDamage()` with protection lookup and over-protection healing
- 208 POL built-in stubs across 3 modules (basic, object, structural)
- 1120 tests passing

V2 audits and validates all of the above against the POL C++ source.

## Phase 1: Stub Audit — Critical Path

The stubs on the combat critical path have the highest blast radius if wrong. Audit these first.

### M-V2.1 — Combat Dispatch Audit

**Goal**: Verify `execute_hit` flow, `ApplyRawDamage`, and `start_script` against POL's `charactr.cpp` attack dispatch.

**Audit targets** (read POL C++ → compare Python → fix → test):

| Stub | POL source | Priority | Notes |
|------|-----------|----------|-------|
| `execute_hit` flow | `charactr.cpp:3280` (`attack()`) | Critical | V1.5 had M18 double-damage bug from misunderstanding `run_hit_script` vs `apply_damage` dispatch |
| `ApplyRawDamage` | `charactr.cpp` / `ufunc.cpp` | Critical | Core damage application — null checks, negative damage, HP floor |
| `start_script` / `Start_Script` | `osmod.cpp`, `scrstore.cpp` | Critical | Sub-script dispatch — argument passing, return values, scope isolation |
| `SetScriptController` | `osmod.cpp` | Low | Currently a no-op; verify that's correct for combat path |

**Deliverables**:
- Read POL C++ source for each stub, document exact semantics
- Compare against Python implementation, fix any divergences
- Write/update unit tests encoding POL behavior with comments citing C++ source lines
- Document findings in a `docs/stub_audit.md` or inline comments

**Acceptance**:
- `ApplyRawDamage` handles: 0 damage, negative damage, target already dead, HP floor at 0
- `start_script` argument passing matches POL (array indexing, scope isolation)
- No regression in existing 1120 tests

---

### M-V2.2 — Property & Stat Accessor Audit

**Goal**: Verify property bags and stat/vital/skill accessors match POL semantics exactly.

**Audit targets**:

| Stub | POL source | Priority | Notes |
|------|-----------|----------|-------|
| `GetObjProperty` / `SetObjProperty` / `EraseObjProperty` | `uomod.cpp` | High | Property bags — return types, missing property behavior, type coercion |
| `GetStrength` / `GetDexterity` / `GetIntelligence` | `vitals.em`, `charactr.cpp` | High | Base + mod, capping, hundredths vs display |
| `GetHP` / `SetHP` / `GetMaxHP` | `vitals.em` | High | HP semantics, death trigger, max clamp |
| `GetMana` / `SetMana` / `GetStamina` / `SetStamina` | `vitals.em` | High | Hundredths conversion, max clamp |
| `GetVital` / `SetVital` / `GetVitalMaximumValue` | `vitals.em` | Medium | Generic vital access — hundredths units |
| `GetEffectiveSkill` / `GetAttribute` / `GetBaseSkill` | `attributes.em` | High | Skill lookup, effective vs base, tenths/display conversion |
| `HealDamage` | `vitals.em` | Medium | Max HP clamp, return value |
| `GetEquipmentByLayer` / `ListEquippedItems` | `uomod.cpp` | Medium | Layer constants, empty slot return |

**Deliverables**:
- Read POL `.em` module definitions and C++ implementations
- Verify return types (int vs float, ERROR vs None), edge cases (missing skill → 0?), hundredths conversion
- Fix any divergences found
- Unit tests per stub citing POL behavior

**Acceptance**:
- Stat accessors match POL's hundredths-to-display conversion
- Missing properties return correct default (None? 0? ERROR?)
- All tests pass with no stat/property regressions

---

### M-V2.3 — Config, RNG & Utility Audit

**Goal**: Verify config file reading, RNG functions, type casts, and math functions.

**Audit targets**:

| Stub | POL source | Priority | Notes |
|------|-----------|----------|-------|
| `ReadConfigFile` | `cfgmod.cpp` | High | Wildcard `:*:` resolution, caching, elem access patterns |
| `FindConfigElem` / `GetConfigInt` / `GetConfigString` / `GetConfigStringKeys` | `cfgmod.cpp` | High | Missing elem → ERROR, type coercion |
| `Random` / `RandomInt` | `basicmod.cpp` | High | Range semantics (inclusive/exclusive), 0 arg, negative arg |
| `RandomDiceRoll` | `utilmod.cpp` | Medium | Dice notation parsing, edge cases |
| `CInt` / `CDbl` / `CStr` | `utilmod.cpp` | High | Type coercion rules — string→int, float→int truncation direction |
| `Pow` / `Abs` / `Min` / `Max` | `mathmod.cpp` | Medium | Return types (int vs float), edge cases |
| `TypeOf` | `basicmod.cpp` | Medium | Return string values for each type |
| `Find` / `Len` / `SubStr` / `SplitWords` | `basicmod.cpp` | Medium | 1-based indexing, empty string, out-of-bounds |
| `Distance` | `uomod.cpp` | Medium | 2D vs 3D, same-location → 0, Z-axis handling |
| `ReadGameClock` | `osmod.cpp` | Low | Return value semantics |

**Deliverables**:
- Read POL C++ implementations for each
- Verify edge cases: `CInt("abc")`, `Random(0)`, `Find("", "x")`, `Distance(same, same)`
- Fix divergences
- Unit tests covering edge cases

**Acceptance**:
- `CInt` truncation direction matches C/POL (toward zero)
- `Random(n)` range is `[0, n)` (verify inclusive/exclusive)
- `ReadConfigFile` wildcard resolution matches POL package search
- `Find` returns 1-based index, 0 for not found

---

## Phase 2: Coverage Gaps

### M-V2.4 — Astral Damage Path Validation

**Goal**: Test the astral damage path end-to-end through the interpreter.

The astral path (`RecalcAstralDmg` in hitscriptinc.inc) is functional in eScript but has zero tests. It follows a different pipeline than physical damage:

```
RecalcAstralDmg(attacker, defender, weapon, basedamage)
  │  Spirit Speak scaling
  │  Class bonuses (Mystic, Mage)
  │  Meditation resistance
  │  Astral armor reduction
  │  50% base reduction
  ▼
ApplyTheDamage(dmgtype: ASTRAL)
```

**Deliverables**:
- Create weapons with `Astral` property to trigger the astral path
- Test astral damage pipeline: base → spirit speak → class bonus → meditation resist → astral armor → 50% reduction
- `__RecordSimulatorMetric` instrumentation for astral-specific metrics (spirit speak scaling, meditation resist, astral armor absorbed)
- Property-based test assertions (astral damage < physical for same base, meditation reduces astral, etc.)
- Verify interaction with elemental damage (astral weapons can also have elemental properties)

**Acceptance**:
- Astral weapon deals non-zero damage through the interpreter
- Spirit Speak skill increases astral damage
- Meditation skill reduces astral damage taken
- Astral armor (defender property) absorbs astral damage
- 50% base reduction applied
- No regression in physical damage tests

---

### M-V2.5 — Reactive Armor & Resistance Integration

**Goal**: Test reactive armor interactions with spell resistance, enchantment damage, and elemental damage.

Reactive armor (M17) and spell resistance (M20) were implemented independently. This milestone tests their combined behavior and edge cases.

**Deliverables**:
- Test reactive armor with elemental weapons (reflects physical portion, not elemental?)
- Test reactive armor with spell strike weapons (reactive triggers on physical hit, spell damage separate)
- Test reactive armor with effect enchantments (drain + reactive)
- Test reactive armor damage reflection vs PvP scaling (does reflected damage get PvP-scaled?)
- Verify `Resisted()` metrics accuracy: confirm `resist_chance` matches hand-calculated values for known skill/class combinations
- Test class modifier stacking: Mage caster vs Mage defender resistance
- Edge case: reactive armor + over-protection healing (defender heals from elemental, reflects physical)

**Acceptance**:
- Reactive armor + spell strike: both fire independently, metrics captured for each
- Resistance class modifiers produce expected probability shifts
- At least 3 hand-calculated resistance scenarios validated
- Combined enchantment + reactive scenarios execute without error

---

## Phase 3: Polish

### M-V2.6 — Fixture Transition & Test Hardening

**Goal**: Ensure all V2 tests use fixture shard files, update `sync_fixtures.py` for any new shard resources, and harden test assertions.

**Deliverables**:
- Audit all V2 tests: none should reference `submodules/` directly
- Update `sync_fixtures.py` if any new shard scripts were needed (astral-specific includes, etc.)
- Run full fixture sync and verify clean
- Convert any exact-value assertions to property-based assertions where appropriate
- Verify full test suite passes with `pytest -n auto`

**Acceptance**:
- Zero references to `submodules/zuluhotel_omega_2.5` in test code
- `sync_fixtures.py --dry-run` shows no pending changes
- All tests pass in parallel mode

---

### M-V2.7 — Notebook Enrichment & Documentation Update

**Goal**: Enrich existing notebooks with V2 content and update documentation.

**Notebook updates**:
- **NB01 (basic_damage)**: Add an astral damage example alongside the physical example — show how the astral pipeline produces different damage distribution
- **NB03 (class_comparison)**: Add a spell resistance section — compare how Mage/Warrior/Paladin defenders resist spell strike damage differently using class modifier impact
- **NB05 (enchantments)**: Add spell resistance analysis for spell strike enchantments — sweep defender Magic Resistance skill and show resist rate + damage reduction curves. Add reactive armor + enchantment combination examples

**Documentation updates**:
- Update `notebooks/docs/concepts.md` — add astral damage pipeline section, expand spell resistance mechanics with class modifier details
- Update `notebooks/docs/results.md` — document any new metrics from astral path instrumentation
- Update `notebooks/docs/runtime.md` — document stub audit findings, link to audit notes
- Update `notebooks/docs/constants-reference.md` — add astral-related constants if any new ones surfaced

**Acceptance**:
- Updated notebooks render correctly with new sections
- Documentation reflects all V2 changes
- Astral damage pipeline documented alongside physical pipeline

---

## Milestone Dependencies

```
M-V2.1 (Combat Dispatch Audit)
  │
  ▼
M-V2.2 (Property & Stat Audit)
  │
  ▼
M-V2.3 (Config, RNG & Utility Audit)
  │
  ├──────────────────┐
  ▼                  ▼
M-V2.4 (Astral)    M-V2.5 (Reactive + Resist)
  │                  │
  └────────┬─────────┘
           ▼
M-V2.6 (Fixture Transition)
           │
           ▼
M-V2.7 (Notebooks + Docs)
```

Phase 1 (M-V2.1 → M-V2.3) is sequential — each audit batch builds on the previous.
Phase 2 (M-V2.4, M-V2.5) can run in parallel after Phase 1.
Phase 3 (M-V2.6, M-V2.7) is sequential after Phase 2.

## Summary

| Milestone | Phase | Focus |
|-----------|-------|-------|
| M-V2.1 | Audit | Combat dispatch: execute_hit, ApplyRawDamage, start_script |
| M-V2.2 | Audit | Properties, stats, vitals, skills, equipment |
| M-V2.3 | Audit | Config files, RNG, type casts, math, string ops |
| M-V2.4 | Coverage | Astral damage path (zero tests → validated) |
| M-V2.5 | Coverage | Reactive armor + resistance interaction edge cases |
| M-V2.6 | Polish | Fixture transition, test hardening |
| M-V2.7 | Polish | Notebook enrichment, documentation update |
