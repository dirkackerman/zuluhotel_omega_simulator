# Combatant Specs

This page documents how to define attackers and defenders for simulation scenarios. All spec classes are frozen dataclasses — immutable after creation.

**Import path:**
```python
from omega.simulation import CombatantSpec, WeaponSpec, ArmorSpec
```

## CombatantSpec

Defines a combatant's stats, skills, class levels, and equipment.

```python
@dataclass(frozen=True)
class CombatantSpec:
    name: str = "Combatant"
    is_npc: bool = False
    str_: int = 100
    int_: int = 25
    dex_: int = 100
    hp: int | None = None
    mana: int | None = None
    stamina: int | None = None
    skills: dict[int, int] = {}
    class_levels: dict[str, int] = {}
    weapon: WeaponSpec | None = None
    armor: ArmorSpec | None = None
    npc_template: str | None = None
    properties: dict[str, Any] = {}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `"Combatant"` | Display name, used in results and logs |
| `is_npc` | `bool` | `False` | `True` for NPCs/monsters, `False` for players. Affects PvP scaling and formula branches. |
| `str_` | `int` | `100` | Base Strength. Affects physical damage and HP. |
| `int_` | `int` | `25` | Base Intelligence. Affects mana pool and magic formulas. |
| `dex_` | `int` | `100` | Base Dexterity. Affects stamina and combat timing. |
| `hp` | `int \| None` | `None` | Hit points. Defaults to `str_ * 2` if not set. |
| `mana` | `int \| None` | `None` | Mana points. Defaults to `int_` if not set. |
| `stamina` | `int \| None` | `None` | Stamina points. Defaults to `dex_` if not set. |
| `skills` | `dict[int, int]` | `{}` | Skill ID to **display value** (0–130). See [Constants Reference](constants-reference.md). |
| `class_levels` | `dict[str, int]` | `{}` | Class ID string to level (1–5). See [Class IDs](#class-ids) below. |
| `weapon` | `WeaponSpec \| None` | `None` | Weapon spec. `None` means unarmed (fist). |
| `armor` | `ArmorSpec \| None` | `None` | Armor spec. `None` means unarmored (AR 0). |
| `npc_template` | `str \| None` | `None` | Reserved for future NPC template lookup from config. |
| `properties` | `dict[str, Any]` | `{}` | Mobile-level properties accessible via `GetObjProperty()`. Used for reactive armor (`ReactiveArmor`), creature type (`Type`), etc. |

### Skill values: display vs internal

Skill values in `CombatantSpec.skills` use **display values** (0–130), matching what you see in-game. The simulator internally multiplies by 10 (so display 100 becomes internal 1000) to match POL's `GetEffectiveSkill()` return values.

```python
# 100.0 Swordsmanship, 100.0 Tactics
skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100}

# 75.5 would be 75 (truncated to int at display level)
skills={SKILLID_SWORDSMANSHIP: 75}
```

### Vital defaults

If you don't set `hp`, `mana`, or `stamina`, they default to stat-derived values:

| Vital | Default | Typical player value |
|-------|---------|---------------------|
| HP | `str_ * 2` | 200 (for STR 100) |
| Mana | `int_` | 25 (for INT 25) |
| Stamina | `dex_` | 100 (for DEX 100) |

Set them explicitly when testing edge cases:

```python
# Low-HP attacker (glass cannon)
CombatantSpec(str_=100, hp=50, ...)

# High-mana mage
CombatantSpec(int_=100, mana=200, ...)
```

### Class IDs

Class levels are stored as string keys matching the shard's `GetObjProperty()` keys:

| Constant | String value | Class |
|----------|-------------|-------|
| `CLASSEID_WARRIOR` | `"IsWarrior"` | Warrior |
| `CLASSEID_MAGE` | `"IsMage"` | Mage |
| `CLASSEID_THIEF` | `"IsThief"` | Thief |
| `CLASSEID_RANGER` | `"IsRanger"` | Ranger |
| `CLASSEID_BARD` | `"IsBard"` | Bard |
| `CLASSEID_PALADIN` | `"IsPaladin"` | Paladin |
| `CLASSEID_BLADESINGER` | `"IsBladesinger"` | Bladesinger |
| `CLASSEID_MYSTIC_ARCHER` | `"IsMysticArcher"` | Mystic Archer |
| `CLASSEID_CRAFTER` | `"IsCrafter"` | Crafter |
| `CLASSEID_POWERPLAYER` | `"IsPowerplayer"` | Powerplayer |

Import from `omega.model.constants`:

```python
from omega.model.constants import CLASSEID_WARRIOR, CLASSEID_MAGE

# Level 5 Warrior
class_levels={"IsWarrior": 5}

# Or using the constant
class_levels={CLASSEID_WARRIOR: 5}

# Dual-class: Warrior 3, Paladin 2
class_levels={CLASSEID_WARRIOR: 3, CLASSEID_PALADIN: 2}
```

Class bonuses scale with level. The base multiplier is `CLASSE_BONUS = 1.5` with `BONUS_PER_LEVEL = 0.25` additional per level.

## WeaponSpec

Defines a weapon's damage, speed, and properties.

```python
@dataclass(frozen=True)
class WeaponSpec:
    name: str = "Weapon"
    damage: str = "3d6+2"
    speed: int = 50
    attribute: int = SKILLID_SWORDSMANSHIP
    two_handed: bool = False
    quality: float = 1.0
    hp: int = 50
    max_hp: int = 50
    hitscript: str | None = None
    properties: dict[str, Any] = {}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `"Weapon"` | Display name |
| `damage` | `str` | `"3d6+2"` | Dice notation: `XdY+Z`. Rolls X dice with Y sides plus Z. |
| `speed` | `int` | `50` | Attack speed (lower = faster, but not used in V1 per-hit model) |
| `attribute` | `int` | `SKILLID_SWORDSMANSHIP` | Which weapon skill governs this weapon. Use skill ID constants. |
| `two_handed` | `bool` | `False` | Whether the weapon requires both hands |
| `quality` | `float` | `1.0` | Weapon quality multiplier |
| `hp` | `int` | `50` | Current durability |
| `max_hp` | `int` | `50` | Maximum durability |
| `hitscript` | `str \| None` | `None` | Enchantment hitscript package path (e.g., `":combat:spellstrikescript"`). Set automatically by `enchant_with()`. |
| `properties` | `dict` | `{}` | Custom properties accessible via `GetObjProperty()` in eScript |

### Dice notation

Weapon damage uses the `XdY+Z` format:

| Notation | Min | Max | Mean | Description |
|----------|-----|-----|------|-------------|
| `"1d10"` | 1 | 10 | 5.5 | One 10-sided die |
| `"3d6+2"` | 5 | 20 | 12.5 | Three 6-sided dice plus 2 |
| `"2d8+4"` | 6 | 20 | 13.0 | Two 8-sided dice plus 4 |
| `"5d4"` | 5 | 20 | 12.5 | Five 4-sided dice, no bonus |

### Weapon skill attribute

The `attribute` field determines which combat skill governs hit chance and damage scaling:

```python
from omega.model.constants import (
    SKILLID_SWORDSMANSHIP,  # 40 — swords, broadswords, katanas
    SKILLID_MACEFIGHTING,   # 41 — maces, hammers, staves
    SKILLID_FENCING,        # 42 — daggers, spears, kryss
    SKILLID_WRESTLING,      # 43 — unarmed combat
    SKILLID_ARCHERY,        # 31 — bows, crossbows
)

# A mace weapon
WeaponSpec(name="War Hammer", damage="4d5+3", attribute=SKILLID_MACEFIGHTING)

# A bow
WeaponSpec(name="Heavy Crossbow", damage="2d10", attribute=SKILLID_ARCHERY)
```

### Custom properties (slayer weapons)

Use `properties` for weapon enchantments that the eScript reads via `GetObjProperty()`:

```python
# Slayer weapon — doubles damage against matching creature type
WeaponSpec(
    name="Undead Slayer Sword",
    damage="3d6+2",
    properties={"SlayType": "Undead"},
)
```

The slayer check in the shard scripts compares `weapon.SlayType` against `defender.Type`. If they match, damage is doubled.

### Enchanting weapons with `enchant_with()` (V1.5)

The `enchant_with()` method applies a full enchantment bundle (hitscript + CProps) from the `Enchantment` enum:

```python
from omega.config.enchantments import Enchantment

# Spell strike — casts Fireball on hit
fire_sword = WeaponSpec(name="Fire Sword", damage="3d6+2").enchant_with(
    Enchantment.OF_DAEMONS_BREATH
)
# Equivalent to:
# WeaponSpec(name="Fire Sword", damage="3d6+2",
#            hitscript=":combat:spellstrikescript",
#            properties={"HitWithSpell": Spell.FIREBALL})

# Slayer — bonus damage vs undead
silver_sword = WeaponSpec(name="Silver Sword", damage="3d6+2").enchant_with(
    Enchantment.SILVER
)

# Greater enchantment — dual-element damage
planar_weapon = WeaponSpec(damage="3d6+2").enchant_with(
    Enchantment.OF_PLANAR_FURY
)
```

`enchant_with()` returns a new frozen `WeaponSpec` with `hitscript` and `properties` set. Existing properties take precedence — you can customize per-weapon fields like `EffectCircle` or `ChanceOfEffect`:

```python
# Default ChanceOfEffect is 7 for Planar Fury; override to 15
WeaponSpec(
    damage="3d6+2",
    properties={"ChanceOfEffect": 15},
).enchant_with(Enchantment.OF_PLANAR_FURY)
```

### Enchantment and Spell enums

**`Enchantment`** (`omega.config.enchantments.Enchantment`) — 45 members from `hitscriptdesc.cfg`:
- Spell strike (1–18): `OF_BUNGLING`, `OF_DAEMONS_BREATH`, `OF_THUNDER`, `OF_HELLFIRE`, etc.
- Slayer (19–35): `SLIME_SLAYER`, `SILVER` (Undead), `HOLY` (Daemon), `DRAGON_SLAYER`, etc.
- Effect (36–42): `OF_PIERCING`, `BANISHING`, `POISONED`, `BLOODY`, `VAMPIRIC`, `LEECH`, `BLINDING`
- Greater (43–45): `OF_PLANAR_FURY`, `OF_THE_VOID`, `OF_ELEMENTAL_FURY`

**`Spell`** (`omega.config.spells.Spell`) — 132 spell IDs from `spells.cfg`:
- Used in `HitWithSpell` properties (e.g., `Spell.FIREBALL == 18`)
- See [Constants Reference](constants-reference.md) for the full list

### Elemental weapon properties

Set `ElementalDamage` on a weapon to split damage by element type:

```python
# Fire weapon
WeaponSpec(
    name="Flaming Sword", damage="3d6+2",
    properties={"ElementalDamage": 0x01},  # FIRE
)

# Multi-element weapon
WeaponSpec(
    name="Tri-Elemental Blade", damage="3d6+2",
    properties={"ElementalDamage": 0x01 | 0x02 | 0x04},  # FIRE + AIR + EARTH
)
```

The defender's elemental protection CProps reduce elemental damage:
- `FireProtection`, `AirProtection`, `EarthProtection`, `WaterProtection`
- `NecroProtection`, `HolyProtection`, `PoisonProtection`, `AcidProtection`

### Combatant properties

Use `CombatantSpec.properties` for mobile-level CProps that affect combat:

```python
# Defender with reactive armor
CombatantSpec(
    name="Mage", is_npc=False,
    str_=50, int_=100, dex_=80,
    properties={"ReactiveArmor": 1},
)

# NPC with a creature type (for slayer matching)
CombatantSpec(
    name="Skeleton", is_npc=True,
    str_=80, dex_=60, int_=20,
    properties={"Type": "Undead"},
)
```

## ArmorSpec

Defines a piece of armor.

```python
@dataclass(frozen=True)
class ArmorSpec:
    name: str = "Armor"
    ar: int = 0
    coverage: tuple[str, ...] = ()
    hp: int = 70
    max_hp: int = 70
    layer: int = 0
    properties: dict[str, Any] = {}
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `"Armor"` | Display name |
| `ar` | `int` | `0` | Armor Rating — primary defense stat. Higher = more damage absorbed. |
| `coverage` | `tuple[str, ...]` | `()` | Body parts covered (informational) |
| `hp` | `int` | `70` | Current durability |
| `max_hp` | `int` | `70` | Maximum durability |
| `layer` | `int` | `0` | Equipment layer. Defaults to chest (`LAYER_CHEST`) when equipped. |
| `properties` | `dict` | `{}` | Custom properties for eScript access |

### Armor Rating values

Typical AR values from the shard:

| Armor type | Typical AR | Notes |
|-----------|-----------|-------|
| Unarmored | 0 | No protection |
| Leather | 10–15 | Light armor |
| Chain | 20–25 | Medium armor |
| Plate | 30–40 | Heavy armor |
| Magic plate | 40–50 | Enchanted heavy armor |

```python
# Light armor
ArmorSpec(name="Leather Tunic", ar=13)

# Heavy plate
ArmorSpec(name="Plate Armor", ar=35)

# Custom — testing extreme AR
ArmorSpec(name="Invincible Armor", ar=100)
```

## Full equipment kits (multi-layer)

The `CombatantSpec` takes a single `weapon` and a single `armor`, which is sufficient for basic scenarios. For testing with a full equipment loadout across multiple body slots, use the lower-level factory API directly.

### Equipping multiple armor layers

```python
from omega.model import create_mobile_inline, Weapon, Armor
from omega.config.dice import parse_dice
from omega.model.constants import (
    SKILLID_SWORDSMANSHIP, SKILLID_TACTICS, SKILLID_ANATOMY,
    LAYER_HELM, LAYER_CHEST, LAYER_ARMS, LAYER_GLOVES, LAYER_LEGS, LAYER_SHOES,
)

# Build armor pieces for each slot
helm    = Armor(name="Plate Helm", ar=20, coverage=["Head"], layer=LAYER_HELM)
chest   = Armor(name="Plate Chest", ar=35, coverage=["Body"], layer=LAYER_CHEST)
arms    = Armor(name="Plate Arms", ar=18, coverage=["Arms"], layer=LAYER_ARMS)
gloves  = Armor(name="Plate Gloves", ar=12, coverage=["Hands"], layer=LAYER_GLOVES)
legs    = Armor(name="Plate Leggings", ar=22, coverage=["Legs"], layer=LAYER_LEGS)
boots   = Armor(name="Plate Boots", ar=10, coverage=["Feet"], layer=LAYER_SHOES)

sword = Weapon(name="Katana", damage=parse_dice("3d6+2"), attribute=SKILLID_SWORDSMANSHIP)

# Create a fully kitted mobile
mobile = create_mobile_inline(
    name="Full Plate Warrior",
    str_=100, dex_=100, int_=25,
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
    class_levels={"IsWarrior": 5},
    weapon=sword,
    armor_pieces=[helm, chest, arms, gloves, legs, boots],
)
```

Armor pieces with a `layer` set are equipped to that exact layer. Pieces without a `layer` are auto-assigned based on their `coverage` field (e.g., `"Head"` maps to `LAYER_HELM`). If neither is set, the piece defaults to `LAYER_CHEST`.

> To use this mobile in `run_scenario()`, pass it through the lower-level `execute_hit()` API — see [Runtime](runtime.md). The `CombatantSpec` / `run_scenario()` path uses a single `armor` field for the primary piece; the multi-layer approach is for advanced use.

## Items from config files (itemdesc.cfg)

Instead of specifying weapon damage and armor AR manually, you can load real items directly from the shard's `itemdesc.cfg`. This ensures your simulation uses the exact same stats as the live server.

**Import path:**
```python
from omega.model import find_weapon_by_name, find_armor_by_name
from omega.config.cfg_parser import parse_config_file
```

### Loading the config

```python
from pathlib import Path
from omega.config.cfg_parser import parse_config_file

itemdesc = parse_config_file(
    Path("../submodules/zuluhotel_omega_2.5/pkg/systems/combat/config/itemdesc.cfg")
)
```

### Looking up items by Name

Items in `itemdesc.cfg` are indexed by their hex objtype (e.g., `Weapon 0x27A8`), but each has a `Name` property. Use `find_weapon_by_name` and `find_armor_by_name` to look up items directly:

```python
from omega.model import find_weapon_by_name

heartwood = find_weapon_by_name("TheHeartwood", itemdesc)
# Result: Weapon(name="TheHeartwood", damage=1d18+35, speed=88,
#                attribute=Swords, two_handed=True, max_hp=200)
```

The shard's `TheHeartwood` is a two-handed bokuto dealing `1d18+35` damage (range 36–53), governed by the Swordsmanship skill. All properties — speed, hitscript, two-handed flag — are read directly from the config.

For lower-level access, `ConfigFile.find_by_name(name)` returns the raw `ConfigElement` (or `None`):

```python
elem = itemdesc.find_by_name("TheHeartwood")
# elem is a ConfigElement — pass to create_weapon_from_config() if needed
```

### Player character with a config weapon

```python
from omega.model import create_mobile_inline, find_weapon_by_name
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS, SKILLID_ANATOMY

heartwood = find_weapon_by_name("TheHeartwood", itemdesc)

player = create_mobile_inline(
    name="Heartwood Warrior",
    str_=100, dex_=100, int_=25,
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
    class_levels={"IsWarrior": 5},
    weapon=heartwood,
)
```

### NPC weapon from config

NPC weapons work the same way. For example, Modain's Staff:

```python
from omega.model import find_weapon_by_name

modain_staff = find_weapon_by_name("ModainsStaffWeapon", itemdesc)
# Result: Weapon(name="ModainsStaffWeapon", damage=10d6, speed=50,
#                attribute=Mace, two_handed=True, max_hp=250)
```

`ModainsStaffWeapon` deals `10d6` damage (range 10–60, mean 35) — a very powerful NPC weapon. It also has a `Hitscript` (banish) and `Controlscript` (apply hit script) that would be exercised in V1.5.

### Armor from config

```python
from omega.model import find_armor_by_name

coif = find_armor_by_name("ChainmailCoif", itemdesc)
# Result: Armor(name="ChainmailCoif", ar=16, coverage=["Head", "Neck"], max_hp=70)
# CProps like DefaultDex and MagicPenalty are carried over to the property bag
```

## NPC templates from npcdesc.cfg

For the most realistic simulations, you can create NPCs directly from the shard's `npcdesc.cfg` templates. This resolves the full chain: NPC template → equipment template (equip.cfg) → item definitions (itemdesc.cfg).

**Import path:**
```python
from omega.model import create_mobile_from_template
from omega.config.cfg_parser import parse_config_file
```

### Loading the config files

The NPC template chain requires three config files:

```python
from pathlib import Path
from omega.config.cfg_parser import parse_config_file

shard_root = Path("../submodules/zuluhotel_omega_2.5")

npcdesc  = parse_config_file(shard_root / "config" / "npcdesc.cfg")
equip    = parse_config_file(shard_root / "config" / "equip.cfg")
itemdesc = parse_config_file(shard_root / "pkg" / "systems" / "combat" / "config" / "itemdesc.cfg")
```

### Creating an NPC from template

```python
from omega.model import create_mobile_from_template

dragon_king = create_mobile_from_template("dragonking", npcdesc, equip, itemdesc)
```

This single call:

1. Looks up `NpcTemplate dragonking` in npcdesc.cfg
2. Reads stats: STR 1000, INT 200, DEX 200
3. Reads `CustomHitsLevel` CProp → sets HP to 1,500,000
4. Reads skills: Tactics 200, MaceFighting 200, Magery 200, Parry 200, etc.
5. Reads all CProps → sets properties: `Type="Dragonkin"`, `SuperBoss=1`, `FreeAction=1`, etc.
6. Reads `Equip dragonking` → looks up equipment template in equip.cfg
7. From the equipment template: resolves `Weapon dragonkingWeapon` (15d10 mace, range 15–150) and `Armor Armor30` from itemdesc.cfg
8. Equips everything on the mobile

The resulting `Mobile` has the exact same stats, skills, properties, and equipment as the live server NPC.

### Inspecting a template-created NPC

```python
dk = create_mobile_from_template("dragonking", npcdesc, equip, itemdesc)

print(f"Name: {dk.name}")              # "The Dragon King"
print(f"STR:  {dk.strength}")           # 1000
print(f"HP:   {dk.max_hp}")             # 1500000
print(f"Type: {dk.get_property('Type')}")  # "Dragonkin"

# Check equipped weapon
from omega.model.constants import LAYER_HAND1
weapon = dk.get_equipped(LAYER_HAND1)
if weapon:
    print(f"Weapon: {weapon.name}")     # "dragonkingWeapon"
    print(f"Damage: {weapon.damage}")   # DiceSpec(15, 10, 0) → 15d10

# Check skills (internal values, ×10)
from omega.model.constants import SKILLID_TACTICS, SKILLID_MACEFIGHTING
print(f"Tactics: {dk.get_skill(SKILLID_TACTICS) / 10:.0f}")  # 200
print(f"Mace:    {dk.get_skill(SKILLID_MACEFIGHTING) / 10:.0f}")  # 200
```

### Customizing a template NPC

After creating from template, you can modify the NPC before running a simulation. Common customizations:

**Change the weapon:**
```python
from omega.model import find_weapon_by_name, create_mobile_from_template
from omega.model.constants import LAYER_HAND1

dk = create_mobile_from_template("dragonking", npcdesc, equip, itemdesc)

# Replace with Modain's Staff instead of the default dragon king weapon
modain_staff = find_weapon_by_name("ModainsStaffWeapon", itemdesc)
dk.equip(LAYER_HAND1, modain_staff)
```

**Override stats:**
```python
dk = create_mobile_from_template("dragonking", npcdesc, equip, itemdesc)

# Nerf the dragon king for testing
dk.str_base = 500
dk.hp = 100000
dk.max_hp = 100000
```

**Change skills:**
```python
dk = create_mobile_from_template("dragonking", npcdesc, equip, itemdesc)

# Give him Swordsmanship instead of Mace Fighting
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_MACEFIGHTING
dk.set_skill(SKILLID_MACEFIGHTING, 0)
dk.set_skill(SKILLID_SWORDSMANSHIP, 200 * 10)  # Internal value = display × 10
```

**Change properties:**
```python
dk = create_mobile_from_template("dragonking", npcdesc, equip, itemdesc)

# Change creature type (affects slayer weapons)
dk.set_property("Type", "Undead")  # Now vulnerable to Undead Slayer weapons

# Remove SuperBoss flag
dk.set_property("SuperBoss", 0)
```

### Using template NPCs with execute_hit()

Template-created mobiles work directly with `execute_hit()`:

```python
from omega.combat.hit import execute_hit
from omega.model import create_mobile_from_template, create_mobile_inline
from omega.model.constants import SKILLID_SWORDSMANSHIP, SKILLID_TACTICS, LAYER_HAND1
from omega.shard import ShardData
from pathlib import Path

shard = ShardData.from_path(Path("../submodules/zuluhotel_omega_2.5"))
parse_results = shard.parse_combat_scripts()

# Create NPC from template
dk = create_mobile_from_template("dragonking", npcdesc, equip, itemdesc)
dk_weapon = dk.get_equipped(LAYER_HAND1)

# Create player attacker inline
from omega.config.dice import parse_dice
from omega.model import Weapon, Armor

player = create_mobile_inline(
    name="Warrior",
    str_=100, dex_=100, int_=25,
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    class_levels={"IsWarrior": 5},
    weapon=Weapon(name="Broadsword", damage=parse_dice("3d6+2"),
                  attribute=SKILLID_SWORDSMANSHIP),
)
player_weapon = player.get_equipped(LAYER_HAND1)

# Player attacking the Dragon King
player_armor = Armor(name="Plate", ar=35)
result = execute_hit(
    parse_results,
    player,           # attacker
    dk,               # defender (Dragon King)
    player_weapon,    # weapon
    player_armor,     # defender's armor (from equipment template, or override)
    config_resolver=shard.resolve_config_path,
    em_modules_dir=shard.root / "scripts" / "modules",
)

print(f"Damage dealt to Dragon King: {result.final_damage:.1f}")
```

### The NPC resolution chain

When you call `create_mobile_from_template("dragonking", ...)`, here's the full resolution:

```
npcdesc.cfg                    equip.cfg              itemdesc.cfg
┌───────────────────┐          ┌──────────────┐       ┌────────────────────┐
│ NpcTemplate       │          │ Equipment    │       │ Weapon 0x0F63      │
│   dragonking      │          │   dragonking │       │   Name             │
│ {                 │          │ {            │       │   dragonkingWeapon │
│   STR    1000     │   Equip  │   Weapon     │  ref  │   Damage  15d10    │
│   INT    200      │ ────────►│   dragonking-│──────►│   Attribute Mace   │
│   DEX    200      │          │   Weapon     │       │   Speed   60       │
│   Tactics 200     │          │   Armor      │       │ }                  │
│   MaceFighting    │          │   Armor30    │       │                    │
│     200           │          │ }            │       │ Armor 0x...        │
│   CProp Type      │          └──────────────┘       │   Name Armor30     │
│     sDragonkin    │                           ref   │   AR   30          │
│   CProp           │                          ──────►│ }                  │
│     CustomHits    │                                 └────────────────────┘
│     Level         │
│     i1500000      │
│   Equip           │
│     dragonking    │
│ }                 │
└───────────────────┘
```

## Complete examples

### Melee warrior (player)

```python
from omega.model.constants import (
    SKILLID_SWORDSMANSHIP, SKILLID_TACTICS, SKILLID_ANATOMY, SKILLID_PARRY,
    CLASSEID_WARRIOR,
)

warrior = CombatantSpec(
    name="GM Warrior",
    is_npc=False,
    str_=100, dex_=100, int_=25,
    skills={
        SKILLID_SWORDSMANSHIP: 100,
        SKILLID_TACTICS: 100,
        SKILLID_ANATOMY: 100,
        SKILLID_PARRY: 80,
    },
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=WeaponSpec(name="Katana", damage="3d6+2", attribute=SKILLID_SWORDSMANSHIP),
    armor=ArmorSpec(name="Plate", ar=35),
)
```

### Archer ranger (player)

```python
from omega.model.constants import (
    SKILLID_ARCHERY, SKILLID_TACTICS, SKILLID_ANATOMY,
    CLASSEID_RANGER,
)

ranger = CombatantSpec(
    name="Ranger",
    is_npc=False,
    str_=90, dex_=100, int_=35,
    skills={
        SKILLID_ARCHERY: 100,
        SKILLID_TACTICS: 100,
        SKILLID_ANATOMY: 80,
    },
    class_levels={CLASSEID_RANGER: 4},
    weapon=WeaponSpec(name="Heavy Crossbow", damage="2d10+3", attribute=SKILLID_ARCHERY),
)
```

### NPC target dummy

```python
target = CombatantSpec(
    name="Target Dummy",
    is_npc=True,
    str_=50, dex_=50, int_=50,
    hp=500,
    armor=ArmorSpec(name="Plate", ar=30),
)
```

### Tough NPC boss

```python
boss = CombatantSpec(
    name="Dragon",
    is_npc=True,
    str_=200, dex_=80, int_=100,
    hp=2000,
    skills={SKILLID_TACTICS: 120, SKILLID_WRESTLING: 120},
    armor=ArmorSpec(name="Dragon Scales", ar=60),
)
```
