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
3. Physical: slayer multiplier -> class bonus -> elemental damage -> shield absorption -> AR -> protection -> mace effects
4. Astral: spirit speak scaling -> class bonuses -> meditation resistance -> astral armor -> 50% reduction
5. `ApplyTheDamage()`: PvP scaling (60%) -> tamed multiplier -> ally scaling -> ApplyRawDamage()

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
- PvP damage scaling (60% reduction)

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

### Two test categories
- **Self-contained tests** — use mock data and hand-built fixtures. Never break from shard changes. Run with `pytest -m "not shard"`.
- **Shard-dependent tests** — marked with `@pytest.mark.shard`. Execute real eScript from the pinned submodule. Will break when shard scripts change (new formulas, renamed functions, etc.).

### Running tests
```bash
pytest                    # everything
pytest -m "not shard"     # fast — skips shard-dependent tests
pytest -m shard           # only shard-dependent tests
```

### Submodule update workflow
When the shard submodule (`submodules/zuluhotel_omega_2.5`) is updated for balancing:
1. Update the submodule to the new commit
2. Run `pytest -m shard` to see what broke
3. Fix assertions to match new behavior (use property-based assertions where possible — e.g., "damage > 0", "slayer > non-slayer" — rather than exact values)
4. Commit the submodule update + test fixes together in one commit

### Writing shard-dependent tests
- Use `@pytest.mark.shard` (or `pytestmark = [pytest.mark.shard]` for whole modules)
- Prefer property-based assertions over exact value checks
- Use `pytest.skip()` on execution failure rather than hard-failing — allows gradual coverage expansion
- Document which shard scripts the test exercises

## Development Conventions
- Python 3.14, type hints throughout
- Use `uv` for dependency management if available, otherwise `pip`
- Source code in `src/` with package structure
- Tests alongside source or in `tests/`
- Keep submodules read-only; never modify them
- Structured logging from day one — all subsystems use Python `logging` with named loggers
- After completing each milestone, update `changelog/changelog_to_v1.md` with a summary and test criteria for the work done

## Planning
- **[Path to V1](./path_to_v1.md)** — Milestone plan (M0-M10) with dependency graph, deliverables, and acceptance criteria per milestone
- **[Changelog to V1](./changelog/changelog_to_v1.md)** — Per-milestone change summaries with test criteria

## Commands
- `uv run pytest` or `python -m pytest` - run tests
- `jupyter lab` - launch notebook interface
