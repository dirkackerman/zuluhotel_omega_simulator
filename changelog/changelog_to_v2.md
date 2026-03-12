# Changelog to V2

This changelog tracks progress on V2 (Spell & Resistance Flows). See [Path to V2](../planning/path_to_v2.md) for the full roadmap.

---

## M-V2.1 — Combat Dispatch Audit

Audited combat critical path stubs against POL C++ source (`charactr.cpp`, `uomod.cpp`). Found and fixed 6 bugs, added 50 new tests.

### Bug Fixes

- **ApplyRawDamage — dead guard**: POL returns immediately if target is already dead (`charactr.cpp:1738`). Our stub was applying damage to dead mobiles.
- **ApplyRawDamage — unhide on damage**: POL unhides the mobile when damaged (`charactr.cpp:1762`). Our stub did not.
- **ApplyRawDamage — remove paralysis**: POL removes paralysis on damage (`charactr.cpp:1766`). Added `paralyzed: bool` to Mobile model + snapshot/restore.
- **ApplyRawDamage — float rounding**: `int(amount)` truncated 23.7→23. Changed to `int(round(float(amount)))` with try/except for UNINIT/invalid types.
- **SetPoisoned — kind mismatch**: Recorded `kind="poison"` but `aggregate_cell` checks `"poison_applied"`. Result: `poison_rate` stat was always 0.0.
- **DestroyItem — return value**: POL returns `BLong(1)` on success (`uomod.cpp:2628`). Our stub returned `None`.

### Test Scenarios

- **ApplyRawDamage**: Dead target takes no damage, unhides on damage, removes paralysis, float rounding (23.7→24, 23.4→23), exact lethal damage, large overkill, multiple hits accumulate, string coercion ("25"→25), None/UNINIT amount handling
- **SetPoisoned**: Kind is `"poison_applied"` (not `"poison"`), level recorded correctly, UNINIT level→0, None/UNINIT mobile no crash
- **DestroyItem**: Returns 1 on success, None→returns None, serial recorded, UNINIT item no crash
- **start_script**: No executor→None, executor delegation, exception→None (no crash), args passed as list, UNINIT path
- **SystemFindObjectBySerial / FindMobile**: Registered object, missing serial, None serial, UNINIT serial, non-Mobile returns None
- **Guild stubs**: FindGuild returns stub, IsEnemyGuild/IsAllyGuild→False, guildid==0
- **Global properties**: Set/get roundtrip, defaults, None name, persistence
- **Config stubs**: ReadConfigFile None/missing→None, caching, FindConfigElem None args, GetConfigInt/String None args
- **Misc**: CreateItemAtLocation→None, EnumerateOnlineCharacters→[]

### Stats

- 1219 tests passing (up from 1169), 0 skipped

---

## M-V2.2 — Property & Stat Accessor Audit

Audited property bag, stat/vital/skill accessors, and equipment stubs in `object_stubs.py` against POL C++ source (`attributemod.cpp`, `vitalmod.cpp`, `uomod.cpp`). Found and fixed 10 bugs, added 61 new tests.

### Bug Fixes

- **SetMana — missing clamping**: POL clamps vitals to `[0, maximum]`. Our `SetMana` didn't clamp — mana could go negative or exceed `max_mana`. `SetHP` already had correct clamping.
- **SetStamina — missing clamping**: Same issue as SetMana. Added clamping to `[0, max_stamina]`.
- **GetAttributeBaseValue — wrong units**: POL returns raw tenths (`av.base()`). Our stub returned display value (`tenths // 10`). Skill at 100 display: POL returns 1000, we returned 100.
- **HealDamage — return value**: POL returns `BLong(1)` on success. Our stub returned `None`.
- **EraseObjProperty — return value**: POL returns `BLong(1)` on success. Our stub returned `None`.
- **UNINIT crashes (5 bugs)**: `int(UNINIT)` raises `TypeError` in 12+ call sites across stat mod setters, vital setters, skill/equipment getters. Added try/except guards matching M-V2.1 pattern.

### Test Scenarios

- **Property system**: EraseObjProperty returns 1, UNINIT obj/name handling, any-type storage, overwrite, None value
- **Stat accessors**: Mods affect effective value, negative mods, float/string/UNINIT coercion for set_mod, UNINIT mobile returns 0
- **Vital accessors (SetMana/SetStamina clamping)**: Clamps above max, clamps below 0, UNINIT/string/float value coercion
- **SetHP**: UNINIT value no crash, string coercion, float truncation
- **HealDamage**: Returns 1 on success, UNINIT/string/float amount, caps at max
- **GetVital/SetVital**: UNINIT mobile, UNINIT vital_id, UNINIT value, string value coercion
- **Skill accessors**: Missing skill→0, UNINIT mobile/skill_id, string skill_id, GetAttributeBaseValue returns tenths, UNINIT precision, SetBaseSkill UNINIT
- **Equipment**: UNINIT mobile/layer, string layer coercion, empty list, GetKarma defaults

### Stats

- 1280 tests passing (up from 1219), 0 skipped

---

## M-V2.3 — Config, RNG & Utility Audit

Audited Batch 1 stubs in `basic_stubs.py` against POL C++ source (`mathmod.cpp`, `uomod.cpp`). Found and fixed 8 bugs, added 81 new tests.

### Bug Fixes

- **CInt — float-string returns 0**: POL's `CInt("3.7")` uses `strtol` → 3. Our `int("3.7")` raised `ValueError` → returned 0. Added `int(float(value))` fallback.
- **TypeOf — UNINIT returns "Unknown"**: `TypeOf(UNINIT)` returned "Unknown" because `value is None` is False for UNINIT. Added `value is UNINIT` check.
- **Random/RandomInt — UNINIT crash**: `int(max_val)` unguarded — `int(UNINIT)` raises `TypeError`. Added try/except.
- **Find — UNINIT start crash**: `int(start)` unguarded. Added try/except with default offset=0.
- **SubStr — UNINIT start/length crash**: `int(start)` and `int(length)` unguarded. Added try/except. Also fixed `start=0` edge case (was `idx=-1` → returned last char instead of full string).
- **LogE — UNINIT crash**: `float(value)` unguarded and `value is None` check didn't catch UNINIT. Restructured with try/except.
- **RandomFloat — UNINIT crash**: `float(below)` unguarded — `below is not None` guard passes for UNINIT. Added try/except.
- **SplitWords — UNINIT delimiter**: `str(UNINIT)` → `"UNINIT"` used as split delimiter. Added UNINIT check to fall back to whitespace split.
- **Max/Min — UNINIT returns UNINIT & wrong type**: POL coerces args to Double. Our stub used Python `max()` which raised TypeError on UNINIT and returned original types. Changed to float coercion with try/except.

### Test Scenarios

- **CInt**: Float-string ("3.7"→3), negative float-string, UNINIT→0, negative string
- **CDbl**: UNINIT→0.0, negative string
- **CStr**: UNINIT→string, float→string
- **Hex**: UNINIT→"0x0", negative int
- **Max/Min**: UNINIT args, float args, mixed int/float, returns float type
- **TypeOf**: UNINIT→"Uninit", bool→"Integer"
- **Len**: Dict, UNINIT→0, int→0
- **Pow**: Returns float type, UNINIT base/exp, zero exp, negative exp
- **Abs**: UNINIT→0, float
- **Sqrt**: UNINIT→0.0, zero, float
- **LogE**: Positive, one, UNINIT, zero, negative
- **Sin/Cos**: Zero, UNINIT
- **Random/RandomInt**: UNINIT→0, zero→0, negative→0, string coercion, float coercion
- **RandomFloat**: Default, UNINIT, custom limit
- **RandomDiceRoll**: Simple (1d6), multiple (3d6), bonus (2d6+4), penalty clamped, penalty allowed, None, UNINIT, plain number, deterministic, zero faces
- **Find**: Basic, not found, start offset, UNINIT start/text/search, empty needle
- **SubStr**: UNINIT start/length, zero start, negative start
- **SplitWords**: UNINIT delimiter (whitespace fallback), UNINIT text, empty
- **Lower/Upper**: UNINIT, None
- **No-ops**: set_priority returns 0, detach, SetWarMode

### Stats

- 1361 tests passing (up from 1280), 0 skipped

---

## M-V2.4 — Virtual Time Calculation & DPS Metrics

Implemented POL-conformant swing delay calculation from `Character::schedule_attack()` (`charactr.cpp:2832–2881`) and integrated DPS metrics throughout the simulator stack.

### New Module

- **`src/omega/combat/timing.py`** — `calculate_swing_delay(attacker, weapon)` returns delay in milliseconds matching POL exactly:
  - Speed-based path: `clocks = 1_500_000 // ((DEX + 100) * SPEED)` (C++ integer division)
  - Delay-based path: `clocks = (max(0, delay + delay_mod) * 100) // 1000`
  - SwingSpeedIncrease modifier with -0.99 clamp
  - `_c_round()` matching C++ `round()` semantics (half away from zero, not Python's banker's rounding)
  - No minimum floor — matches POL (line 2872 is a debug log, not a clamp)

### Model Additions

- **`Weapon.delay`** — explicit delay in milliseconds (alternative to speed, default 0)
- **`Mobile.delay_mod`** — delay modifier for delay-based weapons (default 0)
- **`Mobile.swing_speed_increase`** — property summing SwingSpeedIncrease from mobile + all equipped items
- **`MobileSnapshot`** — captures and restores `delay_mod`
- **`WeaponSpec.delay`** — delay field passed through `build_weapon()`

### Result & Stats Enrichment

- **`HitResult.swing_delay_ms`** — populated on every hit (including misses)
- **`TimingStats`** dataclass: `swing_delay_ms`, `swings_per_second`, `dps_mean`, `dps_on_hit`, `effective_dps`
- **`CellResult.timing`** — computed in `aggregate_cell()` from first successful result's swing delay

### Reporting

- **Tables**: 5 new stat columns (`swing_delay_ms`, `swings_per_sec`, `dps_mean`, `dps_on_hit`, `effective_dps`)
- **Plots**: `dps_vs_parameter()` (DPS + delay dual-axis line plot), `dps_comparison()` (bar chart with delay annotations)

### Key Bug Prevention

- **C++ `round()` vs Python `round()`**: C++ rounds half away from zero; Python uses banker's rounding. For `round(132.5)`: C++ gives 133, Python gives 132. Implemented `_c_round()` to match C++ exactly. This prevents swing delay drift across all affected weapon/DEX/SSI combinations.

### Test Scenarios

- **`_c_round` conformance**: 15 tests verifying C++ round semantics including explicit Python divergence proof
- **Speed-based path**: 9 tests — medium/fast/slow weapons, all DEX ranges, integer truncation verification
- **Delay-based path**: 10 tests — basic, positive/negative mod, zero clamp, integer truncation, sub-10ms edge cases
- **SwingSpeedIncrease**: 14 tests — percentage modifiers, negative clamp at -0.99, equipment stacking, delay-based interaction, banker's rounding divergence case
- **Edge cases**: 7 tests — speed-0 guard, no minimum floor, default values, return type
- **`swing_speed_increase` property**: 9 tests — mobile/equipment/stacking, negative, non-numeric, float truncation
- **Snapshot/restore**: 2 tests — `delay_mod` capture and reset
- **HitResult integration**: 3 tests — default, populated by `execute_hit`, populated on miss
- **TimingStats/DPS**: 7 tests — mean, with misses, scaling, empty/error edge cases
- **Table reporting**: 2 tests — DPS columns present, None timing fallback
- **WeaponSpec**: 4 tests — delay field default, custom, materialization
- **Real-world weapons**: 5 tests — ZH shard weapon speeds (axe/mace/longsword/bow), DPS comparison

### Stats

- 1448 tests passing (up from 1361), 0 skipped

---

## M-V2.5 — Astral Damage Path Validation

End-to-end validation of the astral damage path — a completely separate damage system from physical that drains mana/stamina instead of HP. Added 3 new stubs, loop iteration guard, Mobile model additions, shard script instrumentation, and 31 integration tests.

### Infrastructure

- **`Sleep` stub** — no-op (seconds), matching existing `Sleepms` (ms) pattern
- **`set_script_option` stub** — no-op for script option flags (SCRIPTOPT_CAN_ACCESS_OFFLINE_MOBILES etc.)
- **Loop iteration guard** — `_MAX_LOOP_ITERATIONS = 100_000` on `visitWhileStatement`, `visitDoStatement`, `visitRepeatStatement` in evaluator.py. Prevents infinite loops from polling scripts like `astralincapacity.src` where `Sleep` is a no-op.
- **`Mobile.frozen`** — new `bool` attribute + snapshot/restore support. Used by `astralincapacity.src`.
- **`astralincapacity.src`** — added to `sync_fixtures.py` extra scripts and synced to fixtures.

### Shard Instrumentation

- **`RecalcAstralDmg` (hitscriptinc.inc)** — added `meditation_triggered` tracking variable and `__RecordSimulatorMetric` struct: `astral_basedamage`, `astral_rawdamage`, `astral_absorbed`, `astral_ar`, `astral_meditation_triggered`
- **`ApplyTheAstralDamage` (damages.inc)** — added `list:damage_applied` metric with `type` and `amount` fields, matching physical path pattern

### Test Scenarios

- **Basic flow (6 tests)**: Astral weapon drains mana not HP, physical weapon drains HP not mana, dispatch verification, zero base damage, dead defender
- **Drain mechanics (3 tests)**: Mana drained first, overflow to stamina, astral incapacity (both → 0)
- **Spirit Speak scaling (2 tests)**: Higher spirit speak → more damage, zero spirit speak → minimal damage
- **EvalInt scaling (1 test)**: Higher EvalInt → more damage via `(1 + EvalInt * 0.002)` multiplier
- **Class bonuses (4 tests)**: Mage bonus vs NPC (ClasseBonus), mage bonus vs player (level-2), warrior penalty (non-mage), warrior+mage no penalty
- **Meditation resistance (3 tests)**: Meditation reduces damage (seeded), no meditation no resist, piercing bypasses meditation
- **Astral armor (2 tests)**: Astral property + AR absorbs, non-astral armor no absorption
- **50% reduction (1 test)**: rawdamage * 0.5 verified via metrics
- **Metrics (5 tests)**: All 5 struct fields present, damage_applied list with DMGID_ASTRAL type, meditation_triggered is 0/1, absorbed=0 without astral armor, AR metric = Astral*25*armor.ar
- **Edge cases (4 tests)**: Very high damage drains both, frozen set on incapacity, intelligence scaling (higher INT → more), strength reduces astral scaling (higher STR → less)

### Stats

- 1513 tests passing (up from 1448), 0 skipped

---

## M-V2.6 — Reactive Armor & Resistance Integration

Validated reactive armor interactions with all enchantment types and hand-calculated `Resisted()` function scenarios across class/skill combinations. 34 new tests, all passing.

### Test Scenarios

- **Reactive + Spell Strike**: Both fire independently in same hit, reactive uses basedamage (not spell-modified), property consumed
- **Reactive + Effect Enchantments**: Life drain, mana drain, piercing — all combine correctly with reactive
- **Reactive + Greater Enchantments**: Trielemental (FIRE+AIR+WATER) and dualplanar (HOLY+NECRO) — reactive fires before enchantment hitscript, both metrics captured
- **Reactive Power Scaling**: 6 hand-calculated scenarios at power=10/25/50/100/150, player (1/8 reduction) and NPC (full), CInt truncation verified
- **Resisted() Hand Calculations (dualplanar, circle=9)**:
  - No class, low resist: chance=10, evalint=100, resist=60
  - No class, high resist (1300): chance=1226, always resists, dmg floors at 1
  - Mage L5 defender: chance boosted from 13→29
  - Warrior L4 defender: chance reduced from 13→3, resist halved 80→40
  - Paladin L4 defender: chance from 13→19
  - Mage L5 caster: chance from 13→5 (harder to resist)
  - Warrior L4 caster: chance from 13→52 (easy to resist), resist doubled 80→160
  - Mage L5 vs Mage L5: partial cancel, chance=12
  - EvalInt > resist: damage amplified (1.35x factor)
  - EvalInt < resist: damage reduced (0.65x factor)
  - Extreme reduction: damage floors at 1
  - Warrior defender takes more spell damage (class multiplier)
  - Mage defender takes less spell damage (class divisor)
- **Resisted() via Trielemental (circle=8)**: No class chance=13, Mage L3 defender chance=22
- **Over-Protection + Reactive**: Defender with >100% fire protection heals from fire, reactive still reflects physical
- **Metrics Structure**: All 7 fields present (dmg_before, dmg_after, chance, did_resist, circle, evalint, resist), values match skill setup, circle values correct

### Key Discovery

Dualplanar `Resisted()` produces 3 entries per hit: 1 direct call (circle=9, caster=attacker) + 2 from `ApplyPlanarDamage` (circle=1, caster=targ=defender). The inner calls use the defender's skills as "caster", producing different evalint/chance values. Tests filter by circle to validate the correct entry.

### Stats

- 1513 tests passing (up from 1448), 0 skipped

---

## M-V2.7 — Fixture Transition & Test Hardening

Systematic audit of the V2 codebase for bugs, test gaps, and fixture hygiene. Found and fixed 2 bugs, added 20 new tests, updated documentation references.

### Bug Fixes

- **C-style for loop missing iteration guard**: `visitCstyleForStatement` in `evaluator.py` had no `_MAX_LOOP_ITERATIONS` guard, unlike while/do/repeat loops. A `for(i:=1; 1; i:=i)` would infinite-loop. Added the same guard pattern.
- **`OmegaLogger` format-string mismatch**: All 4 loop guard warning calls used printf-style `%d` formatting, but `OmegaLogger.warning()` accepts keyword args only. Changed to f-strings.

### Test Scenarios

- **Loop iteration guard (7 tests)**: while(1) breaks at limit, do...while(1) breaks at limit, repeat...until(0) breaks at limit, C-style for(;;) breaks at limit, normal 100-iteration while completes, normal C-style for completes, break exits before guard triggers. All use `unittest.mock.patch` with `_MAX_LOOP_ITERATIONS=50`.
- **Frozen snapshot (4 tests)**: Captures frozen=True, captures frozen=False default, restores frozen=True, restores frozen=False after True.
- **Sleep & set_script_option stubs (5 tests)**: Sleep returns None, Sleep no args, Sleep with UNINIT, set_script_option returns None, set_script_option with UNINIT.
- **Astral edge cases (3 tests)**: Astral PvP has no basedamage 0.4x scaling (unlike physical), defender warrior+mage gets no 5/6 penalty, mage level below threshold (level-2 < 1) → ClasseBonusByLevel not applied.
- **Timing defaults (1 test)**: Mobile with default stats (dex=10) + standard weapon → reasonable 2720ms delay.
- **Frozen/incapacity fix**: Corrected `test_frozen_set_on_incapacity` → `test_frozen_reset_after_incapacity_script` — with Sleep as no-op, the polling loop hits the guard, then the script's cleanup resets frozen to 0.

### Documentation Fixes

- **`test_timing.py`** — Updated docstring reference from `submodules/zuluhotel_omega_2.5/` to `fixtures/shard/`
- **`CLAUDE.md`** — Updated fixture count from "246 files, 962 KB" to "247 files, 2332 KB"

### Assertion Hardening Decision

Audited all exact-value assertions across the test suite. All are appropriate — they test formulas with test-controlled inputs (hand-calculated expected values), not shard balance constants. No conversion to property-based assertions needed.

### Stats

- 1533 tests passing (up from 1513), 0 skipped

---

## M-V2.8 — Notebook Enrichment & Documentation Update

Comprehensive update of all documentation pages and notebooks with V2 content: DPS/timing metrics, astral damage path, spell resistance with class modifiers, and stub audit findings.

### Documentation Updates (8 files)

- **concepts.md** — Virtual time & DPS section (swing delay formula, DPS metrics table, plot examples), astral damage pipeline diagram with physical vs astral comparison table, spell resistance & class modifiers (base formula, class modifier tables)
- **results.md** — `swing_delay_ms` on HitResult, `timing` on CellResult, full TimingStats section with fields, example code, interpretation guide, astral damage metrics section
- **runtime.md** — Fixed `start_script()` description (V1.5+ dispatches to sub-script executor), V2 stubs (Sleep, set_script_option), loop iteration guard docs, comprehensive V2 stub audit section (M-V2.1 through M-V2.3 findings)
- **constants-reference.md** — Timing constants (POLCLOCKS_PER_SEC, speed formula numerator, SSI clamp), shard weapon speed range table, astral damage constants, spell resistance constants
- **messages-and-metrics.md** — V2 astral metrics table (5 new metric keys)
- **reporting.md** — DPS imports, 5 new DPS stat columns, `dps_vs_parameter()` and `dps_comparison()` plot documentation
- **examples.md** — 4 new recipes: DPS comparison across weapons (R14), DPS vs Dexterity curve (R15), astral damage analysis (R16), spell resistance by class (R17)
- **README.md** — V2 features listed, note about V2 sections in all notebooks

### Notebook Updates (4 notebooks)

- **NB01 (basic_damage)** — DPS & Swing Timing section (TimingStats display + DPS table), Astral Damage section (astral mage scenario with per-hit metric inspection). Fixed invalid `max_mana`/`max_stamina` fields in CombatantSpec.
- **NB02 (skill_sweep)** — DPS vs Dexterity sweep (DEX 25–130, DPS + delay dual-axis plot), DPS vs Weapon Speed sweep (speed 15–95, linear DPS scaling), summary tables with timing columns
- **NB03 (class_comparison)** — DPS Comparison bar chart across classes, DPS comparison table with timing columns, Spell Resistance by Defender Class section (Hellfire spell strike vs Warrior/Mage/Paladin/Bladesinger/Ranger defenders)
- **NB05 (enchantments)** — DPS Comparison: Enchanted vs Plain section (6 enchantment types side-by-side), Spell Resistance Impact on Enchantments section (Hellfire vs NPC/Warrior/Mage/Paladin defenders showing class resistance modifiers)

### Bug Fix

- **NB01 astral cell** — Removed invalid `max_mana=500, max_stamina=200` from CombatantSpec (only `mana` and `stamina` are valid fields; max values auto-set in `build_combatant()`)

### Test Scenarios

No new tests — documentation and notebook-only changes. Full suite verified.

### Stats

- 1533 tests passing, 0 skipped
