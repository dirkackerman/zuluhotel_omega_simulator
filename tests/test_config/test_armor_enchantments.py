"""Tests for ArmorEnchantmentRegistry — parsing onhitscriptdesc.cfg."""

from pathlib import Path

import pytest

from omega.config.armor_enchantments import (
    ArmorEnchantment,
    ArmorEnchantmentEntry,
    ArmorEnchantmentRegistry,
    armor_enchantment_onhitscript,
    armor_enchantment_properties,
)
from omega.config.spells import Spell

from tests.conftest import FIXTURE_SHARD_ROOT

ONHITSCRIPT_CFG = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "onhitscriptdesc.cfg"


@pytest.fixture(scope="module")
def registry() -> ArmorEnchantmentRegistry:
    return ArmorEnchantmentRegistry.from_cfg(ONHITSCRIPT_CFG)


# ---------------------------------------------------------------------------
# Registry parsing
# ---------------------------------------------------------------------------


class TestRegistryParsing:
    def test_total_entries(self, registry: ArmorEnchantmentRegistry):
        assert len(registry) == 47

    def test_spell_count(self, registry: ArmorEnchantmentRegistry):
        spells = registry.by_type("Spell")
        assert len(spells) == 18

    def test_race_resistant_count(self, registry: ArmorEnchantmentRegistry):
        races = registry.by_type("RaceResistant")
        assert len(races) == 17

    def test_effect_count(self, registry: ArmorEnchantmentRegistry):
        effects = registry.by_type("Effect")
        assert len(effects) == 7

    def test_greater_count(self, registry: ArmorEnchantmentRegistry):
        greaters = registry.by_type("Greater")
        assert len(greaters) == 5

    def test_all_entries_sorted(self, registry: ArmorEnchantmentRegistry):
        entries = registry.all_entries()
        assert len(entries) == 47
        assert entries[0].id == 1
        assert entries[-1].id == 47
        ids = [e.id for e in entries]
        assert ids == sorted(ids)

    def test_repr(self, registry: ArmorEnchantmentRegistry):
        assert "47" in repr(registry)

    def test_data_block_not_included(self, registry: ArmorEnchantmentRegistry):
        """The 'Data data' block should not be parsed as an Enchantment."""
        assert registry.by_id(0) is None
        assert registry.find("data") is None


# ---------------------------------------------------------------------------
# Lookup by ID
# ---------------------------------------------------------------------------


class TestLookupByID:
    def test_spell_by_id(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(6)
        assert entry is not None
        assert entry.spell_name == "Fireball"
        assert entry.onhitscript == ":combat:spellonhit"

    def test_spell_first(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(1)
        assert entry is not None
        assert entry.spell_name == "Clumsy"
        assert entry.name == "of Bungling"

    def test_spell_last(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(18)
        assert entry is not None
        assert entry.spell_name == "Earthquake"
        assert entry.name == "of Gaia's Wrath"

    def test_race_resistant_by_id(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(32)
        assert entry is not None
        assert entry.race_type == "Undead"
        assert entry.onhitscript == ":combat:raceresistonhit"

    def test_race_resistant_first(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(19)
        assert entry is not None
        assert entry.race_type == "Slime"

    def test_race_resistant_last(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(35)
        assert entry is not None
        assert entry.race_type == "Human"
        assert entry.name == "Bounty Hunter's"

    def test_effect_by_id(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(36)
        assert entry is not None
        assert entry.name == "Reinforced"
        assert entry.onhitscript == ":combat:piercingonhit"

    def test_effect_poison(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(38)
        assert entry is not None
        assert entry.name == "Venomous"
        assert entry.onhitscript == ":combat:poisononhit"
        assert entry.cprop == "Poisonlvl"

    def test_effect_bouncing(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(39)
        assert entry is not None
        assert entry.name == "Displacing"
        assert entry.onhitscript == ":combat:bouncingonhit"
        assert entry.cprop == "ChanceOfEffect"

    def test_greater_by_id(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(43)
        assert entry is not None
        assert entry.onhitscript == ":combat:trielementalonhit"
        assert entry.name == "of Elemental Fury"

    def test_greater_deflection(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(44)
        assert entry is not None
        assert entry.onhitscript == ":combat:deflectiononhit"
        assert entry.cprop == "ChanceOfEffect"
        assert entry.multiplier == 5.0

    def test_greater_avenging(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(45)
        assert entry is not None
        assert entry.onhitscript == ":combat:avengingonhit"
        assert entry.cprop == "Powerlevel"
        assert entry.multiplier == 10.0

    def test_greater_invisible(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(46)
        assert entry is not None
        assert entry.onhitscript == ":combat:invisibleonhit"

    def test_greater_dualplanar(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(47)
        assert entry is not None
        assert entry.onhitscript == ":combat:dualplanaronhit"
        assert entry.cprop == "ChanceOfEffect"
        assert entry.multiplier == 6.0

    def test_missing_id(self, registry: ArmorEnchantmentRegistry):
        assert registry.by_id(999) is None

    def test_missing_id_zero(self, registry: ArmorEnchantmentRegistry):
        assert registry.by_id(0) is None

    def test_missing_id_negative(self, registry: ArmorEnchantmentRegistry):
        assert registry.by_id(-1) is None


# ---------------------------------------------------------------------------
# Find (flexible lookup)
# ---------------------------------------------------------------------------


class TestFind:
    def test_find_by_spell_name(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("Fireball")
        assert entry is not None
        assert entry.id == 6

    def test_find_by_display_name(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("of Daemon's Breath")
        assert entry is not None
        assert entry.id == 6

    def test_find_by_clean_name(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("Daemon's Breath")
        assert entry is not None
        assert entry.id == 6

    def test_find_by_race_type(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("Undead")
        assert entry is not None
        assert entry.id == 32

    def test_find_by_id_string(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("6")
        assert entry is not None
        assert entry.spell_name == "Fireball"

    def test_find_case_insensitive(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("fireball")
        assert entry is not None
        assert entry.id == 6

    def test_find_greater_by_name(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("Elemental Fury")
        assert entry is not None
        assert entry.onhitscript == ":combat:trielementalonhit"

    def test_find_effect_by_name(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("Reinforced")
        assert entry is not None
        assert entry.onhitscript == ":combat:piercingonhit"

    def test_find_unknown(self, registry: ArmorEnchantmentRegistry):
        assert registry.find("Nonexistent") is None

    def test_find_empty_string(self, registry: ArmorEnchantmentRegistry):
        assert registry.find("") is None

    def test_find_whitespace(self, registry: ArmorEnchantmentRegistry):
        # Spaces around a valid name should still match
        entry = registry.find("  Fireball  ")
        assert entry is not None
        assert entry.id == 6

    def test_find_race_type_case_insensitive(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("undead")
        assert entry is not None
        assert entry.race_type == "Undead"

    def test_find_all_race_types(self, registry: ArmorEnchantmentRegistry):
        """Every race type in onhitscriptdesc.cfg should be findable."""
        race_types = [
            "Slime", "Ratkin", "Plant", "Animal", "Beholder", "Orc",
            "Terathan", "Ophidian", "Animated", "Gargoyle", "Troll",
            "Giantkin", "Elemental", "Undead", "Daemon", "Dragonkin", "Human",
        ]
        for race_type in race_types:
            entry = registry.find(race_type)
            assert entry is not None, f"Race type {race_type!r} not found"
            assert entry.race_type == race_type

    def test_find_all_spell_names(self, registry: ArmorEnchantmentRegistry):
        """Every spell name in onhitscriptdesc.cfg should be findable."""
        spell_names = [
            "Clumsy", "Feeblemind", "Magic Arrow", "Weaken", "Harm",
            "Fireball", "Curse", "Lightning", "Mana Drain", "Mind Blast",
            "Paralyze", "Energy Bolt", "Explosion", "Masscurse",
            "Chain Lightning", "Flame Strike", "Meteor Swarm", "Earthquake",
        ]
        for name in spell_names:
            entry = registry.find(name)
            assert entry is not None, f"Spell name {name!r} not found"
            assert entry.onhitscript_type == "Spell"


# ---------------------------------------------------------------------------
# Armor properties
# ---------------------------------------------------------------------------


class TestArmorProperties:
    def test_spell_properties(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("Fireball")
        props = entry.armor_properties
        assert props["HitWithSpell"] == 18
        assert "EffectCircle" not in props  # per-armor, not enchantment

    def test_race_resistant_properties(self, registry: ArmorEnchantmentRegistry):
        entry = registry.find("Undead")
        props = entry.armor_properties
        assert props["ProtectedType"] == "Undead"

    def test_effect_cprop_poison(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(38)  # Venomous
        assert entry.cprop == "Poisonlvl"
        props = entry.armor_properties
        assert "Poisonlvl" in props

    def test_effect_cprop_chance(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(42)  # Blindingly Bright
        assert entry.cprop == "ChanceOfEffect"
        props = entry.armor_properties
        assert props["ChanceOfEffect"] == 10

    def test_greater_cprop_chance(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(43)  # Elemental Fury
        assert entry.cprop == "ChanceOfEffect"
        props = entry.armor_properties
        assert props["ChanceOfEffect"] == 7

    def test_greater_powerlevel(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(45)  # Avenging
        props = entry.armor_properties
        assert props["Powerlevel"] == 10

    def test_effect_no_cprop(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(36)  # Reinforced (piercingonhit)
        assert entry.cprop == ""
        assert entry.armor_properties == {}

    def test_mana_drain_no_cprop(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(40)  # Blackrock-Studded (manadrainonhit)
        assert entry.cprop == ""
        assert entry.armor_properties == {}

    def test_stamina_drain_no_cprop(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(41)  # Sticky (staminadrainonhit)
        assert entry.cprop == ""
        assert entry.armor_properties == {}


# ---------------------------------------------------------------------------
# Entry field details
# ---------------------------------------------------------------------------


class TestEntryFields:
    def test_spell_entry_fields(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(6)  # Fireball
        assert entry.onhitscript_type == "Spell"
        assert entry.onhitscript == ":combat:spellonhit"
        assert entry.name == "of Daemon's Breath"
        assert entry.cursed_name == "of Daemonic Torment"
        assert entry.place == 2  # suffix
        assert entry.spell_id == 18
        assert entry.spell_name == "Fireball"
        assert entry.spell_script == ":spells:fireball"
        assert entry.as_circle_mod == -1
        assert entry.chance_of_effect_mod == 5

    def test_race_entry_fields(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(27)  # Bewitched Hunter
        assert entry.onhitscript_type == "RaceResistant"
        assert entry.onhitscript == ":combat:raceresistonhit"
        assert entry.name == "Bewitched Hunter's"
        assert entry.cursed_name == "Bewitched Bait"
        assert entry.place == 1  # prefix
        assert entry.race_type == "Animated"

    def test_effect_entry_fields(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(37)  # Sundering (banishonhit)
        assert entry.onhitscript_type == "Effect"
        assert entry.onhitscript == ":combat:banishonhit"
        assert entry.name == "Sundering"
        assert entry.cursed_name == "Summoner's"
        assert entry.place == 1

    def test_greater_entry_fields(self, registry: ArmorEnchantmentRegistry):
        entry = registry.by_id(47)  # Wind's Breath (dualplanaronhit)
        assert entry.onhitscript_type == "Greater"
        assert entry.onhitscript == ":combat:dualplanaronhit"
        assert entry.name == "Wind's Breath"
        assert entry.cursed_name == "Hurricane Gale"
        assert entry.place == 1
        assert entry.cprop == "ChanceOfEffect"
        assert entry.multiplier == 6.0

    def test_all_spells_use_spellonhit(self, registry: ArmorEnchantmentRegistry):
        """All 18 spell enchantments must use the same onhitscript."""
        for entry in registry.by_type("Spell"):
            assert entry.onhitscript == ":combat:spellonhit", (
                f"Spell enchantment {entry.id} ({entry.spell_name}) "
                f"uses {entry.onhitscript}, expected :combat:spellonhit"
            )

    def test_all_race_resistant_use_raceresistonhit(self, registry: ArmorEnchantmentRegistry):
        """All 17 race-resistant enchantments must use the same onhitscript."""
        for entry in registry.by_type("RaceResistant"):
            assert entry.onhitscript == ":combat:raceresistonhit", (
                f"Race-resistant enchantment {entry.id} ({entry.race_type}) "
                f"uses {entry.onhitscript}, expected :combat:raceresistonhit"
            )

    def test_all_spells_have_spell_id(self, registry: ArmorEnchantmentRegistry):
        """All spell enchantments must have a non-zero spell_id."""
        for entry in registry.by_type("Spell"):
            assert entry.spell_id > 0, f"Spell enchantment {entry.id} has spell_id=0"

    def test_all_race_resistant_have_type(self, registry: ArmorEnchantmentRegistry):
        """All race-resistant enchantments must have a non-empty race_type."""
        for entry in registry.by_type("RaceResistant"):
            assert entry.race_type, f"RaceResistant enchantment {entry.id} has empty race_type"

    def test_all_spells_have_script(self, registry: ArmorEnchantmentRegistry):
        """All spell enchantments must have a spell script path."""
        for entry in registry.by_type("Spell"):
            assert entry.spell_script.startswith(":"), (
                f"Spell enchantment {entry.id} ({entry.spell_name}) "
                f"has spell_script={entry.spell_script!r}"
            )

    def test_spell_circle_mods_range(self, registry: ArmorEnchantmentRegistry):
        """Circle mods should be in a reasonable range."""
        for entry in registry.by_type("Spell"):
            assert -5 <= entry.as_circle_mod <= 5, (
                f"Spell {entry.spell_name} has unexpected circle mod: {entry.as_circle_mod}"
            )


# ---------------------------------------------------------------------------
# Clean name
# ---------------------------------------------------------------------------


class TestCleanName:
    def test_clean_name_strips_of(self):
        entry = ArmorEnchantmentEntry(
            id=1, onhitscript_type="Spell", onhitscript="", name="of Burning",
        )
        assert entry.clean_name == "Burning"

    def test_clean_name_no_prefix(self):
        entry = ArmorEnchantmentEntry(
            id=1, onhitscript_type="RaceResistant", onhitscript="", name="Slime Hunter's",
        )
        assert entry.clean_name == "Slime Hunter's"

    def test_clean_name_case_insensitive_of(self):
        entry = ArmorEnchantmentEntry(
            id=1, onhitscript_type="Spell", onhitscript="", name="Of Thunder",
        )
        assert entry.clean_name == "Thunder"

    def test_clean_name_whitespace(self):
        entry = ArmorEnchantmentEntry(
            id=1, onhitscript_type="Spell", onhitscript="", name="  of Burning  ",
        )
        assert entry.clean_name == "Burning"

    def test_clean_name_empty(self):
        entry = ArmorEnchantmentEntry(
            id=1, onhitscript_type="Spell", onhitscript="", name="",
        )
        assert entry.clean_name == ""


# ---------------------------------------------------------------------------
# Empty registry
# ---------------------------------------------------------------------------


class TestEmptyRegistry:
    def test_empty(self):
        reg = ArmorEnchantmentRegistry()
        assert len(reg) == 0
        assert reg.find("anything") is None
        assert reg.by_id(1) is None
        assert reg.all_entries() == []
        assert reg.by_type("Spell") == []

    def test_repr_empty(self):
        reg = ArmorEnchantmentRegistry()
        assert "0" in repr(reg)


# ---------------------------------------------------------------------------
# ArmorEnchantment enum
# ---------------------------------------------------------------------------


class TestArmorEnchantmentEnum:
    def test_spell_enchantment_value(self):
        assert ArmorEnchantment.OF_DAEMONS_BREATH == 6

    def test_race_resistant_enchantment_value(self):
        assert ArmorEnchantment.UNDEAD_HUNTER == 32

    def test_effect_enchantment_value(self):
        assert ArmorEnchantment.REINFORCED == 36

    def test_greater_enchantment_value(self):
        assert ArmorEnchantment.OF_ELEMENTAL_FURY == 43

    def test_all_47_members(self):
        assert len(ArmorEnchantment) == 47

    def test_from_int(self):
        e = ArmorEnchantment(6)
        assert e is ArmorEnchantment.OF_DAEMONS_BREATH

    def test_from_int_invalid(self):
        with pytest.raises(ValueError):
            ArmorEnchantment(999)

    def test_spell_range(self):
        """Spells are IDs 1-18."""
        spell_ids = [e.value for e in ArmorEnchantment if 1 <= e.value <= 18]
        assert len(spell_ids) == 18

    def test_race_range(self):
        """Race-resistant are IDs 19-35."""
        race_ids = [e.value for e in ArmorEnchantment if 19 <= e.value <= 35]
        assert len(race_ids) == 17

    def test_effect_range(self):
        """Effects are IDs 36-42."""
        effect_ids = [e.value for e in ArmorEnchantment if 36 <= e.value <= 42]
        assert len(effect_ids) == 7

    def test_greater_range(self):
        """Greaters are IDs 43-47."""
        greater_ids = [e.value for e in ArmorEnchantment if 43 <= e.value <= 47]
        assert len(greater_ids) == 5

    def test_contiguous_ids(self):
        """All IDs from 1 to 47 should be present."""
        ids = sorted(e.value for e in ArmorEnchantment)
        assert ids == list(range(1, 48))


# ---------------------------------------------------------------------------
# ArmorEnchantment meta (module-level functions)
# ---------------------------------------------------------------------------


class TestArmorEnchantmentMeta:
    def test_spell_onhitscript(self):
        assert armor_enchantment_onhitscript(ArmorEnchantment.OF_DAEMONS_BREATH) == ":combat:spellonhit"

    def test_spell_properties_use_spell_enum(self):
        props = armor_enchantment_properties(ArmorEnchantment.OF_DAEMONS_BREATH)
        assert props["HitWithSpell"] == Spell.FIREBALL
        assert "EffectCircle" not in props

    def test_race_onhitscript(self):
        assert armor_enchantment_onhitscript(ArmorEnchantment.UNDEAD_HUNTER) == ":combat:raceresistonhit"

    def test_race_properties(self):
        props = armor_enchantment_properties(ArmorEnchantment.UNDEAD_HUNTER)
        assert props["ProtectedType"] == "Undead"

    def test_effect_onhitscript(self):
        assert armor_enchantment_onhitscript(ArmorEnchantment.REINFORCED) == ":combat:piercingonhit"

    def test_effect_properties_empty(self):
        props = armor_enchantment_properties(ArmorEnchantment.REINFORCED)
        assert props == {}

    def test_effect_properties_poison(self):
        props = armor_enchantment_properties(ArmorEnchantment.VENOMOUS)
        assert props == {"Poisonlvl": 0}

    def test_greater_onhitscript(self):
        assert armor_enchantment_onhitscript(ArmorEnchantment.OF_ELEMENTAL_FURY) == ":combat:trielementalonhit"

    def test_greater_properties(self):
        props = armor_enchantment_properties(ArmorEnchantment.OF_ELEMENTAL_FURY)
        assert props["ChanceOfEffect"] == 7

    def test_greater_avenging_properties(self):
        props = armor_enchantment_properties(ArmorEnchantment.AVENGING)
        assert props["Powerlevel"] == 10

    def test_all_meta_keys_present(self):
        """Every ArmorEnchantment member should have an entry in _ARMOR_ENCHANTMENT_META."""
        for e in ArmorEnchantment:
            script = armor_enchantment_onhitscript(e)
            assert script.startswith(":"), f"Enchantment {e.name} has invalid script: {script}"

    def test_meta_returns_new_dict(self):
        """Properties should be a fresh copy to prevent mutation."""
        props1 = armor_enchantment_properties(ArmorEnchantment.OF_DAEMONS_BREATH)
        props2 = armor_enchantment_properties(ArmorEnchantment.OF_DAEMONS_BREATH)
        assert props1 == props2
        props1["extra"] = 42
        assert "extra" not in armor_enchantment_properties(ArmorEnchantment.OF_DAEMONS_BREATH)


# ---------------------------------------------------------------------------
# Cross-validation: enum vs cfg
# ---------------------------------------------------------------------------


class TestEnumCfgConsistency:
    """Verify that the ArmorEnchantment enum matches the parsed cfg exactly."""

    def test_enum_ids_match_cfg_ids(self, registry: ArmorEnchantmentRegistry):
        enum_ids = {e.value for e in ArmorEnchantment}
        cfg_ids = {entry.id for entry in registry.all_entries()}
        assert enum_ids == cfg_ids, (
            f"Enum/cfg ID mismatch: enum-only={enum_ids - cfg_ids}, cfg-only={cfg_ids - enum_ids}"
        )

    def test_meta_scripts_match_cfg_scripts(self, registry: ArmorEnchantmentRegistry):
        """The hardcoded meta dict should match the parsed cfg for each entry."""
        for entry in registry.all_entries():
            meta_script = armor_enchantment_onhitscript(ArmorEnchantment(entry.id))
            assert meta_script == entry.onhitscript, (
                f"Script mismatch for ID {entry.id}: "
                f"meta={meta_script}, cfg={entry.onhitscript}"
            )

    def test_meta_spell_ids_match_cfg(self, registry: ArmorEnchantmentRegistry):
        """For spell enchantments, the meta HitWithSpell must match cfg spell_id."""
        for entry in registry.by_type("Spell"):
            meta_props = armor_enchantment_properties(ArmorEnchantment(entry.id))
            assert "HitWithSpell" in meta_props, f"Missing HitWithSpell in meta for ID {entry.id}"
            assert int(meta_props["HitWithSpell"]) == entry.spell_id, (
                f"HitWithSpell mismatch for ID {entry.id}: "
                f"meta={meta_props['HitWithSpell']}, cfg={entry.spell_id}"
            )

    def test_meta_race_types_match_cfg(self, registry: ArmorEnchantmentRegistry):
        """For race-resistant enchantments, the meta ProtectedType must match cfg race_type."""
        for entry in registry.by_type("RaceResistant"):
            meta_props = armor_enchantment_properties(ArmorEnchantment(entry.id))
            assert "ProtectedType" in meta_props, f"Missing ProtectedType in meta for ID {entry.id}"
            assert meta_props["ProtectedType"] == entry.race_type, (
                f"ProtectedType mismatch for ID {entry.id}: "
                f"meta={meta_props['ProtectedType']}, cfg={entry.race_type}"
            )
