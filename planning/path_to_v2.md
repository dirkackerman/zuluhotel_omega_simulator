# Path to V2 — Spell & Resistance Flows

## Goal

Harden the simulator's POL built-in stubs against the actual POL C++ source code, validate the astral damage path, ensure all spell resistance and reactive armor interactions are thoroughly tested, and introduce **virtual time calculation** for DPS metrics. V1.5 delivered the features (elemental damage, enchantments, spell resistance, reactive armor); V2 ensures they're **correct** by auditing every stub against POL's C++ implementation, and adds the timing model needed for meaningful weapon/build comparison.

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

## Phase 2: Virtual Time & DPS

### M-V2.4 — Virtual Time Calculation & DPS Metrics

**Goal**: Implement POL-conformant swing delay calculation and integrate DPS metrics throughout the simulator, enabling damage-per-second analysis for weapon/build comparison and balance tuning.

**Background**: The simulator currently treats each hit as instantaneous. In real POL combat, the delay between swings is governed by `Character::schedule_attack()` in `charactr.cpp:2832–2881`. Without virtual time, DPS — the most important metric for balance tuning — cannot be computed.

#### POL Swing Timer — Authoritative Formula

Source: `submodules/polserver/pol-core/pol/mobile/charactr.cpp:2832–2881`
Clock unit: 1 POL clock = 10ms (`polclock.h:33`, `POLCLOCKS_PER_SEC = 100`)

**Definitive delay sources**:

| # | Source | Where | Notes |
|---|--------|-------|-------|
| 1 | **Weapon Speed** | `itemdesc.cfg` `Speed` field | Primary path for all ZH weapons (15–98 range) |
| 2 | **Attacker Dexterity** | `Mobile.dexterity` | Inverse relationship: higher DEX = faster swing |
| 3 | **Weapon Delay** | `itemdesc.cfg` `Delay` field | Alternative to Speed (explicit ms). Not used in ZH shard, but must implement for POL conformance |
| 4 | **delay_mod** | Character property | Added to weapon delay in delay-based path only |
| 5 | **SwingSpeedIncrease** | Equipment/enchantment property | Percentage modifier applied to final delay. Summed from all equipped items. Clamped >= -0.99 |
| 6 | **Minimum floor** | POL hardcoded | 20 clocks = 200ms minimum swing delay |

**Formula** (two mutually exclusive paths):

Path 1 — Speed-based (when `weapon.delay == 0` — all ZH weapons use this):
```
clocks = (100 * 15000) / ((DEX + 100) * SPEED)
       = 1_500_000 / ((DEX + 100) * SPEED)
```

Path 2 — Delay-based (when `weapon.delay > 0`):
```
delay_sum = max(0, weapon.delay + char.delay_mod)
clocks = (delay_sum * 100) / 1000
```

Both paths then apply SwingSpeedIncrease:
```
modifier = clamp(swing_speed_increase_sum / 100.0, min=-0.99)
clocks = round(clocks / (1 + modifier))
```

Convert: `delay_ms = clocks * 10`
Floor: minimum 200ms (20 clocks)

#### Deliverables

**1. Swing delay calculator** — `src/omega/combat/timing.py` (NEW):
- `calculate_swing_delay(attacker: Mobile, weapon: Weapon) -> float` — returns delay in milliseconds
- Implements both speed-based and delay-based paths matching POL C++
- Applies SwingSpeedIncrease with clamp and 200ms floor

**2. Model additions**:
- `Weapon` (`src/omega/model/items.py`): Add `delay: int = 0` field (ms, alternative to speed)
- `Mobile` (`src/omega/model/mobile.py`): Add `delay_mod: int = 0` field; add `swing_speed_increase` property (sum from property bag + equipped items)
- `WeaponSpec` (`src/omega/simulation/scenario.py`): Add `delay: int = 0` field
- `MobileSnapshot` (`src/omega/model/snapshot.py`): Snapshot/restore `delay_mod`

**3. Hit result enrichment** — `src/omega/combat/result.py`:
- Add `swing_delay_ms: float = 0.0` to `HitResult`

**4. Execute hit integration** — `src/omega/combat/hit.py`:
- Call `calculate_swing_delay(attacker, weapon)` and store on result before script execution

**5. DPS statistics** — `src/omega/simulation/stats.py`:
- New `TimingStats` dataclass: `swing_delay_ms`, `swings_per_second`, `dps_mean`, `dps_on_hit`, `effective_dps`
- Add `timing: TimingStats | None` to `CellResult`
- Compute in `aggregate_cell()`: DPS = mean_damage × (1000 / swing_delay_ms)

**6. Reporting additions**:
- `reporting/tables.py`: Add DPS columns (`swing_delay_ms`, `swings_per_sec`, `dps_mean`, `effective_dps`)
- `reporting/plots.py`: `dps_vs_parameter()` curve, `dps_comparison()` bar chart

**7. Notebook additions**:
- DPS section in `01_basic_damage.ipynb` — swing delay, swings/sec, DPS alongside raw damage
- DPS curves for parameter sweeps (DPS vs DEX, DPS vs weapon speed)

#### POL Conformance Test Vectors

| Scenario | Input | Expected |
|----------|-------|----------|
| Medium weapon, mid DEX | Speed 50, DEX 100 | `1_500_000 / (200×50) = 150 clocks = 1500ms` |
| Fast weapon, high DEX | Speed 98, DEX 130 | `1_500_000 / (230×98) ≈ 66.5 clocks ≈ 670ms` |
| Slow weapon, low DEX | Speed 15, DEX 10 | `1_500_000 / (110×15) ≈ 909 clocks ≈ 9090ms` |
| Delay-based path | Delay 2000, delay_mod -500 | `(1500×100)/1000 = 150 clocks = 1500ms` |
| SwingSpeedIncrease 25% | Speed 50, DEX 100, SSI 25 | `1500ms / 1.25 = 1200ms` |
| Floor enforcement | Speed 98, DEX 255, SSI 50 | Clamped to 200ms minimum |
| Negative SSI clamped | Speed 50, DEX 100, SSI -150 | Clamped to -0.99 → `1500 / 0.01 = 150000ms` |

#### Files to modify

| File | Change |
|------|--------|
| `src/omega/combat/timing.py` | **NEW** — `calculate_swing_delay()` |
| `src/omega/model/items.py` | Add `delay` field to `Weapon` |
| `src/omega/model/mobile.py` | Add `delay_mod`, `swing_speed_increase` property |
| `src/omega/model/snapshot.py` | Snapshot/restore `delay_mod` |
| `src/omega/combat/result.py` | Add `swing_delay_ms` to `HitResult` |
| `src/omega/combat/hit.py` | Call `calculate_swing_delay()`, set on result |
| `src/omega/simulation/scenario.py` | Add `delay` to `WeaponSpec` |
| `src/omega/simulation/stats.py` | Add `TimingStats`, compute DPS in `aggregate_cell()` |
| `src/omega/reporting/tables.py` | Add DPS columns |
| `src/omega/reporting/plots.py` | Add DPS chart functions |
| `src/omega/runtime/structural_stubs.py` | Add `swing_speed_increase` member access if needed |
| `tests/test_combat/test_timing.py` | **NEW** — POL-conformant swing delay tests |
| `tests/test_simulation/test_stats.py` | DPS calculation from known inputs |
| `tests/test_combat/test_hit.py` | Verify `swing_delay_ms` populated on HitResult |

**Acceptance**:
- `calculate_swing_delay()` produces values matching hand-computed POL formulas for all 7 test vectors above
- Both speed-based and delay-based paths implemented and tested
- SwingSpeedIncrease modifier works correctly with clamp at -0.99
- 200ms floor enforced
- `HitResult.swing_delay_ms` populated on every hit
- `CellResult.timing` contains DPS metrics
- DPS appears in summary tables and comparison tables
- At least one notebook demonstrates DPS output
- No regression in existing tests

---

## Phase 3: Coverage Gaps

### M-V2.5 — Astral Damage Path Validation

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

### M-V2.6 — Reactive Armor & Resistance Integration

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

## Phase 4: Polish

### M-V2.7 — Fixture Transition & Test Hardening

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

### M-V2.8 — Notebook Enrichment & Documentation Update

**Goal**: Enrich existing notebooks with V2 content (including DPS metrics from M-V2.4) and update documentation.

**Notebook updates**:
- **NB01 (basic_damage)**: Add DPS section — show swing delay, swings/sec, DPS alongside raw damage stats. Add an astral damage example alongside the physical example — show how the astral pipeline produces different damage distribution
- **NB02 (parameter_sweep)**: Add DPS curves — DPS vs DEX, DPS vs weapon speed sweeps
- **NB03 (class_comparison)**: Add a spell resistance section — compare how Mage/Warrior/Paladin defenders resist spell strike damage differently using class modifier impact. Add DPS comparison across classes
- **NB05 (enchantments)**: Add spell resistance analysis for spell strike enchantments — sweep defender Magic Resistance skill and show resist rate + damage reduction curves. Add reactive armor + enchantment combination examples

**Documentation updates**:
- Update `notebooks/docs/concepts.md` — add virtual time / swing delay section, add astral damage pipeline section, expand spell resistance mechanics with class modifier details
- Update `notebooks/docs/results.md` — document `TimingStats` and DPS metrics, document any new metrics from astral path instrumentation
- Update `notebooks/docs/runtime.md` — document stub audit findings, link to audit notes
- Update `notebooks/docs/constants-reference.md` — add timing constants (POLCLOCKS_PER_SEC, min floor), add astral-related constants if any new ones surfaced

**Acceptance**:
- Updated notebooks render correctly with new sections
- DPS metrics visible in at least 2 notebooks
- Documentation reflects all V2 changes including timing model
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
  ├──────────────────┬──────────────────┐
  ▼                  ▼                  ▼
M-V2.4 (Timing)   M-V2.5 (Astral)   M-V2.6 (Reactive + Resist)
  │                  │                  │
  └────────┬─────────┴──────────────────┘
           ▼
M-V2.7 (Fixture Transition)
           │
           ▼
M-V2.8 (Notebooks + Docs)
```

Phase 1 (M-V2.1 → M-V2.3) is sequential — each audit batch builds on the previous.
Phase 2 (M-V2.4) introduces virtual time and DPS, independent of coverage gaps.
Phase 3 (M-V2.5, M-V2.6) validates coverage gaps, can run in parallel with M-V2.4.
Phase 4 (M-V2.7, M-V2.8) is sequential after all Phase 2/3 milestones complete.

## Summary

| Milestone | Phase | Focus |
|-----------|-------|-------|
| M-V2.1 | Audit | Combat dispatch: execute_hit, ApplyRawDamage, start_script |
| M-V2.2 | Audit | Properties, stats, vitals, skills, equipment |
| M-V2.3 | Audit | Config files, RNG, type casts, math, string ops |
| M-V2.4 | Timing | Virtual time calculation & DPS metrics (POL swing timer) |
| M-V2.5 | Coverage | Astral damage path (zero tests → validated) |
| M-V2.6 | Coverage | Reactive armor + resistance interaction edge cases |
| M-V2.7 | Polish | Fixture transition, test hardening |
| M-V2.8 | Polish | Notebook enrichment, documentation update (incl. DPS) |
