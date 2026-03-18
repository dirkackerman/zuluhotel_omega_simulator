# Path to V3.1 — Casting Armour (Armor OnHitScripts)

## Overview

V3.1 adds **casting armour** — armor enchantments that trigger spell casts, slayer bonuses, effects, or greater abilities when the wearer is hit. This is the armor-side mirror of V1.5's weapon enchantments. The shard calls these **OnHitScripts** (distinct from weapon **HitScripts**).

**Prerequisite**: V3 (Damage Spell Casting) must be complete. V3's spell execution engine, sub-script executor, and metrics infrastructure are all reused directly.

## Scope

- **47 armor enchantments** from `onhitscriptdesc.cfg` across 4 types:
  - **18 Spell** — cast a spell back at the attacker (Clumsy through Earthquake)
  - **17 Race-Resistant** — slayer bonus against matching attacker race
  - **7 Effect** — piercing, banish, poison, life/mana/stamina drain, blinding
  - **5 Greater** — tri-elemental, deflection, avenging, invisibility, dual-planar
- **~13 distinct onhit scripts** to execute through the interpreter
- `ArmorEnchantment` enum, `ArmorEnchantmentRegistry`, `ArmorSpec.enchant_with()` API
- Cursed armor variant (5% generation chance; inverts spell target)
- Metrics instrumentation, stats aggregation, notebook, documentation

### Out of Scope (deferred)

| Item | Reason | Future version |
|---|---|---|
| Armor enchantment loot generation simulation | Requires full `starteqp.inc` — too broad | V4 |
| Enchantment stacking (multiple armor pieces) | DealDamage reads one armor's OnHitScript | V4 |
| Cursed detection/identification | Player knowledge system, not combat | V4 |
| Enchantment durability/degradation | Accumulating state, deferred per V1 strategy | V4 |

## Architecture

Casting armour mirrors the weapon enchantment architecture established in V1.5. The key difference is **when** and **who**:

| Aspect | Weapon Enchantments (V1.5) | Armor Enchantments (V3.1) |
|---|---|---|
| Config file | `hitscriptdesc.cfg` | `onhitscriptdesc.cfg` |
| Enum | `Enchantment` | `ArmorEnchantment` |
| Registry | `EnchantmentRegistry` | `ArmorEnchantmentRegistry` |
| API | `WeaponSpec.enchant_with()` | `ArmorSpec.enchant_with()` |
| Set on | Weapon object | Armor object |
| Triggered by | Attacker's swing landing | Defender being hit |
| Dispatch | `mainhit.src` → hitscript | `DealDamage()` → `OnHitScript` property on armor |
| Spell caster | Attacker | Defender (normal) / Attacker (cursed) |
| Spell target | Defender | Attacker (normal) / Defender (cursed) |

### Dispatch Flow (from `DealDamage()` in `hitscriptinc.inc`)

```
DealDamage(attacker, defender, weapon, armor, basedamage, rawdamage)
    │
    ├─ Check weapon poison (SkillPoisoned property)
    ├─ Check ReactiveArmor (existing V1.5 — one-shot, consumes property)
    │
    ├─ Read armor.OnHitScript property
    │   ├─ If set: start_script(onhit, {attacker, defender, weapon, armor, basedamage, rawdamage})
    │   │          (script calls ApplyTheDamage internally)
    │   └─ If not set: ApplyTheDamage(defender, attacker, rawdamage)
    │
    └─ (Astral path: ApplyTheAstralDamage — no OnHitScript check)
```

### Critical Detail: OnHitScript replaces the direct `ApplyTheDamage()` call

When an armor has `OnHitScript`, the onhit script is responsible for calling `ApplyTheDamage()` at the end. This means the sub-script executor must fully complete for damage to be applied. This is the same pattern as weapon enchantments — the script wraps the damage application.

### Property Model

When an armor piece is enchanted, these properties are set:

| Property | Type | Set by | Read by |
|---|---|---|---|
| `OnHitScript` | string | `SetOnHitscript()` in `starteqp.inc` | `DealDamage()` in `hitscriptinc.inc` |
| `HitWithSpell` | int | `ApplySpellOnHitscript()` | `spellonhit.src` |
| `EffectCircle` | int | `ApplySpellOnHitscript()` | `spellonhit.src` |
| `ChanceOfEffect` | int (0-100) | `ApplySpellOnHitscript()` / effect cfg | `spellonhit.src`, effect/greater scripts |
| `Cursed` | int (0/1) | Random 5% during generation | All onhit scripts (inverts target) |
| `ProtectedType` | string | Race-resistant setup | `raceresistonhit.src` |
| `Poisonlvl` | int | Venomous enchantment setup | `poisononhit.src` |

### Spell-Type OnHitScript Execution (`spellonhit.src`)

```
spellonhit(parms)  ← {attacker, defender, weapon, armor, basedamage, rawdamage}
    │
    ├─ Class weapon check (Thief/Bard/Mage — exit if out-of-class weapon)
    │
    ├─ Roll ChanceOfEffect (1d100 <= chance)
    │   ├─ Read HitWithSpell, EffectCircle from armor
    │   ├─ Cursed? → target=defender, caster=attacker
    │   │   else  → target=attacker, caster=defender
    │   └─ Start_Script(GetScript(spellid), {#MOB, caster, targ, circle, 1})
    │
    └─ ApplyTheDamage(defender, attacker, rawdamage)  ← always, regardless of spell
```

The spell launched is the same spell script used by V3 spell casting (e.g., `:spells:fireball`). The `#MOB` marker tells the spell script it was triggered by a mob (not direct cast), and the circle parameter overrides the spell's natural circle.

### Stubs Likely Needed

| Stub | Module | Purpose | Status |
|---|---|---|---|
| `GetScript(spellid)` | spelldata.inc (eScript) | Map spell ID → script path | Verify — may be eScript function in `spelldata.inc`, not a POL built-in |
| `IsThief(mob)` | classes.inc (eScript) | Class check | Verify — likely eScript function |
| `IsBard(mob)` | classes.inc (eScript) | Class check | Verify — likely eScript function |
| `IsMage(mob)` | classes.inc (eScript) | Class check | Verify — likely eScript function |
| `ClassWeapons(class)` | classes.inc (eScript) | Return weapon list for class | Verify — likely eScript function |
| `GetClass(mob)` | classes.inc (eScript) | Return mob's class | Verify — likely eScript function |
| `SetScriptController(mob)` | uo | Set script controller | May already be stubbed (no-op) |

Note: Most of these are eScript user-defined functions in the include chain, not POL built-ins. They should execute through the interpreter naturally. Only discover and stub actual POL built-in gaps during implementation.

---

## Milestones

### M30 — Armor Enchantment Config, Registry & Fixture Sync

**Goal**: Parse `onhitscriptdesc.cfg`, create `ArmorEnchantment` enum and `ArmorEnchantmentRegistry`, sync all onhit `.src` scripts to test fixtures. Mirror the weapon enchantment pattern from `enchantments.py`.

**Deliverables**:

- **`src/omega/config/armor_enchantments.py`** — new module, mirroring `enchantments.py`:
  - `ArmorEnchantment(IntEnum)` — 47 named constants (IDs 1–47)
  - `_ARMOR_ENCHANTMENT_META` — maps ID → `(onhitscript_path, armor_properties)`
  - `ArmorEnchantmentEntry` dataclass — parsed metadata from `onhitscriptdesc.cfg` (type, script, name, cursed name, spell ID, spell script, circle mod, chance mod, slayer type, cprop, multiplier)
  - `ArmorEnchantmentRegistry` — lookup by ID, name, spell name, slayer type, enchantment type
  - `armor_enchantment_hitscript(enchantment)` → script package path
  - `armor_enchantment_properties(enchantment)` → dict of CProps
  - Note: `onhitscriptdesc.cfg` uses `OnHitscriptType` / `OnHitscript` field names (not `HitscriptType` / `Hitscript`). Parser must handle both conventions.

- **`ArmorSpec.enchant_with(enchantment, *, circle=None, chance=None, cursed=False)`** — set `OnHitScript`, `HitWithSpell`, `EffectCircle`, `ChanceOfEffect`, `Cursed` properties on armor object. Analogous to `WeaponSpec.enchant_with()`.

- **`scripts/sync_fixtures.py`** update — pull all ~13 distinct onhit `.src` scripts:
  - `spellonhit.src` (spell-type)
  - `raceresistonhit.src` (slayer-type)
  - `piercingonhit.src`, `banishonhit.src`, `poisononhit.src`, `manadrainonhit.src`, `staminadrainonhit.src`, `blindingonhit.src`, `bouncingonhit.src` (effects — verify actual filenames)
  - `trielementalonhit.src`, `deflectiononhit.src`, `avengingonhit.src`, `invisibleonhit.src`, `dualplanaronhit.src` (greaters)
  - `onhitscriptdesc.cfg` (if not already in fixtures)

- **Unit tests**:
  - `ArmorEnchantmentRegistry.from_cfg()` parses all 47 entries
  - Lookup by ID, name, spell name, slayer type all work
  - `by_type()` returns correct counts (18 spell, 17 race-resistant, 7 effect, 5 greater)
  - `ArmorEnchantmentEntry.armor_properties` returns correct CProps per type
  - `ArmorSpec.enchant_with()` sets expected properties on armor object
  - Cursed flag propagates correctly

**Acceptance**:
- `ArmorEnchantmentRegistry` loads all 47 entries from fixture `onhitscriptdesc.cfg`
- `ArmorSpec.enchant_with(ArmorEnchantment.OF_BUNGLING)` sets `OnHitScript=":combat:spellonhit"`, `HitWithSpell=1`
- All 13+ onhit `.src` scripts present in `tests/fixtures/shard/`
- No regression in existing tests

---

### M31 — Spell-Type Armor OnHitScripts

**Goal**: Execute `spellonhit.src` through the interpreter for all 18 spell-type armor enchantments. When a defender wears spell-enchanted armor and is hit, the enchantment's spell fires at the attacker (or at the defender if cursed).

**Context**: `spellonhit.src` reads `ChanceOfEffect`, `HitWithSpell`, `EffectCircle`, and `Cursed` from the armor, rolls a chance check, then launches the referenced spell script via `Start_Script(GetScript(spellid), ...)`. The spell scripts themselves are already executable from V3.

**Deliverables**:

- **Stub discovery** — execute `spellonhit.src` and identify any missing POL built-ins. Likely candidates:
  - `GetScript(spellid)` — eScript function in `spelldata.inc` mapping ID to script path. Verify it's in the include chain; if not, ensure `spelldata.inc` is parsed.
  - Class check functions (`IsThief`, `IsBard`, `IsMage`, `ClassWeapons`, `GetClass`) — eScript functions in `classes.inc`. Should already be in the include chain. The class weapon check gates whether the enchantment fires (Thieves/Bards/Mages restricted to class weapons).

- **`__RecordSimulatorMetric` instrumentation** in `spellonhit.src`:
  - `onhit_triggered`: 1 when spell fires
  - `onhit_spell_id`: which spell was cast
  - `onhit_circle`: effective circle
  - `onhit_cursed`: 0/1
  - `onhit_target`: "attacker" or "defender"

- **Integration tests** (per-enchantment):
  - All 18 spell-type enchantments execute without error
  - Spell fires when chance check passes (seed-controlled)
  - Spell does NOT fire when chance check fails
  - Cursed variant: spell targets defender instead of attacker
  - Physical damage (`ApplyTheDamage`) always applied regardless of spell trigger
  - Class weapon restriction: Mage with out-of-class weapon → enchantment skipped
  - Property-based: higher `ChanceOfEffect` → higher trigger rate over N iterations
  - At least 3 spell enchantments validated end-to-end: Clumsy (circle 1), Fireball (circle 3), Flame Strike (circle 7)

**Acceptance**:
- `execute_hit()` with spell-enchanted armor produces `HitResult` with onhit metrics
- 18/18 spell-type enchantments execute with `success=True`
- Cursed armor correctly inverts spell target
- Physical damage is always applied (onhit script calls `ApplyTheDamage`)
- No regression in existing tests

**Depends on**: M30

---

### M32 — Slayer & Effect Armor OnHitScripts

**Goal**: Execute slayer (race-resistant) and effect onhit scripts. 17 slayer enchantments via `raceresistonhit.src`, 7 effect enchantments via their individual scripts.

**Context**: Slayer armor doubles damage when the attacker's race matches the armor's `ProtectedType`. Effect scripts modify damage or apply side effects (piercing bypasses AR, banish kills summons, poison applies poison, drains transfer stats, blinding reduces visibility).

**Deliverables**:

- **`raceresistonhit.src` execution** (17 slayer enchantments):
  - Reads `armor.ProtectedType` and `attacker.Type` (or "Human" for players)
  - Match + NOT cursed: 2x damage bonus (or halves if already reduced)
  - Match + cursed: 2x damage to defender
  - No match: normal damage
  - `__RecordSimulatorMetric` instrumentation: `onhit_slayer_match`, `onhit_slayer_type`, `onhit_slayer_damage_multiplier`

- **Effect script execution** (7 enchantments, ~7 distinct scripts):
  - `piercingonhit.src` — bypasses AR (recalculates with piercing flag)
  - `banishonhit.src` — kills summoned/animated creatures, teleports + kills
  - `poisononhit.src` — applies poison to target (level from `armor.Poisonlvl`)
  - `manadrainonhit.src` — transfers mana from drained to drainer (based on absorbed damage)
  - `staminadrainonhit.src` — transfers stamina from drained to drainer
  - `blindingonhit.src` — applies light level effect (ChanceOfEffect roll)
  - `bouncingonhit.src` — teleports attacker (ChanceOfEffect roll) or 1.5x magic damage if cursed
  - `__RecordSimulatorMetric` instrumentation per script: `onhit_effect_type`, `onhit_effect_triggered`, relevant damage/drain values

- **New stubs** (discovered during execution):
  - `MoveCharacterToLocation` / `MoveObjectToLocation` — no-op in simulation (banish teleport, bouncing teleport)
  - `ApplyPoison` or poison application — record as side effect
  - `GetMana`, `SetMana`, `GetStamina`, `SetStamina` — should already be stubbed from V1
  - `SetLightLevel` — no-op (visual effect)

- **Integration tests**:
  - Slayer match: attacker race matches armor → damage doubled
  - Slayer mismatch: no bonus
  - Slayer cursed: damage doubled on defender
  - Each effect script executes without error
  - Piercing: ignores AR (rawdamage > normal rawdamage for same basedamage)
  - Mana/stamina drain: stat transfer recorded in metrics
  - Poison: `onhit_poison_applied` metric recorded
  - Cursed variants tested for each effect

**Acceptance**:
- 17/17 slayer enchantments execute with `success=True`
- 7/7 effect enchantments execute with `success=True`
- Slayer match correctly doubles damage
- Cursed variants invert target for all 24 enchantments
- Physical damage always applied
- No regression in existing tests

**Depends on**: M30

---

### M33 — Greater Armor OnHitScripts

**Goal**: Execute the 5 greater armor onhit scripts. These are the most complex — they involve spell damage calculations, paralyze effects, astral storms, and multi-element attacks.

**Context**: Greater enchantments are rare, powerful armor effects. Each has a unique script with its own damage model:

| # | Name | Script | Mechanic |
|---|---|---|---|
| 43 | Elemental Fury | `trielementalonhit.src` | Roll ChanceOfEffect → `CalcSpellDamage` × 0.5 → resist → class penalty (Mage/Paladin/MA 0.7x) → random element (Fire/Lightning/Water) |
| 44 | Shifting | `deflectiononhit.src` | Roll ChanceOfEffect → reduce rawdamage to 60% if armor absorbed some |
| 45 | Avenging | `avengingonhit.src` | Calculate absorbed = `basedamage - rawdamage` → retaliate with `absorbed × power / 100` (PvP) or `/ 30` (NPC). Class-gated (not Paladin/Mage/MA). |
| 46 | Shadow's Cloak | `invisibleonhit.src` | Roll ChanceOfEffect → set hidden=1 on target |
| 47 | Wind's Breath | `dualplanaronhit.src` | Roll ChanceOfEffect → paralyze + Astral Storm spell damage. Complex immunity checks (magic resist, holy protection, free action). |

**Deliverables**:

- **Execute all 5 greater scripts** through the interpreter
- **`__RecordSimulatorMetric` instrumentation** per script:
  - Tri-elemental: `onhit_trielemental_triggered`, `onhit_trielemental_element`, `onhit_trielemental_damage`
  - Deflection: `onhit_deflection_triggered`, `onhit_deflection_reduction`
  - Avenging: `onhit_avenging_triggered`, `onhit_avenging_retaliation`
  - Invisible: `onhit_invisible_triggered`
  - Dual-planar: `onhit_dualplanar_triggered`, `onhit_dualplanar_paralyze`, `onhit_dualplanar_damage`

- **New stubs** (discovered during execution):
  - `SetHidden` / `hidden` property — no-op for invisibility
  - `SetParalyzed` / paralysis system — record as side effect metric
  - `CreateDamagePacket` / AoE damage helpers (tri-elemental, dual-planar) — verify scope
  - `PerformAction` / visual effects — no-op

- **Integration tests**:
  - Each greater script executes without error
  - Tri-elemental: spell damage dealt when triggered, random element recorded, class penalty verified
  - Deflection: rawdamage reduced to 60% when armor absorbed
  - Avenging: retaliation proportional to absorbed damage, class-gated
  - Invisible: hidden flag set (or metric recorded)
  - Dual-planar: paralyze + astral damage applied
  - Cursed variants tested for each
  - Property-based: higher ChanceOfEffect → higher trigger rate

**Acceptance**:
- 5/5 greater enchantments execute with `success=True`
- Tri-elemental deals spell damage with correct element
- Deflection reduces rawdamage only when armor absorbed
- Avenging retaliates proportional to absorption
- Dual-planar applies both paralyze and damage
- Cursed variants invert target
- No regression in existing tests

**Depends on**: M30, M31 (spell execution reuse)

---

### M34 — Stats, Reporting, Notebook & Documentation

**Goal**: Aggregate armor enchantment metrics into stats, add reporting support, create a new notebook comparing armor enchantments, and update documentation.

**Deliverables**:

**Stats**:
- Extend `RatioStats` with:
  - `onhit_trigger_rate` — fraction of hits where armor enchantment fired
  - `onhit_trigger_rate_on_hit` — conditional: of successful hits, how often onhit triggered
- Extend `aggregate_cell()` to count `onhit_triggered` metrics
- Additional damage from armor enchantments tracked in `DamageStats` (mean, median, etc.)

**Reporting**:
- `summary_table` / `comparison_table` support `onhit_trigger_rate`, additional damage columns
- `damage_histogram` correctly includes/separates onhit additional damage
- New: `armor_enchantment_comparison` chart — compare enchantments by trigger rate, additional damage, effective DPS contribution

**Notebook**:
- `09_casting_armour.ipynb` — Armor enchantment analysis:
  - Spell-type: compare Clumsy vs Fireball vs Flame Strike armor (trigger rate, spell damage, effective DPS bonus)
  - Slayer-type: race-matched vs unmatched damage
  - Effect-type: piercing impact on AR bypass, drain stat transfers
  - Greater-type: tri-elemental damage, avenging retaliation curves
  - Cursed vs normal comparison
  - ChanceOfEffect sweep (10%–90% trigger rate impact on effective damage)

**Documentation**:
- Update `concepts.md` — casting armour mechanics, OnHitScript dispatch, cursed armor
- Update `combatant-specs.md` — `ArmorSpec.enchant_with()` API, armor enchantment properties
- Update `results.md` — onhit trigger metrics, additional damage tracking
- Update `examples.md` — casting armour cookbook examples
- Update `reporting.md` — new armor enchantment charts

**Acceptance**:
- `onhit_trigger_rate` computed correctly (verified against ChanceOfEffect / 100)
- Notebook renders and produces meaningful visualizations for all 4 enchantment types
- Documentation covers `ArmorEnchantment` enum, `ArmorSpec.enchant_with()`, all new metrics
- Summary/comparison tables include armor enchantment columns
- No regression in existing tests

**Depends on**: M31, M32, M33

---

## Milestone Dependencies

```
M30 (Config, Registry, API, Fixtures)
  │
  ├──────────────────┐
  ▼                  ▼
M31 (Spell OnHit)  M32 (Slayer + Effect OnHit)
  │                  │
  ├──────────────────┤
  ▼                  │
M33 (Greater OnHit) ─┘
  │
  ▼
M34 (Stats, Reporting, Notebook, Docs)
```

M31 and M32 can be worked in parallel after M30. M33 depends on M31 (spell execution reuse for tri-elemental and dual-planar). Everything else is sequential.

---

## Milestone Summary

| ID | Description | Key deliverable | Est. tests |
|---|---|---|---|
| M30 | Config, Registry, API, Fixtures | `ArmorEnchantment` enum, `ArmorEnchantmentRegistry`, `ArmorSpec.enchant_with()` | ~30 |
| M31 | Spell-Type OnHitScripts | 18 spell enchantments via `spellonhit.src` | ~40 |
| M32 | Slayer & Effect OnHitScripts | 17 slayer + 7 effect enchantments | ~50 |
| M33 | Greater OnHitScripts | 5 greater enchantments (complex scripts) | ~30 |
| M34 | Stats, Reporting, Notebook, Docs | `09_casting_armour.ipynb`, updated docs | ~20 |
| **Total** | | **47 armor enchantments, 1 notebook** | **~170** |

## Key Risks

1. **`GetScript()` resolution** — `spellonhit.src` calls `GetScript(spellid)` to map spell ID to script path. This is an eScript function in `spelldata.inc`. If it's not already in the include chain, it needs to be added. V3 may have already solved this.

2. **Class weapon gating** — `spellonhit.src` checks `IsThief`/`IsBard`/`IsMage` and `ClassWeapons` to gate enchantment firing. These are eScript functions in `classes.inc`. They should execute through the interpreter, but depend on correctly configured class properties on the combatant.

3. **Greater script complexity** — `dualplanaronhit.src` (161 lines) has paralyze mechanics, immunity checks, and astral storm sub-scripts. This is the most complex single onhit script and may need additional stubs.

4. **Spell damage overlap with V3** — Spell-type armor enchantments fire the same spell scripts as V3 spell casting. The spells execute with the defending character's stats as the caster, not the attacking character's. This means spell damage from armor depends on the defender's Magery, not the attacker's — a potentially counter-intuitive but correct behavior that needs clear documentation.
