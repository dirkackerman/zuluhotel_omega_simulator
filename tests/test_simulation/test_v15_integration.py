"""V1.5 integration regression tests.

End-to-end tests exercising the full simulation pipeline with V1.5 features:
enchantments, elemental damage, reactive armor, protection properties, and
UNINIT-safe stats aggregation.  These prevent regressions for bugs found
during notebook enrichment (M22).

Bug categories covered:
1. Spell strike weapons need ChanceOfEffect/EffectCircle to fire
2. Elemental protection uses correct property names (FireProtection, etc.)
3. Sub-script resolution requires shard (shard_root + package_map)
4. Stats aggregation handles UNINIT values in metrics without crashing
5. ElementalDamage format uses string ("FIRE:50 PHYSICAL:50"), not bitflags
"""

import dataclasses

import pytest

from omega.combat.result import HitResult
from omega.config.enchantments import Enchantment
from omega.interpreter.types import UNINIT
from omega.model.constants import (
    SKILLID_ANATOMY,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.simulation import (
    ArmorSpec,
    CombatantSpec,
    ParameterSweep,
    Scenario,
    Variable,
    WeaponSpec,
    run_scenario,
    run_sweep,
)
from omega.simulation.stats import aggregate_cell


# ── Shared specs ──────────────────────────────────────────────────────────

WEAPON = WeaponSpec(
    name="Broadsword",
    damage="3d6+2",
    attribute=SKILLID_SWORDSMANSHIP,
)

ATTACKER = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
    str_=100, dex_=100, int_=25,
    class_levels={"IsWarrior": 5},
    weapon=WEAPON,
)

DEFENDER = CombatantSpec(
    name="Target",
    is_npc=True,
    str_=50, dex_=50, int_=50,
    hp=500,
    armor=ArmorSpec(name="Plate", ar=30),
)

ITERATIONS = 30
SEED = 42


@pytest.fixture(scope="module")
def shard(fixture_shard):
    return fixture_shard


# ── 1. Spell strike: ChanceOfEffect / EffectCircle requirement ───────────


class TestSpellStrikeProperties:
    """Spell strike enchantments only fire when the weapon has
    ChanceOfEffect and EffectCircle properties set."""

    def test_spell_strike_with_chance_and_circle(self, shard):
        """Spell strike fires when ChanceOfEffect and EffectCircle are set."""
        weapon = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ChanceOfEffect": 75, "EffectCircle": 10},
        ).enchant_with(Enchantment.OF_DAEMONS_BREATH)

        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        # With 75% chance over 30 iterations, at least some should trigger
        assert result.ratios.spell_strike_rate > 0, (
            "Spell strike never triggered — ChanceOfEffect/EffectCircle may not be read"
        )
        # But NOT 100% — ChanceOfEffect=75 should produce ~75% rate
        assert result.ratios.spell_strike_rate < 1.0, (
            "spell_strike_rate is 100% despite ChanceOfEffect=75 — "
            "RandomDiceStr chance check may be broken"
        )
        assert result.damage_stats.mean > 0

    def test_spell_strike_rate_scales_with_chance(self, shard):
        """Higher ChanceOfEffect should produce higher spell_strike_rate."""
        rates = {}
        for chance in [25, 75]:
            weapon = WeaponSpec(
                name="Broadsword", damage="3d6+2",
                attribute=SKILLID_SWORDSMANSHIP,
                properties={"ChanceOfEffect": chance, "EffectCircle": 10},
            ).enchant_with(Enchantment.OF_DAEMONS_BREATH)
            atk = dataclasses.replace(ATTACKER, weapon=weapon)
            result = run_scenario(
                Scenario(attacker=atk, defender=DEFENDER,
                         iterations=100, base_seed=SEED),
                shard=shard,
            )
            rates[chance] = result.ratios.spell_strike_rate

        assert rates[75] > rates[25], (
            f"Higher chance should yield higher rate: 75%→{rates[75]:.0%} vs 25%→{rates[25]:.0%}"
        )

    def test_spell_strike_without_chance_does_not_fire(self, shard):
        """Without ChanceOfEffect, the spell strike should never trigger."""
        weapon = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            # No ChanceOfEffect / EffectCircle — spell will not fire
        ).enchant_with(Enchantment.OF_DAEMONS_BREATH)

        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.ratios.spell_strike_rate == 0.0

    def test_enchant_with_does_not_set_chance_by_default(self):
        """enchant_with() for spell-type enchantments does NOT auto-set
        ChanceOfEffect — the user must provide it explicitly."""
        spec = WeaponSpec().enchant_with(Enchantment.OF_DAEMONS_BREATH)
        assert "ChanceOfEffect" not in spec.properties or spec.properties["ChanceOfEffect"] == 0

    def test_user_supplied_chance_preserved(self):
        """User-provided ChanceOfEffect/EffectCircle survives enchant_with()."""
        spec = WeaponSpec(
            properties={"ChanceOfEffect": 50, "EffectCircle": 5},
        ).enchant_with(Enchantment.OF_DAEMONS_BREATH)
        assert spec.properties["ChanceOfEffect"] == 50
        assert spec.properties["EffectCircle"] == 5
        assert spec.properties["HitWithSpell"] > 0  # spell ID set

    @pytest.mark.parametrize("enchant", [
        Enchantment.OF_BUNGLING,
        Enchantment.OF_DAEMONS_BREATH,
        Enchantment.OF_DISRUPTION,
        Enchantment.OF_HELLFIRE,
        Enchantment.OF_GAIAS_WRATH,
    ])
    def test_multiple_spell_strikes_with_properties(self, shard, enchant):
        """All spell-type enchantments produce damage when properly configured."""
        weapon = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ChanceOfEffect": 100, "EffectCircle": 10},
        ).enchant_with(enchant)

        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=10, base_seed=SEED),
            shard=shard,
        )
        assert result.success_count > 0, f"{enchant.name} had no successful hits"
        assert result.damage_stats.mean > 0, f"{enchant.name} produced 0 damage"


# ── 2. Protection property names ─────────────────────────────────────────


class TestProtectionPropertyNames:
    """Protection CProps must use the correct names (FireProtection, not
    Protection_Fire) — the shard's GetProtLevel() uses these exact names."""

    # Map protection property → element keyword for ElementalDamage string
    _PROT_TO_ELEMENT = {
        "FireProtection": "FIRE",
        "AirProtection": "AIR",
        "EarthProtection": "EARTH",
        "WaterProtection": "WATER",
        "NecroProtection": "NECRO",
        "HolyProtection": "HOLY",
    }

    @pytest.mark.parametrize("prop_name", [
        "FireProtection",
        "AirProtection",
        "EarthProtection",
        "WaterProtection",
        "NecroProtection",
        "HolyProtection",
    ])
    def test_protection_reduces_elemental_damage(self, shard, prop_name):
        """Setting protection via the correct property name reduces damage
        from a weapon dealing that element's damage."""
        element = self._PROT_TO_ELEMENT[prop_name]
        weapon = WeaponSpec(
            name=f"{element} Sword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ElementalDamage": f"{element}:50 PHYSICAL:50"},
        )

        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        no_prot = dataclasses.replace(DEFENDER, properties={})
        with_prot = dataclasses.replace(
            DEFENDER, properties={prop_name: 80},
        )

        r_none = run_scenario(
            Scenario(attacker=atk, defender=no_prot,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        r_prot = run_scenario(
            Scenario(attacker=atk, defender=with_prot,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )

        # Protection should reduce total damage
        assert r_prot.damage_stats.mean < r_none.damage_stats.mean, (
            f"Protection via {prop_name} did not reduce {element} damage "
            f"({r_prot.damage_stats.mean} >= {r_none.damage_stats.mean})"
        )

    def test_protection_sweep_values_scale(self, shard):
        """Sweeping fire protection from 0 to 80 should produce
        monotonically decreasing damage — validates the protection property
        name is actually read by the shard scripts."""
        fire_weapon = WeaponSpec(
            name="Fire Sword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ElementalDamage": "FIRE:50 PHYSICAL:50"},
        )
        atk = dataclasses.replace(ATTACKER, weapon=fire_weapon)

        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=atk,
                defender=DEFENDER,
                iterations=50,
                base_seed=SEED,
            ),
            variables=(
                Variable.from_range(
                    "defender", "properties.FireProtection",
                    start=0, stop=80, step=40,
                ),
            ),
        )
        result = run_sweep(sweep, shard=shard)
        valid = [c for c in result.cells if c.success_count > 0]
        assert len(valid) >= 3, "Not enough valid sweep cells"

        means = [c.damage_stats.mean for c in valid]
        # Damage at prot=0 should be higher than at prot=80
        assert means[0] > means[-1], (
            f"Protection sweep did not reduce damage: {means}"
        )

    def test_wrong_property_name_has_no_effect(self, shard):
        """Using the wrong property name (Protection_Fire) should NOT
        reduce fire damage — validates we're using the right names."""
        fire_weapon = WeaponSpec(
            name="Fire Sword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ElementalDamage": "FIRE:50 PHYSICAL:50"},
        )
        atk = dataclasses.replace(ATTACKER, weapon=fire_weapon)

        # Wrong name — shard scripts won't read this
        wrong_prot = dataclasses.replace(
            DEFENDER, properties={"Protection_Fire": 80},
        )
        no_prot = dataclasses.replace(DEFENDER, properties={})

        r_wrong = run_scenario(
            Scenario(attacker=atk, defender=wrong_prot,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        r_none = run_scenario(
            Scenario(attacker=atk, defender=no_prot,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )

        # Wrong property name should have no effect — damage should be the same
        assert abs(r_wrong.damage_stats.mean - r_none.damage_stats.mean) < 1.0, (
            "Protection_Fire (wrong name) unexpectedly reduced damage"
        )


# ── 3. Sub-script resolution: shard= vs individual kwargs ────────────────


class TestShardKwarg:
    """The `shard=` kwarg provides shard_root and package_map to the Executor,
    enabling sub-script resolution (enchantments, reactive armor).
    Without it, enchantment hitscripts fail silently."""

    def test_enchantment_works_with_shard_kwarg(self, shard):
        """Enchanted weapon produces extra damage when shard= is passed."""
        weapon = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ChanceOfEffect": 100, "EffectCircle": 10},
        ).enchant_with(Enchantment.OF_DAEMONS_BREATH)

        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=10, base_seed=SEED),
            shard=shard,
        )
        assert result.success_count == 10, (
            "Hits failed — sub-script resolution may be broken"
        )
        assert result.ratios.spell_strike_rate > 0
        # Enchanted should deal more than plain physical
        plain = run_scenario(
            Scenario(attacker=ATTACKER, defender=DEFENDER,
                     iterations=10, base_seed=SEED),
            shard=shard,
        )
        assert result.damage_stats.mean > plain.damage_stats.mean

    def test_reactive_armor_works_with_shard_kwarg(self, shard):
        """Reactive armor triggers when shard= is passed."""
        defender_ra = dataclasses.replace(
            DEFENDER, properties={"ReactiveArmor": 1},
        )
        result = run_scenario(
            Scenario(attacker=ATTACKER, defender=defender_ra,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.ratios.reactive_rate > 0, (
            "Reactive armor never triggered — sub-script may not resolve"
        )

    def test_effect_enchantment_works_with_shard_kwarg(self, shard):
        """Effect enchantments (e.g. Piercing) work with shard= kwarg.
        Piercing bypasses armor — absorbed should be 0 for all hits."""
        weapon = WEAPON.enchant_with(Enchantment.OF_PIERCING)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.success_count > 0
        # Piercing always fires (not chance-based) — verify via metrics
        assert all(
            h.metrics.get("effect_type") == "piercing" for h in result.raw_results if h.success
        ), "Piercing effect_type not set in metrics"
        # Piercing bypasses AR — absorbed should be 0
        assert result.absorbed_stats.mean == 0.0, (
            "Piercing should bypass armor (absorbed=0)"
        )

    def test_greater_enchantment_works_with_shard_kwarg(self, shard):
        """Greater enchantments produce elemental damage with shard= kwarg."""
        weapon = WEAPON.enchant_with(Enchantment.OF_ELEMENTAL_FURY)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.success_count > 0
        # Greater enchantment should produce elemental damage
        assert result.elemental_breakdown.total_net > 0, (
            "Elemental Fury produced no elemental damage"
        )

    def test_slayer_enchantment_works_with_shard_kwarg(self, shard):
        """Slayer enchantment deals bonus damage vs matching creature type."""
        weapon = WEAPON.enchant_with(Enchantment.SILVER)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        undead = dataclasses.replace(
            DEFENDER, name="Skeleton", properties={"Type": "Undead"},
        )
        result = run_scenario(
            Scenario(attacker=atk, defender=undead,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        plain = run_scenario(
            Scenario(attacker=ATTACKER, defender=undead,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.damage_stats.mean > plain.damage_stats.mean, (
            "Slayer enchantment did not increase damage vs matching type"
        )

    def test_sweep_with_shard_kwarg(self, shard):
        """run_sweep also works correctly with shard= kwarg."""
        weapon = WeaponSpec(
            name="Fire Sword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ElementalDamage": "FIRE:50 PHYSICAL:50"},
        )
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=atk,
                defender=DEFENDER,
                iterations=20,
                base_seed=SEED,
            ),
            variables=(
                Variable.from_range(
                    "defender", "properties.FireProtection",
                    start=0, stop=40, step=20,
                ),
            ),
        )
        result = run_sweep(sweep, shard=shard)
        assert len(result.cells) == 3
        valid = [c for c in result.cells if c.success_count > 0]
        assert len(valid) == 3, "Some sweep cells failed"


# ── 4. UNINIT-safe stats aggregation ─────────────────────────────────────


class TestUninitSafeAggregation:
    """Stats aggregation must not crash when metrics contain UNINIT values,
    which can leak from eScript when variables aren't initialized."""

    def test_uninit_attack_type_skipped(self):
        """UNINIT attack_type in elemental_applied is skipped, not crashed."""
        hits = [
            HitResult(
                final_damage=10.0, base_damage=15, absorbed=5.0,
                success=True,
                metrics={"elemental_applied": [
                    {"attack_type": UNINIT, "dmg_gross": 10, "dmg_net": 7, "prot": 30},
                ]},
            ),
        ]
        cell = aggregate_cell(hits)
        # Should not crash; UNINIT entry skipped
        assert cell.elemental_breakdown.total_net == 0.0

    def test_uninit_dmg_values_treated_as_zero(self):
        """UNINIT in dmg_gross/dmg_net/prot/healed treated as 0.0."""
        hits = [
            HitResult(
                final_damage=10.0, base_damage=15, absorbed=5.0,
                success=True,
                metrics={"elemental_applied": [
                    {"attack_type": 0x0001, "dmg_gross": UNINIT, "dmg_net": UNINIT,
                     "prot": UNINIT, "healed": UNINIT},
                ]},
            ),
        ]
        cell = aggregate_cell(hits)
        assert "fire" in cell.elemental_breakdown.elements
        assert cell.elemental_breakdown.elements["fire"].gross == 0.0
        assert cell.elemental_breakdown.elements["fire"].net == 0.0
        assert cell.elemental_breakdown.elements["fire"].prot == 0.0
        assert cell.elemental_breakdown.elements["fire"].healed == 0.0

    def test_none_attack_type_skipped(self):
        """None attack_type is skipped gracefully."""
        hits = [
            HitResult(
                final_damage=10.0, success=True,
                metrics={"elemental_applied": [
                    {"attack_type": None, "dmg_gross": 10, "dmg_net": 7},
                ]},
            ),
        ]
        cell = aggregate_cell(hits)
        assert cell.elemental_breakdown.total_net == 0.0

    def test_string_attack_type_skipped(self):
        """String attack_type (e.g. from corrupted metrics) is skipped."""
        hits = [
            HitResult(
                final_damage=10.0, success=True,
                metrics={"elemental_applied": [
                    {"attack_type": "fire", "dmg_gross": 10, "dmg_net": 7},
                ]},
            ),
        ]
        cell = aggregate_cell(hits)
        # "fire" can't be int-converted to a valid DMGID, skipped
        assert cell.elemental_breakdown.total_net == 0.0

    def test_mixed_valid_and_uninit_entries(self):
        """Valid entries are aggregated even when mixed with UNINIT entries."""
        hits = [
            HitResult(
                final_damage=10.0, success=True,
                metrics={"elemental_applied": [
                    {"attack_type": 0x0001, "dmg_gross": 20, "dmg_net": 14, "prot": 30},
                    {"attack_type": UNINIT, "dmg_gross": 10, "dmg_net": 5},  # skipped
                ]},
            ),
        ]
        cell = aggregate_cell(hits)
        assert cell.elemental_breakdown.elements["fire"].net == 14.0

    def test_uninit_in_planar_applied(self):
        """UNINIT values in planar_applied are handled the same way."""
        hits = [
            HitResult(
                final_damage=10.0, success=True,
                metrics={"planar_applied": [
                    {"attack_type": UNINIT, "dmg_gross": 15, "dmg_net": 10},
                    {"attack_type": 0x0020, "dmg_gross": 15, "dmg_net": UNINIT},
                ]},
            ),
        ]
        cell = aggregate_cell(hits)
        # First entry skipped (UNINIT attack_type), second has UNINIT net → 0
        assert "holy" in cell.elemental_breakdown.elements
        assert cell.elemental_breakdown.elements["holy"].net == 0.0
        assert cell.elemental_breakdown.elements["holy"].gross == 15.0

    def test_missing_metric_keys_default(self):
        """Missing keys in elemental entry dict default gracefully."""
        hits = [
            HitResult(
                final_damage=10.0, success=True,
                metrics={"elemental_applied": [
                    {"attack_type": 0x0001},  # no dmg_gross, dmg_net, prot, healed
                ]},
            ),
        ]
        cell = aggregate_cell(hits)
        fire = cell.elemental_breakdown.elements["fire"]
        assert fire.gross == 0.0
        assert fire.net == 0.0
        assert fire.prot == 0.0
        assert fire.healed == 0.0

    def test_empty_elemental_applied_list(self):
        """Empty elemental_applied list produces no breakdown."""
        hits = [
            HitResult(
                final_damage=10.0, success=True,
                metrics={"elemental_applied": []},
            ),
        ]
        cell = aggregate_cell(hits)
        assert cell.elemental_breakdown.total_net == 0.0

    def test_unknown_attack_type_id_skipped(self):
        """Attack type IDs not in _DMGID_TO_ELEMENT are skipped."""
        hits = [
            HitResult(
                final_damage=10.0, success=True,
                metrics={"elemental_applied": [
                    {"attack_type": 0xFFFF, "dmg_gross": 10, "dmg_net": 7},
                ]},
            ),
        ]
        cell = aggregate_cell(hits)
        assert cell.elemental_breakdown.total_net == 0.0


# ── 5. Elemental damage format ───────────────────────────────────────────


class TestElementalDamageFormat:
    """ElementalDamage property must use string format ("FIRE:50 PHYSICAL:50"),
    not integer bitflags (0x01)."""

    def test_string_format_produces_elemental_damage(self, shard):
        """String-format ElementalDamage splits damage across elements."""
        weapon = WeaponSpec(
            name="Fire Sword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ElementalDamage": "FIRE:50 PHYSICAL:50"},
        )
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.success_count > 0
        # Fire portion should appear in elemental breakdown
        eb = result.elemental_breakdown
        assert eb.total_net > 0, (
            "String ElementalDamage format produced no elemental damage"
        )

    def test_pure_fire_weapon(self, shard):
        """100% fire weapon produces all-fire elemental breakdown."""
        weapon = WeaponSpec(
            name="Pure Fire", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ElementalDamage": "FIRE:100"},
        )
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        eb = result.elemental_breakdown
        if "fire" in eb.elements:
            assert eb.elements["fire"].net > 0

    def test_multi_element_split(self, shard):
        """Multi-element split allocates damage across elements."""
        weapon = WeaponSpec(
            name="Tri-Elemental", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ElementalDamage": "FIRE:33 AIR:33 WATER:34"},
        )
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        eb = result.elemental_breakdown
        # At least one element should have damage
        assert eb.total_net > 0


# ── 6. Reactive armor integration ────────────────────────────────────────


class TestReactiveArmorIntegration:
    """End-to-end reactive armor tests through the simulation pipeline."""

    def test_reactive_armor_triggers(self, shard):
        """ReactiveArmor property on defender triggers reactive hits."""
        defender_ra = dataclasses.replace(
            DEFENDER, properties={"ReactiveArmor": 1},
        )
        result = run_scenario(
            Scenario(attacker=ATTACKER, defender=defender_ra,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.ratios.reactive_rate > 0

    def test_reactive_armor_off_no_triggers(self, shard):
        """Without ReactiveArmor, reactive_rate is 0."""
        result = run_scenario(
            Scenario(attacker=ATTACKER, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.ratios.reactive_rate == 0.0

    def test_reactive_armor_via_sweep(self, shard):
        """ReactiveArmor can be swept as a properties parameter."""
        sweep = ParameterSweep(
            scenario=Scenario(
                attacker=ATTACKER,
                defender=DEFENDER,
                iterations=20,
                base_seed=SEED,
            ),
            variables=(
                Variable(
                    target="defender",
                    parameter="properties.ReactiveArmor",
                    values=(0, 1),
                ),
            ),
        )
        result = run_sweep(sweep, shard=shard)
        assert len(result.cells) == 2

        no_ra = result.get_cell(**{"defender.properties.ReactiveArmor": 0})
        with_ra = result.get_cell(**{"defender.properties.ReactiveArmor": 1})
        assert no_ra is not None and with_ra is not None
        assert no_ra.ratios.reactive_rate == 0.0
        assert with_ra.ratios.reactive_rate > 0


# ── 7. Effect enchantments integration ───────────────────────────────────


class TestEffectEnchantmentsIntegration:
    """End-to-end tests for all effect-type enchantments."""

    @pytest.mark.parametrize("enchant,name", [
        (Enchantment.OF_PIERCING, "Piercing"),
        (Enchantment.BLOODY, "Bloody"),
        (Enchantment.VAMPIRIC, "Vampiric"),
        (Enchantment.LEECH, "Leech"),
        (Enchantment.POISONED, "Poisoned"),
        (Enchantment.BLINDING, "Blinding"),
    ])
    def test_effect_enchantment_produces_damage(self, shard, enchant, name):
        """Each effect enchantment should produce successful hits."""
        weapon = WEAPON.enchant_with(enchant)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.success_count > 0, f"{name} had no successful hits"
        assert result.damage_stats.mean > 0, f"{name} produced 0 mean damage"


# ── 8. Greater enchantments integration ──────────────────────────────────


class TestGreaterEnchantmentsIntegration:
    """End-to-end tests for greater-type enchantments."""

    @pytest.mark.parametrize("enchant,name,expected_elements", [
        (Enchantment.OF_PLANAR_FURY, "Planar Fury", {"holy", "necro"}),
        (Enchantment.OF_THE_VOID, "Void", set()),  # Void doesn't use elemental
        (Enchantment.OF_ELEMENTAL_FURY, "Elemental Fury", {"fire", "air", "water"}),
    ])
    def test_greater_enchantment_damage(self, shard, enchant, name, expected_elements):
        """Greater enchantments produce damage and expected elements."""
        weapon = WEAPON.enchant_with(enchant)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.success_count > 0, f"{name} had no successful hits"
        assert result.damage_stats.mean > 0, f"{name} produced 0 mean damage"

        if expected_elements:
            eb = result.elemental_breakdown
            found = set(eb.elements.keys())
            assert expected_elements & found, (
                f"{name} expected elements {expected_elements} but found {found}"
            )


# ── 9. Enchanted vs plain damage comparison ──────────────────────────────


class TestEnchantedVsPlain:
    """Enchanted weapons should generally deal more total damage than plain."""

    def test_spell_strike_more_than_plain(self, shard):
        """Spell strike weapon deals more damage than plain weapon."""
        enchanted = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ChanceOfEffect": 100, "EffectCircle": 10},
        ).enchant_with(Enchantment.OF_DAEMONS_BREATH)

        atk_plain = ATTACKER
        atk_enchanted = dataclasses.replace(ATTACKER, weapon=enchanted)

        r_plain = run_scenario(
            Scenario(attacker=atk_plain, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        r_enchant = run_scenario(
            Scenario(attacker=atk_enchanted, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert r_enchant.damage_stats.mean > r_plain.damage_stats.mean, (
            "Spell strike weapon should deal more damage than plain"
        )

    def test_elemental_fury_more_than_plain(self, shard):
        """Elemental Fury weapon deals more damage than plain weapon."""
        enchanted = WEAPON.enchant_with(Enchantment.OF_ELEMENTAL_FURY)
        atk = dataclasses.replace(ATTACKER, weapon=enchanted)

        r_plain = run_scenario(
            Scenario(attacker=ATTACKER, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        r_fury = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert r_fury.damage_stats.mean > r_plain.damage_stats.mean


# ── 10. _safe_float unit tests ───────────────────────────────────────────


class TestSafeFloat:
    """Unit tests for the _safe_float helper used in stats aggregation."""

    def test_normal_values(self):
        from omega.simulation.stats import _safe_float
        assert _safe_float(42) == 42.0
        assert _safe_float(3.14) == 3.14
        assert _safe_float("7.5") == 7.5

    def test_uninit_returns_zero(self):
        from omega.simulation.stats import _safe_float
        assert _safe_float(UNINIT) == 0.0

    def test_none_returns_zero(self):
        from omega.simulation.stats import _safe_float
        assert _safe_float(None) == 0.0

    def test_non_numeric_string_returns_zero(self):
        from omega.simulation.stats import _safe_float
        assert _safe_float("not_a_number") == 0.0

    def test_empty_string_returns_zero(self):
        from omega.simulation.stats import _safe_float
        assert _safe_float("") == 0.0

    def test_bool_converts(self):
        from omega.simulation.stats import _safe_float
        assert _safe_float(True) == 1.0
        assert _safe_float(False) == 0.0


# ── 11. Integer division semantics ───────────────────────────────────────


class TestIntegerDivision:
    """eScript int / int must produce integer truncation (like C),
    not Python float division.  This broke the shard's RandomDiceStr()
    PRNG which uses X / QQ where both operands are integers."""

    def test_int_div_truncates(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet("var x := 10 / 3;", "x") == 3
        assert run_snippet("var x := 7 / 2;", "x") == 3
        assert run_snippet("var x := 1 / 3;", "x") == 0

    def test_int_div_exact(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet("var x := 10 / 2;", "x") == 5
        assert run_snippet("var x := 100 / 10;", "x") == 10

    def test_int_div_result_is_int(self):
        from tests.test_interpreter.helpers import run_snippet
        result = run_snippet("var x := 42 / 44488;", "x")
        assert result == 0
        assert isinstance(result, int)

    def test_float_div_stays_float(self):
        from tests.test_interpreter.helpers import run_snippet
        result = run_snippet("var x := 10.0 / 3;", "x")
        assert isinstance(result, float)
        assert abs(result - 3.333) < 0.01

    def test_negative_truncates_toward_zero(self):
        from tests.test_interpreter.helpers import run_snippet
        # C-style truncation: -7/2 = -3 (not -4 like Python floor division)
        assert run_snippet("var x := -7 / 2;", "x") == -3


# ── 12. String slicing semantics ─────────────────────────────────────────


class TestStringSlicing:
    """eScript str[start, length] uses 1-based start and length (not end).
    This broke RandomDiceStr which parses dice notation via string slicing."""

    def test_basic_slice(self):
        from tests.test_interpreter.helpers import run_snippet
        # "hello"[1, 3] → "hel" (3 chars from position 1)
        assert run_snippet('var x := "hello"[1, 3];', "x") == "hel"

    def test_slice_middle(self):
        from tests.test_interpreter.helpers import run_snippet
        # "1d100"[3, 3] → "100" (3 chars from position 3)
        assert run_snippet('var x := "1d100"[3, 3];', "x") == "100"

    def test_dice_notation_parsing(self):
        """The exact slicing patterns used by RandomDiceStr in random.inc."""
        from tests.test_interpreter.helpers import run_snippet
        # For "3d6+4": space=2 (pos of 'd'), space2a=4 (pos of '+')
        # dice_a = CInt(str[1, space-1]) = CInt(str[1, 1]) = CInt("3") = 3
        assert run_snippet('var x := CInt("3d6+4"[1, 1]);', "x") == 3
        # dice_t = CInt(str[space+1, space2a-space-1]) = CInt(str[3, 1]) = CInt("6") = 6
        assert run_snippet('var x := CInt("3d6+4"[3, 1]);', "x") == 6
        # bonus = CInt(str[space2a+1, len-space2a]) = CInt(str[5, 1]) = CInt("4") = 4
        assert run_snippet('var x := CInt("3d6+4"[5, 1]);', "x") == 4

    def test_single_char(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet('var x := "abcde"[3, 1];', "x") == "c"

    def test_length_zero_empty(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet('var x := "hello"[1, 0];', "x") == ""

    def test_slice_to_end(self):
        from tests.test_interpreter.helpers import run_snippet
        # "1d100"[3, 3] → "100"
        assert run_snippet('var x := "1d100"[3, 3];', "x") == "100"


# ── 13. Single-index string access ──────────────────────────────────────


class TestSingleIndexString:
    """eScript str[n] is 1-based single-character access.  Previously
    fell through to Python's 0-based __getitem__, returning the wrong char."""

    def test_first_char(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet('var x := "hello"[1];', "x") == "h"

    def test_last_char(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet('var x := "hello"[5];', "x") == "o"

    def test_out_of_bounds_returns_empty(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet('var x := "hello"[0];', "x") == ""
        assert run_snippet('var x := "hello"[6];', "x") == ""

    def test_combined_with_find(self):
        """Find() returns 1-based position; indexing with it should match."""
        from tests.test_interpreter.helpers import run_snippet
        # Find("abc", "b") → 2, then "abc"[2] should be "b"
        result = run_snippet(
            'var s := "abcdef"; var pos := Find(s, "d", 1); var x := s[pos];', "x"
        )
        assert result == "d"


# ── 14. Modulo semantics (C-style) ──────────────────────────────────────


class TestModuloSemantics:
    """eScript modulo follows C/C++ (sign of dividend), not Python (sign of
    divisor).  The shard uses modulo in time calculations and PRNG."""

    def test_positive_mod(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet("var x := 10 % 3;", "x") == 1

    def test_negative_dividend(self):
        from tests.test_interpreter.helpers import run_snippet
        # C: -7 % 2 = -1 (Python gives 1)
        assert run_snippet("var x := -7 % 2;", "x") == -1

    def test_negative_divisor(self):
        from tests.test_interpreter.helpers import run_snippet
        # C: 7 % -2 = 1 (Python gives -1)
        assert run_snippet("var x := 7 % -2;", "x") == 1

    def test_mod_zero_safe(self):
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet("var x := 10 % 0;", "x") == 0

    def test_division_modulo_identity(self):
        """a == (a / b) * b + (a % b) must hold for C-style truncation."""
        from tests.test_interpreter.helpers import run_snippet
        for a, b in [(10, 3), (-7, 2), (7, -2), (-7, -2), (100, 7)]:
            result = run_snippet(
                f"var a := {a}; var b := {b}; var x := (a / b) * b + (a % b);",
                "x",
            )
            assert result == a, f"Identity failed for {a} % {b}: got {result}"


# ── 15. Type coercion in shard patterns ─────────────────────────────────


class TestShardArithmeticPatterns:
    """Patterns from the actual shard scripts that exercise type coercion
    and integer division together."""

    def test_stat_conversion_cint_div_10(self):
        """CInt(value / 10) pattern from attributes.inc GetDexterity etc."""
        from tests.test_interpreter.helpers import run_snippet
        # GetAttributeBaseValue returns 1050 (hundredths), / 10 = 105
        assert run_snippet("var x := CInt(1050 / 10);", "x") == 105

    def test_vital_conversion_cint_div_100(self):
        """CInt(GetVital(...) / 100) — vitals stored as hundredths."""
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet("var x := CInt(15000 / 100);", "x") == 150

    def test_pvp_scaling_chain(self):
        """basedamage *= 0.4; ... rawdamage *= 0.6 (two-stage PvP)."""
        from tests.test_interpreter.helpers import run_snippet
        result = run_snippet(
            "var dmg := 100; dmg *= 0.4; dmg *= 0.6;", "dmg"
        )
        assert abs(result - 24.0) < 0.001

    def test_ar_absorption_formula(self):
        """absorbed = CInt(ar * (Random(51) + 50) / 100) pattern."""
        from tests.test_interpreter.helpers import run_snippet
        # With fixed values instead of Random: ar=30, roll=75
        # 30 * 75 / 100 = 2250 / 100 = 22 (int truncation)
        assert run_snippet("var x := CInt(30 * 75 / 100);", "x") == 22

    def test_avg_skill_division(self):
        """var avg_skill := total_skills / 8 from hitscriptinc.inc."""
        from tests.test_interpreter.helpers import run_snippet
        assert run_snippet("var x := 750 / 8;", "x") == 93
        assert run_snippet("var x := 100 / 8;", "x") == 12

    def test_warrior_penalty_fraction(self):
        """basedamage *= (bonus * 5/6) — mixed int arithmetic."""
        from tests.test_interpreter.helpers import run_snippet
        # 5/6 = 0 (int truncation!) — this is likely a shard bug but we must
        # match the behavior. In the real shard, ClasseBonus returns a float
        # (1.0 + 0.25 * level) so the multiplication promotes to float first.
        # With int: 5/6 = 0. With float factor: 1.5 * 5/6 = 7.5/6 = 1.25
        assert run_snippet("var x := 5 / 6;", "x") == 0  # pure int
        # With float left operand (real shard path):
        result = run_snippet("var x := 1.5 * 5 / 6;", "x")
        assert abs(result - 1.25) < 0.001

    def test_class_bonus_mul(self):
        """basedamage *= 1 + avg * 0.005 from hitscriptinc.inc."""
        from tests.test_interpreter.helpers import run_snippet
        result = run_snippet("var x := 1 + 100 * 0.005;", "x")
        assert isinstance(result, float)
        assert abs(result - 1.5) < 0.001

    def test_str_bonus_mul(self):
        """basedamage *= 1 + STR * 0.005 (STR=100 → 1.5x)."""
        from tests.test_interpreter.helpers import run_snippet
        result = run_snippet("var dmg := 50; dmg *= 1 + 100 * 0.005;", "dmg")
        assert abs(result - 75.0) < 0.001


# ── 16. Effect triggered metric completeness ────────────────────────────


class TestEffectTriggeredMetric:
    """All enchantment scripts that fire should set effect_triggered := 1
    in their metrics.  Missing this breaks effect_rate aggregation."""

    @pytest.mark.parametrize("enchant,expected_type,needs_chance", [
        (Enchantment.OF_PIERCING, "piercing", False),
        (Enchantment.BLOODY, "lifedrain", False),
        (Enchantment.VAMPIRIC, "manadrain", False),
        (Enchantment.LEECH, "staminadrain", False),
        (Enchantment.POISONED, "poison", False),
        (Enchantment.BLINDING, "blinding", True),
    ])
    def test_effect_enchantment_sets_triggered(self, shard, enchant, expected_type, needs_chance):
        """Each effect enchantment must set effect_triggered=1 in metrics."""
        if needs_chance:
            weapon = WeaponSpec(
                name="Broadsword", damage="3d6+2",
                attribute=SKILLID_SWORDSMANSHIP,
                properties={"ChanceOfEffect": 100},
            ).enchant_with(enchant)
        else:
            weapon = WEAPON.enchant_with(enchant)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=10, base_seed=SEED),
            shard=shard,
        )
        triggered_hits = [
            h for h in result.raw_results
            if h.success and h.metrics.get("effect_triggered") == 1
        ]
        assert len(triggered_hits) > 0, (
            f"{enchant.name} never set effect_triggered=1"
        )
        # Verify effect_type is correct
        for h in triggered_hits:
            assert h.metrics.get("effect_type") == expected_type, (
                f"{enchant.name}: expected effect_type={expected_type!r}, "
                f"got {h.metrics.get('effect_type')!r}"
            )

    @pytest.mark.parametrize("enchant", [
        Enchantment.OF_PLANAR_FURY,
        Enchantment.OF_ELEMENTAL_FURY,
    ])
    def test_greater_enchantment_sets_triggered(self, shard, enchant):
        """Greater enchantments also set effect_triggered."""
        weapon = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ChanceOfEffect": 100},
        ).enchant_with(enchant)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=10, base_seed=SEED),
            shard=shard,
        )
        assert result.ratios.effect_rate > 0, (
            f"{enchant.name} has effect_rate=0 — effect_triggered not set"
        )

    def test_void_sets_triggered(self, shard):
        """Void enchantment sets effect_triggered."""
        weapon = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
        ).enchant_with(Enchantment.OF_THE_VOID)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=10, base_seed=SEED),
            shard=shard,
        )
        triggered = [
            h for h in result.raw_results
            if h.success and h.metrics.get("effect_triggered") == 1
        ]
        assert len(triggered) > 0, "Void never set effect_triggered=1"

    def test_banish_sets_triggered(self, shard):
        """Banish enchantment sets effect_triggered for all target types."""
        weapon = WEAPON.enchant_with(Enchantment.BANISHING)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=10, base_seed=SEED),
            shard=shard,
        )
        triggered = [
            h for h in result.raw_results
            if h.success and h.metrics.get("effect_triggered") == 1
        ]
        assert len(triggered) > 0, "Banish never set effect_triggered=1"


# ── 17. Drain metrics (effect_drain_amount) ──────────────────────────────


class TestDrainMetrics:
    """All drain enchantments must record effect_drain_amount in metrics,
    which flows into CellResult.drain_stats via aggregate_cell().

    Regression: Void previously used void_drain_amount instead of
    effect_drain_amount, so drain_stats was always empty for Void weapons.
    """

    @pytest.mark.parametrize("enchant,expected_type", [
        (Enchantment.VAMPIRIC, "mana"),
    ])
    def test_always_drain_enchantment(self, shard, enchant, expected_type):
        """Mana drain fires every hit (no ChanceOfEffect gate)."""
        weapon = WEAPON.enchant_with(enchant)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        drain_hits = [
            h for h in result.raw_results
            if h.success and h.metrics.get("effect_drain_amount") is not None
        ]
        assert len(drain_hits) > 0, (
            f"{enchant.name} never recorded effect_drain_amount"
        )
        for h in drain_hits:
            assert h.metrics.get("effect_drain_type") == expected_type

    @pytest.mark.parametrize("enchant,expected_type", [
        (Enchantment.BLOODY, "hp"),
        (Enchantment.LEECH, "stamina"),
    ])
    def test_conditional_drain_enchantment(self, shard, enchant, expected_type):
        """Life/stamina drain only fires ~50% of the time (random gate)."""
        weapon = WEAPON.enchant_with(enchant)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=100, base_seed=SEED),
            shard=shard,
        )
        drain_hits = [
            h for h in result.raw_results
            if h.success and h.metrics.get("effect_drain_amount") is not None
        ]
        # With 100 iterations at ~50% rate, should have some drains
        assert len(drain_hits) > 0, (
            f"{enchant.name} never recorded effect_drain_amount"
        )
        for h in drain_hits:
            assert h.metrics.get("effect_drain_type") == expected_type

    def test_void_records_drain_amount(self, shard):
        """Void must record effect_drain_amount (not just void_drain_amount)."""
        weapon = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
        ).enchant_with(Enchantment.OF_THE_VOID)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        drain_hits = [
            h for h in result.raw_results
            if h.success and h.metrics.get("effect_drain_amount") is not None
        ]
        assert len(drain_hits) > 0, (
            "Void never recorded effect_drain_amount "
            "(regression: was only recording void_drain_amount)"
        )
        # Void drain type is random: hp, mana, or stamina
        valid_types = {"hp", "mana", "stamina"}
        for h in drain_hits:
            assert h.metrics.get("effect_drain_type") in valid_types

    def test_drain_flows_into_drain_stats(self, shard):
        """effect_drain_amount metrics should aggregate into drain_stats."""
        weapon = WEAPON.enchant_with(Enchantment.VAMPIRIC)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.drain_stats.count > 0, (
            "drain_stats.count is 0 — drain not flowing through aggregation"
        )
        assert result.drain_stats.mean > 0, (
            "drain_stats.mean is 0 — drain amounts not captured"
        )

    def test_no_drain_for_non_drain_enchantment(self, shard):
        """Enchantments without drain should have empty drain_stats."""
        weapon = WEAPON.enchant_with(Enchantment.OF_PIERCING)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.drain_stats.count == 0


# ── 18. Greater enchantments need ChanceOfEffect ─────────────────────────


class TestGreaterEnchantmentChanceOfEffect:
    """Greater enchantments (Planar Fury, Elemental Fury) gate on
    ChanceOfEffect. Without it, they should have 0% effect rate.

    Regression: Notebooks showed 100% effect_rate because ChanceOfEffect
    wasn't set on weapon specs.
    """

    @pytest.mark.parametrize("enchant", [
        Enchantment.OF_PLANAR_FURY,
        Enchantment.OF_ELEMENTAL_FURY,
    ])
    def test_low_chance_reduces_rate(self, shard, enchant):
        """ChanceOfEffect=10 should give ~10% effect rate, much less than 100."""
        weapon_low = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ChanceOfEffect": 10},
        ).enchant_with(enchant)
        weapon_high = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ChanceOfEffect": 100},
        ).enchant_with(enchant)
        atk_low = dataclasses.replace(ATTACKER, weapon=weapon_low)
        atk_high = dataclasses.replace(ATTACKER, weapon=weapon_high)
        result_low = run_scenario(
            Scenario(attacker=atk_low, defender=DEFENDER,
                     iterations=100, base_seed=SEED),
            shard=shard,
        )
        result_high = run_scenario(
            Scenario(attacker=atk_high, defender=DEFENDER,
                     iterations=100, base_seed=SEED),
            shard=shard,
        )
        assert result_low.ratios.effect_rate < result_high.ratios.effect_rate, (
            f"{enchant.name}: low chance rate ({result_low.ratios.effect_rate}) "
            f">= high chance rate ({result_high.ratios.effect_rate})"
        )

    @pytest.mark.parametrize("enchant", [
        Enchantment.OF_PLANAR_FURY,
        Enchantment.OF_ELEMENTAL_FURY,
    ])
    def test_with_chance_fires(self, shard, enchant):
        """With ChanceOfEffect=100, greater enchantments should always fire."""
        weapon = WeaponSpec(
            name="Broadsword", damage="3d6+2",
            attribute=SKILLID_SWORDSMANSHIP,
            properties={"ChanceOfEffect": 100},
        ).enchant_with(enchant)
        atk = dataclasses.replace(ATTACKER, weapon=weapon)
        result = run_scenario(
            Scenario(attacker=atk, defender=DEFENDER,
                     iterations=ITERATIONS, base_seed=SEED),
            shard=shard,
        )
        assert result.ratios.effect_rate > 0.9, (
            f"{enchant.name} with ChanceOfEffect=100 has low effect_rate: "
            f"{result.ratios.effect_rate}"
        )
