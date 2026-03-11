"""Spell ID constants from the shard's spells.cfg files.

Provides :class:`Spell` IntEnum with all spell IDs across all spell books
(standard, necromancy, earth magic, holy book, song book).

Usage::

    from omega.config.spells import Spell

    # As a weapon property:
    WeaponSpec(
        hitscript=":combat:spellstrikescript",
        properties={"HitWithSpell": Spell.ANGELIC_AURA, "EffectCircle": 9},
    )

    # Resolve from integer ID:
    spell = Spell(169)  # Spell.ANGELIC_AURA
"""

from __future__ import annotations

from enum import IntEnum


class Spell(IntEnum):
    """Spell IDs from the shard's spells.cfg files.

    Source: pkg/std/spells/spells.cfg, pkg/opt/necro/spells.cfg,
    pkg/opt/earth/spells.cfg, pkg/opt/holybook/spells.cfg,
    pkg/opt/songbook/spells.cfg.
    """

    # -- Standard Spells (Circle 1-8, IDs 1-64) --

    # Circle 1
    CLUMSY = 1
    CREATE_FOOD = 2
    FEEBLEMIND = 3
    HEAL = 4
    MAGIC_ARROW = 5
    NIGHT_SIGHT = 6
    REACTIVE_ARMOR = 7
    WEAKEN = 8

    # Circle 2
    AGILITY = 9
    CUNNING = 10
    CURE = 11
    HARM = 12
    MAGIC_TRAP = 13
    MAGIC_UNTRAP = 14
    PROTECTION = 15
    STRENGTH = 16

    # Circle 3
    BLESS = 17
    FIREBALL = 18
    MAGIC_LOCK = 19
    POISON = 20
    TELEKINESIS = 21
    TELEPORT = 22
    UNLOCK = 23
    WALL_OF_STONE = 24

    # Circle 4
    ARCH_CURE = 25
    ARCH_PROTECTION = 26
    CURSE = 27
    FIRE_FIELD = 28
    GREATER_HEAL = 29
    LIGHTNING = 30
    MANA_DRAIN = 31
    RECALL = 32

    # Circle 5
    BLADE_SPIRIT = 33
    DISPEL_FIELD = 34
    INCOGNITO = 35
    SPELL_REFLECTION = 36
    MIND_BLAST = 37
    PARALYZE = 38
    POISON_FIELD = 39
    SUMMON_CREATURE = 40

    # Circle 6
    DISPEL = 41
    ENERGY_BOLT = 42
    EXPLOSION = 43
    INVISIBILITY = 44
    MARK = 45
    MASS_CURSE = 46
    PARALYZE_FIELD = 47
    REVEAL = 48

    # Circle 7
    CHAIN_LIGHTNING = 49
    ENERGY_FIELD = 50
    FLAME_STRIKE = 51
    GATE = 52
    MANA_VAMPIRE = 53
    MASS_DISPEL = 54
    METEOR_SWARM = 55
    POLYMORPH = 56

    # Circle 8
    EARTHQUAKE = 57
    ENERGY_VORTEX = 58
    RESURRECTION = 59
    SUMMON_AIR_ELEMENTAL = 60
    SUMMON_DAEMON = 61
    SUMMON_EARTH_ELEMENTAL = 62
    SUMMON_FIRE_ELEMENTAL = 63
    SUMMON_WATER_ELEMENTAL = 64

    # -- Necromancy (Circle 21-24, IDs 65-80) --

    # Circle 21
    CONTROL_UNDEAD = 65
    DARKNESS = 66
    DECAYING_RAY = 67
    SPECTRES_TOUCH = 68

    # Circle 22
    ABYSSAL_FLAME = 69
    ANIMATE_DEAD = 70
    SACRIFICE = 71
    WRAITHS_BREATH = 72

    # Circle 23
    SORCERERS_BANE = 73
    SUMMON_SPIRIT = 74
    WRAITHFORM = 75
    WYVERN_STRIKE = 76

    # Circle 24
    KILL = 77
    LICHE = 78
    PLAGUE = 79
    SPELLBIND = 80

    # -- Earth Magic (Circle 25-28, IDs 81-96) --

    # Circle 25
    ANTIDOTE = 81
    OWL_SIGHT = 82
    SHIFTING_EARTH = 83
    SUMMON_MAMMALS = 84

    # Circle 26
    CALL_LIGHTNING = 85
    EARTH_BLESSING = 86
    EARTH_PORTAL = 87
    NATURES_TOUCH = 88

    # Circle 27
    GUST_OF_AIR = 89
    RISING_FIRE = 90
    SHAPESHIFT = 91
    ICE_STRIKE = 92

    # Circle 28
    EARTH_SPIRIT = 93
    FLAME_SPIRIT = 94
    STORM_SPIRIT = 95
    WATER_SPIRIT = 96

    # -- Holy Book (Circle 25-28, IDs 166-181) --

    # Circle 25
    GRAND_FEAST = 166
    TURN_UNDEAD = 167
    LIGHT_OF_DAY = 168
    ANGELIC_AURA = 169

    # Circle 26
    HOLY_BOLT = 170
    SERAPHIMS_WILL = 171
    ANGELIC_GATE = 172
    REMOVE_CURSE = 173

    # Circle 27
    WRATH_OF_GOD = 174
    DIVINE_FURY = 175
    ASTRAL_STORM = 176
    ENLIGHTENMENT = 177

    # Circle 28
    REVIVE = 178
    SANCTUARY = 179
    SUMMON_GUARDIAN = 180
    APOCALYPSE = 181

    # -- Song Book (Circle 25-27, IDs 182-197) --

    # Circle 25
    SONG_OF_LIGHT = 182
    SONG_OF_HASTE = 183
    SONG_OF_DEFENSE = 184
    SONG_OF_GLORY = 185

    # Circle 26
    SONG_OF_CLOAKING = 186
    SONG_OF_REMEDY = 187
    SONG_OF_LIFE = 188
    SONG_OF_DISMISSAL = 189

    # Circle 27
    SONG_OF_SIRENS = 190
    SONG_OF_EARTH = 191
    SONG_OF_AIR = 192
    SONG_OF_FIRE = 193
    SONG_OF_WATER = 194
    SONG_OF_BECKON = 195
    SONG_OF_FRIGHT = 196
    SONG_OF_SALVATION = 197
