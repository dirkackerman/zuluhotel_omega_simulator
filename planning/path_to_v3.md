# Path to V3 — Damage Spell Casting

## Overview

V3 adds **damage spell casting** as a new simulation type alongside the existing weapon-hit simulation. The simulator will execute the real shard spell scripts (fireball.src, chain_lightning.src, etc.) through the interpreter, modeling the full spell damage pipeline: skill check → damage roll → resistance → elemental protection → final damage.

**Prerequisite**: V2 (Spell & Resistance Flows, POL stub audit) must be complete first.

## Scope

- **31 damage-dealing spells** across 4 schools (Standard, Necromancy, Earth, Holy)
- **Single-target and AoE spells**
- New `execute_spell()` entry point, `SpellScenario`, spell-specific stats
- Spell fizzle rate (CheckSkill), resistance rate, elemental protection
- 3 new notebooks, full documentation update, test coverage review + POL stub audit

### Out of Scope (deferred)

| Item | Reason | Future version |
|---|---|---|
| Non-damage spells (heal, teleport, buffs, summons) | No damage to simulate | V3.5+ |
| Songs (Bard/Bladesinger) | Buff-based, no direct damage | V3.5+ |
| Provocation / Peacemaking | AI behavior, not damage | V4 |
| Spell reflection (Magic Reflect) | Niche defensive mechanic | V3.5 |
| Casting interruption modeling | Requires multi-step combat state | V4 |
| Reagent consumption | No effect on damage output | V3.5 |
| Archery-specific notebooks | Damage already works in V1; dedicated showcase deferred | V3.5 |
| Parrying-specific notebooks | Already works in V1; dedicated showcase deferred | V3.5 |

## Architecture

Spell casting is **fully eScript** — no POL core success check. The interpreter executes the real shard spell scripts just like it executes mainhit.src for weapon hits.

| Weapon Hit (V1) | Spell Cast (V3) |
|---|---|
| `execute_hit()` | `execute_spell()` |
| `check_hit()` (POL core) | `CheckSkill()` (eScript, in TryToCast) |
| `mainhit.src` entry point | `fireball.src` / `chain_lightning.src` etc. |
| `CalcPhysicalDamage()` | `CalcSpellDamage()` |
| AR absorption | `Resisted()` + elemental protection |
| `ApplyTheDamage()` | `ApplyTheDamage()` (same function) |
| `HitResult` | `SpellResult` |
| `Scenario` / `run_scenario()` | `SpellScenario` / `run_spell_scenario()` |

## Damage Spell Catalog (31 spells)

### Standard (12)

| Spell | ID | Circle | Element | Type |
|---|---|---|---|---|
| Magic Arrow | 5 | 1 | Earth | Single |
| Harm | 12 | 2 | Water | Single |
| Fireball | 18 | 3 | Fire | Single |
| Lightning | 30 | 4 | Air | Single |
| Mind Blast | 37 | 5 | Magic | Single |
| Energy Bolt | 42 | 6 | Air | Single |
| Explosion | 43 | 6 | Fire | AoE |
| Chain Lightning | 49 | 7 | Air | AoE |
| Flame Strike | 51 | 7 | Fire | Single |
| Meteor Swarm | 55 | 7 | Fire+Earth | AoE |
| Earthquake | 57 | 8 | Earth | AoE |

### Necromancy (8)

| Spell | ID | Circle | Element | Type |
|---|---|---|---|---|
| Decaying Ray | 67 | 21 | Necro | Single |
| Spectre's Touch | 68 | 21 | Necro | Single |
| Abyssal Flame | 69 | 22 | Fire/Necro | AoE |
| Sacrifice | 71 | 22 | Necro | Single |
| Wraith's Breath | 72 | 22 | Necro | Single |
| Sorcerer's Bane | 73 | 23 | Necro | Single |
| Wyvern Strike | 76 | 23 | Necro | Single |
| Kill | 77 | 24 | Necro | Single |

### Earth (5)

| Spell | ID | Circle | Element | Type |
|---|---|---|---|---|
| Shifting Earth | 83 | 25 | Holy | Single |
| Call Lightning | 85 | 26 | Air | Single |
| Gust of Air | 89 | 27 | Air | AoE |
| Rising Fire | 90 | 27 | Fire | AoE |
| Ice Strike | 92 | 28 | Water | Single |

### Holy (5)

| Spell | ID | Circle | Element | Type |
|---|---|---|---|---|
| Holy Bolt | 170 | 26 | Holy | Single |
| Wrath of God | 174 | 27 | Holy | AoE |
| Divine Fury | 175 | 27 | Holy | Single |
| Astral Storm | 176 | 27 | Holy | AoE |
| Apocalypse | 181 | 28 | Holy | AoE |

## Spell Damage Pipeline

```
TryToCast()
    │  CheckSkill(SKILLID_MAGERY, difficulty)
    │  ConsumeMana(caster, spellid)
    │  fizzle → 0 damage, no effects
    │
    ▼
CalcSpellDamage(caster, target, circle)
    │  Roll: (circle * 3)d5 + floor(Magery / 5)
    │  Cap:  circle * (13 + circle)
    │  Class efficiency (Mage bonus, Warrior penalty)
    │  Equipment penalty (MagicPenalty)
    │  PvP: /3 for players, *1.5 for NPCs
    │  AoE: circle -= 3 before roll
    │
    ▼
Resisted(caster, target, circle, dmg)
    │  chance = max(resist/6, resist - magery/4 - circle*6)
    │  Target class mods (Mage↑, Paladin↑, Warrior↓)
    │  Caster class mods (Mage↓, Warrior↑)
    │  If resisted: dmg /= 2
    │  Eval Int scaling: dmg *= 1 + (evalint - resist) / 200
    │
    ▼
ApplyElementalDamage(caster, target, circle, dmg, element)
    │  Elemental protection lookup
    │  Mage caster: reduce protection by level*3
    │  Apply protection reduction
    │  Over-protection (>100%): heal instead
    │
    ▼
ApplyTheDamage(target, caster, dmg, dmgtype)
    │  PvP scaling (*0.6)
    │  ApplyRawDamage()
    │
    ▼
Final Spell Damage (recorded in SpellResult)
```

### Key Constants (from spelldata.inc)

- `SPELL_DAMAGES_CIRCLE_MULTIPLIER = 3` — 3 dice per circle
- `SPELL_DAMAGES_DICE_TYPE = 5` — d5 dice
- `SPELL_DAMAGES_MAGERY_DIVIDER = 5` — skill / 5 bonus
- `SPELL_DAMAGES_ON_PLAYER_DIVIDER = 3` — PvP damage divisor

### Key Skill IDs

- `SKILLID_MAGERY = 25`
- `SKILLID_EVALINT = 16`
- `SKILLID_MAGICRESISTANCE = 26`

## Result Model

```python
@dataclass
class SpellResult:
    spell_id: int = 0
    spell_name: str = ""
    circle: int = 0
    element: int = 0

    base_damage: int = 0         # CalcSpellDamage output (before resist)
    resisted: bool = False       # Did target resist?
    final_damage: float = 0.0    # After resist + protection + PvP scaling
    absorbed: float = 0.0        # Elemental protection absorbed

    caster_name: str = ""
    target_name: str = ""
    target_hp_before: int = 0
    target_hp_after: int = 0

    fizzled: bool = False        # CheckSkill failed
    side_effects: list[SideEffect] = []
    metrics: dict[str, Any] = {}

    success: bool = True
    error: str | None = None
```

Stats additions to `CellResult` / `RatioStats`:
- `fizzle_rate` — fraction of casts that fizzled (CheckSkill failed)
- `resist_rate` — fraction of landed spells where target resisted (damage halved)
- `resist_rate_on_cast` — conditional: of successful casts, how often resisted

## New Stubs Required

| Stub | Module | Purpose | Complexity |
|---|---|---|---|
| `CheckSkill` | attributes | Skill check with difficulty + random roll | Moderate |
| `ConsumeMana` | vitals | Deduct mana based on circle | Simple |
| `ConsumeReagents` | uo | Remove reagent items | No-op (skip in sim) |
| `CanTargetSpell` | uo | Interactive target selection | Stub — return provided target |
| `CanTargetArea` | uo | Area target selection | Stub — return provided location |
| `ListMobilesNearLocationEx` | uo | Find mobiles in radius | Stub — return defender list |
| `SmartAoE` | spelldata | Filter AoE targets (allies) | Stub — pass through |
| `CheckLosAt` / `CheckLineOfSight` | uo | Line-of-sight check | Stub — return true |
| `sleep` | basic | Casting delay | No-op in simulation |
| `RandomDiceRoll` | uo | Dice notation roll | Use existing dice parser + sim RNG |

Note: `IsProtected`, `Reflected`, `CalcSpellDamage`, `Resisted`, `ApplyElementalDamage`, `ModifyWithMagicEfficiency`, `GetScript`, `GetCircle` are all **eScript user-defined functions** in `spelldata.inc` — they execute through the interpreter naturally, no Python stubs needed.

---

## Milestones

### M23 — Spell Config Parsing & Fixture Sync

**Goal**: Parse spell and circle configs, sync spell script fixtures.

**Deliverables**:
- Parse `spells.cfg` — spell ID → name, script path, circle, reagents
- Parse `circles.cfg` — circle → mana cost, difficulty, delay, point value
- `sync_fixtures.py` updated to pull all 31 damage spell `.src` files + `spelldata.inc` additions + `spells.cfg` + `circles.cfg`
- `SpellConfig` dataclass for spell metadata lookup
- Unit tests: config parsing, all 31 spells resolvable by ID

**Acceptance**:
- `SpellConfig.get(spell_id)` returns circle, script path, mana cost, difficulty for all 31 damage spells
- Fixture shard contains all damage spell scripts

---

### M24 — Spell Execution Engine

**Goal**: `execute_spell()` entry point that runs a spell script through the interpreter and returns a `SpellResult`.

**Deliverables**:
- `SpellResult` dataclass
- `execute_spell(parse_results, caster, target, spell_id, ...)` function
  - Sets up SimulationContext with caster/target
  - Builds parameter array matching spell script signature (`parms`, `spell_id`)
  - Runs spell `.src` through executor
  - Collects damage via `ApplyRawDamage` side effect
  - Collects resist/fizzle via metrics
- New POL stubs: `CheckSkill`, `ConsumeMana`, `CanTargetSpell`, `sleep` (no-op), `CheckLineOfSight` (true), `RandomDiceRoll`
- `__RecordSimulatorMetric` instrumentation in `spelldata.inc` for: `spell_base_damage`, `spell_resisted`, `spell_resist_chance`, `spell_circle`, `spell_element`

**Acceptance**:
- `execute_spell()` successfully runs Fireball (single-target, circle 3, fire element)
- Returns `SpellResult` with correct `final_damage > 0`, `fizzled=False`, `resisted` flag
- Fizzle scenario: low Magery → `fizzled=True`, `final_damage=0`

---

### M25 — Single-Target Damage Spells

**Goal**: All 20 single-target damage spells executing correctly with validated damage.

**Deliverables**:
- Any additional stubs discovered during execution
- Parse and execute all single-target spell scripts through the interpreter
- Per-spell unit tests verifying:
  - Script executes without error
  - Damage is in expected range (circle-based bounds)
  - Correct element type recorded in metrics
  - Resistance reduces damage
  - PvP scaling applied when both are players
  - Class bonuses affect damage (Mage caster bonus, Warrior penalty)

**Spell list** (20 single-target):
Magic Arrow, Harm, Fireball, Lightning, Mind Blast, Energy Bolt, Flame Strike, Decaying Ray, Spectre's Touch, Sacrifice, Wraith's Breath, Sorcerer's Bane, Wyvern Strike, Kill, Call Lightning, Ice Strike, Shifting Earth, Holy Bolt, Divine Fury

**Acceptance**:
- All 20 spells execute with `success=True`
- Property-based assertions: higher circle → higher damage, Mage bonus > base, resist halves damage
- At least 3 spells with hand-calculated damage validation (Fireball, Flame Strike, Kill)

---

### M26 — AoE Damage Spells

**Goal**: All 11 AoE damage spells executing correctly, hitting multiple targets.

**Deliverables**:
- `ListMobilesNearLocationEx` stub — returns defender(s) registered in context
- `SmartAoE` stub — pass-through (no faction filtering in sim)
- `CanTargetArea` stub — return provided location coordinates
- `CheckLosAt` stub — return true
- AoE-aware `execute_spell()` — accepts list of targets, returns per-target `SpellResult`
- AoE circle reduction verified (circle -= 3 for damage calc)
- Per-spell unit tests verifying:
  - Multiple targets receive damage
  - Circle reduction applied (AoE deals less per-target than single-target equivalent)
  - Each target independently resists

**Spell list** (11 AoE):
Explosion, Chain Lightning, Meteor Swarm, Earthquake, Abyssal Flame, Gust of Air, Rising Fire, Wrath of God, Astral Storm, Apocalypse

**Acceptance**:
- All 11 AoE spells execute against 3+ targets with `success=True`
- AoE damage < equivalent single-target damage (circle - 3 reduction verified)
- Per-target resistance works independently

---

### M27 — Spell Scenario Runner & Stats ✅

**Goal**: `SpellScenario` and `run_spell_scenario()` that runs N iterations with statistical aggregation.

**Deliverables**:
- `SpellScenario` dataclass: caster spec, target spec(s), spell ID, iterations, seed
- `SpellParameterSweep`: sweep over Magery, Eval Int, Resist, circle, etc.
- `run_spell_scenario()` → `CellResult` with spell-specific stats:
  - `fizzle_rate` — fraction of iterations where CheckSkill failed
  - `resist_rate` — fraction of all casts where target resisted
  - `resist_rate_on_cast` — fraction of successful casts where target resisted
  - Reuses existing `DamageStats` for damage distribution (overall and on-cast)
- Extend `RatioStats` with `fizzle_rate`, `resist_rate`, `resist_rate_on_cast`
- Executor reuse across iterations (parse once, reset per iteration)
- State snapshot/restore between iterations

**Acceptance**:
- `run_spell_scenario()` runs 1000 iterations of Fireball, returns `CellResult` with meaningful stats
- `fizzle_rate` matches expected CheckSkill success probability
- `resist_rate` matches expected Resisted() probability
- Parameter sweep: damage vs Magery produces monotonically increasing curve
- Parameter sweep: damage vs target Resist produces monotonically decreasing curve

---

### M28 — Reporting, Notebooks & Documentation

**Goal**: Spell-specific reporting, new notebooks, and full documentation update.

**Deliverables**:

**Reporting**:
- `summary_table` / `comparison_table` support spell stats (`fizzle_rate`, `resist_rate`, `resist_rate_on_cast`, `mean_on_cast`)
- `damage_histogram` works with spell results (filters fizzles like it filters misses)
- `damage_vs_parameter` works with spell sweeps
- New: `spell_comparison` chart (compare spells across circles/elements)

**Notebooks**:
- `06_spell_damage.ipynb` — Basic spell casting: Fireball scenario, damage distribution, fizzle rate
- `07_spell_comparison.ipynb` — Compare spells: circle scaling, element comparison, school comparison (Standard vs Necro vs Earth vs Holy)
- `08_spell_resistance.ipynb` — Resistance analysis: resist rate vs skill, class modifier impact, Eval Int vs Resist sweeps, elemental protection impact
- Each notebook demonstrates both single-target and AoE scenarios

**Documentation**:
- Update `concepts.md` — spell casting pipeline, spell success/fizzle, resistance mechanics
- Update `results.md` — `SpellResult` fields, spell-specific stats
- Update `scenarios.md` — `SpellScenario`, `SpellParameterSweep`
- Update `combatant-specs.md` — caster-relevant fields (Magery, Eval Int, equipment penalties)
- Update `examples.md` — spell casting cookbook examples
- New `spells.md` — spell catalog reference (all 31 damage spells with circle, element, type)
- Update `reporting.md` — new spell charts and table columns

**Acceptance**:
- All 3 notebooks render and produce meaningful visualizations
- Documentation covers all new APIs
- `damage_histogram` shows clean spell damage distribution (no fizzle spike at 0)

---

### M29 — Test Coverage Review & POL Stub Audit

**Goal**: Comprehensive test coverage review and stub conformance audit.

**Deliverables**:

**Test coverage review**:
- Every damage spell has at least 2 tests (executes + damage in range)
- AoE spells tested with 1, 3, and 5 targets
- Resistance tested at 0%, 50%, 100% resist skill
- Class modifiers tested: Mage caster, Warrior caster, Mage target, Warrior target
- PvP scaling tested (player vs player, player vs NPC)
- Fizzle tested at low/high Magery
- Edge cases: 0 damage floor, over-protection healing, max circle

**POL stub audit** (spell-path stubs):
- `CheckSkill` — verify against POL's `check_skill_hook` behavior
- `ConsumeMana` — verify mana deduction matches circle config
- `ApplyRawDamage` — re-verify for spell damage path
- `GetEffectiveSkill` — verify returns correct values for Magery, Eval Int, Resist
- `GetObjProperty` / `SetObjProperty` — verify class level properties work correctly
- `Random` / `RandomInt` — verify distribution matches POL
- `ReadConfigFile` — verify spell/circle configs parsed correctly
- Unit test per stub encoding expected POL behavior

**Acceptance**:
- All new tests pass
- No stub divergence from POL behavior on the spell path
- Test count increase documented in changelog

---

## Milestone Dependencies

```
M23 (Config + Fixtures)
  │
  ▼
M24 (Execution Engine)
  │
  ├──────────────┐
  ▼              ▼
M25 (Single)   M26 (AoE)
  │              │
  └──────┬───────┘
         ▼
M27 (Runner + Stats)
         │
         ▼
M28 (Reporting + Notebooks + Docs)
         │
         ▼
M29 (Coverage + Stub Audit)
```

M25 and M26 can be worked in parallel after M24. Everything else is sequential.
