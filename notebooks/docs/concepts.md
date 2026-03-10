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

## Damage pipeline

The shard's combat scripts calculate damage through these stages:

```
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
│  Astral path (not in V1):             │
│    Spirit Speak, Meditation resist,    │
│    astral armor, 50% base reduction    │
│                                        │
└────────────────────────────────────────┘
    │
    ▼
Post-Mitigation Damage
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
| Base damage | Weapon dice roll | `HitResult.base_damage` |
| Final damage | `ApplyRawDamage()` call | `HitResult.final_damage` |
| Absorbed | `__RecordSimulatorMetric("absorbed", ...)` | `HitResult.absorbed` |
| Side effects | POL stub calls (poison, paralyze, equipment damage) | `HitResult.side_effects` |
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

## What V1 does and doesn't simulate

### Included
- Physical weapon damage (full pipeline from dice roll to HP reduction)
- Slayer weapon bonus
- Class bonuses (all 10 classes)
- Skill scaling (weapon skill, Tactics, Anatomy)
- Armor Rating absorption
- PvP damage scaling
- Side effect recording (poison, paralyze, equipment damage)
- Deterministic RNG for reproducibility

### Not included (future versions)
- Elemental weapon damage (V1.5)
- Weapon enchantment sub-scripts via `start_script()` (V1.5)
- Spell casting and spell resistance (V2)
- HP tracking across multiple hits / kill-time distributions (V3)
- Buff/debuff accumulation over time (V3)
- Group combat (V3)
