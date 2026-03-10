"""Tests for the POL config file parser."""

from pathlib import Path

import pytest

from omega.config.cfg_parser import ConfigElement, ConfigFile, parse_config_file

SHARD_ROOT = Path("/home/saru/git/temp/zuluhotel_omega_simulator/submodules/zuluhotel_omega_2.5")


class TestFlatFormat:
    """Test flat key=value config files (e.g., combat.cfg)."""

    def test_parse_combat_cfg(self):
        cfg = parse_config_file(SHARD_ROOT / "config/combat.cfg")
        assert len(cfg.flat_properties) > 0
        assert cfg["DisplayParrySuccessMessages"] == "0"
        assert cfg["WarModeDelay"] == "1"
        assert cfg["CoreHitSounds"] == "1"
        assert cfg["SendDamagePacket"] == "0"
        assert cfg["AttackWhileFrozen"] == "1"

    def test_all_combat_keys_present(self):
        cfg = parse_config_file(SHARD_ROOT / "config/combat.cfg")
        expected_keys = [
            "DisplayParrySuccessMessages",
            "WarmodeInhibitsRegen",
            "WarModeDelay",
            "SingleCombat",
            "CoreHitSounds",
            "ScriptedAttackChecks",
            "ResetSwingOnTurn",
            "SendSwingPacket",
            "SendDamagePacket",
            "AttackWhileFrozen",
            "SendAttackMsg",
        ]
        for key in expected_keys:
            assert cfg[key] is not None, f"Missing key: {key}"


class TestBlockFormat:
    """Test block-based config files."""

    def test_parse_npcdesc_cfg(self):
        cfg = parse_config_file(SHARD_ROOT / "config/npcdesc.cfg")
        assert len(cfg) > 100  # Hundreds of NPC templates

    def test_npc_beckon_properties(self):
        cfg = parse_config_file(SHARD_ROOT / "config/npcdesc.cfg")
        npc = cfg["beckon"]
        assert npc is not None
        assert npc["STR"] == "200"
        assert npc["INT"] == "200"
        assert npc["DEX"] == "175"
        assert npc["Name"] == "a fairy"
        assert npc["script"] == "goodcaster"

    def test_npc_multi_value_keys(self):
        cfg = parse_config_file(SHARD_ROOT / "config/npcdesc.cfg")
        npc = cfg["beckon"]
        spells = npc.get_all("spell")
        assert len(spells) >= 5
        assert "ebolt" in spells
        assert "flamestrike" in spells

    def test_npc_cprops(self):
        cfg = parse_config_file(SHARD_ROOT / "config/npcdesc.cfg")
        npc = cfg["beckon"]
        assert npc.get_cprop("Type") == "Human"
        assert npc.get_cprop("BaseStrmod") == 100
        assert npc.get_cprop("PermPoisonImmunity") == 3
        assert npc.get_cprop("EarthProtection") == 100

    def test_npc_dracoliche(self):
        cfg = parse_config_file(SHARD_ROOT / "config/npcdesc.cfg")
        npc = cfg["dracoliche"]
        assert npc is not None
        assert npc["STR"] == "300"
        assert npc["INT"] == "500"
        assert npc.get_cprop("Type") == "Undead"
        assert npc.get_cprop("BaseStrmod") == 750


class TestItemdescFormat:
    """Test weapon/armor itemdesc.cfg parsing."""

    def test_parse_itemdesc(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg"
        )
        assert len(cfg) > 100

    def test_armor_by_objtype_int(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg"
        )
        armor = cfg[0x13BB]
        assert armor is not None
        assert armor["Name"] == "ChainmailCoif"
        assert armor["AR"] == "16"

    def test_armor_by_objtype_string(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg"
        )
        armor = cfg["0x13BB"]
        assert armor is not None
        assert armor["AR"] == "16"

    def test_armor_coverage_multi(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg"
        )
        armor = cfg[0x13BB]
        coverage = armor.get_all("Coverage")
        assert "Head" in coverage
        assert "Neck" in coverage

    def test_armor_cprops(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg"
        )
        armor = cfg[0x13BB]
        assert armor.get_cprop("DefaultDex") == -2
        assert armor.get_cprop("MagicPenalty") == 8


class TestSettingsFormat:
    """Test Elem-based settings config."""

    def test_parse_settings(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/settings.cfg"
        )
        assert len(cfg) > 0

    def test_settings_elem_access(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/settings.cfg"
        )
        settings = cfg["Settings"]
        assert settings is not None
        assert settings["AutoDefend"] == "1"
        assert settings["PvPGains"] == "1"

    def test_weapons_wear_chance(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/settings.cfg"
        )
        weapons = cfg["Weapons"]
        assert weapons is not None
        # Value may have inline comment stripped
        assert weapons["WearChance"].startswith("8")


class TestEquipFormat:
    """Test equipment config parsing."""

    def test_parse_equip(self):
        cfg = parse_config_file(SHARD_ROOT / "config/equip.cfg")
        assert len(cfg) > 10

    def test_nazgul_equipment(self):
        cfg = parse_config_file(SHARD_ROOT / "config/equip.cfg")
        equip = cfg["nazgul"]
        assert equip is not None
        # Should have Armor and Equip entries
        assert len(equip.get_all("Armor")) > 0 or len(equip.get_all("Equip")) > 0


class TestHitscriptdescFormat:
    """Test enchantment config parsing."""

    def test_parse_hitscriptdesc(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/hitscriptdesc.cfg"
        )
        assert len(cfg) > 10

    def test_enchantment_access(self):
        cfg = parse_config_file(
            SHARD_ROOT / "pkg/systems/combat/config/hitscriptdesc.cfg"
        )
        ench = cfg["1"]
        assert ench is not None
        assert ench["HitscriptType"] == "Spell"
        assert ench["SpellName"] == "Clumsy"


class TestConfigElement:
    """Unit tests for ConfigElement methods."""

    def test_get_int(self):
        elem = ConfigElement("Test", "test")
        elem.set("HP", "100")
        assert elem.get_int("HP") == 100
        assert elem.get_int("Missing", 50) == 50

    def test_get_float(self):
        elem = ConfigElement("Test", "test")
        elem.set("Rate", "1.5")
        assert elem.get_float("Rate") == 1.5
        assert elem.get_float("Missing", 0.0) == 0.0

    def test_contains(self):
        elem = ConfigElement("Test", "test")
        elem.set("Key", "val")
        elem.set_cprop("Type", "sHuman")
        assert "Key" in elem
        assert "Type" in elem
        assert "Missing" not in elem
