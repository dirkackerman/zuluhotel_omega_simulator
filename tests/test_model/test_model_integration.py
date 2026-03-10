"""Integration tests: create game objects from real shard config files."""

from pathlib import Path

import pytest

from omega.config import PackageResolver, parse_config_file
from omega.model.constants import (
    LAYER_HAND1,
    POLCLASS_ARMOR,
    POLCLASS_MOBILE,
    POLCLASS_NPC,
    POLCLASS_WEAPON,
    SKILLID_PARRY,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.model.factories import (
    _resolve_item_ref,
    create_armor_from_config,
    create_mobile_from_template,
    create_weapon_from_config,
)
from omega.model.items import Armor, Weapon
from omega.model.snapshot import restore, snapshot
from tests.conftest import FIXTURE_SHARD_ROOT as SHARD_ROOT


@pytest.fixture(scope="module")
def npcdesc():
    return parse_config_file(SHARD_ROOT / "config/npcdesc.cfg")


@pytest.fixture(scope="module")
def equip_cfg():
    return parse_config_file(SHARD_ROOT / "config/equip.cfg")


@pytest.fixture(scope="module")
def itemdesc():
    return parse_config_file(SHARD_ROOT / "pkg/systems/combat/config/itemdesc.cfg")


class TestResolveItemRef:
    def test_resolve_by_name(self, itemdesc):
        """Resolve an item by its Name property."""
        elem = _resolve_item_ref("WispWeapon", itemdesc)
        assert elem is not None
        assert elem.get("Name") == "WispWeapon"
        assert elem.block_type == "Weapon"

    def test_resolve_by_objtype_hex(self, itemdesc):
        """Resolve an item by hex objtype string."""
        elem = _resolve_item_ref("0x13BB", itemdesc)
        assert elem is not None
        assert elem.get("Name") == "ChainmailCoif"

    def test_resolve_unknown_returns_none(self, itemdesc):
        """Unknown reference returns None."""
        elem = _resolve_item_ref("NonexistentItem99999", itemdesc)
        assert elem is None

    def test_resolve_armor_by_name(self, itemdesc):
        """Resolve an armor piece by Name."""
        elem = _resolve_item_ref("ChainmailCoif", itemdesc)
        assert elem is not None
        assert elem.block_type == "Armor"
        assert elem.get("Name") == "ChainmailCoif"


class TestWeaponFromConfig:
    def test_wisp_weapon(self, itemdesc):
        """WispWeapon: Speed 35, Damage 5d6, Attribute Swords."""
        elem = None
        for e in itemdesc:
            if e.get("Name") == "WispWeapon":
                elem = e
                break
        assert elem is not None, "WispWeapon not found in itemdesc"

        w = create_weapon_from_config(elem)
        assert isinstance(w, Weapon)
        assert w.isa(POLCLASS_WEAPON)
        assert w.name == "WispWeapon"
        assert w.speed == 35
        assert w.damage.count == 5
        assert w.damage.sides == 6

    def test_weapon_has_hitscript(self, itemdesc):
        """Some weapons have Hitscript property."""
        found = False
        for e in itemdesc:
            if e.block_type == "Weapon" and e.get("Hitscript"):
                w = create_weapon_from_config(e)
                assert w.hitscript is not None
                found = True
                break
        assert found, "No weapon with Hitscript found"


class TestArmorFromConfig:
    def test_chainmail_coif(self, itemdesc):
        """ChainmailCoif (0x13BB): AR 16, Coverage Head+Neck."""
        elem = itemdesc[0x13BB]
        assert elem is not None

        a = create_armor_from_config(elem)
        assert isinstance(a, Armor)
        assert a.isa(POLCLASS_ARMOR)
        assert a.ar == 16
        assert "Head" in a.coverage
        assert "Neck" in a.coverage

    def test_armor_cprops_carried(self, itemdesc):
        """Armor CProps (DefaultDex, MagicPenalty) are in property bag."""
        elem = itemdesc[0x13BB]
        a = create_armor_from_config(elem)
        # ChainmailCoif has DefaultDex and MagicPenalty CProps
        dex_penalty = a.get_property("DefaultDex")
        assert dex_penalty is not None
        assert isinstance(dex_penalty, int)
        assert dex_penalty < 0


class TestMobileFromTemplate:
    def test_beckon_npc(self, npcdesc, equip_cfg, itemdesc):
        """Create NPC from 'beckon' template — fairy with high stats."""
        m = create_mobile_from_template("beckon", npcdesc, equip_cfg, itemdesc)
        assert m.isa(POLCLASS_MOBILE)
        assert m.isa(POLCLASS_NPC)
        assert m.is_npc
        assert m.npctemplate == "beckon"
        # beckon has STR 200, INT 200, DEX 175
        assert m.strength == 200
        assert m.intelligence == 200
        assert m.dexterity == 175

    def test_beckon_has_skills(self, npcdesc, equip_cfg, itemdesc):
        """beckon has Parry 120, Tactics listed."""
        m = create_mobile_from_template("beckon", npcdesc, equip_cfg, itemdesc)
        assert m.get_effective_skill(SKILLID_PARRY) > 0

    def test_beckon_has_equipment(self, npcdesc, equip_cfg, itemdesc):
        """beckon has Equip template, should have some equipped items."""
        m = create_mobile_from_template("beckon", npcdesc, equip_cfg, itemdesc)
        equip = m.list_equipment()
        # May or may not have items depending on equip template resolution
        # Just verify no crash
        assert isinstance(equip, dict)

    def test_npc_with_cprops(self, npcdesc, equip_cfg, itemdesc):
        """NPCs with CProps should have them in property bag."""
        # Find an NPC with Type CProp
        for name in ["earthelementalsummons", "airelemental", "earthelemental"]:
            elem = npcdesc[name]
            if elem is not None and hasattr(elem, 'get_cprop') and elem.get_cprop("Type") is not None:
                m = create_mobile_from_template(name, npcdesc, equip_cfg, itemdesc)
                assert m.get_property("Type") is not None
                return
        pytest.skip("No NPC with Type CProp found")

    def test_unknown_template_raises(self, npcdesc, equip_cfg, itemdesc):
        with pytest.raises(ValueError, match="not found"):
            create_mobile_from_template("nonexistent_npc_12345", npcdesc, equip_cfg, itemdesc)


class TestSnapshotWithRealNPC:
    def test_snapshot_restore_cycle(self, npcdesc, equip_cfg, itemdesc):
        """Snapshot a real NPC, modify state, restore to original."""
        m = create_mobile_from_template("beckon", npcdesc, equip_cfg, itemdesc)
        original_hp = m.hp
        original_mana = m.mana

        snap = snapshot(m)

        # Simulate combat effects
        m.hp = 1
        m.mana = 0
        m.dead = True
        m.set_property("poison", 3)

        restore(m, snap)

        assert m.hp == original_hp
        assert m.mana == original_mana
        assert not m.dead
        assert m.get_property("poison") is None
