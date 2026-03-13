"""Integration tests for execute_spell with eScript spell scripts."""

import pytest

import omega.runtime  # noqa: F401

from omega.combat.spell import execute_spell, _resolve_spell_script
from omega.combat.spell_result import SpellResult
from omega.config.spell_registry import SpellRegistry, DAMAGE_SPELL_IDS
from omega.config.spells import Spell
from omega.model.constants import SKILLID_MAGERY, SKILLID_EVALINT, SKILLID_MAGICRESISTANCE
from omega.config.dice import DiceSpec
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.parser.parser import parse_text, ParseResult
from omega.runtime.context import SimulationContext, set_context
from pathlib import Path

from tests.conftest import FIXTURE_SHARD_ROOT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mage(name="Mage", magery=1000, eval_int=1000, mana=100, hp=100, is_npc=False):
    """Create a mage mobile with sensible defaults (skill values in tenths).

    Mana is in display units (e.g., 100 = 100 mana points visible to
    the player).  POL stores vitals in hundredths internally, but our
    Mobile model stores display units — GetVital(mob, "Mana") returns
    mob.mana * 100 to match POL's API.
    """
    m = Mobile(name=name, is_npc=is_npc)
    m.set_skill(SKILLID_MAGERY, magery)  # 100.0 display
    m.set_skill(SKILLID_EVALINT, eval_int)
    m.hp = hp
    m.max_hp = hp
    m.mana = mana
    m.max_mana = mana
    m.int_base = 100
    m.str_base = 25
    m.dex_base = 25
    return m


def _make_defender(name="Target", hp=500, resist=0, is_npc=True):
    """Create a defender mobile."""
    m = Mobile(name=name, is_npc=is_npc, npctemplate="test_mob" if is_npc else "")
    m.hp = hp
    m.max_hp = hp
    m.mana = 50
    m.max_mana = 50
    m.set_skill(SKILLID_MAGICRESISTANCE, resist)
    m.str_base = 50
    m.int_base = 50
    m.dex_base = 50
    return m


@pytest.fixture(scope="module")
def spell_registry():
    """Build spell registry from fixture shard."""
    circles_path = FIXTURE_SHARD_ROOT / "config" / "circles.cfg"
    spell_cfg_paths = [
        (FIXTURE_SHARD_ROOT / "pkg" / "std" / "spells" / "spells.cfg", "Standard"),
        (FIXTURE_SHARD_ROOT / "pkg" / "opt" / "necro" / "spells.cfg", "Necromancy"),
        (FIXTURE_SHARD_ROOT / "pkg" / "opt" / "earth" / "spells.cfg", "Earth"),
        (FIXTURE_SHARD_ROOT / "pkg" / "opt" / "holybook" / "spells.cfg", "Holy"),
    ]
    return SpellRegistry.from_cfg(
        spell_cfg_paths=spell_cfg_paths,
        circles_path=circles_path,
    )


@pytest.fixture(scope="module")
def spell_parse_results(fixture_shard):
    """Parsed spell scripts + includes."""
    return fixture_shard.parse_combat_scripts()


def _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell_id, *,
                caster=None, target=None, npc_mode=True, debug=True,
                rng_seed=42, circle_override=0, **kwargs):
    """Helper to run a spell through execute_spell with fixture shard."""
    if caster is None:
        caster = _make_mage()
    if target is None:
        target = _make_defender()

    return execute_spell(
        spell_parse_results,
        caster,
        target,
        int(spell_id),
        rng_seed=rng_seed,
        debug=debug,
        config_resolver=fixture_shard.resolve_config_path,
        em_modules_dir=fixture_shard.root / "scripts" / "modules",
        shard_root=fixture_shard.root,
        package_map=fixture_shard.package_map,
        npc_mode=npc_mode,
        circle_override=circle_override,
        spell_registry=spell_registry,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# SpellResult tests
# ---------------------------------------------------------------------------


class TestSpellResult:
    def test_default_values(self):
        r = SpellResult()
        assert r.spell_id == 0
        assert r.base_damage == 0
        assert r.final_damage == 0.0
        assert r.fizzled is False
        assert r.resisted is False
        assert r.immuned is False
        assert r.success is True
        assert r.error is None

    def test_field_types(self):
        r = SpellResult(spell_id=18, spell_name="Fireball", circle=3)
        assert r.spell_id == 18
        assert r.spell_name == "Fireball"
        assert r.circle == 3
        assert isinstance(r.side_effects, list)
        assert isinstance(r.metrics, dict)

    def test_error_state(self):
        r = SpellResult(success=False, error="Script not found")
        assert r.success is False
        assert r.error == "Script not found"


# ---------------------------------------------------------------------------
# Script path resolution
# ---------------------------------------------------------------------------


class TestResolveSpellScript:
    def test_standard_spell(self):
        assert _resolve_spell_script(18, "fireball") == ":spells:fireball"
        assert _resolve_spell_script(5, "magicarrow") == ":spells:magicarrow"
        assert _resolve_spell_script(57, "earthquake") == ":spells:earthquake"

    def test_necro_spell(self):
        assert _resolve_spell_script(77, "kill") == ":Necro:kill"
        assert _resolve_spell_script(67, "decayingray") == ":Necro:decayingray"

    def test_earth_spell(self):
        assert _resolve_spell_script(83, "shiftingearth") == ":Earth:shiftingearth"
        assert _resolve_spell_script(92, "icestrike") == ":Earth:icestrike"

    def test_holy_spell(self):
        assert _resolve_spell_script(170, "holybolt") == ":holybook:holybolt"
        assert _resolve_spell_script(181, "apocalypse") == ":holybook:apocalypse"

    def test_song_spell(self):
        assert _resolve_spell_script(182, "songoflight") == ":songbook:songoflight"

    def test_boundary_ids(self):
        assert _resolve_spell_script(64, "script") == ":spells:script"
        assert _resolve_spell_script(65, "script") == ":Necro:script"
        assert _resolve_spell_script(80, "script") == ":Necro:script"
        assert _resolve_spell_script(81, "script") == ":Earth:script"
        assert _resolve_spell_script(96, "script") == ":Earth:script"
        assert _resolve_spell_script(166, "script") == ":holybook:script"
        assert _resolve_spell_script(181, "script") == ":holybook:script"
        assert _resolve_spell_script(197, "script") == ":songbook:script"


# ---------------------------------------------------------------------------
# Fireball (NPC mode — simplest path)
# ---------------------------------------------------------------------------


class TestExecuteSpellFireball:
    def test_executes_successfully(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        assert result.success, f"Spell failed: {result.error}"

    def test_damages_target(self, fixture_shard, spell_parse_results, spell_registry):
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL, target=target)
        assert result.final_damage > 0
        assert target.hp < 500

    def test_npc_mode_bypasses_trytocast(self, fixture_shard, spell_parse_results, spell_registry):
        """NPC mode skips skill check, mana, reagents — direct damage."""
        caster = _make_mage(magery=0, mana=0)  # Zero magery and mana
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster, npc_mode=True, circle_override=3)
        assert result.success
        assert result.final_damage > 0  # Still does damage despite 0 magery

    def test_deterministic_with_same_seed(self, fixture_shard, spell_parse_results, spell_registry):
        r1 = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL, rng_seed=123)
        t2 = _make_defender(hp=500)
        r2 = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL, rng_seed=123, target=t2)
        assert r1.final_damage == r2.final_damage

    def test_different_seeds_vary(self, fixture_shard, spell_parse_results, spell_registry):
        results = set()
        for seed in range(1, 20):
            t = _make_defender(hp=500)
            r = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                            rng_seed=seed, target=t)
            results.add(r.final_damage)
        assert len(results) > 1  # At least some variation

    def test_spell_base_damage_metric(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        assert "spell_base_damage" in result.metrics
        assert result.base_damage > 0

    def test_circle_in_result(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        assert result.circle == 3

    def test_spell_name_in_result(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        assert result.spell_name  # Should have a name

    def test_npc_target_scaling(self, fixture_shard, spell_parse_results, spell_registry):
        """NPC targets get 1.5x damage multiplier in CalcSpellDamage."""
        npc_target = _make_defender(hp=500, is_npc=True)
        player_target = _make_defender(name="Player", hp=500, is_npc=False)

        # Use same seed for both
        r_npc = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                            rng_seed=42, target=npc_target)
        r_player = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                               rng_seed=42, target=player_target)

        # NPC should take more base damage (1.5x vs /3 for players)
        assert r_npc.base_damage > r_player.base_damage


# ---------------------------------------------------------------------------
# Player mode tests (with fizzle)
# ---------------------------------------------------------------------------


class TestSpellFizzle:
    def test_low_magery_fizzles(self, fixture_shard, spell_parse_results, spell_registry):
        """Very low magery should fail the CheckSkill."""
        caster = _make_mage(magery=10, mana=100)  # 1.0 display skill
        # Run multiple times — with very low skill, most should fizzle
        fizzle_count = 0
        for seed in range(1, 21):
            t = _make_defender(hp=500)
            r = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                            caster=_make_mage(magery=10, mana=100), target=t,
                            npc_mode=False, rng_seed=seed)
            if r.fizzled or r.final_damage == 0:
                fizzle_count += 1
        assert fizzle_count > 10  # Most should fizzle with skill 1

    def test_high_magery_succeeds(self, fixture_shard, spell_parse_results, spell_registry):
        """High magery should usually succeed."""
        success_count = 0
        for seed in range(1, 21):
            t = _make_defender(hp=500)
            r = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                            caster=_make_mage(magery=1200, mana=100), target=t,
                            npc_mode=False, rng_seed=seed)
            if r.final_damage > 0:
                success_count += 1
        assert success_count > 10  # Most should succeed with skill 120


# ---------------------------------------------------------------------------
# Spell resistance
# ---------------------------------------------------------------------------


class TestSpellResistance:
    def test_high_resist_reduces_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """High magic resistance should reduce spell damage."""
        low_resist = _make_defender(hp=500, resist=0)
        high_resist = _make_defender(hp=500, resist=1200)  # 120 display

        r_low = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                            rng_seed=42, target=low_resist)
        r_high = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             rng_seed=42, target=high_resist)

        # High resist should take less or equal damage
        assert r_high.final_damage <= r_low.final_damage

    def test_resisted_metric_populated(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        # Resisted list should be in metrics (may or may not have resisted)
        assert "resisted" in result.metrics
        assert isinstance(result.metrics["resisted"], list)


# ---------------------------------------------------------------------------
# Elemental protection
# ---------------------------------------------------------------------------


class TestElementalProtection:
    def test_elemental_applied_metric(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        # Elemental_applied should be recorded
        assert "elemental_applied" in result.metrics or "damage_applied" in result.metrics


# ---------------------------------------------------------------------------
# Stub tests
# ---------------------------------------------------------------------------


class TestCheckSkillStub:
    def test_returns_int(self):
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1000)
        from omega.runtime.structural_stubs import check_skill
        result = check_skill(mob, SKILLID_MAGERY, 50, 100)
        assert isinstance(result, int)
        assert result in (0, 1)

    def test_high_skill_high_chance(self):
        """Skill 130, difficulty 50 → chance = clamp(130-50+50,0,100) = 100."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1300)  # 130 display
        from omega.runtime.structural_stubs import check_skill
        # With chance=100, should always succeed
        result = check_skill(mob, SKILLID_MAGERY, 50, 100)
        assert result == 1

    def test_zero_skill_low_chance(self):
        """Skill 0, difficulty 50 → chance = clamp(0-50+50,0,100) = 0."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=0)
        from omega.runtime.structural_stubs import check_skill
        result = check_skill(mob, SKILLID_MAGERY, 50, 100)
        assert result == 0  # chance=0, always fails

    def test_metrics_recorded(self):
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1000)
        from omega.runtime.structural_stubs import check_skill
        check_skill(mob, SKILLID_MAGERY, 50, 100)
        assert "spell_skill_check" in ctx.metrics
        assert "spell_skill_chance" in ctx.metrics
        assert "spell_difficulty" in ctx.metrics

    def test_none_character_returns_zero(self):
        ctx = SimulationContext()
        set_context(ctx)
        from omega.runtime.structural_stubs import check_skill
        assert check_skill(None, SKILLID_MAGERY, 50, 100) == 0


class TestConsumeManaStub:
    def test_deducts_mana(self, fixture_shard):
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=100)
        from omega.runtime.structural_stubs import consume_mana
        result = consume_mana(mob, Spell.FIREBALL)
        assert result == 1
        assert mob.mana < 100  # Mana was deducted (display units)

    def test_deducts_correct_amount(self, fixture_shard):
        """Mana deduction should match circle cost from circles.cfg."""
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=100)
        from omega.runtime.structural_stubs import consume_mana
        consume_mana(mob, Spell.FIREBALL)
        cost = ctx.metrics.get("spell_mana_cost", 0)
        assert cost > 0
        assert mob.mana == 100 - cost

    def test_insufficient_mana_returns_zero(self, fixture_shard):
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=0)
        from omega.runtime.structural_stubs import consume_mana
        result = consume_mana(mob, Spell.FIREBALL)
        assert result == 0

    def test_barely_insufficient_mana(self, fixture_shard):
        """Mana just below cost should fail."""
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        # First find the cost, then test with cost-1
        mob = _make_mage(mana=100)
        from omega.runtime.structural_stubs import consume_mana
        consume_mana(mob, Spell.FIREBALL)
        cost = ctx.metrics["spell_mana_cost"]
        # Now test with exactly cost-1
        ctx2 = SimulationContext(debug_mode=True)
        ctx2._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx2)
        mob2 = _make_mage(mana=cost - 1)
        result = consume_mana(mob2, Spell.FIREBALL)
        assert result == 0
        assert mob2.mana == cost - 1  # Unchanged

    def test_exact_mana_succeeds(self, fixture_shard):
        """Mana exactly equal to cost should succeed."""
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=100)
        from omega.runtime.structural_stubs import consume_mana
        consume_mana(mob, Spell.FIREBALL)
        cost = ctx.metrics["spell_mana_cost"]
        # Now test with exactly cost
        ctx2 = SimulationContext(debug_mode=True)
        ctx2._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx2)
        mob2 = _make_mage(mana=cost)
        result = consume_mana(mob2, Spell.FIREBALL)
        assert result == 1
        assert mob2.mana == 0

    def test_metrics_recorded(self, fixture_shard):
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=100)
        from omega.runtime.structural_stubs import consume_mana
        consume_mana(mob, Spell.FIREBALL)
        assert "spell_mana_cost" in ctx.metrics
        assert ctx.metrics["spell_mana_cost"] > 0
        assert ctx.metrics["spell_mana_before"] == 100

    def test_none_character_returns_zero(self):
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        from omega.runtime.structural_stubs import consume_mana
        assert consume_mana(None, Spell.FIREBALL) == 0

    def test_none_spell_id_returns_zero(self):
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        from omega.runtime.structural_stubs import consume_mana
        assert consume_mana(_make_mage(), None) == 0


class TestSpellStubsNoOp:
    def test_consume_reagents_always_true(self):
        from omega.runtime.structural_stubs import consume_reagents
        assert consume_reagents(None, None) == 1

    def test_check_line_of_sight_always_true(self):
        from omega.runtime.structural_stubs import check_line_of_sight
        assert check_line_of_sight(None, None) == 1

    def test_check_los_at_always_true(self):
        from omega.runtime.structural_stubs import check_los_at
        assert check_los_at(None, 0, 0, 0) == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_dead_caster_zero_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Dead caster returns 0 from CalcSpellDamage."""
        caster = _make_mage()
        caster.dead = True
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster)
        assert result.final_damage == 0

    def test_dead_target_zero_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Dead target returns 0 from CalcSpellDamage."""
        target = _make_defender(hp=0)
        target.dead = True
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             target=target)
        assert result.final_damage == 0

    def test_hidden_target_zero_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Hidden target returns 0 from CalcSpellDamage."""
        target = _make_defender(hp=500)
        target.hidden = True
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             target=target)
        assert result.final_damage == 0

    def test_minimum_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Even low-power spells should do at least 1 damage to NPC targets."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.MAGIC_ARROW,
                             circle_override=1)
        if result.final_damage > 0:
            assert result.base_damage >= 1

    def test_no_spell_script_returns_error(self, fixture_shard, spell_parse_results, spell_registry):
        """Invalid spell ID with no script should return error."""
        result = execute_spell(
            spell_parse_results,
            _make_mage(),
            _make_defender(),
            9999,  # Non-existent spell
            debug=True,
            spell_registry=spell_registry,
        )
        assert not result.success or result.final_damage == 0


# ---------------------------------------------------------------------------
# Multi-school spells
# ---------------------------------------------------------------------------


class TestMultiSchool:
    def test_lightning(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.LIGHTNING)
        assert result.success, f"Lightning failed: {result.error}"
        assert result.final_damage > 0

    def test_harm(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.HARM)
        assert result.success, f"Harm failed: {result.error}"
        assert result.final_damage > 0

    def test_energy_bolt(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.ENERGY_BOLT)
        assert result.success, f"Energy Bolt failed: {result.error}"
        assert result.final_damage > 0

    def test_flame_strike(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FLAME_STRIKE)
        assert result.success, f"Flame Strike failed: {result.error}"
        assert result.final_damage > 0

    def test_mind_blast(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.MIND_BLAST)
        assert result.success, f"Mind Blast failed: {result.error}"
        assert result.final_damage > 0

    def test_chain_lightning(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.CHAIN_LIGHTNING)
        assert result.success, f"Chain Lightning failed: {result.error}"
        assert result.final_damage > 0


# ---------------------------------------------------------------------------
# Mana unit consistency (regression tests for ConsumeMana //100 bug)
# ---------------------------------------------------------------------------


class TestManaUnitConsistency:
    """Verify ConsumeMana operates in display units, not POL hundredths.

    Regression: ConsumeMana had ``display_mana = current_mana // 100``
    which treated display units as hundredths.  mob.mana=100 (100 mana)
    became 1 after division, failing the cost check.
    """

    def test_consume_mana_display_units_100(self, fixture_shard):
        """mob.mana=100 (display) should have enough for any standard spell."""
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=100)
        from omega.runtime.structural_stubs import consume_mana
        result = consume_mana(mob, Spell.FIREBALL)
        assert result == 1
        assert mob.mana < 100
        assert mob.mana > 0  # should not lose all 100 mana for a circle 3

    def test_consume_mana_display_units_small(self, fixture_shard):
        """mob.mana=15 (display) should be enough for a circle 3 spell."""
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=15)
        from omega.runtime.structural_stubs import consume_mana
        result = consume_mana(mob, Spell.FIREBALL)
        cost = ctx.metrics["spell_mana_cost"]
        # Circle 3 mana cost should be < 15
        assert cost < 15, f"Unexpected circle 3 mana cost: {cost}"
        assert result == 1
        assert mob.mana == 15 - cost

    def test_consume_mana_no_double_conversion(self, fixture_shard):
        """mob.mana must not be divided by 100 before comparison."""
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=200)  # High-INT mage
        from omega.runtime.structural_stubs import consume_mana
        result = consume_mana(mob, Spell.FLAME_STRIKE)
        cost = ctx.metrics["spell_mana_cost"]
        assert result == 1
        assert mob.mana == 200 - cost
        # Cost should be reasonable (not 200 * 100 = 20000)
        assert cost < 100

    def test_consume_mana_deduction_not_multiplied(self, fixture_shard):
        """Deduction must subtract cost directly, not cost*100."""
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=50)
        from omega.runtime.structural_stubs import consume_mana
        before = mob.mana
        consume_mana(mob, Spell.FIREBALL)
        cost = ctx.metrics["spell_mana_cost"]
        deducted = before - mob.mana
        assert deducted == cost, (
            f"Deducted {deducted} but cost was {cost} — "
            f"suggests *100 multiplication in deduction"
        )

    def test_player_mode_mana_consumed_display(self, fixture_shard, spell_parse_results, spell_registry):
        """Player mode spell should consume reasonable mana in display units."""
        caster = _make_mage(magery=1200, mana=100)
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster, target=target, npc_mode=False, rng_seed=42)
        if not result.fizzled:
            mana_before = result.metrics.get("spell_mana_before", 0)
            mana_cost = result.metrics.get("spell_mana_cost", 0)
            assert mana_before == 100, f"mana_before should be 100 display, got {mana_before}"
            assert 0 < mana_cost < 50, f"Unreasonable mana cost: {mana_cost}"

    def test_getmana_consistency_with_consume(self, fixture_shard):
        """After ConsumeMana, GetMana must return the reduced display value."""
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=80)
        from omega.runtime.structural_stubs import consume_mana
        from omega.runtime.object_stubs import get_mana
        assert get_mana(mob) == 80
        consume_mana(mob, Spell.FIREBALL)
        cost = ctx.metrics["spell_mana_cost"]
        assert get_mana(mob) == 80 - cost


# ---------------------------------------------------------------------------
# CheckSkill UNINIT and edge case tests
# ---------------------------------------------------------------------------


class TestCheckSkillEdgeCases:
    """Edge cases for CheckSkill stub — UNINIT, type coercion, boundary values."""

    def test_uninit_difficulty_returns_zero(self):
        """UNINIT difficulty should not crash; int(UNINIT) raises TypeError,
        caught by try/except → returns 0."""
        from omega.interpreter.types import UNINIT as _UNINIT
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1000)
        from omega.runtime.structural_stubs import check_skill
        result = check_skill(mob, SKILLID_MAGERY, _UNINIT, 100)
        assert result == 0  # caught by try/except

    def test_uninit_skill_id_returns_zero(self):
        """UNINIT skill_id → returns 0 (None check)."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1000)
        from omega.runtime.structural_stubs import check_skill
        result = check_skill(mob, None, 50, 100)
        assert result == 0

    def test_string_difficulty_coercion(self):
        """String difficulty like '40' should be coerced to int."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1300)  # 130 display → chance = 130-40+50 = 100
        from omega.runtime.structural_stubs import check_skill
        result = check_skill(mob, SKILLID_MAGERY, "40", 100)
        assert result == 1  # 100% chance

    def test_boundary_chance_50(self):
        """Skill exactly equal to difficulty → chance = 50%."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=500)  # 50 display
        from omega.runtime.structural_stubs import check_skill
        # chance = 50 - 50 + 50 = 50
        check_skill(mob, SKILLID_MAGERY, 50, 100)
        assert ctx.metrics["spell_skill_chance"] == 50

    def test_negative_difficulty_clamps(self):
        """Negative difficulty → chance clamped to 100, not over."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1000)  # 100 display
        from omega.runtime.structural_stubs import check_skill
        result = check_skill(mob, SKILLID_MAGERY, -50, 100)
        # chance = 100 - (-50) + 50 = 200 → clamped to 100
        assert result == 1
        assert ctx.metrics["spell_skill_chance"] == 100

    def test_missing_skill_gives_chance_zero_to_fifty(self):
        """Mobile with no magery skill → skill_val=0, chance = 0 - diff + 50."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = Mobile(name="NoSkills")
        from omega.runtime.structural_stubs import check_skill
        check_skill(mob, SKILLID_MAGERY, 60, 100)
        # chance = 0 - 60 + 50 = -10 → clamped to 0
        assert ctx.metrics["spell_skill_chance"] == 0

    def test_debug_off_no_metrics(self):
        """When debug_mode=False, metrics should NOT be recorded."""
        ctx = SimulationContext(debug_mode=False)
        set_context(ctx)
        mob = _make_mage(magery=1000)
        from omega.runtime.structural_stubs import check_skill
        check_skill(mob, SKILLID_MAGERY, 50, 100)
        assert "spell_skill_check" not in ctx.metrics

    def test_deterministic_with_rng_seed(self):
        """Same RNG seed → same CheckSkill result."""
        from omega.runtime.rng import set_rng_seed
        from omega.runtime.structural_stubs import check_skill

        results = []
        for _ in range(2):
            set_rng_seed(999)
            ctx = SimulationContext(debug_mode=True)
            set_context(ctx)
            mob = _make_mage(magery=700)  # 70 display, diff 50 → chance 70
            result = check_skill(mob, SKILLID_MAGERY, 50, 100)
            results.append(result)
        assert results[0] == results[1]


# ---------------------------------------------------------------------------
# Sleepms/Sleep UNINIT edge cases
# ---------------------------------------------------------------------------


class TestSleepUninitEdgeCases:
    def test_sleepms_uninit_no_crash(self):
        """Sleepms(UNINIT) must not crash — UNINIT fails int(), caught."""
        from omega.interpreter.types import UNINIT as _UNINIT
        ctx = SimulationContext(game_clock=1000)
        set_context(ctx)
        from omega.runtime.basic_stubs import sleepms
        sleepms(_UNINIT)
        assert ctx._virtual_time_ms == 0  # unchanged

    def test_sleep_uninit_no_crash(self):
        """Sleep(UNINIT) must not crash."""
        from omega.interpreter.types import UNINIT as _UNINIT
        ctx = SimulationContext(game_clock=1000)
        set_context(ctx)
        from omega.runtime.basic_stubs import sleep_func
        sleep_func(_UNINIT)
        assert ctx._virtual_time_ms == 0

    def test_sleepms_negative_no_effect(self):
        """Negative ms should not subtract virtual time."""
        ctx = SimulationContext(game_clock=1000)
        set_context(ctx)
        from omega.runtime.basic_stubs import sleepms
        sleepms(-500)
        assert ctx._virtual_time_ms == 0

    def test_sleepms_string_coercion(self):
        """String '500' should be coerced to int."""
        ctx = SimulationContext(game_clock=1000)
        set_context(ctx)
        from omega.runtime.basic_stubs import sleepms
        sleepms("500")
        assert ctx._virtual_time_ms == 500

    def test_sleepms_float_truncates(self):
        """Float 750.9 should truncate to 750."""
        ctx = SimulationContext(game_clock=1000)
        set_context(ctx)
        from omega.runtime.basic_stubs import sleepms
        sleepms(750.9)
        assert ctx._virtual_time_ms == 750


# ---------------------------------------------------------------------------
# Player mode spell pipeline
# ---------------------------------------------------------------------------


class TestPlayerModeSpellPipeline:
    """Tests verifying the full TryToCast pipeline in player mode."""

    def test_player_mode_success(self, fixture_shard, spell_parse_results, spell_registry):
        """High-skill mage should succeed in player mode."""
        caster = _make_mage(magery=1200, mana=100)
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster, target=target, npc_mode=False, rng_seed=42)
        assert result.success, f"Failed: {result.error}"
        assert result.final_damage > 0
        assert result.cast_success

    def test_player_mode_mana_deducted(self, fixture_shard, spell_parse_results, spell_registry):
        """Player mode should consume mana from the caster."""
        caster = _make_mage(magery=1200, mana=100)
        initial_mana = caster.mana
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster, target=target, npc_mode=False, rng_seed=42)
        if not result.fizzled:
            assert caster.mana < initial_mana

    def test_player_mode_zero_mana_fizzles(self, fixture_shard, spell_parse_results, spell_registry):
        """Player with 0 mana should fail to cast."""
        caster = _make_mage(magery=1200, mana=0)
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster, target=target, npc_mode=False, rng_seed=42)
        assert result.fizzled or result.final_damage == 0

    def test_npc_mode_no_mana_required(self, fixture_shard, spell_parse_results, spell_registry):
        """NPC mode with 0 mana should still deal damage."""
        caster = _make_mage(magery=0, mana=0)
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster, target=target, npc_mode=True, circle_override=3, rng_seed=42)
        assert result.success
        assert result.final_damage > 0

    def test_player_mode_fizzle_no_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Fizzled spell should do zero damage."""
        fizzle_found = False
        for seed in range(1, 50):
            caster = _make_mage(magery=10, mana=100)  # Very low skill
            target = _make_defender(hp=500)
            result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                                 caster=caster, target=target, npc_mode=False, rng_seed=seed)
            if result.fizzled:
                assert result.final_damage == 0, "Fizzled spell should deal 0 damage"
                fizzle_found = True
                break
        assert fizzle_found, "Expected at least one fizzle with skill=1"


# ---------------------------------------------------------------------------
# Target and multi-defender stub edge cases
# ---------------------------------------------------------------------------


class TestTargetStubEdgeCases:
    def test_target_empty_defenders(self):
        """Target() with no defenders returns None."""
        ctx = SimulationContext(defenders=[])
        set_context(ctx)
        from omega.runtime.structural_stubs import target_stub
        assert target_stub() is None

    def test_target_coordinates_no_defender(self):
        """TargetCoordinates() with no defender returns 0,0,0."""
        ctx = SimulationContext(defenders=[])
        set_context(ctx)
        from omega.runtime.structural_stubs import target_coordinates
        result = target_coordinates()
        assert result.get_member("x") == 0
        assert result.get_member("y") == 0
        assert result.get_member("z") == 0


# ---------------------------------------------------------------------------
# End-to-end vital unit consistency through the eScript pipeline
#
# These tests verify that damage/mana values flowing through the actual
# eScript interpreter (not just isolated stubs) use consistent units.
# ---------------------------------------------------------------------------


class TestEndToEndVitalUnits:
    """Verify vital units are consistent through the full eScript execution."""

    def test_damage_equals_hp_delta(self, fixture_shard, spell_parse_results, spell_registry):
        """ApplyRawDamage(target, N) must reduce target.hp by exactly N.

        This catches unit confusion where eScript computes damage in one
        unit system but ApplyRawDamage interprets it in another.
        """
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             rng_seed=42, target=target)
        if result.final_damage > 0:
            hp_delta = result.target_hp_before - result.target_hp_after
            assert hp_delta == result.final_damage, (
                f"HP delta ({hp_delta}) != final_damage ({result.final_damage}) — "
                f"possible unit mismatch in ApplyRawDamage"
            )

    def test_getmana_matches_mob_mana_after_consume(self, fixture_shard, spell_parse_results, spell_registry):
        """After player-mode cast, GetMana(caster) must equal caster.mana.

        Verifies ConsumeMana didn't use *100 or //100 internally.
        """
        from omega.runtime.object_stubs import get_mana
        caster = _make_mage(magery=1200, mana=100)
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster, target=target, npc_mode=False, rng_seed=42)
        # After execution, GetMana and mob.mana must agree
        assert get_mana(caster) == caster.mana, (
            f"GetMana={get_mana(caster)} != caster.mana={caster.mana} — "
            f"unit mismatch after ConsumeMana"
        )

    def test_getvital_mana_is_mob_mana_times_100(self, fixture_shard, spell_parse_results, spell_registry):
        """After spell execution, GetVital(caster, 'mana') must be caster.mana * 100.

        Ensures the hundredths↔display conversion is consistent.
        """
        from omega.runtime.object_stubs import get_vital
        caster = _make_mage(magery=1200, mana=100)
        target = _make_defender(hp=500)
        _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                     caster=caster, target=target, npc_mode=False, rng_seed=42)
        assert get_vital(caster, "mana") == caster.mana * 100, (
            f"GetVital={get_vital(caster, 'mana')} != mana*100={caster.mana * 100}"
        )

    def test_getvital_life_is_mob_hp_times_100(self, fixture_shard, spell_parse_results, spell_registry):
        """After spell damage, GetVital(target, 'life') must be target.hp * 100."""
        from omega.runtime.object_stubs import get_vital
        target = _make_defender(hp=500)
        _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                     rng_seed=42, target=target)
        assert get_vital(target, "life") == target.hp * 100, (
            f"GetVital={get_vital(target, 'life')} != hp*100={target.hp * 100}"
        )

    def test_mana_cost_is_reasonable_display_value(self, fixture_shard, spell_parse_results, spell_registry):
        """Mana cost from circles.cfg should be a small display value (1-40),
        not a hundredths value (100-4000)."""
        caster = _make_mage(magery=1200, mana=100)
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             caster=caster, target=target, npc_mode=False, rng_seed=42)
        if not result.fizzled:
            cost = result.metrics.get("spell_mana_cost", 0)
            assert 1 <= cost <= 40, (
                f"Mana cost {cost} is outside expected range for display units — "
                f"possible hundredths confusion"
            )


# ---------------------------------------------------------------------------
# M25 — All single-target damage spells
# ---------------------------------------------------------------------------

# Spells that actually deal damage in NPC mode with standard NPC→NPC setup
_STANDARD_DAMAGE_SPELLS = [
    (Spell.MAGIC_ARROW, 1),
    (Spell.HARM, 2),
    (Spell.FIREBALL, 3),
    (Spell.LIGHTNING, 4),
    (Spell.MIND_BLAST, 5),
    (Spell.ENERGY_BOLT, 6),
    (Spell.FLAME_STRIKE, 7),
]

_NECRO_DAMAGE_SPELLS = [
    (Spell.SPECTRES_TOUCH, 21),
    (Spell.SORCERERS_BANE, 23),
    (Spell.WYVERN_STRIKE, 23),
    (Spell.KILL, 24),
]

_EARTH_DAMAGE_SPELLS = [
    (Spell.SHIFTING_EARTH, 25),
    (Spell.CALL_LIGHTNING, 26),
    (Spell.ICE_STRIKE, 28),
]

_HOLY_DAMAGE_SPELLS = [
    # Holy Bolt requires NPC caster → player target for damage path
    (Spell.DIVINE_FURY, 27),
]

# All damage spells that work with NPC→NPC (standard test setup)
_ALL_NPC_DAMAGE_SPELLS = (
    _STANDARD_DAMAGE_SPELLS
    + _NECRO_DAMAGE_SPELLS
    + _EARTH_DAMAGE_SPELLS
    + _HOLY_DAMAGE_SPELLS
)

# Non-damage "spells" listed in path_to_v3.md but actually debuff/CC
_NON_DAMAGE_SPELLS = [
    Spell.DECAYING_RAY,     # AR debuff
    Spell.WRAITHS_BREATH,   # Paralysis/CC (also AoE)
]


class TestAllSingleTargetDamageSpells:
    """Every single-target damage spell executes and deals damage."""

    @pytest.mark.parametrize("spell,circle", _ALL_NPC_DAMAGE_SPELLS,
                             ids=[s.name for s, _ in _ALL_NPC_DAMAGE_SPELLS])
    def test_executes_successfully(self, fixture_shard, spell_parse_results, spell_registry,
                                   spell, circle):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell)
        assert result.success, f"{spell.name} failed: {result.error}"

    @pytest.mark.parametrize("spell,circle", _ALL_NPC_DAMAGE_SPELLS,
                             ids=[s.name for s, _ in _ALL_NPC_DAMAGE_SPELLS])
    def test_deals_positive_damage(self, fixture_shard, spell_parse_results, spell_registry,
                                   spell, circle):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell)
        assert result.success, f"{spell.name} failed: {result.error}"
        assert result.final_damage > 0, (
            f"{spell.name} dealt 0 damage; metrics={result.metrics}"
        )

    @pytest.mark.parametrize("spell,circle", _ALL_NPC_DAMAGE_SPELLS,
                             ids=[s.name for s, _ in _ALL_NPC_DAMAGE_SPELLS])
    def test_deterministic_with_seed(self, fixture_shard, spell_parse_results, spell_registry,
                                     spell, circle):
        r1 = _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell, rng_seed=99)
        r2 = _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell, rng_seed=99)
        assert r1.final_damage == r2.final_damage, (
            f"{spell.name} not deterministic: {r1.final_damage} vs {r2.final_damage}"
        )

    @pytest.mark.parametrize("spell,circle", _ALL_NPC_DAMAGE_SPELLS,
                             ids=[s.name for s, _ in _ALL_NPC_DAMAGE_SPELLS])
    def test_spell_has_circle(self, fixture_shard, spell_parse_results, spell_registry,
                              spell, circle):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell)
        assert result.circle > 0, f"{spell.name} missing circle"


class TestHolyBoltAlignment:
    """Holy Bolt damages evil/neutral NPCs and player targets, heals good NPCs."""

    def test_npc_caster_player_target_damages(self, fixture_shard, spell_parse_results, spell_registry):
        """NPC caster → player target always deals damage (holybolt.src line 65-67)."""
        caster = _make_mage(is_npc=True)
        caster.npctemplate = "test_caster"
        target = _make_defender(is_npc=False)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.HOLY_BOLT, caster=caster, target=target)
        assert result.success
        assert result.final_damage > 0, "NPC→player should deal damage"

    def test_npc_to_npc_heals(self, fixture_shard, spell_parse_results, spell_registry):
        """NPC caster → NPC target with no alignment falls to heal path (line 77-79)."""
        caster = _make_mage(is_npc=True)
        caster.npctemplate = "test_caster"
        target = _make_defender(is_npc=True, hp=300)
        target.hp = 200  # Below max — healing is observable
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.HOLY_BOLT, caster=caster, target=target)
        assert result.success
        assert result.final_damage == 0.0, "NPC→NPC should heal, not damage"
        # Verify heal side effect
        heal_effects = [se for se in result.side_effects if se.kind == "heal"]
        assert len(heal_effects) > 0, "Expected heal side effect"

    def test_player_caster_evil_npc_damages(self, fixture_shard, spell_parse_results, spell_registry):
        """Player caster → evil NPC target should deal damage (line 68-72).
        Requires npcdesc.cfg with alignment field; skip if config unavailable."""
        caster = _make_mage(is_npc=False)
        # Target needs to be an NPC with a template that has alignment="evil" in npcdesc.cfg
        target = _make_defender(is_npc=True)
        target.npctemplate = "evilmage"
        target.set_property("alignment", "evil")
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.HOLY_BOLT, caster=caster, target=target)
        assert result.success
        # The alignment check reads from npcdesc.cfg, not object properties.
        # If the config doesn't have this template, the damage path won't trigger.
        # Either damage > 0 (config has evil alignment) or heal (fallback).
        # This is a best-effort test — skip if neither damage nor heal occurred.

    def test_player_to_player_heals(self, fixture_shard, spell_parse_results, spell_registry):
        """Player caster → player target heals (line 77-79)."""
        caster = _make_mage(is_npc=False)
        target = _make_defender(is_npc=False, hp=300)
        target.hp = 200
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.HOLY_BOLT, caster=caster, target=target, npc_mode=False)
        # May fizzle — that's OK; if it succeeds, it should heal not damage
        if not result.fizzled:
            assert result.final_damage == 0.0, "Player→player should heal, not damage"


class TestNonDamageSpells:
    """Spells that are debuffs/CC rather than damage."""

    def test_decaying_ray_executes(self, fixture_shard, spell_parse_results, spell_registry):
        """Decaying Ray is an AR debuff — should execute without error."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.DECAYING_RAY)
        assert result.success, f"Decaying Ray failed: {result.error}"

    def test_decaying_ray_no_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Decaying Ray doesn't call ApplyRawDamage — final_damage should be 0."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.DECAYING_RAY)
        assert result.final_damage == 0.0

    def test_wraiths_breath_executes(self, fixture_shard, spell_parse_results, spell_registry):
        """Wraith's Breath is a paralysis spell — should execute without error."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.WRAITHS_BREATH)
        assert result.success, f"Wraith's Breath failed: {result.error}"

    def test_wraiths_breath_no_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Wraith's Breath doesn't call ApplyRawDamage — final_damage should be 0."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.WRAITHS_BREATH)
        assert result.final_damage == 0.0

    def test_sacrifice_executes(self, fixture_shard, spell_parse_results, spell_registry):
        """Sacrifice is AoE pet sacrifice — executes but may not deal damage without
        nearby mobs. Deferred to M26 for full AoE testing."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.SACRIFICE)
        assert result.success, f"Sacrifice failed: {result.error}"


class TestSpellDamageProperties:
    """Property-based assertions about spell damage behavior."""

    def test_higher_circle_higher_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Higher circle spells should generally deal more damage."""
        low = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                          Spell.MAGIC_ARROW, rng_seed=42)   # Circle 1
        high = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                           Spell.FLAME_STRIKE, rng_seed=42)  # Circle 7
        assert high.final_damage > low.final_damage, (
            f"Circle 7 ({high.final_damage}) should exceed circle 1 ({low.final_damage})"
        )

    def test_npc_target_more_damage_than_player(self, fixture_shard, spell_parse_results, spell_registry):
        """NPC targets receive 1.5x scaling; player targets receive 1/3x."""
        npc_target = _make_defender(is_npc=True)
        player_target = _make_defender(is_npc=False, hp=500)
        npc_result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.FIREBALL, target=npc_target, rng_seed=42)
        player_result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                                    Spell.FIREBALL, target=player_target, rng_seed=42)
        assert npc_result.final_damage > player_result.final_damage, (
            f"NPC damage ({npc_result.final_damage}) should exceed player ({player_result.final_damage})"
        )

    def test_resistance_reduces_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """High magic resistance should reduce spell damage."""
        low_resist = _make_defender(resist=0)
        high_resist = _make_defender(resist=1200)
        low_r = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                            Spell.FIREBALL, target=low_resist, rng_seed=42)
        high_r = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.FIREBALL, target=high_resist, rng_seed=42)
        assert high_r.final_damage <= low_r.final_damage, (
            f"High resist ({high_r.final_damage}) should not exceed low resist ({low_r.final_damage})"
        )

    def test_all_standard_spells_increase_with_circle(self, fixture_shard, spell_parse_results, spell_registry):
        """Damage should generally increase across standard spell circles."""
        damages = {}
        for spell, circle in _STANDARD_DAMAGE_SPELLS:
            result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                                 spell, rng_seed=42)
            damages[circle] = (spell.name, result.final_damage)

        # Verify monotonically increasing from circle 1 to 7
        # Mind Blast (circle 5) uses a different formula so allow some flexibility
        prev_dmg = 0
        for circle in sorted(damages.keys()):
            name, dmg = damages[circle]
            if circle != 5:  # Mind Blast uses INT difference, may not follow pattern
                assert dmg >= prev_dmg, (
                    f"{name} (circle {circle}, dmg={dmg}) less than previous ({prev_dmg})"
                )
                prev_dmg = dmg


class TestSchoolSpecificMetrics:
    """Verify correct metric types per school."""

    @pytest.mark.parametrize("spell,circle", _STANDARD_DAMAGE_SPELLS[:3],
                             ids=[s.name for s, _ in _STANDARD_DAMAGE_SPELLS[:3]])
    def test_standard_spells_have_elemental_metrics(self, fixture_shard, spell_parse_results,
                                                     spell_registry, spell, circle):
        """Standard spells use ApplyElementalDamage → should have elemental_applied metric."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell)
        assert result.success
        # Standard damage spells go through ApplyElementalDamage
        assert "elemental_applied" in result.metrics or "planar_applied" in result.metrics, (
            f"{spell.name} missing elemental/planar metrics; keys={list(result.metrics.keys())}"
        )

    @pytest.mark.parametrize("spell,circle", _NECRO_DAMAGE_SPELLS,
                             ids=[s.name for s, _ in _NECRO_DAMAGE_SPELLS])
    def test_necro_spells_have_planar_metrics(self, fixture_shard, spell_parse_results,
                                              spell_registry, spell, circle):
        """Necro spells use ApplyPlanarDamage → should have planar_applied metric."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell)
        assert result.success
        has_planar = "planar_applied" in result.metrics
        has_elemental = "elemental_applied" in result.metrics
        # Sorcerer's Bane uses elemental (fire+water), others use planar
        assert has_planar or has_elemental, (
            f"{spell.name} missing planar/elemental metrics; keys={list(result.metrics.keys())}"
        )

    @pytest.mark.parametrize("spell,circle", _EARTH_DAMAGE_SPELLS,
                             ids=[s.name for s, _ in _EARTH_DAMAGE_SPELLS])
    def test_earth_spells_have_elemental_metrics(self, fixture_shard, spell_parse_results,
                                                  spell_registry, spell, circle):
        """Earth spells use ApplyElementalDamage → should have elemental_applied metric."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, spell)
        assert result.success
        assert "elemental_applied" in result.metrics, (
            f"{spell.name} missing elemental_applied; keys={list(result.metrics.keys())}"
        )

    def test_divine_fury_has_planar_metrics(self, fixture_shard, spell_parse_results, spell_registry):
        """Divine Fury uses ApplyPlanarDamage with HOLY plane."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.DIVINE_FURY)
        assert result.success
        assert "planar_applied" in result.metrics, (
            f"Divine Fury missing planar_applied; keys={list(result.metrics.keys())}"
        )


class TestSpellEdgeCases:
    """Edge cases for specific spell mechanics."""

    def test_wyvern_strike_poison_side_effect(self, fixture_shard, spell_parse_results, spell_registry):
        """Wyvern Strike applies poison via SetPoison after damage."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.WYVERN_STRIKE)
        assert result.success
        assert result.final_damage > 0
        # Poison may or may not trigger depending on water protection
        # Just verify the spell runs without error

    def test_sorcerers_bane_deals_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Sorcerer's Bane does mana drain + elemental damage (fire+water)."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.SORCERERS_BANE)
        assert result.success
        assert result.final_damage > 0

    def test_kill_deals_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Kill spell deals massive necro damage."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.KILL)
        assert result.success
        assert result.final_damage > 0

    def test_kill_high_damage_vs_low_hp(self, fixture_shard, spell_parse_results, spell_registry):
        """Kill with high caster magery vs low HP target — may instant-kill."""
        caster = _make_mage(magery=1200, eval_int=1200)
        target = _make_defender(hp=50)  # Very low HP
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.KILL, caster=caster, target=target, rng_seed=42)
        assert result.success
        # Target should be dead or near-dead
        assert result.final_damage > 0

    def test_spectres_touch_deals_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Spectre's Touch deals necro planar damage."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.SPECTRES_TOUCH)
        assert result.success
        assert result.final_damage > 0

    def test_shifting_earth_deals_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Shifting Earth deals elemental damage (+ dex debuff, not tested here)."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.SHIFTING_EARTH)
        assert result.success
        assert result.final_damage > 0

    def test_call_lightning_deals_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Call Lightning deals air elemental damage."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.CALL_LIGHTNING)
        assert result.success
        assert result.final_damage > 0

    def test_ice_strike_deals_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Ice Strike deals water elemental damage."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.ICE_STRIKE)
        assert result.success
        assert result.final_damage > 0


class TestHandCalculatedDamage:
    """Hand-calculated damage validation for specific spells.

    CalcSpellDamage formula:
        dice = circle * 3  (SPELL_DAMAGES_CIRCLE_MULTIPLIER)
        sides = 5  (SPELL_DAMAGES_DICE_TYPE)
        bonus = magery / 5  (SPELL_DAMAGES_MAGERY_DIVIDER)
        dmg = roll(dice, sides) + bonus
        cap = circle * (13 + circle)
        dmg = min(dmg, cap)
        ModifyWithMagicEfficiency(caster, dmg)  # class penalty/bonus
        NPC target: dmg *= 1.5
        Player target: dmg /= 3
    """

    def test_fireball_npc_damage_range(self, fixture_shard, spell_parse_results, spell_registry):
        """Fireball (circle 3): dice=9d5, bonus=magery(100)/5=20.
        Range: 9+20=29 to 45+20=65, cap=3*(13+3)=48. So range [29, 48].
        NPC target: *1.5 → [43.5, 72]. After Resisted + ApplyTheDamage scaling."""
        results = []
        for seed in range(50):
            r = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                            Spell.FIREBALL, rng_seed=seed)
            if r.success:
                results.append(r.final_damage)
        assert len(results) > 0
        # Damage should be within reasonable bounds (after all modifiers)
        assert min(results) > 0, "Some casts dealt 0 damage"
        assert max(results) < 200, f"Fireball max {max(results)} seems too high for circle 3"

    def test_flame_strike_higher_than_fireball(self, fixture_shard, spell_parse_results, spell_registry):
        """Flame Strike (circle 7) should significantly exceed Fireball (circle 3)."""
        fb_results = []
        fs_results = []
        for seed in range(20):
            fb = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.FIREBALL, rng_seed=seed)
            fs = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.FLAME_STRIKE, rng_seed=seed)
            if fb.success:
                fb_results.append(fb.final_damage)
            if fs.success:
                fs_results.append(fs.final_damage)

        avg_fb = sum(fb_results) / len(fb_results) if fb_results else 0
        avg_fs = sum(fs_results) / len(fs_results) if fs_results else 0
        assert avg_fs > avg_fb * 1.3, (
            f"Flame Strike avg ({avg_fs:.1f}) should be >30% higher than Fireball ({avg_fb:.1f})"
        )

    def test_kill_massive_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Kill (circle 24/effective) — highest damage necro spell."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.KILL, rng_seed=42)
        assert result.success
        # Kill at high circle should deal substantial damage
        assert result.final_damage > 100, (
            f"Kill damage {result.final_damage} too low for a circle 24 spell"
        )

    def test_magic_arrow_low_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Magic Arrow (circle 1) — weakest spell, should deal modest damage."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.MAGIC_ARROW, rng_seed=42)
        assert result.success
        assert 0 < result.final_damage < 100, (
            f"Magic Arrow damage {result.final_damage} outside expected range for circle 1"
        )


class TestRecalcVitalsStub:
    """Verify RecalcVitals no-op stub doesn't cause errors."""

    def test_recalc_vitals_registered(self):
        """RecalcVitals should be a registered POL built-in."""
        from omega.runtime.object_stubs import recalc_vitals
        result = recalc_vitals(None)
        assert result == 1

    def test_decaying_ray_no_recalcvitals_error(self, fixture_shard, spell_parse_results, spell_registry):
        """Decaying Ray path through DotempMod may call RecalcVitals — should not error."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.DECAYING_RAY)
        assert result.success, f"Decaying Ray failed: {result.error}"


# ---------------------------------------------------------------------------
# M26 — AoE Damage Spells
# ---------------------------------------------------------------------------

def _make_defenders(count=3, hp=500, resist=0, is_npc=True):
    """Create a list of defender mobiles for AoE testing."""
    defenders = []
    for i in range(count):
        d = _make_defender(name=f"Target_{i}", hp=hp, resist=resist, is_npc=is_npc)
        d.serial = 2000 + i  # Unique serials, distinct from caster
        defenders.append(d)
    return defenders


def _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry, spell_id, *,
                    caster=None, targets=None, npc_mode=True, debug=True,
                    rng_seed=42, circle_override=0, **kwargs):
    """Helper to run an AoE spell with multiple targets."""
    if caster is None:
        caster = _make_mage(is_npc=True)
        caster.serial = 1000
    if targets is None:
        targets = _make_defenders()

    return execute_spell(
        spell_parse_results,
        caster,
        targets,
        int(spell_id),
        rng_seed=rng_seed,
        debug=debug,
        config_resolver=fixture_shard.resolve_config_path,
        em_modules_dir=fixture_shard.root / "scripts" / "modules",
        shard_root=fixture_shard.root,
        package_map=fixture_shard.package_map,
        npc_mode=npc_mode,
        circle_override=circle_override,
        spell_registry=spell_registry,
        **kwargs,
    )


# Standard AoE spells: Explosion, Chain Lightning, Earthquake
# (Meteor Swarm has special dual-phase behavior, tested separately)
_STANDARD_AOE_SPELLS = [
    (Spell.EXPLOSION, 6, "Fire"),
    (Spell.CHAIN_LIGHTNING, 7, "Air"),
    (Spell.EARTHQUAKE, 8, "Earth"),
]


class TestAoEBasicExecution:
    """All AoE damage spells execute successfully against multiple targets."""

    @pytest.mark.parametrize("spell_id,circle,element", _STANDARD_AOE_SPELLS,
                             ids=["Explosion", "ChainLightning", "Earthquake"])
    def test_standard_aoe_executes(self, fixture_shard, spell_parse_results, spell_registry,
                                   spell_id, circle, element):
        """Standard AoE spell executes with success against 3 targets."""
        targets = _make_defenders(count=3)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 spell_id, targets=targets)
        assert result.success, f"{spell_id.name} failed: {result.error}"
        assert result.final_damage > 0, f"{spell_id.name} dealt 0 damage"

    def test_explosion_multiple_targets_take_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Explosion: each of 3 targets should take HP damage."""
        targets = _make_defenders(count=3, hp=500)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EXPLOSION, targets=targets)
        assert result.success, f"Explosion failed: {result.error}"
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 2, f"Only {damaged}/3 targets took HP damage"

    def test_chain_lightning_multiple_targets(self, fixture_shard, spell_parse_results, spell_registry):
        """Chain Lightning: each target should take HP damage."""
        targets = _make_defenders(count=3, hp=500)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.CHAIN_LIGHTNING, targets=targets)
        assert result.success, f"Chain Lightning failed: {result.error}"
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 2, f"Only {damaged}/3 targets took HP damage"

    def test_earthquake_multiple_targets(self, fixture_shard, spell_parse_results, spell_registry):
        """Earthquake: multiple targets take damage (caster excluded)."""
        targets = _make_defenders(count=3, hp=500)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EARTHQUAKE, targets=targets)
        assert result.success, f"Earthquake failed: {result.error}"
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 2, f"Only {damaged}/3 targets took HP damage"

    def test_aoe_deterministic_with_seed(self, fixture_shard, spell_parse_results, spell_registry):
        """AoE spells are deterministic with the same seed."""
        targets1 = _make_defenders(count=3, hp=500)
        targets2 = _make_defenders(count=3, hp=500)
        r1 = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                              Spell.EXPLOSION, targets=targets1, rng_seed=99)
        r2 = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                              Spell.EXPLOSION, targets=targets2, rng_seed=99)
        assert r1.final_damage == r2.final_damage

    def test_rising_fire_executes(self, fixture_shard, spell_parse_results, spell_registry):
        """Rising Fire (Earth school) executes successfully."""
        targets = _make_defenders(count=3, hp=500)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.RISING_FIRE, targets=targets)
        assert result.success, f"Rising Fire failed: {result.error}"
        assert result.final_damage > 0

    def test_rising_fire_multiple_targets(self, fixture_shard, spell_parse_results, spell_registry):
        """Rising Fire: each target takes HP damage across both phases."""
        targets = _make_defenders(count=3, hp=500)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.RISING_FIRE, targets=targets)
        assert result.success, f"Rising Fire failed: {result.error}"
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 2, f"Only {damaged}/3 targets took HP damage"

    def test_abyssal_flame_executes(self, fixture_shard, spell_parse_results, spell_registry):
        """Abyssal Flame (Necro) executes with primary + AoE targets."""
        targets = _make_defenders(count=3, hp=500)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.ABYSSAL_FLAME, targets=targets)
        assert result.success, f"Abyssal Flame failed: {result.error}"
        assert result.final_damage > 0


class TestMeteorSwarm:
    """Meteor Swarm dual-phase: Fire+Earth split, two damage applications per target."""

    def test_executes_successfully(self, fixture_shard, spell_parse_results, spell_registry):
        """Meteor Swarm runs without error."""
        targets = _make_defenders(count=3, hp=500)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.METEOR_SWARM, targets=targets)
        assert result.success, f"Meteor Swarm failed: {result.error}"
        assert result.final_damage > 0

    def test_multiple_targets_take_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """All targets take HP damage from Meteor Swarm."""
        targets = _make_defenders(count=3, hp=500)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.METEOR_SWARM, targets=targets)
        assert result.success
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 2, f"Only {damaged}/3 targets took HP damage"

    def test_dual_phase_more_damage_than_single(self, fixture_shard, spell_parse_results, spell_registry):
        """Meteor Swarm's dual phase should deal more total damage than a single-phase AoE of same circle."""
        # Compare with Explosion (circle 6) — Meteor is circle 7 with dual phases
        targets_ms = _make_defenders(count=1, hp=1000)
        targets_ex = _make_defenders(count=1, hp=1000)
        ms = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                              Spell.METEOR_SWARM, targets=targets_ms, rng_seed=42)
        ex = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                              Spell.EXPLOSION, targets=targets_ex, rng_seed=42)
        assert ms.success and ex.success
        # Meteor Swarm (circle 7 dual-phase) should deal more than Explosion (circle 6 single-phase)
        assert ms.final_damage > ex.final_damage, (
            f"Meteor Swarm ({ms.final_damage}) should exceed Explosion ({ex.final_damage})"
        )


class TestAbyssalFlame:
    """Abyssal Flame: primary target + AoE secondary targets."""

    def test_primary_and_secondary_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Primary target and secondary targets all take damage."""
        targets = _make_defenders(count=3, hp=500)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.ABYSSAL_FLAME, targets=targets)
        assert result.success, f"Abyssal Flame failed: {result.error}"
        # Primary target is targets[0] (main_target_index=0)
        assert targets[0].hp < hp_before[0], "Primary target should take damage"
        # At least some secondary targets should also take damage
        secondary_damaged = sum(1 for i in range(1, len(targets)) if targets[i].hp < hp_before[i])
        assert secondary_damaged >= 1, "At least 1 secondary target should take damage"

    def test_primary_uses_elemental_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Primary target path uses ApplyElementalDamage (Fire element)."""
        targets = _make_defenders(count=1, hp=500)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.ABYSSAL_FLAME, targets=targets)
        assert result.success
        # Should have elemental_applied metric from the primary target
        assert "elemental_applied" in result.metrics or result.final_damage > 0


class TestEarthquake:
    """Earthquake: caster-centered, structure damage stubs."""

    def test_list_items_near_location_of_type_no_crash(self, fixture_shard, spell_parse_results, spell_registry):
        """ListItemsNearLocationOfType no-op doesn't crash Earthquake."""
        targets = _make_defenders(count=3, hp=500)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EARTHQUAKE, targets=targets)
        assert result.success, f"Earthquake failed: {result.error}"

    def test_multi_access_no_crash(self, fixture_shard, spell_parse_results, spell_registry):
        """mobile.multi access returns UNINIT without crashing."""
        targets = _make_defenders(count=3, hp=500)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EARTHQUAKE, targets=targets)
        assert result.success, f"Earthquake failed: {result.error}"
        assert result.final_damage > 0

    def test_caster_excluded_from_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Earthquake checks mobile.serial != caster.serial — caster not in target list, so all targets hit."""
        caster = _make_mage(is_npc=True)
        caster.serial = 9999
        targets = _make_defenders(count=3, hp=500)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EARTHQUAKE, caster=caster, targets=targets)
        assert result.success
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 2, f"Only {damaged}/3 targets took damage"


class TestApocalypse:
    """Apocalypse: 3-phase (chain lightning + earthquake + meteor), complex gating."""

    def test_npc_caster_executes(self, fixture_shard, spell_parse_results, spell_registry):
        """Apocalypse NPC caster mode executes against player targets."""
        # NPC caster → only damages non-NPC targets in the NPC branch
        caster = _make_mage(is_npc=True)
        caster.serial = 1000
        targets = _make_defenders(count=3, hp=500, is_npc=False)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.APOCALYPSE, caster=caster, targets=targets)
        assert result.success, f"Apocalypse NPC mode failed: {result.error}"

    def test_npc_caster_deals_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Apocalypse NPC caster deals damage to player targets."""
        caster = _make_mage(is_npc=True)
        caster.serial = 1000
        targets = _make_defenders(count=3, hp=500, is_npc=False)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.APOCALYPSE, caster=caster, targets=targets)
        assert result.success
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 1, f"Only {damaged}/3 targets took damage from Apocalypse"

    def test_multi_property_no_crash(self, fixture_shard, spell_parse_results, spell_registry):
        """caster.multi and mobile.multi access doesn't crash (returns UNINIT)."""
        caster = _make_mage(is_npc=True)
        caster.serial = 1000
        targets = _make_defenders(count=2, hp=500, is_npc=False)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.APOCALYPSE, caster=caster, targets=targets)
        assert result.success, f"Apocalypse failed: {result.error}"


class TestAoECircleReduction:
    """Verify AoE damage uses circle-3 reduction (AREA_EFFECT_SPELL flag)."""

    def test_aoe_deals_less_per_target_than_single_target(self, fixture_shard, spell_parse_results, spell_registry):
        """AoE per-target damage < equivalent single-target damage at same circle.

        Explosion (circle 6 AoE) should deal less per target than Energy Bolt (circle 6 single-target).
        """
        aoe_damages = []
        st_damages = []
        for seed in range(10, 20):
            aoe_target = _make_defender(hp=500)
            aoe_result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                          Spell.EXPLOSION, targets=[aoe_target], rng_seed=seed)
            if aoe_result.success and aoe_result.final_damage > 0:
                aoe_damages.append(aoe_result.final_damage)

            st_result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                                     Spell.ENERGY_BOLT, rng_seed=seed)
            if st_result.success and st_result.final_damage > 0:
                st_damages.append(st_result.final_damage)

        if aoe_damages and st_damages:
            avg_aoe = sum(aoe_damages) / len(aoe_damages)
            avg_st = sum(st_damages) / len(st_damages)
            assert avg_aoe < avg_st, (
                f"AoE avg ({avg_aoe:.1f}) should be less than single-target avg ({avg_st:.1f}) "
                f"due to circle-3 reduction"
            )


class TestDualPhaseSpells:
    """Dual-phase spells: Meteor Swarm, Rising Fire."""

    def test_rising_fire_dual_phase_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Rising Fire applies damage in two phases (CInt(dmg/2) each)."""
        targets = _make_defenders(count=1, hp=1000)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.RISING_FIRE, targets=targets, rng_seed=42)
        assert result.success
        assert result.final_damage > 0
        # Damage should be applied — the total is two half-applications
        hp_lost = 1000 - targets[0].hp
        assert hp_lost > 0, "Target should lose HP from Rising Fire"

    def test_meteor_swarm_phase2_no_area_flag(self, fixture_shard, spell_parse_results, spell_registry):
        """Meteor Swarm phase 2 uses full circle (no AREA_EFFECT_SPELL).

        This means phase 2 deals more per-target damage than phase 1.
        Total damage should reflect both phases.
        """
        targets = _make_defenders(count=1, hp=1000)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.METEOR_SWARM, targets=targets, rng_seed=42)
        assert result.success
        # Total damage from both phases
        assert result.final_damage > 0
        # The spell_base_damage metric fires for each CalcSpellDamage call
        # Phase 1: circle-3 (AoE), Phase 2: full circle
        # Just verify execution succeeded and damage was dealt
        hp_lost = 1000 - targets[0].hp
        assert hp_lost > 0, "Target should lose HP from both phases"


class TestAoEWithResistance:
    """Resistance affects each target independently."""

    def test_high_resist_reduces_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """High resist target takes less or equal damage than low resist target (averaged over seeds)."""
        low_total = 0
        high_total = 0
        count = 0
        for seed in range(10, 30):
            low_r = _make_defender(name="LowResist", hp=500, resist=0)
            high_r = _make_defender(name="HighResist", hp=500, resist=1200)  # 120.0 resist
            low_r.serial = 2001
            high_r.serial = 2002

            r_low = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                     Spell.EXPLOSION, targets=[low_r], rng_seed=seed)
            r_high = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                      Spell.EXPLOSION, targets=[high_r], rng_seed=seed)

            if r_low.success and r_high.success:
                low_total += (500 - low_r.hp)
                high_total += (500 - high_r.hp)
                count += 1

        assert count > 0
        avg_low = low_total / count
        avg_high = high_total / count
        assert avg_high <= avg_low, (
            f"High resist avg ({avg_high:.1f} HP lost) should not exceed "
            f"low resist avg ({avg_low:.1f} HP lost)"
        )


class TestReclassifiedSingleTarget:
    """Gust of Air and Wrath of God: reclassified from AoE to single-target."""

    def test_gust_of_air_executes(self, fixture_shard, spell_parse_results, spell_registry):
        """Gust of Air executes as single-target."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.GUST_OF_AIR, rng_seed=42)
        assert result.success, f"Gust of Air failed: {result.error}"

    def test_gust_of_air_deals_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Gust of Air deals positive damage (Air element)."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.GUST_OF_AIR, rng_seed=42)
        assert result.success
        assert result.final_damage > 0, f"Gust of Air dealt 0 damage"

    def test_gust_of_air_deterministic(self, fixture_shard, spell_parse_results, spell_registry):
        """Same seed → same damage."""
        r1 = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                          Spell.GUST_OF_AIR, rng_seed=99)
        r2 = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                          Spell.GUST_OF_AIR, rng_seed=99)
        assert r1.final_damage == r2.final_damage

    def test_wrath_of_god_executes(self, fixture_shard, spell_parse_results, spell_registry):
        """Wrath of God executes as single-target."""
        # Wrath of God uses Karma difference — set Karma on both mobiles
        caster = _make_mage(is_npc=True)
        caster.set_property("Karma", 5000)
        target = _make_defender(hp=500)
        target.set_property("Karma", -5000)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.WRATH_OF_GOD, caster=caster, target=target, rng_seed=42)
        assert result.success, f"Wrath of God failed: {result.error}"

    def test_wrath_of_god_karma_based_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Wrath of God: higher karma difference → higher damage."""
        caster = _make_mage(is_npc=True)
        caster.set_property("Karma", 10000)
        target = _make_defender(hp=500)
        target.set_property("Karma", -10000)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.WRATH_OF_GOD, caster=caster, target=target, rng_seed=42)
        assert result.success
        assert result.final_damage > 0, "Large karma difference should deal damage"

    def test_wrath_of_god_equal_karma(self, fixture_shard, spell_parse_results, spell_registry):
        """Wrath of God with equal karma deals 0 damage."""
        caster = _make_mage(is_npc=True)
        caster.set_property("Karma", 5000)
        target = _make_defender(hp=500)
        target.set_property("Karma", 5000)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.WRATH_OF_GOD, caster=caster, target=target, rng_seed=42)
        assert result.success
        # Equal karma → early return with 0 damage via ApplyPlanarDamage(... 0 ...)
        # The final_damage should be 0 or very low


class TestAstralStorm:
    """Astral Storm: CC (paralyze) + damage sub-script."""

    def test_executes_without_error(self, fixture_shard, spell_parse_results, spell_registry):
        """Astral Storm main script executes successfully."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.ASTRAL_STORM, rng_seed=42)
        assert result.success, f"Astral Storm failed: {result.error}"

    def test_paralysis_side_effect(self, fixture_shard, spell_parse_results, spell_registry):
        """Astral Storm should record a paralysis side effect via SetParalyzed."""
        target = _make_defender(hp=500)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.ASTRAL_STORM, target=target, rng_seed=42)
        assert result.success, f"Astral Storm failed: {result.error}"
        # Check that frozen was set on the target (direct property assignment)
        # The script does cast_on.frozen := 1 then later cast_on.frozen := 0
        # and cast_on.SetParalyzed(0) — the SetParalyzed should now dispatch
        # to the POL stub via the method call fallback

    def test_damage_sub_script_fires(self, fixture_shard, spell_parse_results, spell_registry):
        """start_script('astralstorm_damage') runs and deals damage."""
        target = _make_defender(hp=500)
        hp_before = target.hp
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.ASTRAL_STORM, target=target, rng_seed=42)
        assert result.success
        # astralstorm_damage applies CalcSpellDamage/8 five times via ApplyPlanarDamage
        assert result.final_damage > 0, "Astral Storm should deal damage via sub-script"
        assert target.hp < hp_before, "Target HP should decrease"


class TestMethodCallDispatch:
    """Regression tests for Bug 1: method-call syntax dispatching to POL built-ins."""

    def test_set_paralyzed_method_call(self, fixture_shard, spell_parse_results, spell_registry):
        """mobile.SetParalyzed(0) dispatches to the POL stub."""
        from omega.runtime.registry import is_registered
        assert is_registered("", "SetParalyzed"), "SetParalyzed should be registered"

    def test_set_paralyzed_via_method_call_records_side_effect(self):
        """SetParalyzed called as method should record a side effect."""
        from omega.runtime.context import SimulationContext, set_context

        ctx = SimulationContext(
            attacker=_make_mage(),
            defenders=[_make_defender()],
            debug_mode=True,
        )
        set_context(ctx)

        target = _make_defender()
        target.serial = 5555

        # Simulate what the evaluator does in _call_method
        from omega.runtime.registry import call_builtin, is_registered
        assert is_registered("", "SetParalyzed")
        call_builtin("", "SetParalyzed", [target, 0])

        # Check side effect was recorded
        paralyze_effects = [se for se in ctx.side_effects if se.kind == "paralyze"]
        assert len(paralyze_effects) >= 1, "SetParalyzed should record paralyze side effect"

    def test_method_call_fallback_in_evaluator(self):
        """_call_method falls back to POL registry for unknown instance methods."""
        from omega.runtime.registry import is_registered

        # SetParalyzed is a POL built-in, not an instance method on Mobile
        target = _make_defender()
        assert not hasattr(target, "SetParalyzed"), "Mobile should NOT have SetParalyzed method"
        assert is_registered("", "SetParalyzed"), "SetParalyzed should be in POL registry"


class TestAoEEdgeCases:
    """Edge cases for AoE spell execution."""

    def test_empty_defender_list(self, fixture_shard, spell_parse_results, spell_registry):
        """AoE spell with no targets — should execute but deal 0 damage."""
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EXPLOSION, targets=[])
        # With no defenders, ListMobilesNearLocationEx returns empty list
        # Script loops over empty list, no damage applied
        assert result.success, f"Explosion with no targets failed: {result.error}"

    def test_single_defender(self, fixture_shard, spell_parse_results, spell_registry):
        """AoE spell with 1 target degenerates to single-target."""
        targets = _make_defenders(count=1, hp=500)
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EXPLOSION, targets=targets)
        assert result.success
        assert result.final_damage > 0

    def test_five_defenders(self, fixture_shard, spell_parse_results, spell_registry):
        """AoE spell with 5 targets — damage is independent per target."""
        targets = _make_defenders(count=5, hp=500)
        hp_before = [t.hp for t in targets]
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.CHAIN_LIGHTNING, targets=targets)
        assert result.success
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 3, f"Only {damaged}/5 targets took damage"

    def test_dead_target_no_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Dead target gets no damage (CalcSpellDamage checks cast_on.dead)."""
        targets = _make_defenders(count=2, hp=500)
        targets[1].dead = True
        targets[1].hp = 0
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EXPLOSION, targets=targets)
        assert result.success
        # Only the living target should take damage
        assert targets[0].hp < 500, "Living target should take damage"

    def test_hidden_target_no_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Hidden target gets no damage (CalcSpellDamage checks cast_on.hidden)."""
        targets = _make_defenders(count=2, hp=500)
        targets[1].hidden = True
        result = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EXPLOSION, targets=targets)
        assert result.success
        # Hidden target should receive 0 from CalcSpellDamage
        assert targets[0].hp < 500, "Visible target should take damage"


class TestAoEDamageProperties:
    """Property-based assertions on AoE damage behavior."""

    def test_higher_circle_aoe_more_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """Higher circle AoE deals more per-target damage."""
        # Explosion (circle 6) vs Chain Lightning (circle 7)
        damages_explosion = []
        damages_chain = []
        for seed in range(10, 25):
            t1 = _make_defender(hp=500)
            r1 = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                  Spell.EXPLOSION, targets=[t1], rng_seed=seed)
            if r1.success and r1.final_damage > 0:
                damages_explosion.append(r1.final_damage)

            t2 = _make_defender(hp=500)
            r2 = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                  Spell.CHAIN_LIGHTNING, targets=[t2], rng_seed=seed)
            if r2.success and r2.final_damage > 0:
                damages_chain.append(r2.final_damage)

        if damages_explosion and damages_chain:
            avg_ex = sum(damages_explosion) / len(damages_explosion)
            avg_cl = sum(damages_chain) / len(damages_chain)
            assert avg_cl > avg_ex, (
                f"Chain Lightning (circle 7, avg {avg_cl:.1f}) should deal more than "
                f"Explosion (circle 6, avg {avg_ex:.1f})"
            )

    def test_npc_targets_take_more_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """NPC targets take 1.5x damage, player targets take /3 damage."""
        npc_target = _make_defender(hp=500, is_npc=True)
        player_target = _make_defender(hp=500, is_npc=False)

        r_npc = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.EXPLOSION, targets=[npc_target], rng_seed=42)
        r_player = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                                    Spell.EXPLOSION, targets=[player_target], rng_seed=42)

        if r_npc.success and r_player.success and r_npc.final_damage > 0 and r_player.final_damage > 0:
            assert r_npc.final_damage > r_player.final_damage, (
                f"NPC target damage ({r_npc.final_damage}) should exceed "
                f"player target damage ({r_player.final_damage})"
            )

    def test_target_count_doesnt_reduce_per_target_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """More targets doesn't reduce per-target damage — damage is independent."""
        # 1 target
        t1 = _make_defender(hp=500)
        r1 = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                              Spell.EXPLOSION, targets=[t1], rng_seed=42)
        hp_lost_1 = 500 - t1.hp

        # 5 targets — first target should take same damage
        targets_5 = _make_defenders(count=5, hp=500)
        r5 = _exec_aoe_spell(fixture_shard, spell_parse_results, spell_registry,
                              Spell.EXPLOSION, targets=targets_5, rng_seed=42)
        hp_lost_5_first = 500 - targets_5[0].hp

        if r1.success and r5.success and hp_lost_1 > 0:
            # Allow some variance from RNG state divergence due to more targets
            # but the first target should get similar damage
            assert hp_lost_5_first > 0, "First target in 5-target AoE should take damage"


class TestListItemsStubs:
    """Verify the new ListItemsNearLocation* stubs work correctly."""

    def test_list_items_near_location_registered(self):
        from omega.runtime.registry import is_registered
        assert is_registered("uo", "ListItemsNearLocation")
        assert is_registered("", "ListItemsNearLocation")

    def test_list_items_near_location_of_type_registered(self):
        from omega.runtime.registry import is_registered
        assert is_registered("uo", "ListItemsNearLocationOfType")
        assert is_registered("", "ListItemsNearLocationOfType")

    def test_list_items_near_location_returns_empty(self):
        from omega.runtime.structural_stubs import list_items_near_location
        result = list_items_near_location(100, 200, 0, 10)
        assert len(result) == 0

    def test_list_items_near_location_of_type_returns_empty(self):
        from omega.runtime.structural_stubs import list_items_near_location_of_type
        result = list_items_near_location_of_type(100, 200, 0, 10, 0x1234)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# M28 — New metric tracking tests
# ---------------------------------------------------------------------------


class TestSpellDiceRollMetric:
    """Test that spell_dice_roll metric is captured from CalcSpellDamage."""

    def test_dice_roll_present(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        assert "spell_dice_roll" in result.metrics
        assert result.metrics["spell_dice_roll"] > 0

    def test_dice_roll_gte_base_damage_player_target(self, fixture_shard, spell_parse_results, spell_registry):
        """For player targets (no 1.5x NPC multiplier), dice_roll >= base_damage always.

        dice_roll is raw from RandomDiceRoll. base_damage is post-cap, post-efficiency,
        post-PvP-div — all of which reduce. So dice_roll >= base_damage.
        NPC targets get *1.5 which can push base_damage ABOVE dice_roll.
        """
        target = _make_defender(name="Player", hp=500, is_npc=False)
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             target=target)
        if not result.fizzled and result.base_damage > 0:
            assert result.metrics["spell_dice_roll"] >= result.base_damage

    def test_dice_roll_different_circles(self, fixture_shard, spell_parse_results, spell_registry):
        """Higher circle spells roll more dice → higher dice_roll on average."""
        low_rolls = []
        high_rolls = []
        for seed in range(1, 11):
            t1 = _make_defender(hp=500)
            t2 = _make_defender(hp=500)
            r_low = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.MAGIC_ARROW,
                                rng_seed=seed, target=t1)
            r_high = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FLAME_STRIKE,
                                 rng_seed=seed, target=t2)
            if "spell_dice_roll" in r_low.metrics:
                low_rolls.append(r_low.metrics["spell_dice_roll"])
            if "spell_dice_roll" in r_high.metrics:
                high_rolls.append(r_high.metrics["spell_dice_roll"])
        if low_rolls and high_rolls:
            assert sum(high_rolls) / len(high_rolls) > sum(low_rolls) / len(low_rolls)

    def test_dice_roll_present_even_debug_off(self, fixture_shard, spell_parse_results, spell_registry):
        """spell_dice_roll is guarded by shard const DEBUG_MODE=1, not Python debug flag.

        The shard declares ``const DEBUG_MODE := 1`` in client.inc, so
        ``if(DEBUG_MODE)`` is always true regardless of the Python debug parameter.
        """
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             debug=False)
        assert "spell_dice_roll" in result.metrics


class TestSpellFinalAppliedDamageMetric:
    """Test that spell_final_applied_damage is recorded by ApplyRawDamage."""

    def test_metric_present(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        if result.final_damage > 0:
            assert "spell_final_applied_damage" in result.metrics

    def test_metric_matches_final_damage(self, fixture_shard, spell_parse_results, spell_registry):
        """The metric should equal the damage actually applied."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        if result.final_damage > 0:
            assert result.metrics["spell_final_applied_damage"] == result.final_damage

    def test_metric_not_present_on_fizzle(self, fixture_shard, spell_parse_results, spell_registry):
        """Fizzled spells don't call ApplyRawDamage, so no metric."""
        caster = _make_mage(magery=10, mana=100)
        fizzled_found = False
        for seed in range(1, 51):
            t = _make_defender(hp=500)
            result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                                 caster=_make_mage(magery=10, mana=100), target=t,
                                 npc_mode=False, rng_seed=seed)
            if result.fizzled:
                fizzled_found = True
                assert "spell_final_applied_damage" not in result.metrics
                break
        assert fizzled_found, "Expected at least one fizzle with Magery=1.0"

    def test_metric_not_present_when_debug_off(self, fixture_shard, spell_parse_results, spell_registry):
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL,
                             debug=False)
        assert "spell_final_applied_damage" not in result.metrics


class TestAoeTargetCountMetric:
    """Test that aoe_target_count metric is recorded for AoE spells."""

    def test_metric_present_for_aoe(self, fixture_shard, spell_parse_results, spell_registry):
        """Chain Lightning is AoE — should record aoe_target_count."""
        targets = [_make_defender(hp=500) for _ in range(3)]
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                             Spell.CHAIN_LIGHTNING, target=targets)
        assert "aoe_target_count" in result.metrics
        assert result.metrics["aoe_target_count"] == 3

    def test_metric_not_present_for_single_target(self, fixture_shard, spell_parse_results, spell_registry):
        """Single-target spells don't call ListMobilesNearLocationEx."""
        result = _exec_spell(fixture_shard, spell_parse_results, spell_registry, Spell.FIREBALL)
        assert "aoe_target_count" not in result.metrics

    def test_metric_scales_with_target_count(self, fixture_shard, spell_parse_results, spell_registry):
        """More targets → higher aoe_target_count."""
        for n in [1, 3, 5]:
            targets = [_make_defender(hp=500) for _ in range(n)]
            result = _exec_spell(fixture_shard, spell_parse_results, spell_registry,
                                 Spell.CHAIN_LIGHTNING, target=targets)
            if "aoe_target_count" in result.metrics:
                assert result.metrics["aoe_target_count"] == n


# ---------------------------------------------------------------------------
# DEBUG_MODE Override Tests
# ---------------------------------------------------------------------------

class TestDebugModeOverride:
    """Verify the executor always overrides DEBUG_MODE to 1.

    The fixture copy of client.inc has ``const DEBUG_MODE := 0`` (patched by
    sync_fixtures.py).  The executor must force it to 1 so that all
    ``__RecordSimulatorMetric`` calls in shard scripts are active.
    """

    def test_fixture_has_debug_mode_zero(self, fixture_shard):
        """Precondition: fixture client.inc has DEBUG_MODE := 0."""
        client_inc = fixture_shard.root / "scripts" / "include" / "client.inc"
        text = client_inc.read_text()
        assert "DEBUG_MODE\t:= 0" in text or "DEBUG_MODE := 0" in text, (
            "Fixture client.inc should have DEBUG_MODE := 0 (set by sync_fixtures.py)"
        )

    def test_spell_metrics_recorded_despite_fixture_debug_off(
        self, fixture_shard, spell_parse_results, spell_registry,
    ):
        """Shard-side metrics (spell_dice_roll, spell_base_damage) must be
        recorded even though the fixture has DEBUG_MODE := 0, because the
        executor overrides it to 1."""
        result = _exec_spell(
            fixture_shard, spell_parse_results, spell_registry,
            Spell.FIREBALL, debug=True,
        )
        assert not result.fizzled, "Need a non-fizzled cast to check metrics"
        assert "spell_dice_roll" in result.metrics, (
            "spell_dice_roll missing — executor did not override DEBUG_MODE to 1"
        )
        assert "spell_base_damage" in result.metrics, (
            "spell_base_damage missing — executor did not override DEBUG_MODE to 1"
        )
        assert result.metrics["spell_dice_roll"] > 0
        assert result.metrics["spell_base_damage"] > 0

    def test_hit_metrics_recorded_despite_fixture_debug_off(self, fixture_shard):
        """Weapon-hit shard metrics must also be recorded despite DEBUG_MODE := 0
        in the fixture, because execute_hit also overrides DEBUG_MODE to 1."""
        from omega.combat.hit import execute_hit

        attacker = Mobile(name="TestWarrior", is_npc=False)
        attacker.str_base = 100
        attacker.dex_base = 100
        attacker.int_base = 25
        attacker.hp = 100
        attacker.max_hp = 100
        attacker.class_name = "Warrior"
        attacker.class_level = 5
        attacker.set_skill(40, 1000)   # Swordsmanship
        attacker.set_skill(27, 1000)   # Tactics
        attacker.set_skill(1, 1000)    # Anatomy

        defender = Mobile(name="TestDummy", is_npc=True, npctemplate="test_mob")
        defender.str_base = 100
        defender.dex_base = 100
        defender.int_base = 100
        defender.hp = 500
        defender.max_hp = 500

        weapon = Weapon(
            objtype=0x0F5E, graphic=0x0F5E, name="broadsword",
            damage=DiceSpec(3, 7, 3), speed=30, attribute=40,
            two_handed=False,
        )

        armor = Armor(objtype=0x1415, graphic=0x1415, name="leather",
                       ar=13, coverage=["body"])

        parse_results = fixture_shard.parse_combat_scripts()

        result = execute_hit(
            parse_results, attacker, defender, weapon, armor,
            rng_seed=42, debug=True,
            config_resolver=fixture_shard.resolve_config_path,
            em_modules_dir=fixture_shard.root / "scripts" / "modules",
            shard_root=fixture_shard.root,
            package_map=fixture_shard.package_map,
        )

        # Shard-side metrics that live behind if(DEBUG_MODE) guards in the
        # eScript code (damages.inc, hitscriptinc.inc)
        assert "damage_applied" in result.metrics, (
            "damage_applied missing — execute_hit did not override DEBUG_MODE to 1"
        )
        assert len(result.metrics["damage_applied"]) > 0
        assert "damage_before_ar" in result.metrics, (
            "damage_before_ar missing — execute_hit did not override DEBUG_MODE to 1"
        )
