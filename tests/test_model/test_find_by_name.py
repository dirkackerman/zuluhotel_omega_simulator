"""Tests for ConfigFile.find_by_name and find_weapon/armor_by_name helpers."""

import pytest

from omega.config import parse_config_file
from omega.model.constants import POLCLASS_ARMOR, POLCLASS_WEAPON, SKILLID_SWORDSMANSHIP
from omega.model.factories import find_armor_by_name, find_weapon_by_name
from omega.model.items import Armor, Weapon
from tests.conftest import FIXTURE_SHARD_ROOT as SHARD_ROOT


@pytest.fixture(scope="module")
def itemdesc():
    return parse_config_file(SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg")


class TestConfigFileFindByName:
    """ConfigFile.find_by_name searches elements by their Name property."""

    def test_find_weapon_element(self, itemdesc):
        elem = itemdesc.find_by_name("WispWeapon")
        assert elem is not None
        assert elem.block_type == "Weapon"
        assert elem.get("Name") == "WispWeapon"

    def test_find_armor_element(self, itemdesc):
        elem = itemdesc.find_by_name("ChainmailCoif")
        assert elem is not None
        assert elem.block_type == "Armor"

    def test_not_found_returns_none(self, itemdesc):
        assert itemdesc.find_by_name("NoSuchItem999") is None


class TestFindWeaponByName:
    def test_wisp_weapon(self, itemdesc):
        w = find_weapon_by_name("WispWeapon", itemdesc)
        assert isinstance(w, Weapon)
        assert w.isa(POLCLASS_WEAPON)
        assert w.name == "WispWeapon"
        assert w.speed == 35
        assert w.damage.count == 5
        assert w.damage.sides == 6

    def test_heartwood(self, itemdesc):
        w = find_weapon_by_name("TheHeartwood", itemdesc)
        assert isinstance(w, Weapon)
        assert w.name == "TheHeartwood"
        assert w.two_handed is True
        assert w.attribute == "Swords"

    def test_not_found_raises(self, itemdesc):
        with pytest.raises(KeyError, match="Weapon.*not found"):
            find_weapon_by_name("NoSuchWeapon999", itemdesc)

    def test_armor_name_raises(self, itemdesc):
        """Looking up an armor name via find_weapon_by_name raises."""
        with pytest.raises(KeyError, match="Weapon.*not found"):
            find_weapon_by_name("ChainmailCoif", itemdesc)


class TestFindArmorByName:
    def test_chainmail_coif(self, itemdesc):
        a = find_armor_by_name("ChainmailCoif", itemdesc)
        assert isinstance(a, Armor)
        assert a.isa(POLCLASS_ARMOR)
        assert a.ar == 16
        assert "Head" in a.coverage
        assert "Neck" in a.coverage

    def test_cprops_carried(self, itemdesc):
        a = find_armor_by_name("ChainmailCoif", itemdesc)
        dex_penalty = a.get_property("DefaultDex")
        assert dex_penalty is not None
        assert isinstance(dex_penalty, int)
        assert dex_penalty < 0

    def test_not_found_raises(self, itemdesc):
        with pytest.raises(KeyError, match="Armor.*not found"):
            find_armor_by_name("NoSuchArmor999", itemdesc)

    def test_weapon_name_raises(self, itemdesc):
        """Looking up a weapon name via find_armor_by_name raises."""
        with pytest.raises(KeyError, match="Armor.*not found"):
            find_armor_by_name("WispWeapon", itemdesc)
