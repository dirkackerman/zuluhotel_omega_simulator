"""Tests for ArmorZoneConfig — parsing armrzone.cfg and choose_armor().

Covers:
- Parsing armrzone.cfg → 6 zones with correct names, chances, layers
- Chance sum equals 1.0
- choose_armor() probability distribution matches POL's zone weights
- choose_armor() selects highest-AR piece per zone (matching POL refresh_ar)
- Empty zone returns None
- No armor equipped → always None
- Single armor piece → only selected when its zone is hit
"""

import pytest

from omega.config.armor_zones import ArmorZone, ArmorZoneConfig
from omega.model.constants import (
    LAYER_ARMS,
    LAYER_CHEST,
    LAYER_GLOVES,
    LAYER_HELM,
    LAYER_LEGS,
    LAYER_NECK,
    LAYER_PANTS,
    LAYER_ROBE,
    LAYER_SHIRT,
    LAYER_SHOES,
)
from omega.model.items import Armor
from omega.model.mobile import Mobile
from omega.runtime.rng import SimulationRNG

from tests.conftest import FIXTURE_SHARD_ROOT

ARMRZONE_CFG = FIXTURE_SHARD_ROOT / "config" / "armrzone.cfg"


@pytest.fixture(scope="module")
def zone_config() -> ArmorZoneConfig:
    return ArmorZoneConfig.from_cfg(ARMRZONE_CFG)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


class TestArmorZoneParsing:
    def test_zone_count(self, zone_config: ArmorZoneConfig):
        assert len(zone_config.zones) == 6

    def test_chance_sum(self, zone_config: ArmorZoneConfig):
        assert abs(zone_config.chance_sum - 1.0) < 1e-9

    def test_body_zone(self, zone_config: ArmorZoneConfig):
        body = zone_config.zones[0]
        assert body.name == "Body"
        assert abs(body.chance - 0.44) < 1e-9
        assert body.layers == (13, 20, 22, 5, 17)

    def test_arms_zone(self, zone_config: ArmorZoneConfig):
        arms = zone_config.zones[1]
        assert arms.name == "Arms"
        assert abs(arms.chance - 0.14) < 1e-9
        assert arms.layers == (19,)

    def test_head_zone(self, zone_config: ArmorZoneConfig):
        head = zone_config.zones[2]
        assert head.name == "Head"
        assert abs(head.chance - 0.14) < 1e-9
        assert head.layers == (6,)

    def test_legs_zone(self, zone_config: ArmorZoneConfig):
        legs = zone_config.zones[3]
        assert legs.name == "Legs/feet"
        assert abs(legs.chance - 0.14) < 1e-9
        assert legs.layers == (4, 3, 24)

    def test_neck_zone(self, zone_config: ArmorZoneConfig):
        neck = zone_config.zones[4]
        assert neck.name == "Neck"
        assert abs(neck.chance - 0.07) < 1e-9
        assert neck.layers == (10,)

    def test_hands_zone(self, zone_config: ArmorZoneConfig):
        hands = zone_config.zones[5]
        assert hands.name == "Hands"
        assert abs(hands.chance - 0.07) < 1e-9
        assert hands.layers == (7,)

    def test_all_chances_sum_to_100_pct(self, zone_config: ArmorZoneConfig):
        total = sum(z.chance for z in zone_config.zones)
        assert abs(total - 1.0) < 1e-9

    def test_frozen_zone_dataclass(self, zone_config: ArmorZoneConfig):
        zone = zone_config.zones[0]
        with pytest.raises(AttributeError):
            zone.name = "Modified"


# ---------------------------------------------------------------------------
# choose_armor() — probability distribution
# ---------------------------------------------------------------------------


def _make_mobile_full_armor():
    """Mobile with armor on every zone layer."""
    mob = Mobile(name="FullArmor", is_npc=True, npctemplate="test")
    mob.str_base = 50
    mob.hp = 200
    mob.max_hp = 200

    # Body zone (layer 13)
    chest = Armor(name="Chest", ar=30)
    mob.equip(LAYER_CHEST, chest)

    # Arms zone (layer 19)
    arms = Armor(name="Arms", ar=15)
    mob.equip(LAYER_ARMS, arms)

    # Head zone (layer 6)
    helm = Armor(name="Helm", ar=20)
    mob.equip(LAYER_HELM, helm)

    # Legs/feet zone (layer 4)
    legs = Armor(name="Legs", ar=18)
    mob.equip(LAYER_PANTS, legs)

    # Neck zone (layer 10)
    gorget = Armor(name="Gorget", ar=12)
    mob.equip(LAYER_NECK, gorget)

    # Hands zone (layer 7)
    gloves = Armor(name="Gloves", ar=10)
    mob.equip(LAYER_GLOVES, gloves)

    return mob, {"Chest": chest, "Arms": arms, "Helm": helm, "Legs": legs, "Gorget": gorget, "Gloves": gloves}


class TestChooseArmorDistribution:
    """Verify zone probabilities match POL's weights."""

    def test_distribution_matches_pol(self, zone_config: ArmorZoneConfig):
        """Run 10,000 selections and verify distribution within 3% of expected."""
        mob, pieces = _make_mobile_full_armor()

        counts: dict[str, int] = {}
        n = 10_000
        for seed in range(n):
            rng = SimulationRNG(seed)
            selected = zone_config.choose_armor(mob, rng)
            name = selected.name if selected else "None"
            counts[name] = counts.get(name, 0) + 1

        # Expected: Body=44%, Arms=14%, Head=14%, Legs=14%, Neck=7%, Hands=7%
        tolerance = 0.03  # 3% tolerance
        assert abs(counts.get("Chest", 0) / n - 0.44) < tolerance, f"Body: {counts.get('Chest', 0)/n:.3f}"
        assert abs(counts.get("Arms", 0) / n - 0.14) < tolerance, f"Arms: {counts.get('Arms', 0)/n:.3f}"
        assert abs(counts.get("Helm", 0) / n - 0.14) < tolerance, f"Head: {counts.get('Helm', 0)/n:.3f}"
        assert abs(counts.get("Legs", 0) / n - 0.14) < tolerance, f"Legs: {counts.get('Legs', 0)/n:.3f}"
        assert abs(counts.get("Gorget", 0) / n - 0.07) < tolerance, f"Neck: {counts.get('Gorget', 0)/n:.3f}"
        assert abs(counts.get("Gloves", 0) / n - 0.07) < tolerance, f"Hands: {counts.get('Gloves', 0)/n:.3f}"

    def test_no_armor_returns_none(self, zone_config: ArmorZoneConfig):
        """Mobile with no armor → choose_armor always returns None."""
        mob = Mobile(name="Naked", is_npc=True)
        mob.hp = 200
        mob.max_hp = 200

        for seed in range(50):
            rng = SimulationRNG(seed)
            assert zone_config.choose_armor(mob, rng) is None

    def test_single_chest_only_selected_for_body_zone(self, zone_config: ArmorZoneConfig):
        """Mobile with only chest armor → selected ~44% of hits, None ~56%."""
        mob = Mobile(name="ChestOnly", is_npc=True)
        mob.hp = 200
        mob.max_hp = 200
        chest = Armor(name="Chest", ar=30)
        mob.equip(LAYER_CHEST, chest)

        selected_count = 0
        n = 10_000
        for seed in range(n):
            rng = SimulationRNG(seed)
            selected = zone_config.choose_armor(mob, rng)
            if selected is not None:
                assert selected is chest
                selected_count += 1

        rate = selected_count / n
        assert abs(rate - 0.44) < 0.03, f"Expected ~44% selection, got {rate:.3f}"

    def test_helm_only_selected_for_head_zone(self, zone_config: ArmorZoneConfig):
        """Mobile with only helm → selected ~14% of hits."""
        mob = Mobile(name="HelmOnly", is_npc=True)
        mob.hp = 200
        mob.max_hp = 200
        helm = Armor(name="Helm", ar=20)
        mob.equip(LAYER_HELM, helm)

        selected_count = 0
        n = 10_000
        for seed in range(n):
            rng = SimulationRNG(seed)
            if zone_config.choose_armor(mob, rng) is not None:
                selected_count += 1

        rate = selected_count / n
        assert abs(rate - 0.14) < 0.03, f"Expected ~14% selection, got {rate:.3f}"


# ---------------------------------------------------------------------------
# choose_armor() — highest AR selection per zone
# ---------------------------------------------------------------------------


class TestChooseArmorHighestAR:
    """POL's refresh_ar() selects the highest-AR piece per zone."""

    def test_highest_ar_in_body_zone(self, zone_config: ArmorZoneConfig):
        """Multiple pieces in Body zone → highest AR is selected."""
        mob = Mobile(name="MultiBody", is_npc=True)
        mob.hp = 200
        mob.max_hp = 200

        # Body zone has layers: 13 (chest), 20 (cloak), 22 (robe), 5 (shirt), 17 (tunic)
        shirt = Armor(name="Shirt", ar=5)
        mob.equip(LAYER_SHIRT, shirt)  # layer 5
        chest = Armor(name="Chest", ar=30)
        mob.equip(LAYER_CHEST, chest)  # layer 13
        robe = Armor(name="Robe", ar=10)
        mob.equip(LAYER_ROBE, robe)  # layer 22

        # Find a seed that hits Body zone
        for seed in range(200):
            rng = SimulationRNG(seed)
            selected = zone_config.choose_armor(mob, rng)
            if selected is not None:
                # Body zone → should pick Chest (AR 30, highest)
                assert selected is chest, f"Expected Chest (AR 30), got {selected.name} (AR {selected.ar})"
                return

        pytest.fail("Never hit Body zone in 200 seeds")

    def test_legs_zone_highest_ar(self, zone_config: ArmorZoneConfig):
        """Multiple pieces in Legs/feet zone → highest AR selected."""
        mob = Mobile(name="MultiLegs", is_npc=True)
        mob.hp = 200
        mob.max_hp = 200

        shoes = Armor(name="Shoes", ar=3)
        mob.equip(LAYER_SHOES, shoes)  # layer 3
        pants = Armor(name="Pants", ar=8)
        mob.equip(LAYER_PANTS, pants)  # layer 4
        leg_armor = Armor(name="LegArmor", ar=20)
        mob.equip(LAYER_LEGS, leg_armor)  # layer 24

        for seed in range(200):
            rng = SimulationRNG(seed)
            selected = zone_config.choose_armor(mob, rng)
            if selected is not None and selected.name in ("Shoes", "Pants", "LegArmor"):
                assert selected is leg_armor, f"Expected LegArmor (AR 20), got {selected.name}"
                return

        pytest.fail("Never hit Legs zone in 200 seeds")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestChooseArmorEdgeCases:
    def test_empty_zone_config(self):
        """ArmorZoneConfig with no zones → always returns None."""
        config = ArmorZoneConfig()
        mob = Mobile(name="Test", is_npc=True)
        mob.hp = 200
        mob.max_hp = 200
        mob.equip(LAYER_CHEST, Armor(name="Chest", ar=30))

        rng = SimulationRNG(42)
        assert config.choose_armor(mob, rng) is None

    def test_zero_chance_sum(self):
        """Chance sum of 0 → returns None (avoid division by zero)."""
        config = ArmorZoneConfig(
            zones=[ArmorZone(name="Test", chance=0.0, layers=(13,))],
            chance_sum=0.0,
        )
        mob = Mobile(name="Test", is_npc=True)
        mob.hp = 200
        mob.max_hp = 200
        mob.equip(LAYER_CHEST, Armor(name="Chest", ar=30))

        rng = SimulationRNG(42)
        assert config.choose_armor(mob, rng) is None

    def test_armor_on_non_zone_layer(self, zone_config: ArmorZoneConfig):
        """Armor on a layer not covered by any zone → never selected."""
        mob = Mobile(name="WristOnly", is_npc=True)
        mob.hp = 200
        mob.max_hp = 200
        # Layer 14 (WRIST) is not in any zone
        wrist = Armor(name="Wrist", ar=10)
        mob.equip(0x0E, wrist)

        for seed in range(100):
            rng = SimulationRNG(seed)
            assert zone_config.choose_armor(mob, rng) is None

    def test_deterministic_with_same_seed(self, zone_config: ArmorZoneConfig):
        """Same seed → same zone selected."""
        mob, pieces = _make_mobile_full_armor()

        rng1 = SimulationRNG(42)
        result1 = zone_config.choose_armor(mob, rng1)
        rng2 = SimulationRNG(42)
        result2 = zone_config.choose_armor(mob, rng2)

        if result1 is None:
            assert result2 is None
        else:
            assert result1.name == result2.name
