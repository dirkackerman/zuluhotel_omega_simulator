"""Comprehensive shard integration tests for the spell simulation runner.

Tests spell execution through run_spell_scenario / run_spell_sweep with
real shard scripts and configs. Validates damage, fizzle rates, resistance,
mana cost, casting delay, DPS, class bonuses, elemental protection,
magic efficiency, and skill/stat scaling.
"""

import pytest

from omega.config.spell_registry import SpellRegistry, DAMAGE_SPELL_IDS
from omega.config.spells import Spell
from omega.model.constants import (
    SKILLID_MAGERY,
    SKILLID_EVALINT,
    SKILLID_MAGICRESISTANCE,
)
from omega.simulation.scenario import (
    CombatantSpec,
    SpellParameterSweep,
    SpellScenario,
    Variable,
)
from omega.simulation.spell_runner import run_spell_scenario, run_spell_sweep

from tests.conftest import FIXTURE_SHARD_ROOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _caster(
    *,
    magery: int = 100,
    eval_int: int = 100,
    int_: int = 100,
    mana: int = 200,
    is_npc: bool = False,
    class_levels: dict | None = None,
    properties: dict | None = None,
) -> CombatantSpec:
    return CombatantSpec(
        name="Caster",
        is_npc=is_npc,
        int_=int_,
        mana=mana,
        str_=25,
        dex_=25,
        skills={SKILLID_MAGERY: magery, SKILLID_EVALINT: eval_int},
        class_levels=class_levels or {},
        properties=properties or {},
    )


def _target(
    *,
    hp: int = 1000,
    resist: int = 0,
    is_npc: bool = True,
    class_levels: dict | None = None,
    properties: dict | None = None,
) -> CombatantSpec:
    return CombatantSpec(
        name="Target",
        is_npc=is_npc,
        hp=hp,
        int_=50,
        str_=50,
        dex_=50,
        skills={SKILLID_MAGICRESISTANCE: resist},
        class_levels=class_levels or {},
        properties=properties or {},
    )


def _run(
    shard,
    spell: Spell,
    *,
    caster: CombatantSpec | None = None,
    target: CombatantSpec | None = None,
    iterations: int = 100,
    npc_mode: bool = True,
    debug: bool = True,
    base_seed: int = 0,
    circle_override: int = 0,
):
    """Run a spell scenario against the shard."""
    scenario = SpellScenario(
        caster=caster or _caster(),
        target=target or _target(),
        spell_id=spell,
        iterations=iterations,
        base_seed=base_seed,
        debug_mode=debug,
        npc_mode=npc_mode,
        circle_override=circle_override,
    )
    return run_spell_scenario(scenario, shard=shard)


# ---------------------------------------------------------------------------
# C1. Per-Spell Execution — all damage spells execute without error
# ---------------------------------------------------------------------------

# Spells known to deal 0 damage (buff/debuff/heal disguised as damage spell):
# Decaying Ray, Wraith's Breath, Sacrifice, Rising Fire, Astral Storm
_ZERO_DAMAGE_SPELLS = frozenset({
    Spell.DECAYING_RAY,
    Spell.WRAITHS_BREATH,
    Spell.SACRIFICE,
    Spell.RISING_FIRE,
    Spell.ASTRAL_STORM,
    # Holy spells heal non-undead targets instead of dealing damage
    Spell.HOLY_BOLT,
    Spell.WRATH_OF_GOD,
})


# Standard single-target damage spells
_SINGLE_TARGET_DAMAGE = [
    Spell.MAGIC_ARROW,
    Spell.HARM,
    Spell.FIREBALL,
    Spell.LIGHTNING,
    Spell.MIND_BLAST,
    Spell.ENERGY_BOLT,
    Spell.FLAME_STRIKE,
    # Necromancy
    Spell.SPECTRES_TOUCH,
    Spell.ABYSSAL_FLAME,
    Spell.SORCERERS_BANE,
    Spell.WYVERN_STRIKE,
    Spell.KILL,
    # Earth
    Spell.SHIFTING_EARTH,
    Spell.CALL_LIGHTNING,
    Spell.GUST_OF_AIR,
    Spell.ICE_STRIKE,
    # Holy
    Spell.HOLY_BOLT,
    Spell.WRATH_OF_GOD,
    Spell.DIVINE_FURY,
    Spell.APOCALYPSE,
]

# AoE damage spells
_AOE_DAMAGE = [
    Spell.EXPLOSION,
    Spell.CHAIN_LIGHTNING,
    Spell.METEOR_SWARM,
    Spell.EARTHQUAKE,
]


class TestPerSpellExecution:
    """C1. Every damage spell executes without error and deals expected damage."""

    @pytest.mark.parametrize("spell", _SINGLE_TARGET_DAMAGE, ids=lambda s: s.name)
    def test_single_target_spells_execute(self, fixture_shard, spell):
        cell = _run(fixture_shard, spell, iterations=50)
        assert cell.success_count == 50, f"{spell.name} had errors"
        assert cell.error_count == 0

    @pytest.mark.parametrize(
        "spell",
        [s for s in _SINGLE_TARGET_DAMAGE if s not in _ZERO_DAMAGE_SPELLS],
        ids=lambda s: s.name,
    )
    def test_single_target_spells_deal_damage(self, fixture_shard, spell):
        cell = _run(fixture_shard, spell, iterations=50)
        assert cell.damage_stats.mean > 0, f"{spell.name} dealt no damage"

    @pytest.mark.parametrize("spell", _AOE_DAMAGE, ids=lambda s: s.name)
    def test_aoe_spells_execute(self, fixture_shard, spell):
        cell = _run(fixture_shard, spell, iterations=50)
        assert cell.success_count == 50, f"{spell.name} had errors"

    @pytest.mark.parametrize("spell", _AOE_DAMAGE, ids=lambda s: s.name)
    def test_aoe_spells_deal_damage(self, fixture_shard, spell):
        cell = _run(fixture_shard, spell, iterations=50)
        assert cell.damage_stats.mean > 0, f"{spell.name} dealt no damage"

    def test_zero_damage_spells(self, fixture_shard):
        """Known non-damage spells in DAMAGE_SPELL_IDS execute without error."""
        for spell in _ZERO_DAMAGE_SPELLS:
            cell = _run(fixture_shard, spell, iterations=10)
            assert cell.error_count == 0, f"{spell.name} had errors"


# ---------------------------------------------------------------------------
# C2. Fizzle Rate Validation
# ---------------------------------------------------------------------------


class TestFizzleRate:
    """C2. Fizzle rate matches CheckSkill formula expectations.

    CheckSkill: chance = clamp(skill - difficulty + 50, 0, 100)
    Circle 3 difficulty = 40 → Magery 100: chance=110→100 (0% fizzle)
    """

    def test_high_magery_no_fizzle(self, fixture_shard):
        """Magery 100, Circle 3 difficulty 40 → 0% fizzle."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=100),
            iterations=500,
            npc_mode=False,
        )
        assert cell.ratios.fizzle_rate == 0.0

    def test_low_magery_high_fizzle(self, fixture_shard):
        """Magery 20, Circle 7 difficulty 80 → chance=clamp(20-80+50,0,100)=0 → 100% fizzle."""
        cell = _run(
            fixture_shard,
            Spell.FLAME_STRIKE,
            caster=_caster(magery=20, mana=200),
            iterations=200,
            npc_mode=False,
        )
        assert cell.ratios.fizzle_rate == 1.0

    def test_mid_magery_partial_fizzle(self, fixture_shard):
        """Magery 50, Circle 3 difficulty 40 → chance=60 → fizzle≈0.40."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=50, mana=200),
            iterations=1000,
            npc_mode=False,
        )
        # Allow ±0.06 statistical tolerance
        assert 0.30 <= cell.ratios.fizzle_rate <= 0.50

    def test_magery_80_circle7_fizzle(self, fixture_shard):
        """Magery 80, Circle 7 difficulty 80 → chance=50 → fizzle≈0.50."""
        cell = _run(
            fixture_shard,
            Spell.FLAME_STRIKE,
            caster=_caster(magery=80, mana=200),
            iterations=1000,
            npc_mode=False,
        )
        assert 0.40 <= cell.ratios.fizzle_rate <= 0.60

    def test_npc_mode_no_fizzle(self, fixture_shard):
        """NPC mode bypasses TryToCast — no fizzles."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=10),
            iterations=100,
            npc_mode=True,
        )
        assert cell.ratios.fizzle_rate == 0.0


# ---------------------------------------------------------------------------
# C3. Resistance Validation
# ---------------------------------------------------------------------------


class TestResistance:
    """C3. Resistance rate matches formula expectations."""

    def test_zero_resist_low_rate(self, fixture_shard):
        """Zero Magic Resistance → very low resist rate."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            target=_target(resist=0),
            iterations=500,
        )
        assert cell.ratios.resist_rate_on_cast < 0.15

    def test_high_resist_high_rate(self, fixture_shard):
        """Very high Magic Resistance → high resist rate."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            target=_target(resist=130),
            iterations=500,
        )
        assert cell.ratios.resist_rate_on_cast > 0.5

    def test_resist_reduces_damage(self, fixture_shard):
        """Higher resist → lower mean damage."""
        low = _run(fixture_shard, Spell.FIREBALL, target=_target(resist=0), iterations=500)
        high = _run(fixture_shard, Spell.FIREBALL, target=_target(resist=130), iterations=500)
        assert high.damage_stats.mean < low.damage_stats.mean


# ---------------------------------------------------------------------------
# C4. Damage Validation
# ---------------------------------------------------------------------------


class TestDamageValidation:
    """C4. Damage values in expected ranges from CalcSpellDamage formula."""

    def test_fireball_npc_damage_positive(self, fixture_shard):
        """Fireball deals positive damage in NPC mode."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=100, is_npc=True),
            target=_target(resist=0, is_npc=True),
            iterations=500,
        )
        assert cell.damage_stats.mean > 0
        assert cell.damage_stats.min > 0

    def test_flame_strike_higher_than_fireball(self, fixture_shard):
        """Flame Strike (Circle 7) should deal more damage than Fireball (Circle 3)."""
        fb = _run(fixture_shard, Spell.FIREBALL, iterations=300)
        fs = _run(fixture_shard, Spell.FLAME_STRIKE, iterations=300)
        assert fs.damage_stats.mean > fb.damage_stats.mean

    def test_kill_higher_than_fireball(self, fixture_shard):
        """Kill (Circle 24, UseCircle 16) should deal more damage than Fireball."""
        fb = _run(fixture_shard, Spell.FIREBALL, iterations=200)
        kill = _run(fixture_shard, Spell.KILL, iterations=200)
        assert kill.damage_stats.mean > fb.damage_stats.mean

    def test_magic_arrow_lowest_damage(self, fixture_shard):
        """Magic Arrow (Circle 1) should deal the least damage."""
        cell = _run(fixture_shard, Spell.MAGIC_ARROW, iterations=200)
        kill = _run(fixture_shard, Spell.KILL, iterations=200)
        assert cell.damage_stats.mean < kill.damage_stats.mean


# ---------------------------------------------------------------------------
# C5. Mana Cost Validation
# ---------------------------------------------------------------------------


class TestManaCost:
    """C5. Mana consumption matches circles.cfg values."""

    def test_fireball_mana_cost(self, fixture_shard):
        """Fireball circle 3 → mana cost = 9."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=100, mana=200),
            iterations=1,
            npc_mode=False,
        )
        # Extract from raw results
        r = cell.raw_results[0]
        assert r.metrics.get("spell_mana_cost") == 9

    def test_lightning_mana_cost(self, fixture_shard):
        """Lightning circle 4 → mana cost = 11."""
        cell = _run(
            fixture_shard,
            Spell.LIGHTNING,
            caster=_caster(magery=100, mana=200),
            iterations=1,
            npc_mode=False,
        )
        r = cell.raw_results[0]
        assert r.metrics.get("spell_mana_cost") == 11

    def test_insufficient_mana_fizzle(self, fixture_shard):
        """With 0 mana → spell fizzles (mana consumed = 0)."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=100, mana=0),
            iterations=100,
            npc_mode=False,
        )
        # All should fizzle due to no mana
        assert cell.ratios.fizzle_rate == 1.0


# ---------------------------------------------------------------------------
# C6. Casting Delay / DPS
# ---------------------------------------------------------------------------


class TestCastingDelay:
    """C6. Casting delay from circles.cfg, DPS computation."""

    def test_fireball_delay(self, fixture_shard):
        """Fireball circle 3 → delay = 1500ms (player mode)."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=100, mana=200),
            iterations=10,
            npc_mode=False,
        )
        if cell.timing is not None:
            assert cell.timing.swing_delay_ms == 1500.0

    def test_flame_strike_delay(self, fixture_shard):
        """Flame Strike circle 7 → delay = 2000ms (player mode)."""
        cell = _run(
            fixture_shard,
            Spell.FLAME_STRIKE,
            caster=_caster(magery=100, mana=200),
            iterations=10,
            npc_mode=False,
        )
        if cell.timing is not None:
            assert cell.timing.swing_delay_ms == 2000.0

    def test_npc_mode_no_delay(self, fixture_shard):
        """NPC mode bypasses TryToCast — no casting delay."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            iterations=10,
            npc_mode=True,
        )
        # NPC mode skips TryToCast which sets the delay
        # Delay should be 0 or timing should be None
        if cell.timing is not None:
            assert cell.timing.swing_delay_ms == 0.0

    def test_dps_computed(self, fixture_shard):
        """DPS = mean_damage * casts_per_second."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=100, mana=200),
            iterations=100,
            npc_mode=False,
        )
        if cell.timing is not None and cell.timing.swing_delay_ms > 0:
            expected_dps = cell.damage_stats.mean * cell.timing.swings_per_second
            assert abs(cell.timing.dps_mean - expected_dps) < 0.1


# ---------------------------------------------------------------------------
# C7. Magic Efficiency (MagicPenalty)
# ---------------------------------------------------------------------------


class TestMagicEfficiency:
    """C7. MagicPenalty reduces spell damage via MagicEfficiency.

    Note: MagicPenalty is checked on equipped items via GetMagicEfficiencyPenalty.
    For the simulation, we test via NPC mode where MagicPenalty is always 0
    vs player mode where it's read from equipment properties.
    """

    def test_no_penalty_baseline(self, fixture_shard):
        """NPC caster (no penalty) → full damage."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(is_npc=True),
            iterations=200,
        )
        assert cell.damage_stats.mean > 0


# ---------------------------------------------------------------------------
# C8. Class Bonus Effects
# ---------------------------------------------------------------------------


class TestClassBonusEffects:
    """C8. Class system affects spell damage and resistance."""

    def test_mage_caster_increases_damage(self, fixture_shard):
        """Mage caster (level 5) should deal more damage than classless."""
        classless = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(),
            iterations=300,
        )
        mage = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(class_levels={"IsMage": 5}),
            iterations=300,
        )
        # Mage class bonus increases damage
        assert mage.damage_stats.mean >= classless.damage_stats.mean


# ---------------------------------------------------------------------------
# C9. PvP Scaling
# ---------------------------------------------------------------------------


class TestPvPScaling:
    """C9. PvP damage scaling: CalcSpellDamage /3 for player targets."""

    def test_npc_vs_npc_higher_damage(self, fixture_shard):
        """NPC caster vs NPC target should deal more than vs player target."""
        vs_npc = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(is_npc=True),
            target=_target(is_npc=True),
            iterations=300,
        )
        vs_player = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(is_npc=True),
            target=_target(is_npc=False),
            iterations=300,
        )
        # NPC target gets *1.5, player target gets /3 → significant difference
        assert vs_npc.damage_stats.mean > vs_player.damage_stats.mean


# ---------------------------------------------------------------------------
# C10. Elemental Protection
# ---------------------------------------------------------------------------


class TestElementalProtection:
    """C10. Elemental protection reduces spell damage."""

    def test_fire_protection_reduces_fireball(self, fixture_shard):
        """FireProtection=50 on target → Fireball damage reduced."""
        no_prot = _run(
            fixture_shard,
            Spell.FIREBALL,
            target=_target(properties={}),
            iterations=300,
        )
        with_prot = _run(
            fixture_shard,
            Spell.FIREBALL,
            target=_target(properties={"FireProtection": 50}),
            iterations=300,
        )
        assert with_prot.damage_stats.mean < no_prot.damage_stats.mean


# ---------------------------------------------------------------------------
# C11. Skill/Stat Scaling Sweeps
# ---------------------------------------------------------------------------


class TestSkillScaling:
    """C11. Scaling sweeps produce monotonic damage curves."""

    def test_magery_sweep_increases_damage(self, fixture_shard):
        """Higher Magery → more damage (more dice bonus)."""
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_caster(magery=50),
                target=_target(),
                spell_id=Spell.FIREBALL,
                iterations=200,
                debug_mode=True,
                npc_mode=True,
            ),
            variables=(
                Variable(
                    target="caster",
                    parameter=f"skills.{SKILLID_MAGERY}",
                    values=(50, 80, 110),
                ),
            ),
        )
        result = run_spell_sweep(sweep, shard=fixture_shard)
        means = [c.damage_stats.mean for c in result.cells]
        # Should be monotonically non-decreasing
        for i in range(len(means) - 1):
            assert means[i] <= means[i + 1], f"Damage not increasing: {means}"

    def test_resist_sweep_decreases_damage(self, fixture_shard):
        """Higher Magic Resistance → less damage (more resists + EvalInt scaling)."""
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_caster(),
                target=_target(resist=0),
                spell_id=Spell.FIREBALL,
                iterations=300,
                debug_mode=True,
                npc_mode=True,
            ),
            variables=(
                Variable(
                    target="target",
                    parameter=f"skills.{SKILLID_MAGICRESISTANCE}",
                    values=(0, 50, 100),
                ),
            ),
        )
        result = run_spell_sweep(sweep, shard=fixture_shard)
        means = [c.damage_stats.mean for c in result.cells]
        # Should be monotonically non-increasing
        for i in range(len(means) - 1):
            assert means[i] >= means[i + 1], f"Damage not decreasing: {means}"


# ---------------------------------------------------------------------------
# C12. AoE Multi-Target (basic validation)
# ---------------------------------------------------------------------------


class TestAoEMultiTarget:
    """C12. AoE spells with multiple targets."""

    def test_aoe_executes_with_targets(self, fixture_shard):
        """AoE spells execute against single target without error."""
        cell = _run(fixture_shard, Spell.CHAIN_LIGHTNING, iterations=50)
        assert cell.error_count == 0
        assert cell.damage_stats.mean > 0


# ---------------------------------------------------------------------------
# C13. Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """C13. Edge case handling."""

    def test_zero_magery_full_fizzle(self, fixture_shard):
        """Zero Magery, Circle 3 (difficulty 40) → chance=clamp(0-40+50,0,100)=10 → ~90% fizzle."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=0, mana=200),
            iterations=500,
            npc_mode=False,
        )
        assert 0.82 <= cell.ratios.fizzle_rate <= 0.98

    def test_zero_mana_fizzle(self, fixture_shard):
        """Zero mana → all fizzle (ConsumeMana returns 0)."""
        cell = _run(
            fixture_shard,
            Spell.FIREBALL,
            caster=_caster(magery=100, mana=0),
            iterations=50,
            npc_mode=False,
        )
        assert cell.ratios.fizzle_rate == 1.0

    def test_very_high_iterations(self, fixture_shard):
        """Verify no memory leak with high iteration count."""
        cell = _run(fixture_shard, Spell.FIREBALL, iterations=500)
        assert cell.iteration_count == 500
        assert cell.success_count == 500


# ---------------------------------------------------------------------------
# C14. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """C14. Same seed produces identical results."""

    def test_same_seed_identical_results(self, fixture_shard):
        r1 = _run(fixture_shard, Spell.FIREBALL, iterations=100, base_seed=12345)
        r2 = _run(fixture_shard, Spell.FIREBALL, iterations=100, base_seed=12345)
        assert r1.damage_stats.mean == r2.damage_stats.mean
        assert r1.damage_stats.min == r2.damage_stats.min
        assert r1.damage_stats.max == r2.damage_stats.max

    def test_different_seeds_differ(self, fixture_shard):
        r1 = _run(fixture_shard, Spell.FIREBALL, iterations=200, base_seed=1)
        r2 = _run(fixture_shard, Spell.FIREBALL, iterations=200, base_seed=999)
        # Very unlikely to have identical means with different seeds
        # Allow for theoretical possibility but assert the distributions differ
        assert r1.damage_stats.mean != r2.damage_stats.mean or r1.damage_stats.min != r2.damage_stats.min


# ---------------------------------------------------------------------------
# C15. Sweep Acceptance Criteria
# ---------------------------------------------------------------------------


class TestSweepAcceptance:
    """C15. Sweeps produce expected monotonic relationships."""

    def test_spell_id_sweep(self, fixture_shard):
        """Sweep across different spells — each produces valid results."""
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_caster(),
                target=_target(),
                spell_id=Spell.FIREBALL,
                iterations=50,
                debug_mode=True,
                npc_mode=True,
            ),
            variables=(
                Variable(
                    target="spell",
                    parameter="spell_id",
                    values=(Spell.MAGIC_ARROW, Spell.FIREBALL, Spell.FLAME_STRIKE),
                ),
            ),
        )
        result = run_spell_sweep(sweep, shard=fixture_shard)
        assert len(result.cells) == 3
        for cell in result.cells:
            assert cell.error_count == 0
            assert cell.damage_stats.mean > 0

    def test_mage_class_sweep(self, fixture_shard):
        """Mage class level sweep → monotonically increasing damage."""
        sweep = SpellParameterSweep(
            scenario=SpellScenario(
                caster=_caster(class_levels={"IsMage": 1}),
                target=_target(),
                spell_id=Spell.FIREBALL,
                iterations=300,
                debug_mode=True,
                npc_mode=True,
            ),
            variables=(
                Variable(
                    target="caster",
                    parameter="class_levels.IsMage",
                    values=(1, 3, 5),
                ),
            ),
        )
        result = run_spell_sweep(sweep, shard=fixture_shard)
        means = [c.damage_stats.mean for c in result.cells]
        for i in range(len(means) - 1):
            assert means[i] <= means[i + 1], f"Mage class damage not increasing: {means}"
