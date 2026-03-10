# Zuluhotel Omega Combat Simulator

## Project Overview

An eScript interpreter and combat simulator for the Zuluhotel Omega UO shard. Parses and executes POL eScript files to model combat scenarios (damage, resistance, mitigation) without running a full POL server. Target audience: game designers iterating on balance.

**Python 3.14** project.

## Submodules (read-only reference)

- `submodules/polserver` - POL emulator C++ source. Reference for built-in module APIs (`.em` files in `pol-core/support/scripts/`) and core combat mechanics (`pol-core/pol/mobile/charactr.cpp`, `pol-core/pol/cmbtcfg.h`).
- `submodules/escript-antlr4` - ANTLR4 lexer (`EscriptLexer.g4`) and parser (`EscriptParser.g4`) grammars for eScript. Only has a JS/TS target currently; we need a Python target or use Lark.
- `submodules/zuluhotel_omega_2.5` - The shard scripts and configs. Key combat files listed below.

## Key Shard Files (zuluhotel_omega_2.5)

### Combat Core
- `pkg/systems/combat/mainhit.src` - Main hit script entry point
- `pkg/systems/combat/crithit.src` - Critical hit calculations
- `pkg/systems/combat/include/hitscriptinc.inc` - Physical & astral damage formulas, RecalcDmg(), DealDamage()
- `scripts/include/damages.inc` - ApplyTheDamage(), damage type constants, hitlist management

### Include Dependency Tree (combat path)
```
mainhit.src
  └─ :combat:hitscriptinc (hitscriptinc.inc)
       ├─ include/client          (101KB — large utility file, only subset used by combat)
       ├─ include/dotempmods      (temporary stat modifications)
       ├─ include/classes         (class system, bonuses)
       ├─ include/damages
       │    ├─ include/attributes
       │    ├─ :karmafame:karmafame
       │    ├─ include/astralfights
       │    └─ include/math
       ├─ include/skillpoints
       └─ include/attributes
```

### Definitions & Config
- `scripts/include/attributes.inc` - 48 skill IDs, stats, vitals, caps (BASE_CAP=1300, SKILL_STAT_CAP=130)
- `scripts/include/classes.inc` - 10 classes (Warrior, Mage, Thief, Bard, Ranger, Paladin, Mystic Archer, Bladesinger, Crafter, Powerplayer), CLASSE_BONUS=1.5
- `scripts/include/constants/skillids.inc` - Skill ID constants
- `config/npcdesc.cfg` - NPC templates (stats, skills, spells, equipment)
- `config/combat.cfg` - Combat settings (key=value format)
- `config/equip.cfg` - Equipment templates (references itemdesc.cfg)
- `pkg/systems/combat/config/itemdesc.cfg` - Weapon/armor definitions (damage dice, AR, speed, skill type)
- `pkg/systems/combat/config/hitscriptdesc.cfg` - 44+ weapon enchantments
- `pkg/*/pkg.cfg` - Package metadata (Name field maps `:pkgname:` include paths)

### Config File Formats

**npcdesc.cfg** — block format:
```
NpcTemplate [name]
{
    Name/STR/INT/DEX/HITS/MANA/STAM  [value]
    [SkillName]  [level]
    Equip  [equipment_template_name]
    CProp  [PropertyName]  [type_prefix][value]   # i=int, s=string
}
```

**itemdesc.cfg** — weapon/armor blocks:
```
Weapon 0x[ObjType] { Damage [XdY+Z]; Speed [n]; Attribute [Swords|Mace|...]; AR [n]; ... }
Armor 0x[ObjType] { AR [n]; Coverage [Head|Body|...]; ... }
```

**equip.cfg** — equipment sets referencing itemdesc templates:
```
Equipment [name] { Armor [template]; Weapon [template]; Equip 0x[objtype] [color]; }
```

**NPC-by-name resolution chain**: npcdesc.cfg → equip.cfg → itemdesc.cfg

### Damage Types (bitflags from damages.inc)
FIRE=0x01, AIR=0x02, EARTH=0x04, WATER=0x08, NECRO=0x10, HOLY=0x20, POISON=0x40, ACID=0x80, PHYSICAL=0x100, MAGIC=0x200, ASTRAL=0x400, NO_RESIST=0x800

### Combat Flow
1. `mainhit.src` receives (attacker, defender, weapon, armor, basedamage, rawdamage)
2. `RecalcDmg()` branches to Physical or Astral path
3. Physical path (`RecalcPhysicalDmg` → `CalcPhysicalDamage`):
   1. Slayer multiplier (2x match, 1.5x human vs player, 1x none)
   2. Weapon quality bonus: `basedamage += (quality - 1) * 15`
   3. STR bonus (players only): `basedamage *= 1 + STR * 0.005`
   4. Class skill bonus (Warrior melee): `basedamage *= 1 + avg(Anatomy, Tactics) * 0.005`
   5. Class level bonus vs NPC: `basedamage *= ClasseSmallBonusByLevel(level - 3)`
   6. Defender class penalty (Warrior/Paladin/Mage)
   7. **PvP basedamage scaling: `basedamage *= 0.4`** (player vs player only)
   8. Shield/parry absorption
   9. AR absorption: `absorbed = basedamage * Pow(ar/5, 0.5) * 0.05`
   10. Protection modifier: `rawdamage *= 1 - PhysicalProtection * 0.05`
4. Astral: spirit speak scaling -> class bonuses -> meditation resistance -> astral armor -> 50% reduction
5. `ApplyTheDamage()`: **PvP final scaling `*= 0.6`** -> tamed multiplier -> ally scaling -> ApplyRawDamage()
6. **Net PvP multiplier: 0.4 × 0.6 = 0.24** (76% total reduction, applied in two stages)

### Class Bonus Constants (classes.inc)
- `BONUS_PER_LEVEL = 0.25` — `ClasseBonusByLevel(n) = 1 + 0.25 * n`
- `SMALL_BONUS_PER_LEVEL = 0.15` — `ClasseSmallBonusByLevel(n) = 1 + 0.15 * n`
- Level can be negative (e.g., level 1 warrior: `ClasseSmallBonusByLevel(1-3) = 0.70`)

### Combat Path Side Effects (per hit)
These occur in the real scripts but need careful handling in simulation:
- Equipment degradation (8% chance per hit, item.hp -= 1)
- Stamina drain (mace fighting)
- Poison application (weapon charges, consumed on use)
- Hitlist writes (attacker tracking with timestamps)
- War mode toggling, killer attribution, karma/fame
- start_script() calls (reactive armor, on-hit enchantments)

**V1 strategy**: Reset combatant state between each hit iteration (each hit is independent). Record side effects as output stats (e.g., "poison applied 23% of hits") but don't let them accumulate. Skip start_script() calls entirely.

## eScript Language Key Features
- Assignment: `:=` (not `=`)
- Control flow: if/elseif/endif, while/endwhile, for/endfor, foreach/endforeach, case/endcase
- Functions: `function name(params) ... endfunction`, `program name(params) ... endprogram`
- Modules: `use uo;`, `use vitals;`, `use attributes;`, `use cfgfile;`
- Includes: `include "path";`, `include ":package:file";`
- Member access: `.`, method calls, `[]` indexing
- Built-ins: GetObjProperty/SetObjProperty, CInt/CDbl, Random, ReadGameClock, TypeOf
- Scoped calls: `namespace::function()`
- No try/catch; ERROR type for error handling

## Architecture Decisions

### Approach: Interpreter scoped to combat
Build a general-purpose eScript interpreter but only stub the POL built-ins that the combat call path exercises. When an un-stubbed built-in is hit, raise a clear `NotImplemented: module::function` error. Expand stubs incrementally.

### Parser Strategy
- **Using**: ANTLR4 with Python target generated from `submodules/escript-antlr4/*.g4`
- **Note**: The POL server grammar (`submodules/polserver/lib/Parser/EscriptGrammar/`) is newer and has features the ANTLR4 grammar lacks: `uninit` literal keyword, interpolated strings (`$"..."`), class declarations (CLASS/ENDCLASS), destructuring assignments, lambdas, spread operator (`...`), `is` operator, regex literals. None of these are used in the combat scripts for V1. If future versions need these features, either patch the ANTLR4 grammar or port the POL server grammar to a Python target.

### Required Parsers (V1 deliverables)
1. **eScript parser** — main deliverable, from ANTLR4 grammar or Lark
2. **POL config file parser** — block-based `.cfg` format (npcdesc, itemdesc, equip, combat, settings)
3. **Package path resolver** — reads `pkg.cfg` files to map `:pkgname:` include prefixes to filesystem paths
4. **Dice notation parser** — `XdY+Z` format for weapon damage rolls

### Simulation Architecture
- Mock POL built-in modules — stub as needed (uo, vitals, attributes, cfgfile, os, math, basic, util)
- Property-bag system for game objects (GetObjProperty/SetObjProperty pattern)
- Deterministic RNG with seed support for reproducible simulations
- State reset between iterations (each hit is independent in V1)

### eScript Functions vs POL Built-ins
Many combat functions (e.g., `GetProtLevel`, `ApplyElementalDamageNoResist`, `ApplyTheDamage`, `IsImmunedFromThisDamageType`) are **eScript user-defined functions** in the shard scripts — NOT POL built-ins. They're already in the parsed include chain and execute through the interpreter directly. **Do not wrap them in Python overrides** (`set_override`) — function names may change when the shard is updated. Prefer instrumenting the shard scripts with `__RecordSimulatorMetric` calls to capture pipeline values.

### `__RecordSimulatorMetric` Protocol
No-op function in `client.inc`, overridden by Python in `execute_hit` via `set_override`. Three calling conventions:
- **Single KVP**: `__RecordSimulatorMetric("key", value)` → `ctx.metrics["key"] = value`
- **Struct merge**: `__RecordSimulatorMetric(struct{...})` → flattened into `ctx.metrics`
- **List append**: `__RecordSimulatorMetric("list:name", struct{...})` → appended to `ctx.metrics["name"]` (a list)

All calls must be inside `if(DEBUG_MODE)` guards, single-line, using structs for multi-KVP. The `list:` prefix protocol is explicit and self-documenting — controlled from the eScript side.

### POL Built-in Stub Strategy
~60 distinct built-in calls on the combat path, grouped by implementation effort:
- **Batch 1 — trivial (~30)**: Type casts (CInt, CDbl), math (Random, RandomInt, Pow, Max), messaging no-ops (SendSysMessage, PrintTextAbovePrivate), utilities (TypeOf, SplitWords, ReadGameClock)
- **Batch 2 — moderate (~20)**: Property bags (GetObjProperty, SetObjProperty, EraseObjProperty), stat accessors (GetStrength, GetIntelligence, GetDexterity, GetHP, GetStamina, GetMana, SetStamina, SetMana), skill queries (GetEffectiveSkill, GetAttribute), type checks (.isa/IsA), equipment (GetEquipmentByLayer)
- **Batch 3 — structural (~10)**: Config file reading (ReadConfigFile + elem access), damage application (ApplyRawDamage), script control (start_script, SetScriptController), guild lookups (FindGuild), object search (SystemFindObjectBySerial)

### Logging — first-class concern
Structured logging from day one:
- **Interpreter trace**: function entry/exit, variable assignments, branch decisions — configurable verbosity
- **Stub calls**: every POL built-in call logged with args and return value (INFO level)
- **NotImplemented hits**: logged at WARNING with full context (module, function, args, call site)
- **Simulation events**: damage calculated, damage applied, side effects triggered — structured for post-analysis
- Use Python `logging` module with named loggers per subsystem (parser, interpreter, runtime, simulation)

### Combatant Input Model
Two modes for defining a combatant:
1. **By NPC name**: Lookup from npcdesc.cfg → equip.cfg → itemdesc.cfg (full resolution chain)
2. **Inline/manual**: User specifies class, skills dict, stats, weapon damage/speed/attribute, armor AR directly

Both produce the same internal `Combatant` object. Manual mode works without config parsing (unblocks early testing).

### Scenario & Parameter Variation
- A `Scenario` holds fixed params (attacker, defender) plus one or more `Variable` ranges
- Single-variable sweep: e.g., attacker Swordsmanship 50→130, step 10
- Multi-variable grid: combinatorial (attacker class × defender class × weapon type)
- Each cell in the grid runs N iterations (configurable, default 1000)

### Testing & Reporting
- Jupyter notebooks for scenario definition and result visualization
- Statistical output per cell: mean, median, min, max, std dev, percentiles
- Distributions: damage histogram, damage breakdown by type, absorbed vs dealt
- Ratios: hit/miss/crit, poison applied, equipment break chance
- Curves: damage vs skill level, damage vs AR
- Hot reload: watch eScript files for changes, re-parse and re-run

### Validation
Hand-calculate 3-5 specific combat scenarios from the eScript source as integration test fixtures. Verify in-game where possible:
- Plain weapon vs unarmored target (baseline)
- Weapon vs armored target (AR absorption)
- Class bonus scenarios (Warrior attacker bonus, Warrior defender penalty)
- Slayer weapon vs matching creature type
- PvP damage scaling (two-stage: 0.4 × 0.6 = 0.24 net)

## Scope & Roadmap

### V1 — Physical Damage PoC
- **Goal**: Simplest possible combat flow — pure physical weapon hits, no enchantments
- **Simulation unit**: Repeated single hit over N iterations across parameter variations
- **Combatants**: 1v1 only. Player vs Player, Player vs NPC, NPC vs NPC
- **Input**: Attacker (class, skills, stats, weapon) vs Defender (class, skills, stats, armor)
- **NPC definitions**: Define inline for a test case OR reference by name from npcdesc.cfg
- **Damage scope**: Pure physical weapon hits. No elemental damage, no enchantments, no start_script() calls, no spell effects. Elemental weapon damage and enchantment sub-scripts deferred to V1.5.
- **State**: Static per hit — state resets between iterations. Side effects recorded as stats but don't accumulate.
- **Output stats**: Mean, median, min, max, std dev, damage distribution histogram, damage breakdown (raw vs absorbed), hit/miss/crit ratios, damage per skill level curves
- **POL built-in stubs**: Batches 1-2 minimum; Batch 3 as needed for the physical-only path
- **Deliverables**: eScript parser, POL config parser, package resolver, dice parser, interpreter, mock runtime, simulation runner, Jupyter notebook with example scenario

### V1.5 — Elemental & Enchanted Weapons
- Elemental damage on weapons (inline in hitscriptinc.inc)
- Weapon enchantment sub-scripts (start_script calls)
- Reactive armor

### V2 — Spell & Resistance Flows
- Spell casting weapons (spellonhit, spellstrikescript)
- Spell resistance calculations
- Reactive armor with spell resistance
- Expanded stats for magical damage types

### V3 — Extended Combat
- HP tracking and kill-time distributions
- Buff/debuff state over time (accumulating state across hits)
- Group combat (1vN, NvN)
- Skill progression modeling

## Testing Strategy

### Running tests
```bash
pytest                    # everything (737 tests, ~57s)
```

All tests run unconditionally — no markers, no skips, no submodule dependency.

### Test fixture locality principle
- Tests **never** directly reference the shard submodule. All shard resources are snapshotted into `tests/fixtures/shard/` (209 files, 866 KB).
- `tests/conftest.py` provides session-scoped fixtures: `fixture_shard` (ShardData), `fixture_parse_results` (parsed combat scripts).
- `FIXTURE_SHARD_ROOT` from `tests/conftest.py` is the canonical path for all test files needing shard data.

### Submodule update workflow
When the shard submodule (`submodules/zuluhotel_omega_2.5`) is updated for balancing:
1. Update the submodule to the new commit
2. Run `python scripts/sync_fixtures.py` to refresh fixtures from the updated submodule
3. Run `pytest` to see what broke
4. Fix assertions to match new behavior (prefer property-based assertions — e.g., "damage > 0", "slayer > non-slayer" — over exact values)
5. Commit the fixture update + test fixes together

### Writing new tests that use shard data
- Import `FIXTURE_SHARD_ROOT` from `tests.conftest` or use `fixture_shard`/`fixture_parse_results` fixtures
- Never reference `submodules/zuluhotel_omega_2.5` directly in test code
- If a test needs shard resources not yet in fixtures, add them to `scripts/sync_fixtures.py` and re-run it
- Prefer property-based assertions over exact value checks
- Use `pytest.skip()` on execution failure rather than hard-failing — allows gradual coverage expansion

## Development Conventions
- Python 3.14, type hints throughout
- Use `uv` for dependency management if available, otherwise `pip`
- Source code in `src/` with package structure
- Tests alongside source or in `tests/`
- Keep submodules read-only; never modify them — **exception**: the shard submodule (`zuluhotel_omega_2.5`) may be instrumented with `__RecordSimulatorMetric` calls for metric capture. These are no-ops in POL and live behind `if(DEBUG_MODE)` guards.
- Structured logging from day one — all subsystems use Python `logging` with named loggers
- After completing each milestone, update the relevant changelog with a summary and test criteria for the work done
- Changelog test sections describe **critical test scenarios for testers**, not unit test counts

## Documentation
- **[Notebook Documentation](./notebooks/docs/README.md)** — User-facing wiki for notebook authors and game designers. Covers the simulation API, combatant specs, scenarios, results, reporting, runtime internals, and cookbook examples.

## Planning
- **[Path to V1](./planning/path_to_v1.md)** — Milestone plan (M0-M11) with dependency graph, deliverables, and acceptance criteria per milestone
- **[Changelog to V1](./changelog/changelog_to_v1.md)** — Per-milestone change summaries with test criteria
- **V1 status**: All milestones (M0–M11) complete. 374 hits/sec, submodule-independent fixtures.
- **V1.5 status**: M12–M13 complete (elemental protection + elemental damage application). 737 tests.
- **[Path to V1.5](./planning/path_to_v1.5.md)** — Elemental & Enchanted Weapons roadmap (M12–M22), three phases: elemental damage, sub-script execution, polish
- **[Changelog to V1.5](./changelog/changelog_to_v1.5.md)** — Per-milestone change summaries for V1.5

## Commands
- `uv run pytest` or `python -m pytest` - run tests
- `python scripts/sync_fixtures.py` - sync shard files into test fixtures (run after submodule update)
- `python scripts/sync_fixtures.py --dry-run` - preview what would be synced
- `jupyter lab` - launch notebook interface
