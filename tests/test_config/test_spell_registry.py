"""Tests for SpellRegistry — parsing spells.cfg and circles.cfg."""

from pathlib import Path

import pytest

from omega.config.spell_registry import (
    CASTABLE_SPELL_IDS,
    DAMAGE_SPELL_IDS,
    NON_DAMAGE_SPELL_IDS,
    CircleConfig,
    SpellEntry,
    SpellRegistry,
)
from omega.config.spells import Spell

from tests.conftest import FIXTURE_SHARD_ROOT

CIRCLES_CFG = FIXTURE_SHARD_ROOT / "config" / "circles.cfg"

SPELL_CFG_PATHS: list[tuple[Path, str]] = [
    (FIXTURE_SHARD_ROOT / "pkg" / "std" / "spells" / "spells.cfg", "Standard"),
    (FIXTURE_SHARD_ROOT / "pkg" / "opt" / "necro" / "spells.cfg", "Necromancy"),
    (FIXTURE_SHARD_ROOT / "pkg" / "opt" / "earth" / "spells.cfg", "Earth"),
    (FIXTURE_SHARD_ROOT / "pkg" / "opt" / "holybook" / "spells.cfg", "Holy"),
    (FIXTURE_SHARD_ROOT / "pkg" / "opt" / "songbook" / "spells.cfg", "Song"),
]


@pytest.fixture(scope="module")
def registry() -> SpellRegistry:
    return SpellRegistry.from_cfg(SPELL_CFG_PATHS, CIRCLES_CFG)


# ---------------------------------------------------------------------------
# Circle parsing
# ---------------------------------------------------------------------------


class TestCircleParsing:
    def test_total_circles(self, registry: SpellRegistry):
        """All 33 circles parsed from circles.cfg."""
        count = sum(1 for i in range(1, 34) if registry.circle(i) is not None)
        assert count == 33

    def test_circle_1_values(self, registry: SpellRegistry):
        c = registry.circle(1)
        assert c is not None
        assert c.mana == 4
        assert c.difficulty == 20
        assert c.point_value == 75
        assert c.delay == 500
        assert c.use_circle == 0

    def test_circle_8_values(self, registry: SpellRegistry):
        c = registry.circle(8)
        assert c is not None
        assert c.mana == 50
        assert c.difficulty == 90
        assert c.point_value == 800
        assert c.delay == 2700
        assert c.use_circle == 0

    def test_circle_21_use_circle(self, registry: SpellRegistry):
        """Necro lower circle remaps to standard circle 10."""
        c = registry.circle(21)
        assert c is not None
        assert c.use_circle == 10
        assert c.mana == 40
        assert c.difficulty == 80

    def test_circle_28_use_circle(self, registry: SpellRegistry):
        """Earth higher circle remaps to standard circle 12."""
        c = registry.circle(28)
        assert c is not None
        assert c.use_circle == 12

    def test_standard_circles_no_use_circle(self, registry: SpellRegistry):
        """Circles 1-20 have no UseCircle remapping."""
        for i in range(1, 21):
            c = registry.circle(i)
            assert c is not None, f"Circle {i} missing"
            assert c.use_circle == 0, f"Circle {i} has unexpected use_circle={c.use_circle}"

    def test_effective_circle_standard(self, registry: SpellRegistry):
        """Standard circle returns itself."""
        assert registry.effective_circle(3) == 3
        assert registry.effective_circle(7) == 7

    def test_effective_circle_necro(self, registry: SpellRegistry):
        """Necro circle 21 remaps to standard circle 10."""
        assert registry.effective_circle(21) == 10

    def test_effective_circle_earth(self, registry: SpellRegistry):
        """Earth circles remap to standard circles."""
        assert registry.effective_circle(25) == 6
        assert registry.effective_circle(26) == 8
        assert registry.effective_circle(27) == 10
        assert registry.effective_circle(28) == 12

    def test_circle_missing(self, registry: SpellRegistry):
        assert registry.circle(99) is None

    def test_effective_circle_missing_returns_input(self, registry: SpellRegistry):
        """Non-existent circle returns the input number unchanged."""
        assert registry.effective_circle(99) == 99


# ---------------------------------------------------------------------------
# Spell parsing
# ---------------------------------------------------------------------------


class TestSpellParsing:
    def test_total_spells(self, registry: SpellRegistry):
        """128 spells across all 5 config files."""
        assert len(registry) == 128

    def test_standard_spell_count(self, registry: SpellRegistry):
        assert len(registry.by_school("Standard")) == 64

    def test_necro_spell_count(self, registry: SpellRegistry):
        assert len(registry.by_school("Necromancy")) == 16

    def test_earth_spell_count(self, registry: SpellRegistry):
        assert len(registry.by_school("Earth")) == 16

    def test_holy_spell_count(self, registry: SpellRegistry):
        assert len(registry.by_school("Holy")) == 16

    def test_song_spell_count(self, registry: SpellRegistry):
        assert len(registry.by_school("Song")) == 16

    def test_fireball_fields(self, registry: SpellRegistry):
        entry = registry.by_id(Spell.FIREBALL)
        assert entry is not None
        assert entry.id == 18
        assert entry.name == "Fireball"
        assert entry.script == "fireball"
        assert entry.circle == 3
        assert entry.school == "Standard"
        assert entry.power_words == "Vas Flam"

    def test_kill_fields(self, registry: SpellRegistry):
        entry = registry.by_id(Spell.KILL)
        assert entry is not None
        assert entry.id == 77
        assert entry.name == "Kill"
        assert entry.circle == 24
        assert entry.school == "Necromancy"
        assert entry.script == "kill"

    def test_holy_bolt_fields(self, registry: SpellRegistry):
        entry = registry.by_id(Spell.HOLY_BOLT)
        assert entry is not None
        assert entry.id == 170
        assert entry.circle == 26
        assert entry.school == "Holy"

    def test_spell_id_case_insensitive(self, registry: SpellRegistry):
        """Earth spells use SpellID (capital D), Holy uses SpellID too.
        Both parse correctly."""
        # Earth spell
        entry = registry.by_id(Spell.SHIFTING_EARTH)
        assert entry is not None
        assert entry.id == 83
        # Holy spell
        entry = registry.by_id(Spell.APOCALYPSE)
        assert entry is not None
        assert entry.id == 181

    def test_flame_strike_name(self, registry: SpellRegistry):
        """FlameStrike (no space) as written in cfg."""
        entry = registry.by_id(Spell.FLAME_STRIKE)
        assert entry is not None
        assert entry.name == "FlameStrike"
        assert entry.script == "fstrike"


# ---------------------------------------------------------------------------
# Damage spells
# ---------------------------------------------------------------------------


class TestDamageSpells:
    def test_castable_spell_count(self):
        """All 29 castable spells (damage + non-damage with scripts)."""
        assert len(CASTABLE_SPELL_IDS) == 29

    def test_damage_spell_count(self):
        """26 spells that deal direct damage."""
        assert len(DAMAGE_SPELL_IDS) == 26

    def test_non_damage_spell_count(self):
        """3 spells reclassified as non-damage (AR debuff, CC, pet mechanic)."""
        assert len(NON_DAMAGE_SPELL_IDS) == 3

    def test_sets_partition_correctly(self):
        """DAMAGE + NON_DAMAGE = CASTABLE, no overlap."""
        assert DAMAGE_SPELL_IDS | NON_DAMAGE_SPELL_IDS == CASTABLE_SPELL_IDS
        assert DAMAGE_SPELL_IDS & NON_DAMAGE_SPELL_IDS == frozenset()

    def test_non_damage_members(self):
        """Reclassified non-damage spells are correct."""
        assert Spell.DECAYING_RAY in NON_DAMAGE_SPELL_IDS
        assert Spell.WRAITHS_BREATH in NON_DAMAGE_SPELL_IDS
        assert Spell.SACRIFICE in NON_DAMAGE_SPELL_IDS

    def test_all_castable_spells_resolvable(self, registry: SpellRegistry):
        """Every castable spell ID resolves to a SpellEntry."""
        for spell_id in CASTABLE_SPELL_IDS:
            entry = registry.by_id(spell_id)
            assert entry is not None, f"Spell {spell_id!r} ({spell_id.name}) not found in registry"

    def test_damage_spells_have_circles(self, registry: SpellRegistry):
        for spell_id in DAMAGE_SPELL_IDS:
            entry = registry.by_id(spell_id)
            assert entry is not None
            assert entry.circle > 0, f"Spell {spell_id.name} has circle={entry.circle}"

    def test_damage_spells_have_scripts(self, registry: SpellRegistry):
        for spell_id in CASTABLE_SPELL_IDS:
            entry = registry.by_id(spell_id)
            assert entry is not None
            assert entry.script, f"Spell {spell_id.name} has empty script"

    def test_no_song_damage_spells(self):
        """No songs should be in any spell set."""
        song_ids = range(182, 198)
        for sid in song_ids:
            assert sid not in DAMAGE_SPELL_IDS
            assert sid not in CASTABLE_SPELL_IDS

    def test_damage_spell_schools(self, registry: SpellRegistry):
        """At least one damage spell from each of the 4 schools."""
        schools = {registry.by_id(sid).school for sid in DAMAGE_SPELL_IDS if registry.by_id(sid)}
        assert "Standard" in schools
        assert "Necromancy" in schools
        assert "Earth" in schools
        assert "Holy" in schools

    def test_damage_spells_method(self, registry: SpellRegistry):
        """registry.damage_spells() returns the correct list."""
        dmg = registry.damage_spells()
        assert len(dmg) == 26
        ids = {e.id for e in dmg}
        assert ids == set(DAMAGE_SPELL_IDS)

    def test_damage_spells_sorted_by_id(self, registry: SpellRegistry):
        dmg = registry.damage_spells()
        ids = [e.id for e in dmg]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


class TestLookup:
    def test_by_id_existing(self, registry: SpellRegistry):
        entry = registry.by_id(Spell.FIREBALL)
        assert entry is not None
        assert entry.name == "Fireball"

    def test_by_id_with_int(self, registry: SpellRegistry):
        """Raw int works the same as Spell enum."""
        entry = registry.by_id(18)
        assert entry is not None
        assert entry.name == "Fireball"

    def test_by_id_missing(self, registry: SpellRegistry):
        assert registry.by_id(999) is None

    def test_find_by_name(self, registry: SpellRegistry):
        entry = registry.find("Fireball")
        assert entry is not None
        assert entry.id == 18

    def test_find_by_name_case_insensitive(self, registry: SpellRegistry):
        entry = registry.find("fireball")
        assert entry is not None
        assert entry.id == 18

    def test_find_by_id_string(self, registry: SpellRegistry):
        entry = registry.find("18")
        assert entry is not None
        assert entry.name == "Fireball"

    def test_find_missing(self, registry: SpellRegistry):
        assert registry.find("nonexistent_spell") is None

    def test_find_by_name_with_whitespace(self, registry: SpellRegistry):
        entry = registry.find("  Chain Lightning  ")
        assert entry is not None
        assert entry.id == 49


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_value_keys_ignored(self, registry: SpellRegistry):
        """Spells with Change/Duration/Amount (empty-value keys) parse fine."""
        # Spell 1 (Clumsy) has Change and Duration with no value
        entry = registry.by_id(Spell.CLUMSY)
        assert entry is not None
        assert entry.name == "Clumsy"

    def test_fireball_reagents(self, registry: SpellRegistry):
        entry = registry.by_id(Spell.FIREBALL)
        assert entry is not None
        assert entry.reagents == ("blackpearl",)

    def test_chain_lightning_reagents(self, registry: SpellRegistry):
        entry = registry.by_id(Spell.CHAIN_LIGHTNING)
        assert entry is not None
        assert len(entry.reagents) == 4
        # All reagents present (order from cfg)
        reagent_lower = tuple(r.lower() for r in entry.reagents)
        assert "bloodmoss" in reagent_lower
        assert "mandrakeroot" in reagent_lower
        assert "blackpearl" in reagent_lower
        assert "sulphurousash" in reagent_lower

    def test_kill_reagents(self, registry: SpellRegistry):
        """Kill has 7 reagents."""
        entry = registry.by_id(Spell.KILL)
        assert entry is not None
        assert len(entry.reagents) == 7

    def test_power_words(self, registry: SpellRegistry):
        entry = registry.by_id(Spell.FLAME_STRIKE)
        assert entry is not None
        assert entry.power_words == "Kal Vas Flam"

    def test_double_space_spell_5(self, registry: SpellRegistry):
        """Standard spells.cfg has 'Spell  5' (double space) — parses to id 5."""
        entry = registry.by_id(Spell.MAGIC_ARROW)
        assert entry is not None
        assert entry.id == 5
        assert entry.script == "magicarrow"

    def test_spell_with_many_reagents_tuple_type(self, registry: SpellRegistry):
        """Reagents are stored as a tuple, not a list."""
        entry = registry.by_id(Spell.KILL)
        assert isinstance(entry.reagents, tuple)

    def test_all_entries_sorted(self, registry: SpellRegistry):
        entries = registry.all_entries()
        ids = [e.id for e in entries]
        assert ids == sorted(ids)

    def test_registry_repr(self, registry: SpellRegistry):
        r = repr(registry)
        assert "SpellRegistry" in r
        assert "spells=128" in r
        assert "circles=33" in r


# ---------------------------------------------------------------------------
# Registry construction from shard path
# ---------------------------------------------------------------------------


class TestRegistryFromShard:
    def test_by_school_method(self, registry: SpellRegistry):
        necro = registry.by_school("Necromancy")
        assert len(necro) == 16
        assert all(e.school == "Necromancy" for e in necro)

    def test_by_school_sorted_by_id(self, registry: SpellRegistry):
        std = registry.by_school("Standard")
        ids = [e.id for e in std]
        assert ids == sorted(ids)

    def test_by_school_empty(self, registry: SpellRegistry):
        assert registry.by_school("NonExistent") == []

    def test_empty_registry(self):
        """Empty registry works without errors."""
        reg = SpellRegistry()
        assert len(reg) == 0
        assert reg.by_id(1) is None
        assert reg.find("Fireball") is None
        assert reg.circle(1) is None
        assert reg.damage_spells() == []
