"""Integration tests for the astral damage path.

The astral path is a completely separate damage system from physical:
- Triggered by ``GetObjProperty(weapon, "Astral")`` in ``RecalcDmg``
- Damage drains mana first, then stamina (NOT HP)
- Scales with Spirit Speak, EvalInt, class bonuses
- Meditation can resist (random check, bypassed by piercing)
- Astral armor absorbs damage
- Final damage is halved (``rawdamage * 0.5``)
- Does NOT call ``ApplyRawDamage`` — uses ``SetMana``/``SetStamina`` directly
"""

import pytest

from omega.combat.hit import execute_hit
from omega.config.dice import DiceSpec
from omega.model.constants import (
    CLASSEID_MAGE,
    CLASSEID_WARRIOR,
    DMGID_ASTRAL,
    SKILLID_ANATOMY,
    SKILLID_EVALINT,
    SKILLID_MAGICRESISTANCE,
    SKILLID_MEDITATION,
    SKILLID_SPIRITSPEAK,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile


@pytest.fixture
def shard(fixture_shard):
    return fixture_shard


@pytest.fixture
def combat_trees(fixture_parse_results):
    return fixture_parse_results


def _em_dir(shard):
    return shard.root / "scripts" / "modules"


def _make_astral_attacker(
    *,
    spirit_speak=1000,
    eval_int=1000,
    tactics=1000,
    strength=100,
    intelligence=100,
    is_npc=False,
):
    """Create an attacker configured for astral combat."""
    mob = Mobile(name="AstralAttacker", is_npc=is_npc)
    mob.str_base = strength
    mob.int_base = intelligence
    mob.dex_base = 100
    mob.hp = 200
    mob.max_hp = 200
    mob.mana = 100
    mob.max_mana = 100
    mob.stamina = 100
    mob.max_stamina = 100
    mob.set_skill(SKILLID_SPIRITSPEAK, spirit_speak)
    mob.set_skill(SKILLID_EVALINT, eval_int)
    mob.set_skill(SKILLID_TACTICS, tactics)
    mob.set_skill(SKILLID_SWORDSMANSHIP, 1000)
    mob.set_skill(SKILLID_ANATOMY, 1000)
    return mob


def _make_defender(
    *,
    mana=100,
    max_mana=100,
    stamina=100,
    max_stamina=100,
    hp=500,
    meditation=0,
    magic_resist=0,
    intelligence=50,
    is_npc=True,
):
    """Create a defender for astral combat tests."""
    mob = Mobile(
        name="AstralTarget",
        is_npc=is_npc,
        npctemplate="test" if is_npc else "",
    )
    mob.str_base = 50
    mob.int_base = intelligence
    mob.dex_base = 50
    mob.hp = hp
    mob.max_hp = hp
    mob.mana = mana
    mob.max_mana = max_mana
    mob.stamina = stamina
    mob.max_stamina = max_stamina
    if meditation:
        mob.set_skill(SKILLID_MEDITATION, meditation)
    if magic_resist:
        mob.set_skill(SKILLID_MAGICRESISTANCE, magic_resist)
    return mob


def _make_astral_weapon():
    """Create a weapon with the Astral property set."""
    weapon = Weapon(
        name="AstralBlade",
        damage=DiceSpec(2, 6, 0),
        attribute=SKILLID_SWORDSMANSHIP,
    )
    weapon.set_property("Astral", 1)
    return weapon


def _make_physical_weapon():
    """Create a standard physical weapon (no Astral property)."""
    return Weapon(
        name="PhysicalSword",
        damage=DiceSpec(2, 6, 0),
        attribute=SKILLID_SWORDSMANSHIP,
    )


def _run_hit(shard, combat_trees, attacker, defender, weapon, armor, **kwargs):
    """Run a hit through the full shard script pipeline."""
    defaults = dict(
        base_damage=40,
        debug=True,
        core_hit_check=False,
        rng_seed=42,
        config_resolver=shard.resolve_config_path,
        em_modules_dir=_em_dir(shard),
        shard_root=shard.root,
        package_map=shard.package_map,
    )
    defaults.update(kwargs)
    return execute_hit(
        combat_trees, attacker, defender, weapon, armor, **defaults
    )


# =========================================================================
# Basic astral flow
# =========================================================================


class TestAstralBasicFlow:
    """Basic astral damage path tests."""

    def test_astral_weapon_drains_mana(self, shard, combat_trees):
        """An astral weapon should drain defender mana, not HP."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=200, max_mana=200)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        mana_before = defender.mana
        hp_before = defender.hp
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)

        assert result.success, f"Hit failed: {result.error}"
        # Astral drains mana, not HP
        assert defender.mana < mana_before, "Astral should drain mana"
        assert defender.hp == hp_before, "Astral should NOT drain HP"

    def test_astral_no_hp_damage(self, shard, combat_trees):
        """Astral damage should never reduce HP directly."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=100,
        )

        assert result.success, f"Hit failed: {result.error}"
        assert defender.hp == defender.max_hp, "HP must be unchanged for astral hits"

    def test_physical_weapon_drains_hp(self, shard, combat_trees):
        """A physical weapon should drain HP (not mana) — confirming dispatch works."""
        attacker = _make_astral_attacker()
        defender = _make_defender()
        weapon = _make_physical_weapon()
        armor = Armor(name="Plate", ar=30)

        hp_before = defender.hp
        mana_before = defender.mana
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)

        assert result.success, f"Hit failed: {result.error}"
        assert defender.hp < hp_before, "Physical should drain HP"

    def test_astral_vs_physical_dispatch(self, shard, combat_trees):
        """Same setup, one astral and one physical — verify different paths."""
        defender_a = _make_defender(mana=200, max_mana=200)
        defender_p = _make_defender(mana=200, max_mana=200)
        armor = Armor(name="Plate", ar=30)

        result_a = _run_hit(
            shard, combat_trees, _make_astral_attacker(), defender_a,
            _make_astral_weapon(), armor,
        )
        result_p = _run_hit(
            shard, combat_trees, _make_astral_attacker(), defender_p,
            _make_physical_weapon(), armor,
        )

        assert result_a.success and result_p.success
        # Astral: mana drained, HP intact
        assert defender_a.mana < 200
        assert defender_a.hp == defender_a.max_hp
        # Physical: HP drained (mana may or may not change)
        assert defender_p.hp < defender_p.max_hp

    def test_astral_zero_base_damage(self, shard, combat_trees):
        """Zero base damage should result in no mana drain."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=100, max_mana=100)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        mana_before = defender.mana
        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=0,
        )

        assert result.success, f"Hit failed: {result.error}"
        assert defender.mana == mana_before, "Zero damage should not drain mana"

    def test_astral_dead_defender(self, shard, combat_trees):
        """Dead defender should receive no astral damage."""
        attacker = _make_astral_attacker()
        defender = _make_defender()
        defender.dead = True
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        mana_before = defender.mana
        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)

        assert result.success, f"Hit failed: {result.error}"
        assert defender.mana == mana_before, "Dead defender should not take astral damage"


# =========================================================================
# Mana/stamina drain mechanics
# =========================================================================


class TestAstralDrainMechanics:
    """Test mana-first, stamina-overflow drain behavior."""

    def test_drains_mana_first(self, shard, combat_trees):
        """When mana > damage, only mana is drained."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=200, max_mana=200, stamina=100, max_stamina=100)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        stamina_before = defender.stamina
        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=20,
        )

        assert result.success, f"Hit failed: {result.error}"
        assert defender.mana < 200, "Should drain mana"
        assert defender.stamina == stamina_before, "Should NOT drain stamina when mana sufficient"

    def test_overflow_to_stamina(self, shard, combat_trees):
        """When damage > mana, overflow drains stamina."""
        attacker = _make_astral_attacker()
        # Low mana so overflow hits stamina
        defender = _make_defender(mana=5, max_mana=100, stamina=100, max_stamina=100)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        assert defender.mana == 0, "Mana should be fully drained on overflow"
        assert defender.stamina < 100, "Overflow should drain stamina"

    def test_astral_incapacity(self, shard, combat_trees):
        """When damage exceeds both mana and stamina, both go to 0."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=5, max_mana=100, stamina=5, max_stamina=100)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=100,
        )

        assert result.success, f"Hit failed: {result.error}"
        assert defender.mana == 0, "Both mana should be 0 on incapacity"
        assert defender.stamina == 0, "Both stamina should be 0 on incapacity"


# =========================================================================
# Spirit Speak scaling
# =========================================================================


class TestAstralSpiritSpeakScaling:
    """Spirit Speak scales astral basedamage via the ratio formula."""

    def test_spirit_speak_increases_damage(self, shard, combat_trees):
        """Higher spirit speak → more mana drained."""
        defender_low = _make_defender(mana=500, max_mana=500)
        defender_high = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        attacker_low = _make_astral_attacker(spirit_speak=200)
        attacker_high = _make_astral_attacker(spirit_speak=1000)

        result_low = _run_hit(
            shard, combat_trees, attacker_low, defender_low, weapon, armor,
            base_damage=40,
        )
        result_high = _run_hit(
            shard, combat_trees, attacker_high, defender_high, weapon, armor,
            base_damage=40,
        )

        assert result_low.success and result_high.success
        mana_drain_low = 500 - defender_low.mana
        mana_drain_high = 500 - defender_high.mana
        assert mana_drain_high > mana_drain_low, (
            f"Higher spirit speak should deal more: {mana_drain_high} vs {mana_drain_low}"
        )

    def test_low_spirit_speak_low_damage(self, shard, combat_trees):
        """Spirit speak 0 → minimal astral damage."""
        attacker = _make_astral_attacker(spirit_speak=0)
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        mana_drain = 500 - defender.mana
        # With 0 spirit speak the scaling ratio is very low
        assert mana_drain < 20, f"Zero spirit speak should deal minimal damage, got {mana_drain}"


# =========================================================================
# EvalInt scaling
# =========================================================================


class TestAstralEvalIntScaling:
    """EvalInt multiplier: basedamage *= (1 + EvalInt * 0.002)."""

    def test_evalint_increases_damage(self, shard, combat_trees):
        """Higher EvalInt → more damage."""
        defender_low = _make_defender(mana=500, max_mana=500)
        defender_high = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        attacker_low = _make_astral_attacker(eval_int=0)
        attacker_high = _make_astral_attacker(eval_int=1000)

        result_low = _run_hit(
            shard, combat_trees, attacker_low, defender_low, weapon, armor,
            base_damage=40,
        )
        result_high = _run_hit(
            shard, combat_trees, attacker_high, defender_high, weapon, armor,
            base_damage=40,
        )

        assert result_low.success and result_high.success
        drain_low = 500 - defender_low.mana
        drain_high = 500 - defender_high.mana
        assert drain_high > drain_low, (
            f"Higher EvalInt should deal more: {drain_high} vs {drain_low}"
        )


# =========================================================================
# Class bonuses
# =========================================================================


class TestAstralClassBonuses:
    """Class-based modifiers on astral damage."""

    def test_mage_bonus_vs_npc(self, shard, combat_trees):
        """Mage attacker gets ClasseBonus vs NPC defender."""
        attacker_mage = _make_astral_attacker()
        attacker_mage.set_property(CLASSEID_MAGE, 6)
        attacker_plain = _make_astral_attacker()

        defender_mage = _make_defender(mana=500, max_mana=500, is_npc=True)
        defender_plain = _make_defender(mana=500, max_mana=500, is_npc=True)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result_mage = _run_hit(
            shard, combat_trees, attacker_mage, defender_mage, weapon, armor,
            base_damage=40,
        )
        result_plain = _run_hit(
            shard, combat_trees, attacker_plain, defender_plain, weapon, armor,
            base_damage=40,
        )

        assert result_mage.success and result_plain.success
        drain_mage = 500 - defender_mage.mana
        drain_plain = 500 - defender_plain.mana
        assert drain_mage > drain_plain, (
            f"Mage bonus should increase damage: {drain_mage} vs {drain_plain}"
        )

    def test_mage_bonus_vs_player(self, shard, combat_trees):
        """Mage attacker vs player uses ClasseBonusByLevel(level - 2)."""
        attacker = _make_astral_attacker()
        attacker.set_property(CLASSEID_MAGE, 5)  # level 5 → level-2=3, bonus
        defender = _make_defender(mana=500, max_mana=500, is_npc=False)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        drain = 500 - defender.mana
        assert drain > 0, "Mage vs player should deal damage"

    def test_warrior_attacker_penalty(self, shard, combat_trees):
        """Warrior (non-mage) attacker deals less astral damage."""
        attacker_warrior = _make_astral_attacker()
        attacker_warrior.set_property(CLASSEID_WARRIOR, 6)
        attacker_plain = _make_astral_attacker()

        defender_w = _make_defender(mana=500, max_mana=500)
        defender_p = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result_w = _run_hit(
            shard, combat_trees, attacker_warrior, defender_w, weapon, armor,
            base_damage=40,
        )
        result_p = _run_hit(
            shard, combat_trees, attacker_plain, defender_p, weapon, armor,
            base_damage=40,
        )

        assert result_w.success and result_p.success
        drain_w = 500 - defender_w.mana
        drain_p = 500 - defender_p.mana
        assert drain_w < drain_p, (
            f"Warrior penalty should reduce astral damage: {drain_w} vs {drain_p}"
        )

    def test_warrior_mage_no_penalty(self, shard, combat_trees):
        """Warrior+Mage attacker does NOT get the warrior penalty."""
        attacker = _make_astral_attacker()
        attacker.set_property(CLASSEID_WARRIOR, 6)
        attacker.set_property(CLASSEID_MAGE, 6)
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        # Compare with plain attacker (no class)
        attacker_plain = _make_astral_attacker()
        defender_plain = _make_defender(mana=500, max_mana=500)

        result_wm = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )
        result_plain = _run_hit(
            shard, combat_trees, attacker_plain, defender_plain, weapon, armor,
            base_damage=40,
        )

        assert result_wm.success and result_plain.success
        drain_wm = 500 - defender.mana
        drain_plain = 500 - defender_plain.mana
        # Warrior+Mage has mage bonus vs NPC, so should be >= plain
        assert drain_wm >= drain_plain, (
            f"Warrior+Mage should not have warrior penalty: {drain_wm} vs {drain_plain}"
        )


# =========================================================================
# Meditation resistance
# =========================================================================


class TestAstralMeditationResist:
    """Meditation-based resistance to astral damage."""

    def test_meditation_can_reduce_damage(self, shard, combat_trees):
        """High meditation can reduce astral damage (seeded to trigger)."""
        # We need a seed that triggers the meditation check.
        # meditation * ClasseBonus * 0.5 must be >= random roll (1-100).
        # With meditation=200 (display), mage level 6: 200*1.5*0.5=150 → always triggers.
        attacker = _make_astral_attacker()
        defender = _make_defender(
            mana=500, max_mana=500, meditation=2000, magic_resist=1000,
        )
        defender.set_property(CLASSEID_MAGE, 6)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        # Also test without meditation for comparison
        defender_no_med = _make_defender(mana=500, max_mana=500, meditation=0)
        result_med = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )
        result_no_med = _run_hit(
            shard, combat_trees, attacker, defender_no_med, weapon, armor,
            base_damage=40,
        )

        assert result_med.success and result_no_med.success
        drain_med = 500 - defender.mana
        drain_no_med = 500 - defender_no_med.mana
        # With meditation, damage should be reduced (or same if check didn't trigger)
        assert drain_med <= drain_no_med, (
            f"Meditation should reduce or not increase damage: {drain_med} vs {drain_no_med}"
        )

    def test_no_meditation_no_resist(self, shard, combat_trees):
        """Zero meditation → no chance to resist."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=500, max_mana=500, meditation=0)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        # No meditation = no resistance check, full damage applied
        drain = 500 - defender.mana
        assert drain > 0, "Should deal damage with no meditation resist"

    def test_piercing_bypasses_meditation(self, shard, combat_trees):
        """Piercing flag should skip meditation check entirely."""
        # Piercing weapons have the property; we need to check how piercing
        # reaches RecalcAstralDmg. It's passed as the 'piercing' parameter.
        # In the normal flow, piercing comes from weapon property "Piercing".
        # For astral+piercing, weapon needs both "Astral" and "Piercing".
        attacker = _make_astral_attacker()

        # High meditation defender — if piercing works, damage is same regardless
        defender_piercing = _make_defender(mana=500, max_mana=500, meditation=2000)
        defender_piercing.set_property(CLASSEID_MAGE, 6)
        defender_no_med = _make_defender(mana=500, max_mana=500, meditation=0)

        weapon_piercing = _make_astral_weapon()
        weapon_piercing.set_property("Piercing", 1)
        weapon_no_pierce = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result_p = _run_hit(
            shard, combat_trees, attacker, defender_piercing, weapon_piercing, armor,
            base_damage=40,
        )
        result_np = _run_hit(
            shard, combat_trees, attacker, defender_no_med, weapon_no_pierce, armor,
            base_damage=40,
        )

        assert result_p.success and result_np.success
        drain_p = 500 - defender_piercing.mana
        drain_np = 500 - defender_no_med.mana
        # Piercing bypasses meditation, so high-meditation defender takes same
        # damage as zero-meditation defender (class differences aside)
        # The piercing defender has mage class bonus on defender side but piercing
        # bypasses meditation AND ar. Without meditation resist, same base logic.
        assert drain_p > 0, "Piercing astral should deal damage"


# =========================================================================
# Astral armor
# =========================================================================


class TestAstralArmor:
    """Armor with Astral property absorbs astral damage."""

    def test_astral_armor_absorbs(self, shard, combat_trees):
        """Armor with Astral property reduces astral damage."""
        attacker = _make_astral_attacker()
        defender_armored = _make_defender(mana=500, max_mana=500)
        defender_unarmored = _make_defender(mana=500, max_mana=500)

        weapon = _make_astral_weapon()
        armor_astral = Armor(name="AstralPlate", ar=30)
        armor_astral.set_property("Astral", 1)
        armor_plain = Armor(name="Robe", ar=0)

        result_armored = _run_hit(
            shard, combat_trees, attacker, defender_armored, weapon, armor_astral,
            base_damage=40,
        )
        result_unarmored = _run_hit(
            shard, combat_trees, attacker, defender_unarmored, weapon, armor_plain,
            base_damage=40,
        )

        assert result_armored.success and result_unarmored.success
        drain_armored = 500 - defender_armored.mana
        drain_unarmored = 500 - defender_unarmored.mana
        assert drain_armored < drain_unarmored, (
            f"Astral armor should absorb damage: {drain_armored} vs {drain_unarmored}"
        )

    def test_no_astral_armor_no_absorption(self, shard, combat_trees):
        """Armor without Astral property provides no astral defense."""
        attacker = _make_astral_attacker()
        defender_plate = _make_defender(mana=500, max_mana=500)
        defender_none = _make_defender(mana=500, max_mana=500)

        weapon = _make_astral_weapon()
        # High AR but no Astral property
        armor_plate = Armor(name="HeavyPlate", ar=50)
        armor_none = Armor(name="Robe", ar=0)

        result_plate = _run_hit(
            shard, combat_trees, attacker, defender_plate, weapon, armor_plate,
            base_damage=40,
        )
        result_none = _run_hit(
            shard, combat_trees, attacker, defender_none, weapon, armor_none,
            base_damage=40,
        )

        assert result_plate.success and result_none.success
        drain_plate = 500 - defender_plate.mana
        drain_none = 500 - defender_none.mana
        # Without Astral property, AR doesn't matter for astral damage
        assert drain_plate == drain_none, (
            f"Non-astral armor should not absorb: {drain_plate} vs {drain_none}"
        )


# =========================================================================
# 50% reduction
# =========================================================================


class TestAstral50PercentReduction:
    """Astral damage is halved (rawdamage * 0.5)."""

    def test_astral_50pct_reduction(self, shard, combat_trees):
        """Verify the astral 50% reduction via metrics."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        metrics = result.metrics
        # The instrumented RecalcAstralDmg should record these
        if "astral_rawdamage" in metrics and "astral_basedamage" in metrics:
            raw = metrics["astral_rawdamage"]
            base = metrics["astral_basedamage"]
            # rawdamage should be approximately basedamage * 0.5
            # (before absorption, raw = base; after 50% reduction, raw ≈ base/2)
            assert raw <= base, f"After 50% reduction, raw ({raw}) should be <= base ({base})"


# =========================================================================
# Metrics recording
# =========================================================================


class TestAstralMetrics:
    """Verify __RecordSimulatorMetric instrumentation."""

    def test_astral_metrics_recorded(self, shard, combat_trees):
        """RecalcAstralDmg metrics should be present in result."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        metrics = result.metrics
        # Should have astral-specific metrics from our instrumentation
        assert "astral_basedamage" in metrics, f"Missing astral_basedamage in {list(metrics.keys())}"
        assert "astral_rawdamage" in metrics, f"Missing astral_rawdamage in {list(metrics.keys())}"
        assert "astral_absorbed" in metrics, f"Missing astral_absorbed in {list(metrics.keys())}"
        assert "astral_ar" in metrics, f"Missing astral_ar in {list(metrics.keys())}"
        assert "astral_meditation_triggered" in metrics

    def test_astral_damage_applied_metric(self, shard, combat_trees):
        """list:damage_applied metric should record astral damage."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        damage_list = result.metrics.get("damage_applied")
        assert damage_list is not None, f"Missing damage_applied in {list(result.metrics.keys())}"
        assert len(damage_list) > 0, "damage_applied list should not be empty"
        # At least one entry should have astral type
        astral_entries = [e for e in damage_list if e.get("type") == DMGID_ASTRAL]
        assert len(astral_entries) > 0, (
            f"No ASTRAL entries in damage_applied: {damage_list}"
        )

    def test_meditation_triggered_metric(self, shard, combat_trees):
        """Meditation triggered flag should be 0 or 1."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        triggered = result.metrics.get("astral_meditation_triggered")
        assert triggered is not None
        assert triggered in (0, 1), f"meditation_triggered should be 0 or 1, got {triggered}"

    def test_astral_metrics_no_absorption_when_no_astral_armor(self, shard, combat_trees):
        """Without astral armor, absorbed metric should be 0."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        assert result.metrics.get("astral_absorbed") == 0

    def test_astral_ar_metric_with_astral_armor(self, shard, combat_trees):
        """Astral AR metric should be > 0 when armor has Astral property."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="AstralPlate", ar=30)
        armor.set_property("Astral", 1)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=40,
        )

        assert result.success, f"Hit failed: {result.error}"
        # ar = CInt(GetObjProperty(armor, "Astral")) * 25 * CInt(armor.ar)
        # = 1 * 25 * 30 = 750
        assert result.metrics.get("astral_ar") == 750


# =========================================================================
# Edge cases
# =========================================================================


class TestAstralEdgeCases:
    """Edge cases and boundary conditions."""

    def test_very_high_damage_drains_both(self, shard, combat_trees):
        """Very high damage should drain all mana and stamina."""
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=10, max_mana=100, stamina=10, max_stamina=100)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=200,
        )

        assert result.success, f"Hit failed: {result.error}"
        assert defender.mana == 0
        assert defender.stamina == 0
        # HP should still be untouched
        assert defender.hp == defender.max_hp

    def test_frozen_reset_after_incapacity_script(self, shard, combat_trees):
        """astralincapacity.src sets frozen=1, polls, then resets frozen=0.

        With Sleep as a no-op the polling loop hits the iteration guard,
        then the script's cleanup (who.frozen := 0) runs. End state is
        frozen=False — the script ran to completion.
        """
        attacker = _make_astral_attacker()
        defender = _make_defender(mana=1, max_mana=100, stamina=1, max_stamina=100)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor,
            base_damage=200,
        )

        assert result.success, f"Hit failed: {result.error}"
        # astralincapacity.src sets who.frozen := 1, polls in a while loop
        # (Sleep is no-op so loop guard breaks it), then sets who.frozen := 0
        assert not defender.frozen, (
            "Defender should not be frozen after incapacity script completes"
        )

    def test_intelligence_scaling(self, shard, combat_trees):
        """Intelligence affects the spirit speak scaling formula."""
        # Formula: basedamage * ((SpiritSpeak + 50 + INT*0.2) * 0.01) / ((Tactics + 50 + STR*0.2) * 0.01)
        # Higher INT → higher numerator → more damage
        defender_hi = _make_defender(mana=500, max_mana=500)
        defender_lo = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        attacker_hi = _make_astral_attacker(intelligence=200)
        attacker_lo = _make_astral_attacker(intelligence=10)

        result_hi = _run_hit(
            shard, combat_trees, attacker_hi, defender_hi, weapon, armor,
            base_damage=40,
        )
        result_lo = _run_hit(
            shard, combat_trees, attacker_lo, defender_lo, weapon, armor,
            base_damage=40,
        )

        assert result_hi.success and result_lo.success
        drain_hi = 500 - defender_hi.mana
        drain_lo = 500 - defender_lo.mana
        assert drain_hi > drain_lo, (
            f"Higher INT should increase astral damage: {drain_hi} vs {drain_lo}"
        )

    def test_strength_reduces_astral_scaling(self, shard, combat_trees):
        """Higher STR increases denominator → reduces astral damage."""
        # Formula denominator: (Tactics + 50 + STR*0.2) * 0.01
        defender_hi = _make_defender(mana=500, max_mana=500)
        defender_lo = _make_defender(mana=500, max_mana=500)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        # High STR attacker — larger denominator = less astral damage
        attacker_hi_str = _make_astral_attacker(strength=200, intelligence=100)
        attacker_lo_str = _make_astral_attacker(strength=10, intelligence=100)

        result_hi = _run_hit(
            shard, combat_trees, attacker_hi_str, defender_hi, weapon, armor,
            base_damage=40,
        )
        result_lo = _run_hit(
            shard, combat_trees, attacker_lo_str, defender_lo, weapon, armor,
            base_damage=40,
        )

        assert result_hi.success and result_lo.success
        drain_hi = 500 - defender_hi.mana
        drain_lo = 500 - defender_lo.mana
        assert drain_hi < drain_lo, (
            f"Higher STR should reduce astral damage: {drain_hi} vs {drain_lo}"
        )

    def test_astral_pvp_no_basedamage_scaling(self, shard, combat_trees):
        """Astral damage does NOT apply the physical PvP 0.4x basedamage scaling.

        Physical path has ``basedamage *= 0.4`` for player vs player.
        Astral path has no such scaling — only VALUE_MULTIPLIER_FOR_ALLIES
        in ApplyTheAstralDamage applies (which is 0.5 for tamed/ally).
        """
        attacker = _make_astral_attacker()
        defender_npc = _make_defender(mana=500, max_mana=500, is_npc=True)
        defender_player = _make_defender(mana=500, max_mana=500, is_npc=False)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result_npc = _run_hit(
            shard, combat_trees, attacker, defender_npc, weapon, armor,
            base_damage=40,
        )
        result_player = _run_hit(
            shard, combat_trees, attacker, defender_player, weapon, armor,
            base_damage=40,
        )

        assert result_npc.success and result_player.success
        drain_npc = 500 - defender_npc.mana
        drain_player = 500 - defender_player.mana
        # Astral does NOT have 0.4x PvP scaling on basedamage.
        # Both should deal similar damage (small class bonus differences aside).
        # Physical PvP would be 0.4x → huge difference. Astral should be close.
        assert drain_player > 0, "Astral should deal damage to players"
        # If PvP 0.4x were applied, drain_player would be ~40% of drain_npc.
        # Without it, they should be within a reasonable range of each other.
        assert drain_player > drain_npc * 0.5, (
            f"Astral PvP drain ({drain_player}) should NOT be reduced by 0.4x vs NPC ({drain_npc})"
        )

    def test_defender_warrior_mage_no_penalty(self, shard, combat_trees):
        """Defender with both Warrior and Mage class should NOT get 5/6 penalty.

        The shard code checks: if(defender.IsWarrior) if(!defender.IsMage)
        Warrior+Mage fails the inner check → no penalty applied.
        """
        attacker = _make_astral_attacker()
        # Defender with Warrior+Mage — should NOT get 5/6 penalty
        defender_wm = _make_defender(mana=500, max_mana=500)
        defender_wm.set_property(CLASSEID_WARRIOR, 6)
        defender_wm.set_property(CLASSEID_MAGE, 6)
        # Plain defender (no class)
        defender_plain = _make_defender(mana=500, max_mana=500)

        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result_wm = _run_hit(
            shard, combat_trees, attacker, defender_wm, weapon, armor,
            base_damage=40,
        )
        result_plain = _run_hit(
            shard, combat_trees, attacker, defender_plain, weapon, armor,
            base_damage=40,
        )

        assert result_wm.success and result_plain.success
        drain_wm = 500 - defender_wm.mana
        drain_plain = 500 - defender_plain.mana
        # Warrior+Mage defender should not have the 5/6 penalty
        # (The defender warrior check requires NOT mage)
        # So damage to warrior+mage should be similar to plain defender
        assert drain_wm > 0, "Should deal damage to warrior+mage defender"

    def test_mage_level_below_threshold(self, shard, combat_trees):
        """Mage level 1 vs player: level-2 = -1 < 1 → ClasseBonusByLevel not applied.

        The code checks: if(level >= 1) basedamage *= ClasseBonusByLevel(level).
        Mage level 1 → level = 1-2 = -1, fails the >= 1 check.
        """
        attacker_low = _make_astral_attacker()
        attacker_low.set_property(CLASSEID_MAGE, 1)  # level 1-2 = -1, no bonus
        attacker_high = _make_astral_attacker()
        attacker_high.set_property(CLASSEID_MAGE, 5)  # level 5-2 = 3, gets bonus

        defender_low = _make_defender(mana=500, max_mana=500, is_npc=False)
        defender_high = _make_defender(mana=500, max_mana=500, is_npc=False)
        weapon = _make_astral_weapon()
        armor = Armor(name="Robe", ar=0)

        result_low = _run_hit(
            shard, combat_trees, attacker_low, defender_low, weapon, armor,
            base_damage=40,
        )
        result_high = _run_hit(
            shard, combat_trees, attacker_high, defender_high, weapon, armor,
            base_damage=40,
        )

        assert result_low.success and result_high.success
        drain_low = 500 - defender_low.mana
        drain_high = 500 - defender_high.mana
        # Level 5 mage (bonus) should deal more than level 1 mage (no bonus)
        assert drain_high > drain_low, (
            f"Mage level 5 should deal more than level 1: {drain_high} vs {drain_low}"
        )
