# Concepts

This page explains the domain model and terminology used throughout the simulator. Read this before diving into the API reference pages.

## The simulation model

The simulator answers one question: **"Given this attacker, this defender, and this weapon — how much damage does a single hit deal?"**

It answers that question many times (hundreds or thousands) with controlled randomness, then gives you statistical summaries of the results. This lets you reason about damage distributions rather than individual lucky or unlucky rolls.

## Key terms

### Hit

A single execution of the shard's `mainhit.src` combat script. One hit represents one weapon swing connecting with a target. The script calculates damage through a multi-step pipeline (see [Damage Pipeline](#damage-pipeline) below).

### Iteration

One independent run of the hit script. Each iteration:

1. Starts from identical combatant state (stats, HP, skills — all reset)
2. Uses a unique RNG seed derived from `base_seed XOR iteration_index`
3. Produces one `HitResult` with damage values and side effects

Iterations are independent — damage from iteration 5 does not carry over to iteration 6. This is deliberate: V1 models **per-hit damage distribution**, not sustained combat over time.

### Scenario

A complete simulation definition: one attacker, one defender, N iterations, and an RNG seed. See [Scenarios](scenarios.md).

### Parameter sweep

A scenario with one or more parameters that vary across a range. For example, sweeping Tactics from 50 to 130 in steps of 10 creates 9 cells, each running the full N iterations. See [Scenarios](scenarios.md).

### Cell

One point in a parameter sweep grid. If you sweep Tactics across 9 values, you get 9 cells. Each cell holds its own `CellResult` with independent statistics.

### Seed

An integer that controls the random number generator. Same seed + same inputs = identical results. The per-iteration seed is computed as `base_seed XOR iteration_index`, so iteration 0 uses `base_seed`, iteration 1 uses `base_seed ^ 1`, and so on.

## Combatants

A combatant is either an **attacker** or a **defender**. Each has:

- **Base stats**: Strength, Dexterity, Intelligence
- **Vitals**: HP (defaults to STR x 2), Mana (defaults to INT), Stamina (defaults to DEX)
- **Skills**: A dictionary mapping skill IDs to display values (0–130). Internally stored as tenths (0–1300).
- **Class levels**: Zero or more class memberships (e.g., Warrior level 5, Mage level 3). Classes provide damage bonuses and resistances.
- **Equipment**: A weapon (attacker) and armor (defender)

The `is_npc` flag distinguishes players from NPCs. This affects PvP scaling and certain formula branches in the combat scripts.

See [Combatant Specs](combatant-specs.md) for the full field reference.

## Hit check (POL core)

Before the hitscript runs, POL's C++ core performs a **hit/miss check** — a swing must "connect" before any damage calculation begins.

### Formula

```
hit_chance = (attacker_skill + 50) / (2 × (defender_skill + 50))
```

A random float `[0, 1)` is rolled. If `roll < hit_chance`, the swing hits and the hitscript executes. Otherwise it's a miss — zero damage, no side effects, no script execution.

### Weapon skill resolution

- **Attacker**: Uses the skill matching the weapon's `Attribute` field (e.g., Swordsmanship for swords, Mace Fighting for maces). Falls back to **Wrestling** if the weapon has no attribute or the attacker is unarmed.
- **Defender**: Uses the skill matching their *equipped weapon's* attribute. Falls back to **Wrestling** if unarmed or no weapon equipped.

### Example hit rates

| Attacker Skill | Defender Skill | Hit Chance |
|:-:|:-:|:-:|
| 100 | 0 | 100% (capped) |
| 100 | 50 | 75.0% |
| 100 | 100 | 50.0% |
| 80 | 100 | 43.3% |
| 130 | 130 | 50.0% |
| 50 | 100 | 33.3% |

Against NPCs with no weapon skill (Wrestling = 0), skilled attackers always hit. PvP and fights against skilled NPCs produce meaningful miss rates.

### Two-tier statistics

Because misses produce zero damage, the simulator reports two tiers of statistics:

- **Overall stats** (`mean`, `spell_strike_rate`, `drain_mean`, etc.) — computed over **all swings** including misses. These represent the expected value per swing attempt.
- **On-hit stats** (`mean_on_hit`, `spell_strike_rate_on_hit`, `drain_mean_on_hit`, etc.) — computed over **hits only**. These show what happens when a swing connects.

For example, if you have a 50% hit rate and deal 20 damage on each hit:
- `mean` = 10.0 (overall expected damage per swing)
- `mean_on_hit` = 20.0 (damage when you connect)

### Opting out with `core_hit_check`

The `execute_hit()` function accepts a `core_hit_check` parameter (default `True`). Setting it to `False` bypasses the hit/miss roll — every swing connects. This is useful for:

- **Unit testing the damage pipeline** — isolating formula logic from RNG hit variance
- **Analyzing "on hit" behavior** — studying enchantment effects without miss dilution
- **Matching pre-V1.5 behavior** — earlier versions didn't model the hit check

```python
result = execute_hit(
    parse_results, attacker, defender, weapon, armor,
    base_damage=25,
    core_hit_check=False,  # skip hit/miss roll
)
```

In `run_scenario()` / `run_sweep()`, the hit check is always enabled (there is no parameter to disable it). This ensures simulation results reflect realistic combat conditions.

## Damage pipeline

The shard's combat scripts calculate damage through these stages:

```
POL Core Hit Check
    │  hit_chance = (atk_skill + 50) / (2 × (def_skill + 50))
    │  miss → 0 damage, no script execution
    │
    ▼
Weapon Dice Roll (e.g., 3d6+2)
    │
    ▼
Base Damage (random roll, 5–20 for 3d6+2)
    │
    ▼
┌─── RecalcDmg() ───────────────────────┐
│                                        │
│  Physical path:                        │
│    1. Slayer multiplier                │
│       (double damage if weapon's       │
│        SlayType matches target Type)   │
│    2. Class bonus                      │
│       (Warrior: +CLASSE_BONUS per lvl) │
│    3. Skill scaling                    │
│       (Anatomy + Tactics factor)       │
│    4. Shield absorption                │
│    5. Armor Rating reduction           │
│    6. Protection enchant               │
│    7. Mace fighting effects            │
│                                        │
│  Astral path (V2):                     │
│    Spirit Speak scaling → class bonus  │
│    → meditation resist → astral armor  │
│    → 50% reduction → mana/stam drain   │
│                                        │
└────────────────────────────────────────┘
    │
    ▼
Post-Mitigation Damage
    │
    ▼
┌─── Elemental Damage (V1.5) ──────────┐
│  If weapon has ElementalDamage CProp:  │
│    1. Split damage by element type     │
│       (fire, air, earth, water, etc.)  │
│    2. Check defender resistances       │
│       (Protection_{Element} CProps)    │
│    3. Apply resistance reduction       │
│    4. Sum physical + elemental totals  │
└────────────────────────────────────────┘
    │
    ▼
┌─── Enchantment Sub-Scripts (V1.5) ───┐
│  If weapon has a hitscript:            │
│    start_script() dispatches to:       │
│    - spellstrikescript (spell on hit)  │
│    - slayerscript (bonus vs type)      │
│    - effect scripts (pierce, drain)    │
│    - greater scripts (planar, void)    │
│  Reactive armor reflects damage back   │
└────────────────────────────────────────┘
    │
    ▼
┌─── ApplyTheDamage() ──────────────────┐
│  1. PvP scaling (if both are players)  │
│     Two-stage: 0.4 x 0.6 = 0.24 net  │
│  2. Tamed creature multiplier          │
│  3. Ally scaling                       │
│  4. ApplyRawDamage() → subtract HP     │
└────────────────────────────────────────┘
    │
    ▼
Final Damage (recorded in HitResult)
```

### What the simulator captures

At each stage, the simulator records:

| Value | Where it comes from | Available in |
|-------|-------------------|--------------|
| Hit/miss | POL core hit check | `HitResult.final_damage > 0` (hit) or `== 0` (miss) |
| Base damage | Weapon dice roll | `HitResult.base_damage` |
| Final damage | `ApplyRawDamage()` call | `HitResult.final_damage` |
| Absorbed | `__RecordSimulatorMetric("absorbed", ...)` | `HitResult.absorbed` |
| Side effects | POL stub calls (poison, paralyze, equipment damage) | `HitResult.side_effects` |
| Elemental breakdown | `__RecordSimulatorMetric("list:elemental_applied", ...)` | `HitResult.metrics["elemental_applied"]` |
| Enchantment effects | Sub-script execution (spell strike, drain, etc.) | `HitResult.side_effects` |
| Metrics | `__RecordSimulatorMetric(...)` calls in scripts | `HitResult.metrics` |
| Debug messages | `SendSysMessage()` calls in the script | Python logging output |

See [Results](results.md) for interpreting these values and [Messages and Metrics](messages-and-metrics.md) for capturing debug output.

## State lifecycle

### Per-iteration reset

Before each iteration, the simulator:

1. Restores attacker and defender to their original stats/HP (via snapshot/restore)
2. Resets weapon and armor durability
3. Clears the `SimulationContext` (side effects, damage counters, metrics)
4. Sets a new RNG seed (`base_seed XOR iteration_index`)

This means each iteration is a clean, independent sample. Side effects like poison or equipment damage are **recorded** but do not accumulate.

### Executor reuse

The eScript interpreter (`Executor`) is built once per scenario and reused across all iterations. Global variables defined in the eScript source are snapshot after initial load and restored before each run via `executor.reset()`. This is much cheaper than re-parsing the scripts each time.

### Config caching

Config files (npcdesc.cfg, combat settings, etc.) are parsed once and cached in the `SimulationContext`. They persist across iterations within a single scenario run.

## How eScript runs in the simulator

The simulator doesn't run eScript on a POL server. Instead:

1. The shard's `.src` and `.inc` files are **parsed** using an ANTLR4-based parser into syntax trees
2. A **tree-walking interpreter** (`Executor`) executes the parsed scripts
3. POL engine functions (`SendSysMessage`, `GetObjProperty`, `ApplyRawDamage`, etc.) are replaced with **Python stubs** that simulate the engine's behavior
4. The stubs read and write state on Python objects (`Mobile`, `Weapon`, `Armor`) that mirror POL's game objects

This means the simulator executes the **real shard scripts** — the same `mainhit.src`, `hitscriptinc.inc`, `damages.inc`, etc. that run on the live server. Formula changes in the shard scripts are immediately reflected in simulation results.

See [Runtime](runtime.md) for details on how the interpreter, stubs, and context work together.

## Virtual time & DPS (V2)

The simulator models POL's swing timer to compute **damage per second (DPS)** — the primary metric for weapon and build comparison.

### Swing delay formula

Source: `Character::schedule_attack()` in POL's `charactr.cpp:2832–2881`. Clock unit: 1 POL clock = 10ms.

**Speed-based path** (all ZH weapons):
```
clocks = 1_500_000 / ((DEX + 100) × SPEED)
delay_ms = clocks × 10
```

**Delay-based path** (when `weapon.delay > 0`):
```
delay_sum = max(0, weapon.delay + char.delay_mod)
clocks = (delay_sum × 100) / 1000
delay_ms = clocks × 10
```

Both paths then apply **SwingSpeedIncrease** (from equipment/enchantments):
```
modifier = clamp(SSI_sum / 100, min=-0.99)
clocks = round(clocks / (1 + modifier))
```

The `round()` uses C++ semantics (half away from zero), not Python's banker's rounding.

### DPS metrics

Each `CellResult` includes a `TimingStats` object with:

| Field | Description |
|-------|-------------|
| `swing_delay_ms` | Milliseconds between swings |
| `swings_per_second` | Attack rate: `1000 / swing_delay_ms` |
| `dps_mean` | Mean DPS over all swings (including misses) |
| `dps_on_hit` | DPS considering only hits |
| `effective_dps` | `hit_rate × mean_on_hit × swings_per_second` |

DPS columns are available in `summary_table()` and `comparison_table()`:
```python
rows = summary_table(result, stats=["mean", "dps_mean", "swing_delay_ms", "effective_dps"])
```

### DPS plots

```python
from omega.reporting.plots import dps_vs_parameter, dps_comparison

# DPS curve across a parameter sweep (dual-axis: damage + delay)
dps_vs_parameter(result, "attacker.skills.27", title="DPS vs Tactics")

# DPS bar chart comparing named scenarios
dps_comparison({"Sword": sword_result, "Mace": mace_result})
```

## Astral damage path (V2)

Astral damage is a completely separate pipeline from physical damage. It drains **mana and stamina** instead of HP, and uses **Spirit Speak** and **Meditation** instead of STR and AR.

### When the astral path triggers

A weapon with the `Astral` property set (`GetObjProperty(weapon, "Astral") == 1`) routes through `RecalcAstralDmg()` instead of `RecalcPhysicalDmg()`.

### Astral pipeline

```
Base Damage (weapon dice roll)
    │
    ▼
Spirit Speak Scaling
    basedamage *= (SpiritSpeak + 50 + INT×0.2) / (Tactics + 50 + STR×0.2)
    │
    ▼
EvalInt Multiplier
    basedamage *= 1 + EvalInt × 0.002
    │
    ▼
Class Bonus (attacker)
    Mage vs NPC: ClasseBonusByLevel(level - 2)
    Mage vs Player: ClasseBonusByLevel(level - 2)
    │
    ▼
Class Penalty (defender)
    Warrior (non-Mage): basedamage *= 5/6
    │
    ▼
Meditation Resistance
    if Random(1000) >= chance: absorbed via meditation
    │
    ▼
Astral Armor
    ar = Astral_property × 25 × armor.ar
    absorbed = basedamage × Pow(ar/5, 0.5) × 0.05
    │
    ▼
50% Base Reduction
    rawdamage = basedamage × 0.5
    │
    ▼
ApplyTheAstralDamage()
    Drains mana first, overflow to stamina
    Does NOT call ApplyRawDamage (no HP change)
```

### Key differences from physical

| Aspect | Physical | Astral |
|--------|----------|--------|
| Resource drained | HP | Mana → Stamina |
| Scaling skill | Tactics + Anatomy | Spirit Speak + EvalInt |
| Scaling stat | STR | INT |
| PvP basedamage scaling | 0.4× | None |
| Armor system | Physical AR | Astral property × 25 × AR |
| Base reduction | None | 50% |
| Incapacity | Death | Frozen (both mana + stamina = 0) |

### Setting up an astral weapon

```python
weapon = WeaponSpec(
    name="Astral Blade",
    damage="3d6+2",
    properties={"Astral": 1},
)
```

The attacker should have Spirit Speak and EvalInt skills for meaningful damage. The defender's Meditation skill provides resistance.

## Spell casting pipeline (V3)

Spell casting uses a different entry point from weapon hits, but shares the damage application stage.

```
TryToCast (player mode only)
    │  CheckSkill(Magery, circle×10)
    │  fizzle → 0 damage, no mana cost
    │
    ▼
CalcSpellDamage
    │  dice roll → cap check → efficiency penalty → PvP /3
    │
    ▼
Resisted() check
    │  Chance based on EvalInt vs MagicResistance
    │  Class modifiers (Mage, Warrior, Paladin)
    │  resist → damage halved
    │
    ▼
ApplyElementalDamage / ApplyElementalDamageNoResist
    │  Element-specific protection check
    │  Over-protection (>100%) → healing
    │
    ▼
ApplyTheDamage()
    │  PvP 0.6× scaling
    │  ApplyRawDamage() → subtract HP
    │
    ▼
SpellResult (recorded)
```

**NPC mode**: Bypasses TryToCast entirely -- no fizzle check, no mana cost. Simulates how NPCs cast spells.

## Spell resistance & class modifiers (V2)

Spell resistance (`Resisted()` in the shard scripts) determines whether spell damage is reduced and by how much. Class membership significantly modifies resistance chances.

### Base resistance formula

```
chance = ((EvalInt - MagicResistance) / 5) + circle + 1
```

If `Random(100) < chance`, the spell is **not resisted** (full damage). Otherwise, the damage is reduced based on the EvalInt/MagicResistance ratio.

### Class modifiers

**Defender class bonuses** (higher chance = easier to resist):

| Defender class | Modifier |
|---------------|----------|
| Mage | `chance += ClasseBonusByLevel(level - 2) × 15` |
| Paladin | `chance += ClasseBonusByLevel(level - 2) × 5` |
| Mystic Archer | `chance += ClasseBonusByLevel(level - 2) × 5` |
| Warrior (non-Mage) | `chance -= ClasseBonusByLevel(level - 2) × 10`, resist halved |

**Caster class modifiers** (lower chance = harder to resist):

| Caster class | Modifier |
|-------------|----------|
| Mage | `chance -= ClasseBonusByLevel(level - 2) × 10` |
| Warrior (non-Mage) | `chance += ClasseBonusByLevel(level - 2) × 30`, resist doubled |

### Damage scaling on resist

When a spell is resisted, damage is scaled by the EvalInt/MagicResistance ratio:
- `EvalInt > MagicResistance`: damage amplified (up to ~1.35×)
- `EvalInt < MagicResistance`: damage reduced (down to floor of 1)
- `EvalInt == MagicResistance`: no change

### Metrics

Resistance events are captured in `list:resisted` metrics with fields: `dmg_before`, `dmg_after`, `chance`, `did_resist`, `circle`, `evalint`, `resist`.

## Casting armour (V3.1)

Armor pieces can have onhit scripts that fire when the wearer is struck, adding a defensive enchantment layer parallel to weapon enchantments.

### OnHitScript dispatch

When a hit connects, `DealDamage()` checks each armor piece for an `OnHitScript` property. If present, it calls `start_script()` with the armor's onhit script, passing `{attacker, defender, weapon, armor, basedamage, rawdamage}` as parameters. The onhit script is responsible for calling `ApplyTheDamage()` — the main pipeline does not apply damage when an onhit script runs.

### Armor zone selection

POL randomly selects which armor piece is hit based on zone probabilities defined in `armrzone.cfg`:

| Zone | Probability |
|------|:-:|
| Body | 44% |
| Arms | 14% |
| Head | 14% |
| Legs | 14% |
| Neck | 7% |
| Hands | 7% |

Only the armor piece covering the selected zone is checked for an onhit script. If no armor covers that zone, or the armor has no onhit script, normal damage processing occurs.

### Cursed armor

Armor can be marked as cursed via the `Cursed` CProp. Cursed armor inverts the onhit target — spell and effect enchantments that normally target the attacker instead target the defender (the armor wearer). This turns defensive enchantments into self-inflicted penalties.

### Armor enchantment types

47 armor enchantments across 4 categories:

| Category | Count | Example | Behavior |
|----------|:-----:|---------|----------|
| Spell | 18 | Of Daemon's Breath | Casts a spell on the attacker when hit |
| Race-Resistant | 17 | Silver (Undead) | Bonus defense against matching creature type |
| Effect | 7 | Of Piercing | Special effect on the attacker (stun, drain, blind) |
| Greater | 5 | Of Planar Fury | Dual-element damage to the attacker |

## What the simulator covers

### V1 + V1.5 (current)
- POL core hit/miss check (weapon skill-based accuracy)
- Physical weapon damage (full pipeline from dice roll to HP reduction)
- Slayer weapon bonus
- Class bonuses (all 10 classes)
- Skill scaling (weapon skill, Tactics, Anatomy)
- Armor Rating absorption
- PvP damage scaling
- Side effect recording (poison, paralyze, equipment damage)
- Deterministic RNG for reproducibility
- Elemental weapon damage (fire, air, earth, water, necro, holy, poison, acid) with resistance checks
- Weapon enchantment sub-scripts via `start_script()` — spell strike, slayer, effect, and greater enchantments
- Reactive armor (reflects physical damage back to attacker)
- `Enchantment` and `Spell` IntEnum types for type-safe weapon configuration
- `WeaponSpec.enchant_with()` convenience method for applying enchantments

### V2 additions
- Virtual time calculation — POL-conformant swing delay for DPS metrics
- Astral damage path — Spirit Speak scaling, meditation resistance, astral armor, 50% reduction
- Spell resistance with class modifiers — Mage, Warrior, Paladin modify resist chance
- Comprehensive stub audit against POL C++ source (60+ stubs verified)

### V3.1 additions
- Casting armour (armor onhit scripts) — spell, race-resistant, effect, and greater enchantments on armor
- `ArmorEnchantment` enum (47 members) with `ArmorSpec.enchant_with()` convenience method
- Armor zone selection based on `armrzone.cfg` probabilities
- Cursed armor (inverts onhit target from attacker to defender)

### V3 additions
- Direct spell casting via `SpellScenario` and `run_spell_scenario()`
- 29 damage spells across 4 schools (Standard, Necromancy, Earth, Holy)
- Full spell pipeline: CheckSkill (fizzle) → CalcSpellDamage → Resisted → Protection → ApplyTheDamage
- Spell-specific stats: fizzle rate, resist rate, on-cast damage, casting DPS
- New plots: `spell_comparison()`, `fizzle_rate_vs_parameter()`
- 3 new notebooks (06, 07, 08) + spell sections in existing notebooks

### Not included (future versions)
- HP tracking across multiple hits / kill-time distributions (V4)
- Buff/debuff accumulation over time (V4)
- Group combat (V4)
