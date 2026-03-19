"""Tests for CreatureType enum — canonical slayer/race type names."""

import pytest

from omega.config.armor_enchantments import (
    ArmorEnchantment,
    ArmorEnchantmentRegistry,
    armor_enchantment_properties,
)
from omega.config.creature_types import CreatureType
from omega.config.enchantments import (
    Enchantment,
    EnchantmentRegistry,
    enchantment_properties,
)

from tests.conftest import FIXTURE_SHARD_ROOT

HITSCRIPT_CFG = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "hitscriptdesc.cfg"
ONHITSCRIPT_CFG = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "onhitscriptdesc.cfg"


@pytest.fixture(scope="module")
def weapon_registry() -> EnchantmentRegistry:
    return EnchantmentRegistry.from_cfg(HITSCRIPT_CFG)


@pytest.fixture(scope="module")
def armor_registry() -> ArmorEnchantmentRegistry:
    return ArmorEnchantmentRegistry.from_cfg(ONHITSCRIPT_CFG)


# ---------------------------------------------------------------------------
# Enum basics
# ---------------------------------------------------------------------------


class TestCreatureTypeEnum:
    def test_member_count(self):
        assert len(CreatureType) == 17

    def test_is_str(self):
        """CreatureType members are str instances for seamless property use."""
        for ct in CreatureType:
            assert isinstance(ct, str)

    def test_str_equality(self):
        assert CreatureType.UNDEAD == "Undead"
        assert CreatureType.DAEMON == "Daemon"
        assert CreatureType.HUMAN == "Human"

    def test_str_inequality(self):
        assert CreatureType.UNDEAD != "Daemon"

    def test_all_values_title_case(self):
        """All values should be title-case to match shard config files."""
        for ct in CreatureType:
            assert ct.value == ct.value[0].upper() + ct.value[1:], (
                f"{ct.name} value {ct.value!r} is not title-case"
            )

    def test_all_values_unique(self):
        values = [ct.value for ct in CreatureType]
        assert len(values) == len(set(values))

    def test_from_value(self):
        assert CreatureType("Undead") is CreatureType.UNDEAD

    def test_from_value_invalid(self):
        with pytest.raises(ValueError):
            CreatureType("Nonexistent")

    def test_expected_members(self):
        expected = {
            "Slime", "Ratkin", "Plant", "Animal", "Beholder", "Orc",
            "Terathan", "Ophidian", "Animated", "Gargoyle", "Troll",
            "Giantkin", "Elemental", "Undead", "Daemon", "Dragonkin", "Human",
        }
        actual = {ct.value for ct in CreatureType}
        assert actual == expected


# ---------------------------------------------------------------------------
# Weapon enchantment meta uses CreatureType
# ---------------------------------------------------------------------------


class TestWeaponEnchantmentMetaUsesCreatureType:
    """Verify all SlayType values in _ENCHANTMENT_META are CreatureType instances."""

    _SLAYER_IDS = range(19, 36)  # Enchantments 19-35 are slayers

    def test_all_slayer_meta_use_creature_type(self):
        for eid in self._SLAYER_IDS:
            props = enchantment_properties(Enchantment(eid))
            slay_type = props.get("SlayType")
            assert slay_type is not None, f"Enchantment {eid} missing SlayType"
            assert isinstance(slay_type, CreatureType), (
                f"Enchantment {eid} SlayType={slay_type!r} is {type(slay_type).__name__}, "
                f"expected CreatureType"
            )

    def test_slayer_str_equality_preserved(self):
        """str(CreatureType.X) == "X" so existing code still works."""
        props = enchantment_properties(Enchantment.SILVER)
        assert props["SlayType"] == "Undead"

    def test_slayer_meta_covers_all_creature_types(self):
        """Every CreatureType should appear in at least one weapon slayer."""
        seen = set()
        for eid in self._SLAYER_IDS:
            props = enchantment_properties(Enchantment(eid))
            seen.add(props["SlayType"])
        for ct in CreatureType:
            assert ct in seen, f"CreatureType.{ct.name} not found in weapon slayer meta"


class TestWeaponRegistryWithCreatureType:
    def test_find_by_creature_type(self, weapon_registry: EnchantmentRegistry):
        """Registry.find() should accept CreatureType values."""
        entry = weapon_registry.find(CreatureType.UNDEAD)
        assert entry is not None
        assert entry.slayer_type == "Undead"

    def test_slayer_type_matches_creature_type(self, weapon_registry: EnchantmentRegistry):
        """Parsed slayer_type from cfg should equal CreatureType value."""
        entry = weapon_registry.find("Undead")
        assert entry.slayer_type == CreatureType.UNDEAD


# ---------------------------------------------------------------------------
# Armor enchantment meta uses CreatureType
# ---------------------------------------------------------------------------


class TestArmorEnchantmentMetaUsesCreatureType:
    """Verify all ProtectedType values in _ARMOR_ENCHANTMENT_META are CreatureType instances."""

    _RACE_IDS = range(19, 36)  # Enchantments 19-35 are race-resistant

    def test_all_race_meta_use_creature_type(self):
        for eid in self._RACE_IDS:
            props = armor_enchantment_properties(ArmorEnchantment(eid))
            prot_type = props.get("ProtectedType")
            assert prot_type is not None, f"ArmorEnchantment {eid} missing ProtectedType"
            assert isinstance(prot_type, CreatureType), (
                f"ArmorEnchantment {eid} ProtectedType={prot_type!r} is {type(prot_type).__name__}, "
                f"expected CreatureType"
            )

    def test_race_str_equality_preserved(self):
        props = armor_enchantment_properties(ArmorEnchantment.UNDEAD_HUNTER)
        assert props["ProtectedType"] == "Undead"

    def test_race_meta_covers_all_creature_types(self):
        """Every CreatureType should appear in at least one armor race-resistant."""
        seen = set()
        for eid in self._RACE_IDS:
            props = armor_enchantment_properties(ArmorEnchantment(eid))
            seen.add(props["ProtectedType"])
        for ct in CreatureType:
            assert ct in seen, f"CreatureType.{ct.name} not found in armor race-resistant meta"


class TestArmorRegistryWithCreatureType:
    def test_find_by_creature_type(self, armor_registry: ArmorEnchantmentRegistry):
        entry = armor_registry.find(CreatureType.UNDEAD)
        assert entry is not None
        assert entry.race_type == "Undead"

    def test_race_type_matches_creature_type(self, armor_registry: ArmorEnchantmentRegistry):
        entry = armor_registry.find("Undead")
        assert entry.race_type == CreatureType.UNDEAD


# ---------------------------------------------------------------------------
# Cross-validation: weapon and armor creature types match
# ---------------------------------------------------------------------------


class TestCrossValidation:
    def test_weapon_and_armor_use_same_creature_types(
        self, weapon_registry: EnchantmentRegistry, armor_registry: ArmorEnchantmentRegistry
    ):
        """Both weapon slayers and armor race-resistant use the same 17 types."""
        weapon_types = {e.slayer_type for e in weapon_registry.by_type("Slayer")}
        armor_types = {e.race_type for e in armor_registry.by_type("RaceResistant")}
        assert weapon_types == armor_types, (
            f"Weapon-only: {weapon_types - armor_types}, "
            f"Armor-only: {armor_types - weapon_types}"
        )

    def test_all_cfg_types_are_creature_type_values(
        self, weapon_registry: EnchantmentRegistry, armor_registry: ArmorEnchantmentRegistry
    ):
        """Every type from both cfgs should be a valid CreatureType value."""
        creature_type_values = {ct.value for ct in CreatureType}
        for entry in weapon_registry.by_type("Slayer"):
            assert entry.slayer_type in creature_type_values, (
                f"Weapon slayer type {entry.slayer_type!r} not in CreatureType enum"
            )
        for entry in armor_registry.by_type("RaceResistant"):
            assert entry.race_type in creature_type_values, (
                f"Armor race type {entry.race_type!r} not in CreatureType enum"
            )
