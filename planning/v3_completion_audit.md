# V3 Completion Audit — Requirements vs Specification vs Implementation

**Date**: 2025-03-13
**Scope**: Cross-reference CLAUDE.md requirements, planning/path_to_v3.md specifications, changelog/changelog_to_v3.md records, and actual implementation.
**Test suite**: 2196 tests, 0 skipped, 0 failures.

---

## 1. Discrepancies Between CLAUDE.md and Planning Specs

### 1.1 Spell Count: "31 damage-dealing spells"

**CLAUDE.md** (line in V3 scope): "31 damage-dealing spells across 4 schools"
**path_to_v3.md** (line 11): "31 damage-dealing spells across 4 schools"
**path_to_v3.md spell tables**: Only **30 spells listed** across the four tables:
- Standard: 11 (table header says 12, but only 11 rows)
- Necromancy: 8
- Earth: 5
- Holy: 5
- **Missing spell**: The Standard section header claims "(12)" but only lists 11 spells. No 12th Standard spell appears anywhere.

**path_to_v3.md M25**: Says "20 single-target" spells but lists only 19 names.
**path_to_v3.md M26**: Says "11 AoE" spells but lists only 10 names.

**Implementation** (`DAMAGE_SPELL_IDS` in `spell_registry.py`): **29 entries** (Standard 11, Necro 8, Earth 5, Holy 5).

**Verdict**: The "31" figure in both CLAUDE.md and path_to_v3.md is incorrect. The tables show 30 (with a phantom 12th Standard spell), and implementation has 29. The single-target and AoE sub-counts in M25/M26 also don't add up (20+11=31, but 19+10=29 actual).

**Recommended fix**: Update CLAUDE.md and path_to_v3.md to say "29 damage-dealing spells" (11 Standard + 8 Necro + 5 Earth + 5 Holy). Fix the Standard header from "(12)" to "(11)". Fix M25 from "20 single-target" to "19 single-target" and M26 from "11 AoE" to "10 AoE".

---

### 1.2 DAMAGE_SPELL_IDS Contains Reclassified Non-Damage Spells

During M25 and M26, six spells were reclassified:

| Spell | ID | Original Classification | Actual Behavior | Still in DAMAGE_SPELL_IDS? |
|---|---|---|---|---|
| Decaying Ray | 67 | Single-target damage | AR debuff (no damage calls) | **Yes** |
| Wraith's Breath | 72 | Single-target damage | AoE paralysis/CC (no damage calls) | **Yes** |
| Sacrifice | 71 | Single-target damage | AoE pet sacrifice mechanic | **Yes** |
| Gust of Air | 89 | AoE damage | Single-target (not AoE) | Yes (correct — still does damage) |
| Wrath of God | 174 | AoE damage | Single-target karma-based | Yes (correct — still does damage) |
| Astral Storm | 176 | AoE damage | CC + damage sub-script | Yes (debatable — damage is secondary) |

**Issue**: Decaying Ray, Wraith's Breath, and Sacrifice were explicitly documented as **not dealing damage** in the M25 changelog, yet remain in `DAMAGE_SPELL_IDS`. The M29 coverage audit (`TestSpellPerSpellCoverage`) asserts "every damage spell in DAMAGE_SPELL_IDS executes successfully and deals positive damage" — these three are likely filtered as zero-damage exceptions (`_ZERO_DAMAGE_SPELLS`).

**Recommended fix**: Remove Decaying Ray (67), Wraith's Breath (72), and Sacrifice (71) from `DAMAGE_SPELL_IDS`, or rename the set to `SPELL_IDS_WITH_SCRIPTS` to reflect its actual semantics.

---

### 1.3 V3 Status Label

**CLAUDE.md**: "V3 status: In progress — M23–M29 complete."

**Issue**: If M23–M29 are all complete and M29 is the final planned milestone, V3 should be marked as **complete**, not "in progress."

**Recommended fix**: Update to "V3 status: Complete (M23–M29). 2196 tests."

---

### 1.4 Missing `notebooks/docs/spells.md`

**path_to_v3.md M28 deliverables**: "New `spells.md` — spell catalog reference (all 31 damage spells with circle, element, type)"
**changelog M28**: Lists `notebooks/docs/spells.md` as a new file.
**Filesystem**: File does **not exist**.

**Verdict**: The M28 deliverable was documented in the changelog as done but the file was never created.

**Recommended fix**: Create `notebooks/docs/spells.md` with the 29-spell catalog, or remove it from the M28 deliverables list.

---

### 1.5 Hot Reload: "Watch eScript files for changes"

**CLAUDE.md** (Testing & Reporting section): "Hot reload: watch eScript files for changes, re-parse and re-run"

**Implementation** (`src/omega/reporting/reload.py`): `reload_omega()` — a manual function call that reloads Python `omega.*` modules via `importlib.reload()`. It does **not** watch eScript files or auto-detect changes.

**Verdict**: The CLAUDE.md description implies automatic file-watching behavior that doesn't exist. The actual feature is a manual Python module reload utility for Jupyter kernels.

**Recommended fix**: Reword to: "Hot reload: call `reload_omega()` in notebooks to pick up Python source changes without restarting the kernel." Note that eScript re-parsing requires re-running `shard.parse_combat_scripts()` / `shard.parse_spell_scripts()`.

---

### 1.6 Conditional Skips vs "All tests run unconditionally"

**CLAUDE.md** (Testing Strategy): "All tests run unconditionally — no markers, no skips, no submodule dependency."

**Reality**: 41 `pytest.skip()` calls across 10 test files. These are **conditional** skips that trigger only when script execution fails (e.g., a missing stub causes an eScript runtime error). Currently all 2196 tests pass with 0 skipped, so the statement is *technically* true at this moment, but the skip infrastructure means tests can silently disappear if a stub regresses.

**Verdict**: Minor inaccuracy. The intent ("no tests are permanently skipped") is met, but the mechanism differs from what the documentation implies.

**Recommended fix**: Reword to: "All tests currently pass — none are permanently skipped or marked xfail. Some integration tests use conditional `pytest.skip()` on script execution failure to allow gradual stub coverage expansion."

---

## 2. Specification vs Implementation Completeness

### 2.1 V3 Milestone Deliverables Checklist

| Milestone | Deliverable | Status | Notes |
|---|---|---|---|
| **M23** | Parse `spells.cfg` | Done | 128 spells across 5 schools |
| M23 | Parse `circles.cfg` | Done | 33 circles |
| M23 | `SpellConfig` / `SpellRegistry` | Done | Named `SpellRegistry` with `SpellEntry` |
| M23 | `sync_fixtures.py` updated | Done | 29 spell scripts synced |
| M23 | Unit tests | Done | 51 tests |
| **M24** | `SpellResult` dataclass | Done | |
| M24 | `execute_spell()` | Done | NPC and player modes |
| M24 | `CheckSkill` stub | Done | Simplified model |
| M24 | `ConsumeMana` stub | Done | Display-unit correct |
| M24 | `CanTargetSpell` stub | Done | |
| M24 | `RandomDiceRoll` stub | Done | Uses existing dice parser + sim RNG |
| M24 | `sleep` no-op | Done | Advances virtual time |
| M24 | `__RecordSimulatorMetric` in spelldata.inc | Done | 3 metric points |
| **M25** | All single-target spells execute | Done | 16 execute (3 reclassified as non-damage) |
| M25 | Per-spell unit tests | Done | 98 tests |
| M25 | Hand-calculated validation | Done | Fireball, Flame Strike, Kill |
| **M26** | All AoE spells execute | Done | 7 execute (3 reclassified) |
| M26 | `ListMobilesNearLocationEx` stub | Done | |
| M26 | `SmartAoE` stub | Done | Pass-through |
| M26 | Multi-target execution | Done | Per-target SpellResult |
| **M27** | `SpellScenario` dataclass | Done | Frozen dataclass |
| M27 | `run_spell_scenario()` | Done | N iterations with snapshot/restore |
| M27 | `run_spell_sweep()` | Done | Cartesian product sweeps |
| M27 | `fizzle_rate` / `resist_rate` / `resist_rate_on_cast` | Done | In `RatioStats` |
| M27 | `damage_stats_on_cast` | Done | In `CellResult` |
| **M28** | `spell_comparison()` plot | Done | Grouped bar chart |
| M28 | `fizzle_rate_vs_parameter()` plot | Done | Dual-line plot |
| M28 | Notebook 06 (spell damage) | Done | |
| M28 | Notebook 07 (spell comparison) | Done | |
| M28 | Notebook 08 (spell resistance) | Done | |
| M28 | V3 sections in notebooks 01–05 | Done | |
| M28 | Documentation updates | Done | concepts, results, scenarios, reporting, examples |
| M28 | **`spells.md` reference page** | **Missing** | File not created |
| **M29** | Coverage audit tests | Done | 178 tests across 20 classes |
| M29 | POL stub audit (spell path) | Done | 9 stub audit classes |
| M29 | ApplyRawDamage truncation fix | Done | `int(float(amount))` |

**Summary**: 34/35 deliverables complete. One file (`spells.md`) missing.

---

### 2.2 V1 and V1.5 Completeness (Spot Check)

| CLAUDE.md Requirement | Status |
|---|---|
| eScript parser from ANTLR4 | Done |
| POL config file parser | Done |
| Package path resolver | Done |
| Dice notation parser | Done |
| Interpreter | Done |
| Mock runtime with ~60 stubs | Done |
| Simulation runner | Done |
| Jupyter notebooks | Done (8 notebooks) |
| Deterministic RNG with seed | Done |
| State reset between iterations | Done (snapshot/restore) |
| V1.5: Elemental damage | Done |
| V1.5: Enchantment sub-scripts | Done (44 enchantments) |
| V1.5: Reactive armor | Done |

---

### 2.3 V2 Completeness (Spot Check)

| CLAUDE.md Requirement | Status |
|---|---|
| Virtual time / swing delay | Done (`timing.py`) |
| DPS metrics | Done (`TimingStats` in `CellResult`) |
| Spell resistance calculations | Done (`Resisted()` via interpreter) |
| Reactive armor + resistance integration | Done |
| POL stub conformance audit | Done (24 bugs fixed across V2 milestones) |
| Notebook enrichment | Done |

---

## 3. Invalid or Partial Assumptions

### 3.1 CheckSkill Simplified Model

**Assumption** (M24): `chance = clamp(skill - difficulty + 50, 0, 100)`
**POL reality**: CheckSkill uses a hook-driven system where the shard's `checkskill.src` hook script is called. The actual shard logic may include skill gain, partial success, and advanced probability models.

**Impact**: Fizzle rate predictions are approximate. The simplified model produces reasonable results for balance analysis but may diverge from live server behavior at extreme skill/difficulty combinations.

**Severity**: Low — documented as a known simplification in M24 changelog.

---

### 3.2 AoE Target Filtering (SmartAoE)

**Assumption**: `SmartAoE` is a pass-through (no faction/ally filtering).
**Reality**: In the live shard, `SmartAoE` filters targets based on guild membership, party membership, and criminal status.

**Impact**: AoE damage simulations hit all provided targets. In practice, some targets would be excluded by faction logic.

**Severity**: Low — simulation provides worst-case (maximum targets hit). Users should be aware when modeling group PvP.

---

### 3.3 Spell Delay Model

**Assumption**: `Sleepms()` in TryToCast advances virtual time for DPS calculations.
**Reality**: In the live server, casting can be interrupted by damage, movement, or equipment changes. The simulation assumes uninterrupted casting.

**Impact**: DPS calculations represent maximum theoretical throughput, not real-world sustained DPS.

**Severity**: Low — this is explicitly listed in V3 out-of-scope ("Casting interruption modeling → V4").

---

### 3.4 Holy Bolt Alignment Logic

**Discovered in M25**: Holy Bolt (170) has alignment-based behavior — NPC caster → player target deals damage; NPC → NPC or player → good NPC heals instead.

**Impact**: The spell behaves differently depending on caster/target alignment, which is not a typical damage spell pattern. It's in `DAMAGE_SPELL_IDS` but filtered as a zero-damage exception in some test parametrizations.

**Severity**: Low — well-documented in M25 changelog with tests covering both paths.

---

### 3.5 Wrath of God Karma-Based Damage

**Discovered in M26**: Wrath of God (174) deals damage based on karma difference between caster and target, not the standard CalcSpellDamage formula. Equal karma → 0 damage.

**Impact**: Standard spell damage assertions (higher circle → higher damage) don't hold for this spell. It's in `DAMAGE_SPELL_IDS` but filtered as a zero-damage exception.

**Severity**: Low — documented with karma-specific tests.

---

### 3.6 Astral Storm Damage Sub-Script

**Discovered in M26**: Astral Storm (176) is primarily a paralysis/CC spell. Damage is dealt via a `start_script("astralstorm_damage")` sub-script that applies 5× `ApplyPlanarDamage` at `CalcSpellDamage/8` each.

**Impact**: The damage pathway is indirect (sub-script, not main script), making it harder to attribute damage correctly in the simulation metrics.

**Severity**: Low — working correctly with sub-script execution, documented in M26.

---

### 3.7 Non-Damage Spells in DAMAGE_SPELL_IDS

Three spells in `DAMAGE_SPELL_IDS` deal zero damage:
- Decaying Ray (67): AR debuff only
- Wraith's Breath (72): Paralysis/CC only
- Sacrifice (71): Pet sacrifice mechanic

These are handled via `_ZERO_DAMAGE_SPELLS` filters in tests, but any consumer of `DAMAGE_SPELL_IDS` expecting all entries to deal damage would get incorrect results.

**Severity**: Medium — API contract violation. Users iterating over `DAMAGE_SPELL_IDS` for damage analysis will include non-damage spells.

---

## 4. Documentation Gaps

| Gap | Location | Severity |
|---|---|---|
| `spells.md` not created | `notebooks/docs/` | Medium — referenced in M28 deliverables |
| V3 marked "in progress" | CLAUDE.md | Low — cosmetic |
| Spell count "31" incorrect | CLAUDE.md, path_to_v3.md | Low — off by 2 |
| Hot reload description overstated | CLAUDE.md | Low — misleading but functional |
| Standard "(12)" header wrong | path_to_v3.md | Low — off by 1 |
| M25 "20 single-target" wrong | path_to_v3.md | Low — should be 19 |
| M26 "11 AoE" wrong | path_to_v3.md | Low — should be 10 |
| Conditional skip mechanism undocumented | CLAUDE.md | Low |

---

## 5. Implementation Quality Notes

### Strengths
- **Comprehensive test coverage**: 2196 tests with 0 failures, 0 skipped
- **POL conformance**: Two full stub audits (V2 + V3) caught 25+ bugs
- **Property-based assertions**: Tests check relationships (e.g., "slayer > non-slayer") rather than exact values, surviving balance changes
- **Deterministic RNG**: All simulation results reproducible with seed
- **State isolation**: Snapshot/restore ensures iteration independence
- **Bug documentation**: Every bug fix includes root cause analysis in the changelog

### Areas for Improvement
- **DAMAGE_SPELL_IDS hygiene**: Remove non-damage spells or rename the set
- **CheckSkill model**: Consider documenting the expected fizzle rate divergence from live server
- **Missing spells.md**: Single outstanding M28 deliverable
- **CLAUDE.md staleness**: Several numbers and status labels need updating

---

## 6. Recommended Actions

### Priority 1 (Correctness)
1. Remove Decaying Ray, Wraith's Breath, Sacrifice from `DAMAGE_SPELL_IDS` (or create separate `CASTABLE_SPELL_IDS` set)
2. Create `notebooks/docs/spells.md` (M28 deliverable)

### Priority 2 (Documentation accuracy)
3. Update CLAUDE.md: V3 status → "Complete", spell count → 29
4. Update path_to_v3.md: Fix spell counts (Standard 11 not 12, M25 19 not 20, M26 10 not 11, total 29 not 31)
5. Update CLAUDE.md: Hot reload description
6. Update CLAUDE.md: Conditional skip clarification

### Priority 3 (Nice to have)
7. Add a note in CLAUDE.md V3 scope about the 6 reclassified spells
8. Document CheckSkill simplification in the notebook docs
