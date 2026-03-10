# Constants Reference

All constants are importable from `omega.model.constants`:

```python
from omega.model.constants import SKILLID_SWORDSMANSHIP, CLASSEID_WARRIOR, DMGID_PHYSICAL
```

## Skill IDs

Used in `CombatantSpec.skills` dictionaries and `Variable` parameter paths.

### Combat skills

| Constant | ID | Skill name | Used for |
|----------|-----|-----------|----------|
| `SKILLID_SWORDSMANSHIP` | 40 | Swordsmanship | Swords, broadswords, katanas |
| `SKILLID_MACEFIGHTING` | 41 | Mace Fighting | Maces, hammers, staves |
| `SKILLID_FENCING` | 42 | Fencing | Daggers, spears, kryss |
| `SKILLID_WRESTLING` | 43 | Wrestling | Unarmed combat |
| `SKILLID_ARCHERY` | 31 | Archery | Bows, crossbows |
| `SKILLID_TACTICS` | 27 | Tactics | Damage multiplier |
| `SKILLID_ANATOMY` | 1 | Anatomy | Damage multiplier |
| `SKILLID_PARRY` | 5 | Parry / Battle Defense | Shield blocking |
| `SKILLID_MAGICRESISTANCE` | 26 | Magic Resistance | Spell damage reduction |

### Magic skills

| Constant | ID | Skill name |
|----------|-----|-----------|
| `SKILLID_MAGERY` | 25 | Magery |
| `SKILLID_MEDITATION` | 46 | Meditation |
| `SKILLID_SPIRITSPEAK` | 32 | Spirit Speak |
| `SKILLID_EVALINT` | 16 | Evaluating Intelligence |
| `SKILLID_INSCRIPTION` | 23 | Inscription |

### Stealth skills

| Constant | ID | Skill name |
|----------|-----|-----------|
| `SKILLID_HIDING` | 21 | Hiding |
| `SKILLID_STEALTH` | 47 | Stealth |
| `SKILLID_SNOOPING` | 28 | Snooping |
| `SKILLID_STEALING` | 33 | Stealing |
| `SKILLID_DETECTINGHIDDEN` | 14 | Detecting Hidden |
| `SKILLID_LOCKPICKING` | 24 | Lockpicking |
| `SKILLID_REMOVETRAP` | 48 | Remove Trap |
| `SKILLID_POISONING` | 30 | Poisoning |

### Crafting skills

| Constant | ID | Skill name |
|----------|-----|-----------|
| `SKILLID_BLACKSMITHY` | 7 | Blacksmithy |
| `SKILLID_TAILORING` | 34 | Tailoring |
| `SKILLID_TINKERING` | 37 | Tinkering |
| `SKILLID_CARPENTRY` | 11 | Carpentry |
| `SKILLID_BOWCRAFT` | 8 | Bowcraft |
| `SKILLID_ALCHEMY` | 0 | Alchemy |
| `SKILLID_COOKING` | 13 | Cooking |
| `SKILLID_MINING` | 45 | Mining |
| `SKILLID_LUMBERJACKING` | 44 | Lumberjacking |

### Other skills

| Constant | ID | Skill name |
|----------|-----|-----------|
| `SKILLID_HEALING` | 17 | Healing |
| `SKILLID_VETERINARY` | 39 | Veterinary |
| `SKILLID_ANIMALLORE` | 2 | Animal Lore |
| `SKILLID_TAMING` | 35 | Animal Taming |
| `SKILLID_HERDING` | 20 | Herding |
| `SKILLID_ITEMID` | 3 | Item Identification |
| `SKILLID_ARMSLORE` | 4 | Arms Lore |
| `SKILLID_BEGGING` | 6 | Begging |
| `SKILLID_PEACEMAKING` | 9 | Peacemaking |
| `SKILLID_CAMPING` | 10 | Camping |
| `SKILLID_CARTOGRAPHY` | 12 | Cartography |
| `SKILLID_ENTICEMENT` | 15 | Enticement |
| `SKILLID_FISHING` | 18 | Fishing |
| `SKILLID_FORENSICS` | 19 | Forensic Evaluation |
| `SKILLID_PROVOCATION` | 22 | Provocation |
| `SKILLID_MUSICIANSHIP` | 29 | Musicianship |
| `SKILLID_TASTEID` | 36 | Taste Identification |
| `SKILLID_TRACKING` | 38 | Tracking |

### Quick-import for combat notebooks

```python
from omega.model.constants import (
    # Weapon skills
    SKILLID_SWORDSMANSHIP, SKILLID_MACEFIGHTING, SKILLID_FENCING,
    SKILLID_WRESTLING, SKILLID_ARCHERY,
    # Combat support
    SKILLID_TACTICS, SKILLID_ANATOMY, SKILLID_PARRY,
    # Magic
    SKILLID_MAGERY, SKILLID_MEDITATION, SKILLID_MAGICRESISTANCE,
)
```

## Class IDs

Used in `CombatantSpec.class_levels` dictionaries. Values are strings matching the shard's `GetObjProperty()` keys.

| Constant | String value | Class | Role |
|----------|-------------|-------|------|
| `CLASSEID_WARRIOR` | `"IsWarrior"` | Warrior | Melee damage, physical toughness |
| `CLASSEID_MAGE` | `"IsMage"` | Mage | Spell damage, magic resistance |
| `CLASSEID_THIEF` | `"IsThief"` | Thief | Backstab, stealth |
| `CLASSEID_RANGER` | `"IsRanger"` | Ranger | Archery, tracking |
| `CLASSEID_BARD` | `"IsBard"` | Bard | Crowd control, support |
| `CLASSEID_PALADIN` | `"IsPaladin"` | Paladin | Holy damage, healing |
| `CLASSEID_BLADESINGER` | `"IsBladesinger"` | Bladesinger | Hybrid melee/magic |
| `CLASSEID_MYSTIC_ARCHER` | `"IsMysticArcher"` | Mystic Archer | Hybrid archery/magic |
| `CLASSEID_CRAFTER` | `"IsCrafter"` | Crafter | Crafting bonuses |
| `CLASSEID_POWERPLAYER` | `"IsPowerplayer"` | Powerplayer | Generalist |

### Class bonus constants

| Constant | Value | Description |
|----------|-------|-------------|
| `CLASSE_BONUS` | `1.5` | Base damage multiplier per class level |
| `BONUS_PER_LEVEL` | `0.25` | Additional bonus per level |
| `SMALL_BONUS_PER_LEVEL` | `0.15` | Smaller bonus for secondary effects |
| `THIEF_BACKSTAB_BONUS_DAMAGE` | `10` | Flat bonus for thief backstab |
| `THIEF_AMBUSH_BONUS_DAMAGE` | `10` | Flat bonus for thief ambush |

### The `ALL_CLASS_IDS` tuple

```python
from omega.model.constants import ALL_CLASS_IDS

for class_id in ALL_CLASS_IDS:
    print(class_id)  # "IsWarrior", "IsMage", ...
```

## Damage type bitflags

Used in the shard scripts for elemental damage and resistance calculations. These are informational for V1 (physical damage only) but included for reference.

| Constant | Hex | Description |
|----------|-----|-------------|
| `DMGID_FIRE` | `0x0001` | Fire damage |
| `DMGID_AIR` | `0x0002` | Air/lightning damage |
| `DMGID_EARTH` | `0x0004` | Earth damage |
| `DMGID_WATER` | `0x0008` | Water/ice damage |
| `DMGID_NECRO` | `0x0010` | Necromantic damage |
| `DMGID_HOLY` | `0x0020` | Holy damage |
| `DMGID_POISON` | `0x0040` | Poison damage |
| `DMGID_ACID` | `0x0080` | Acid damage |
| `DMGID_PHYSICAL` | `0x0100` | Physical damage |
| `DMGID_MAGIC` | `0x0200` | Generic magical damage |
| `DMGID_ASTRAL` | `0x0400` | Astral damage (Spirit Speak path) |
| `DMGID_NO_RESIST` | `0x0800` | Bypasses all resistance |

Damage types are bitflags — they can be combined: `DMGID_FIRE | DMGID_MAGIC` = fire magic damage.

## Equipment layers

Used in `ArmorSpec.layer` to specify where armor is equipped.

| Constant | Hex | Body slot |
|----------|-----|-----------|
| `LAYER_HAND1` | `0x01` | Main hand (weapon) |
| `LAYER_HAND2` | `0x02` | Off-hand (shield) |
| `LAYER_SHOES` | `0x03` | Feet |
| `LAYER_PANTS` | `0x04` | Legs |
| `LAYER_SHIRT` | `0x05` | Shirt (under armor) |
| `LAYER_HELM` | `0x06` | Head |
| `LAYER_GLOVES` | `0x07` | Hands |
| `LAYER_RING` | `0x08` | Ring |
| `LAYER_NECK` | `0x0A` | Necklace |
| `LAYER_WAIST` | `0x0C` | Belt |
| `LAYER_CHEST` | `0x0D` | Torso armor (default for ArmorSpec) |
| `LAYER_WRIST` | `0x0E` | Bracelet |
| `LAYER_TUNIC` | `0x11` | Tunic (over armor) |
| `LAYER_EARS` | `0x12` | Earrings |
| `LAYER_ARMS` | `0x13` | Arms |
| `LAYER_CAPE` | `0x14` | Cape |
| `LAYER_ROBE` | `0x16` | Robe |
| `LAYER_SKIRT` | `0x17` | Skirt |
| `LAYER_LEGS` | `0x18` | Leggings |

## Stat and skill caps

| Constant | Value | Description |
|----------|-------|-------------|
| `SKILL_STAT_CAP` | `130` | Maximum effective skill display value |
| `BASE_CAP` | `1300` | Maximum internal skill value (130 * 10) |

## Vital IDs

Used internally by the vitals system:

| Constant | Value |
|----------|-------|
| `VITALID_LIFE` | `"life"` |
| `VITALID_MANA` | `"mana"` |
| `VITALID_STAMINA` | `"stamina"` |

## POL class constants

Used for type checking with `.isa()`:

| Constant | Value |
|----------|-------|
| `POLCLASS_MOBILE` | `"Mobile"` |
| `POLCLASS_NPC` | `"NPC"` |
| `POLCLASS_WEAPON` | `"Weapon"` |
| `POLCLASS_ARMOR` | `"Armor"` |
| `POLCLASS_ITEM` | `"Item"` |
