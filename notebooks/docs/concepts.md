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

### Not included (future versions)
- Spell casting and spell resistance (V2)
- HP tracking across multiple hits / kill-time distributions (V3)
- Buff/debuff accumulation over time (V3)
- Group combat (V3)
