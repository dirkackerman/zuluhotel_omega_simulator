# Spell Catalog Reference

This page lists all damage spells supported by the V3 spell simulation, organized by school and annotated with reclassifications discovered during implementation.

## Using Spells in Simulations

```python
from omega.config.spells import Spell
from omega.simulation import CombatantSpec, SpellScenario, run_spell_scenario

caster = CombatantSpec(skills={25: 100, 16: 100}, stats=(50, 100, 50))
target = CombatantSpec(skills={26: 50}, stats=(100, 50, 50))

scenario = SpellScenario(
    caster=caster, target=target,
    spell_id=Spell.FIREBALL, iterations=1000,
)
cell = run_spell_scenario(scenario, shard=shard)
```

Spell IDs can be passed as `Spell` enum members or raw integers.

## Spell Sets

| Set | Count | Purpose |
|---|---|---|
| `CASTABLE_SPELL_IDS` | 29 | All spells with executable scripts (damage + non-damage) |
| `DAMAGE_SPELL_IDS` | 26 | Spells that deal direct damage (for damage analysis) |
| `NON_DAMAGE_SPELL_IDS` | 3 | Reclassified non-damage spells (AR debuff, CC, pet mechanic) |

Import from `omega.config.spell_registry`.

---

## Standard Spells (11 damage)

| Spell | Enum | ID | Circle | Element | Type |
|---|---|---|---|---|---|
| Magic Arrow | `Spell.MAGIC_ARROW` | 5 | 1 | Earth | Single |
| Harm | `Spell.HARM` | 12 | 2 | Water | Single |
| Fireball | `Spell.FIREBALL` | 18 | 3 | Fire | Single |
| Lightning | `Spell.LIGHTNING` | 30 | 4 | Air | Single |
| Mind Blast | `Spell.MIND_BLAST` | 37 | 5 | Magic | Single |
| Energy Bolt | `Spell.ENERGY_BOLT` | 42 | 6 | Air | Single |
| Explosion | `Spell.EXPLOSION` | 43 | 6 | Fire | AoE |
| Chain Lightning | `Spell.CHAIN_LIGHTNING` | 49 | 7 | Air | AoE |
| Flame Strike | `Spell.FLAME_STRIKE` | 51 | 7 | Fire | Single |
| Meteor Swarm | `Spell.METEOR_SWARM` | 55 | 7 | Fire+Earth | AoE |
| Earthquake | `Spell.EARTHQUAKE` | 57 | 8 | Earth | AoE |

## Necromancy Spells (5 damage + 3 non-damage)

### Damage Spells

| Spell | Enum | ID | Circle | Element | Type |
|---|---|---|---|---|---|
| Spectre's Touch | `Spell.SPECTRES_TOUCH` | 68 | 21 | Necro | Single |
| Abyssal Flame | `Spell.ABYSSAL_FLAME` | 69 | 22 | Fire/Necro | AoE |
| Sorcerer's Bane | `Spell.SORCERERS_BANE` | 73 | 23 | Necro | Single |
| Wyvern Strike | `Spell.WYVERN_STRIKE` | 76 | 23 | Necro | Single |
| Kill | `Spell.KILL` | 77 | 24 | Necro | Single |

### Non-Damage Spells (reclassified)

| Spell | Enum | ID | Actual Behavior |
|---|---|---|---|
| Decaying Ray | `Spell.DECAYING_RAY` | 67 | AR debuff (`DotempMod("ar", ...)`), no damage calls |
| Sacrifice | `Spell.SACRIFICE` | 71 | AoE pet sacrifice mechanic |
| Wraith's Breath | `Spell.WRAITHS_BREATH` | 72 | AoE paralysis/CC (`mobile.frozen := 1`) |

These are in `CASTABLE_SPELL_IDS` (their scripts execute) but not in `DAMAGE_SPELL_IDS`.

## Earth Spells (5 damage)

| Spell | Enum | ID | Circle | Element | Type |
|---|---|---|---|---|---|
| Shifting Earth | `Spell.SHIFTING_EARTH` | 83 | 25 | Earth | Single |
| Call Lightning | `Spell.CALL_LIGHTNING` | 85 | 26 | Air | Single |
| Gust of Air | `Spell.GUST_OF_AIR` | 89 | 27 | Air | Single |
| Rising Fire | `Spell.RISING_FIRE` | 90 | 27 | Fire | AoE |
| Ice Strike | `Spell.ICE_STRIKE` | 92 | 28 | Water | Single |

**Note**: Gust of Air was originally classified as AoE but uses `CanTargetSpell` (not `CanTargetArea`) with no foreach loop — it is single-target.

## Holy Spells (5 damage)

| Spell | Enum | ID | Circle | Element | Type |
|---|---|---|---|---|---|
| Holy Bolt | `Spell.HOLY_BOLT` | 170 | 26 | Holy | Single |
| Wrath of God | `Spell.WRATH_OF_GOD` | 174 | 27 | Holy | Single |
| Divine Fury | `Spell.DIVINE_FURY` | 175 | 27 | Holy | Single |
| Astral Storm | `Spell.ASTRAL_STORM` | 176 | 27 | Holy | AoE |
| Apocalypse | `Spell.APOCALYPSE` | 181 | 28 | Holy | AoE |

### Conditional Damage Notes

- **Holy Bolt**: Alignment-gated — NPC caster vs player target deals damage; NPC vs NPC or player vs good NPC heals instead.
- **Wrath of God**: Karma-based damage — damage scales with karma difference between caster and target. Equal karma produces 0 damage.
- **Astral Storm**: Primarily a paralysis/CC spell. Damage is dealt via a `start_script("astralstorm_damage")` sub-script (5x `ApplyPlanarDamage` at `CalcSpellDamage/8` each).

---

## AoE Spell Patterns

| Pattern | Spells | Description |
|---|---|---|
| Standard AoE | Explosion, Chain Lightning, Earthquake | `CanTargetArea` → `ListMobiles` → `SmartAoE` → foreach → damage |
| Dual-phase | Meteor Swarm (Fire+Earth), Rising Fire (Fire×2) | Two damage passes with sleep between phases |
| Primary + AoE | Abyssal Flame | Primary target at circle/2, then AoE secondary at circle/2 |
| Three-phase | Apocalypse | Chain lightning + earthquake + meteor effects, 24% damage per phase |

AoE spells use `circle -= 3` before the damage roll, dealing less per-target damage than single-target equivalents.

---

## Damage Formula

```
CalcSpellDamage(caster, target, circle):
    Roll:  (circle * 3)d5 + floor(Magery / 5)
    Cap:   circle * (13 + circle)
    Class: Mage bonus, Warrior penalty (ModifyWithMagicEfficiency)
    Equip: MagicPenalty reduction
    PvP:   /3 for player targets, ×1.5 for NPC targets
    AoE:   circle -= 3 before roll

Resisted(caster, target, circle, dmg):
    Chance: max(resist/6, resist - magery/4 - circle*6)
    Class:  Mage/Paladin target ↑ chance, Warrior target ↓
    Class:  Mage caster ↓ chance, Warrior caster ↑
    Effect: dmg /= 2 if resisted
    Eval:   dmg *= 1 + (evalint - resist) / 200

ApplyElementalDamage(caster, target, circle, dmg, element):
    Protection lookup per element
    Mage caster: reduce protection by level×3
    Over-protection (>100%): heal instead of damage

ApplyTheDamage(target, caster, dmg, dmgtype):
    PvP: × 0.6
    ApplyRawDamage()
```
