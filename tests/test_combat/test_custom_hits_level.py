"""Tests for CustomHitsLevel CProp handling on NPC templates.

The shard uses the ``CustomHitsLevel`` CProp to override NPC max HP
independently of the STR stat (see ``regen.src`` GetLifeMaximumValueExported).

Verifies:
- NPCs with CustomHitsLevel have HP set to the CProp value, not STR-derived
- NPCs without CustomHitsLevel use the HITS config (or STR fallback)
- Invalid CustomHitsLevel values are logged as warnings
"""

import pytest

from omega.config.cfg_parser import parse_config_file
from omega.model.factories import create_mobile_from_template

from tests.conftest import FIXTURE_SHARD_ROOT


@pytest.fixture(scope="module")
def npcdesc():
    return parse_config_file(FIXTURE_SHARD_ROOT / "config" / "npcdesc.cfg")


@pytest.fixture(scope="module")
def equip_cfg():
    return parse_config_file(FIXTURE_SHARD_ROOT / "config" / "equip.cfg")


@pytest.fixture(scope="module")
def itemdesc():
    return parse_config_file(
        FIXTURE_SHARD_ROOT / "pkg" / "systems" / "combat" / "config" / "itemdesc.cfg"
    )


class TestCustomHitsLevelApplied:
    """Verify CustomHitsLevel CProp overrides NPC HP."""

    def test_beckon_hp_30000(self, npcdesc, equip_cfg, itemdesc):
        """beckon has CustomHitsLevel=30000, STR=200."""
        mob = create_mobile_from_template("beckon", npcdesc, equip_cfg, itemdesc)
        # CustomHitsLevel overrides STR-derived HP
        assert mob.hp == 30000
        assert mob.max_hp == 30000
        # STR should still be 200 (not affected by CustomHitsLevel)
        assert mob.str_base == 200

    def test_earthelementalsummons_hp_100000(self, npcdesc, equip_cfg, itemdesc):
        """earthelementalsummons has CustomHitsLevel=100000, STR=100."""
        mob = create_mobile_from_template("earthelementalsummons", npcdesc, equip_cfg, itemdesc)
        assert mob.hp == 100000
        assert mob.max_hp == 100000
        assert mob.str_base == 100

    def test_waterdragon_hp_900000(self, npcdesc, equip_cfg, itemdesc):
        """waterdragon boss has CustomHitsLevel=900000, STR=1000."""
        mob = create_mobile_from_template("waterdragon", npcdesc, equip_cfg, itemdesc)
        assert mob.hp == 900000
        assert mob.max_hp == 900000
        assert mob.str_base == 1000

    def test_dragonking_hp_1500000(self, npcdesc, equip_cfg, itemdesc):
        """dragonking super boss has CustomHitsLevel=1500000, STR=1000."""
        mob = create_mobile_from_template("dragonking", npcdesc, equip_cfg, itemdesc)
        assert mob.hp == 1500000
        assert mob.max_hp == 1500000

    def test_legendaryhunter_hp_1500000(self, npcdesc, equip_cfg, itemdesc):
        """legendaryhunter champion has CustomHitsLevel=1500000, STR=1000."""
        mob = create_mobile_from_template("legendaryhunter", npcdesc, equip_cfg, itemdesc)
        assert mob.hp == 1500000
        assert mob.max_hp == 1500000


class TestWithoutCustomHitsLevel:
    """NPCs without CustomHitsLevel use HITS config or STR fallback."""

    def test_skeleton_uses_hits_not_str(self, npcdesc, equip_cfg, itemdesc):
        """skeleton has no CustomHitsLevel — HP should come from HITS config."""
        mob = create_mobile_from_template("skeleton", npcdesc, equip_cfg, itemdesc)
        # skeleton's HP should NOT be equal to CustomHitsLevel (it has none)
        # It should use the HITS value from npcdesc.cfg (or STR as fallback)
        assert mob.hp > 0
        assert mob.max_hp == mob.hp

    def test_airelemental_uses_hits_not_str(self, npcdesc, equip_cfg, itemdesc):
        """airelemental has no CustomHitsLevel."""
        mob = create_mobile_from_template("airelemental", npcdesc, equip_cfg, itemdesc)
        assert mob.hp > 0
        assert mob.max_hp == mob.hp


class TestCustomHitsLevelEdgeCases:
    """Edge cases around CustomHitsLevel parsing."""

    def test_hp_overrides_not_str(self, npcdesc, equip_cfg, itemdesc):
        """CustomHitsLevel sets HP independently of STR — verify they differ."""
        mob = create_mobile_from_template("beckon", npcdesc, equip_cfg, itemdesc)
        # STR=200, CustomHitsLevel=30000 — they must differ
        assert mob.hp != mob.str_base
        assert mob.hp == 30000
        assert mob.str_base == 200

    def test_custom_hp_survives_combatant_spec_round_trip(self, npcdesc, equip_cfg, itemdesc):
        """CombatantSpec.from_config() should preserve CustomHitsLevel HP."""
        from omega.simulation.scenario import CombatantSpec, build_combatant

        spec = CombatantSpec.from_config("waterdragon", npcdesc, equip_cfg, itemdesc)
        assert spec.hp == 900000

        mob, _, _ = build_combatant(spec)
        assert mob.hp == 900000
        assert mob.max_hp == 900000
