"""Tests for EnchantmentRegistry — parsing hitscriptdesc.cfg."""

from pathlib import Path

import pytest

from omega.config.enchantments import (
    Enchantment,
    EnchantmentEntry,
    EnchantmentRegistry,
    enchantment_hitscript,
    enchantment_properties,
)
from omega.config.spells import Spell

from tests.conftest import FIXTURE_SHARD_ROOT

HITSCRIPT_CFG = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "hitscriptdesc.cfg"


@pytest.fixture(scope="module")
def registry() -> EnchantmentRegistry:
    return EnchantmentRegistry.from_cfg(HITSCRIPT_CFG)


class TestRegistryParsing:
    def test_total_entries(self, registry: EnchantmentRegistry):
        assert len(registry) == 45

    def test_spell_count(self, registry: EnchantmentRegistry):
        spells = registry.by_type("Spell")
        assert len(spells) == 18

    def test_slayer_count(self, registry: EnchantmentRegistry):
        slayers = registry.by_type("Slayer")
        assert len(slayers) == 17

    def test_effect_count(self, registry: EnchantmentRegistry):
        effects = registry.by_type("Effect")
        assert len(effects) == 7

    def test_greater_count(self, registry: EnchantmentRegistry):
        greaters = registry.by_type("Greater")
        assert len(greaters) == 3


class TestLookupByID:
    def test_spell_by_id(self, registry: EnchantmentRegistry):
        entry = registry.by_id(6)
        assert entry is not None
        assert entry.spell_name == "Fireball"
        assert entry.hitscript == ":combat:spellstrikescript"

    def test_slayer_by_id(self, registry: EnchantmentRegistry):
        entry = registry.by_id(32)
        assert entry is not None
        assert entry.slayer_type == "Undead"

    def test_effect_by_id(self, registry: EnchantmentRegistry):
        entry = registry.by_id(36)
        assert entry is not None
        assert entry.name == "of Piercing"

    def test_greater_by_id(self, registry: EnchantmentRegistry):
        entry = registry.by_id(43)
        assert entry is not None
        assert entry.hitscript == ":combat:dualplanarscript"

    def test_missing_id(self, registry: EnchantmentRegistry):
        assert registry.by_id(999) is None


class TestFind:
    def test_find_by_spell_name(self, registry: EnchantmentRegistry):
        entry = registry.find("Fireball")
        assert entry is not None
        assert entry.id == 6

    def test_find_by_display_name(self, registry: EnchantmentRegistry):
        entry = registry.find("of Daemon's Breath")
        assert entry is not None
        assert entry.id == 6

    def test_find_by_clean_name(self, registry: EnchantmentRegistry):
        entry = registry.find("Daemon's Breath")
        assert entry is not None
        assert entry.id == 6

    def test_find_by_slayer_type(self, registry: EnchantmentRegistry):
        entry = registry.find("Undead")
        assert entry is not None
        assert entry.id == 32

    def test_find_by_id_string(self, registry: EnchantmentRegistry):
        entry = registry.find("6")
        assert entry is not None
        assert entry.spell_name == "Fireball"

    def test_find_case_insensitive(self, registry: EnchantmentRegistry):
        entry = registry.find("fireball")
        assert entry is not None
        assert entry.id == 6

    def test_find_greater_by_name(self, registry: EnchantmentRegistry):
        entry = registry.find("Planar Fury")
        assert entry is not None
        assert entry.hitscript == ":combat:dualplanarscript"

    def test_find_effect_by_name(self, registry: EnchantmentRegistry):
        entry = registry.find("Piercing")
        assert entry is not None
        assert entry.hitscript == ":combat:piercingscript"

    def test_find_unknown(self, registry: EnchantmentRegistry):
        assert registry.find("Nonexistent") is None


class TestWeaponProperties:
    def test_spell_properties(self, registry: EnchantmentRegistry):
        entry = registry.find("Fireball")
        props = entry.weapon_properties
        assert props["HitWithSpell"] == 18
        assert "EffectCircle" not in props  # per-weapon, not enchantment

    def test_slayer_properties(self, registry: EnchantmentRegistry):
        entry = registry.find("Undead")
        props = entry.weapon_properties
        assert props["SlayType"] == "Undead"

    def test_effect_cprop(self, registry: EnchantmentRegistry):
        entry = registry.by_id(43)  # Planar Fury
        assert entry.cprop == "ChanceOfEffect"
        props = entry.weapon_properties
        assert "ChanceOfEffect" in props
        assert props["ChanceOfEffect"] == 7

    def test_void_no_cprop(self, registry: EnchantmentRegistry):
        entry = registry.by_id(44)  # Void
        assert entry.cprop == ""
        assert entry.weapon_properties == {}


class TestEmptyRegistry:
    def test_empty(self):
        reg = EnchantmentRegistry()
        assert len(reg) == 0
        assert reg.find("anything") is None
        assert reg.by_id(1) is None
        assert reg.all_entries() == []


class TestEnchantmentEntry:
    def test_clean_name_strips_of(self):
        entry = EnchantmentEntry(id=1, hitscript_type="Spell", hitscript="", name="of Burning")
        assert entry.clean_name == "Burning"

    def test_clean_name_no_prefix(self):
        entry = EnchantmentEntry(id=1, hitscript_type="Slayer", hitscript="", name="Slayer")
        assert entry.clean_name == "Slayer"


class TestEnchantmentEnum:
    def test_spell_enchantment_value(self):
        assert Enchantment.OF_DAEMONS_BREATH == 6

    def test_slayer_enchantment_value(self):
        assert Enchantment.SILVER == 32

    def test_effect_enchantment_value(self):
        assert Enchantment.OF_PIERCING == 36

    def test_greater_enchantment_value(self):
        assert Enchantment.OF_PLANAR_FURY == 43

    def test_all_45_members(self):
        assert len(Enchantment) == 45

    def test_from_int(self):
        e = Enchantment(6)
        assert e is Enchantment.OF_DAEMONS_BREATH


class TestEnchantmentMeta:
    def test_spell_hitscript(self):
        assert enchantment_hitscript(Enchantment.OF_DAEMONS_BREATH) == ":combat:spellstrikescript"

    def test_spell_properties_use_spell_enum(self):
        props = enchantment_properties(Enchantment.OF_DAEMONS_BREATH)
        assert props["HitWithSpell"] == Spell.FIREBALL
        assert "EffectCircle" not in props

    def test_slayer_hitscript(self):
        assert enchantment_hitscript(Enchantment.SILVER) == ":combat:slayerscript"

    def test_slayer_properties_use_slaytype(self):
        props = enchantment_properties(Enchantment.SILVER)
        assert props["SlayType"] == "Undead"

    def test_effect_hitscript(self):
        assert enchantment_hitscript(Enchantment.OF_PIERCING) == ":combat:piercingscript"

    def test_greater_properties(self):
        props = enchantment_properties(Enchantment.OF_PLANAR_FURY)
        assert props["ChanceOfEffect"] == 7

    def test_void_no_properties(self):
        props = enchantment_properties(Enchantment.OF_THE_VOID)
        assert props == {}


class TestSpellEnum:
    def test_standard_spell(self):
        assert Spell.FIREBALL == 18

    def test_necro_spell(self):
        assert Spell.ABYSSAL_FLAME == 69

    def test_earth_spell(self):
        assert Spell.ICE_STRIKE == 92

    def test_holy_spell(self):
        assert Spell.ANGELIC_AURA == 169

    def test_song_spell(self):
        assert Spell.SONG_OF_FIRE == 193

    def test_from_int(self):
        s = Spell(169)
        assert s is Spell.ANGELIC_AURA
