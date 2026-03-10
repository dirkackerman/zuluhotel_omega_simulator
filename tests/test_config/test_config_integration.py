"""Integration tests: full NPC lookup chain and runtime accessor patterns."""

from pathlib import Path

import pytest

from omega.config import PackageResolver, parse_config_file, parse_dice
from omega.config.accessor import RuntimeConfigFile
from tests.conftest import FIXTURE_SHARD_ROOT as SHARD_ROOT


@pytest.fixture(scope="module")
def resolver() -> PackageResolver:
    return PackageResolver(SHARD_ROOT)


class TestNpcLookupChain:
    """Test the full NPC lookup chain: npcdesc → equip → itemdesc."""

    def test_npc_with_equipment(self):
        """Look up an NPC and verify we can find its equipment template."""
        npcs = parse_config_file(SHARD_ROOT / "config/npcdesc.cfg")
        equips = parse_config_file(SHARD_ROOT / "config/equip.cfg")

        npc = npcs["beckon"]
        assert npc is not None

        equip_name = npc["Equip"]
        assert equip_name is not None

        equip_template = equips[equip_name]
        assert equip_template is not None


class TestRuntimeAccessorPatterns:
    """Test access patterns matching how eScript scripts use config files."""

    def test_combat_settings_pattern(self):
        """Matches: combat_settingscfg["Weapons"].WearChance"""
        cfg = RuntimeConfigFile.from_path(
            SHARD_ROOT / "pkg/systems/combat/config/settings.cfg"
        )
        weapons = cfg["Weapons"]
        assert weapons is not None
        # WearChance may have trailing comment stripped, starts with "8"
        assert weapons.WearChance.startswith("8")

    def test_armor_settings_pattern(self):
        """Matches: combat_settingscfg["Armor"].WearChance"""
        cfg = RuntimeConfigFile.from_path(
            SHARD_ROOT / "pkg/systems/combat/config/settings.cfg"
        )
        armor = cfg["Armor"]
        assert armor is not None
        assert armor.WearChance.startswith("15")

    def test_itemdesc_objtype_pattern(self):
        """Matches: weapcfg[weapon_defender.objtype].CanWeaponParry"""
        cfg = RuntimeConfigFile.from_path(
            SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg"
        )
        elem = cfg[0x13BB]
        assert elem is not None
        assert elem.Name == "ChainmailCoif"

    def test_config_via_package_resolver(self, resolver: PackageResolver):
        """Matches: ReadConfigFile(":combat:settings") flow."""
        path = resolver.resolve_config_path(":combat:settings")
        assert path is not None
        cfg = RuntimeConfigFile.from_path(path)
        settings = cfg["Settings"]
        assert settings is not None
        assert settings.AutoDefend == "1"

    def test_wildcard_config_resolution(self, resolver: PackageResolver):
        """Matches: ReadConfigFile(":*:itemdesc") flow."""
        path = resolver.resolve_config_path(":*:itemdesc")
        assert path is not None
        cfg = RuntimeConfigFile.from_path(path)
        assert len(list(cfg._cfg)) > 0


class TestWeaponDamageParsing:
    """Test parsing weapon damage dice from itemdesc."""

    def test_weapon_with_damage_dice(self):
        """Find a weapon in itemdesc and parse its damage dice."""
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg"
        )
        # Find any weapon element
        weapon = None
        for elem in cfg:
            if elem.block_type == "Weapon" and elem.get("Damage"):
                weapon = elem
                break

        if weapon is not None:
            damage_str = weapon["Damage"]
            spec = parse_dice(damage_str)
            assert spec.count > 0 or spec.bonus > 0
            assert spec.max_value > 0
