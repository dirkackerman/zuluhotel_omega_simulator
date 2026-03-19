"""Tests for CombatScript enum — canonical combat script package paths."""

import pytest

from omega.config.armor_enchantments import (
    ArmorEnchantment,
    ArmorEnchantmentRegistry,
    armor_enchantment_onhitscript,
)
from omega.config.combat_scripts import CombatScript
from omega.config.enchantments import (
    Enchantment,
    EnchantmentRegistry,
    enchantment_hitscript,
)

from tests.conftest import FIXTURE_SHARD_ROOT

HITSCRIPT_CFG = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "hitscriptdesc.cfg"
ONHITSCRIPT_CFG = FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "onhitscriptdesc.cfg"


class TestCombatScriptEnum:
    def test_is_str(self):
        """CombatScript members are str instances for seamless use."""
        for cs in CombatScript:
            assert isinstance(cs, str)

    def test_str_equality(self):
        assert CombatScript.SPELLSTRIKESCRIPT == ":combat:spellstrikescript"
        assert CombatScript.SPELLONHIT == ":combat:spellonhit"
        assert CombatScript.MAINHIT == ":combat:mainhit"

    def test_all_start_with_combat(self):
        for cs in CombatScript:
            assert cs.value.startswith(":combat:"), f"{cs.name} = {cs.value!r}"

    def test_all_values_unique(self):
        values = [cs.value for cs in CombatScript]
        assert len(values) == len(set(values))

    def test_weapon_hitscripts_present(self):
        """All weapon hitscript paths from hitscriptdesc.cfg should be in the enum."""
        expected_weapon = {
            CombatScript.SPELLSTRIKESCRIPT,
            CombatScript.SLAYERSCRIPT,
            CombatScript.PIERCINGSCRIPT,
            CombatScript.BANISHSCRIPT,
            CombatScript.POISONHIT,
            CombatScript.LIFEDRAINSCRIPT,
            CombatScript.MANADRAINSCRIPT,
            CombatScript.STAMINADRAINSCRIPT,
            CombatScript.BLINDINGSCRIPT,
            CombatScript.DUALPLANARSCRIPT,
            CombatScript.VOIDSCRIPT,
            CombatScript.TRIELEMENTALSCRIPT,
        }
        assert all(cs in CombatScript for cs in expected_weapon)

    def test_armor_onhitscripts_present(self):
        """All armor onhitscript paths from onhitscriptdesc.cfg should be in the enum."""
        expected_armor = {
            CombatScript.SPELLONHIT,
            CombatScript.RACERESISTONHIT,
            CombatScript.PIERCINGONHIT,
            CombatScript.BANISHONHIT,
            CombatScript.POISONONHIT,
            CombatScript.BOUNCINGONHIT,
            CombatScript.MANADRAINONHIT,
            CombatScript.STAMINADRAINONHIT,
            CombatScript.BLINDINGONHIT,
            CombatScript.TRIELEMENTALONHIT,
            CombatScript.DEFLECTIONONHIT,
            CombatScript.AVENGINGONHIT,
            CombatScript.INVISIBLEONHIT,
            CombatScript.DUALPLANARONHIT,
        }
        assert all(cs in CombatScript for cs in expected_armor)

    def test_from_value(self):
        assert CombatScript(":combat:spellstrikescript") is CombatScript.SPELLSTRIKESCRIPT

    def test_from_value_invalid(self):
        with pytest.raises(ValueError):
            CombatScript(":combat:doesnotexist")


class TestCombatScriptMetaConsistency:
    """Verify that _ENCHANTMENT_META and _ARMOR_ENCHANTMENT_META use CombatScript values."""

    def test_weapon_meta_uses_combat_script(self):
        """All hitscript paths in weapon _ENCHANTMENT_META should be CombatScript instances."""
        for e in Enchantment:
            hs = enchantment_hitscript(e)
            assert isinstance(hs, CombatScript), (
                f"Enchantment.{e.name} hitscript={hs!r} is {type(hs).__name__}, expected CombatScript"
            )

    def test_armor_meta_uses_combat_script(self):
        """All onhitscript paths in armor _ARMOR_ENCHANTMENT_META should be CombatScript instances."""
        for ae in ArmorEnchantment:
            hs = armor_enchantment_onhitscript(ae)
            assert isinstance(hs, CombatScript), (
                f"ArmorEnchantment.{ae.name} onhitscript={hs!r} is {type(hs).__name__}, expected CombatScript"
            )


class TestCombatScriptCfgConsistency:
    """Verify enum matches parsed cfg files."""

    @pytest.fixture(scope="class")
    def weapon_registry(self) -> EnchantmentRegistry:
        return EnchantmentRegistry.from_cfg(HITSCRIPT_CFG)

    @pytest.fixture(scope="class")
    def armor_registry(self) -> ArmorEnchantmentRegistry:
        return ArmorEnchantmentRegistry.from_cfg(ONHITSCRIPT_CFG)

    def test_weapon_cfg_scripts_are_combat_script_values(self, weapon_registry):
        """Every hitscript in parsed hitscriptdesc.cfg should be a valid CombatScript value."""
        combat_script_values = {cs.value for cs in CombatScript}
        for entry in weapon_registry.all_entries():
            assert entry.hitscript in combat_script_values, (
                f"Weapon enchantment {entry.id} ({entry.name}) hitscript={entry.hitscript!r} "
                f"not found in CombatScript enum"
            )

    def test_armor_cfg_scripts_are_combat_script_values(self, armor_registry):
        """Every onhitscript in parsed onhitscriptdesc.cfg should be a valid CombatScript value."""
        combat_script_values = {cs.value for cs in CombatScript}
        for entry in armor_registry.all_entries():
            assert entry.onhitscript in combat_script_values, (
                f"Armor enchantment {entry.id} ({entry.name}) onhitscript={entry.onhitscript!r} "
                f"not found in CombatScript enum"
            )
