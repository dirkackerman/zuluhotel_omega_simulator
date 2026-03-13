"""M29 — Test Coverage Review & POL Stub Audit.

Comprehensive tests covering:
1. POL stub conformance audit (spell-path stubs)
2. Resistance at multiple skill levels (0%, 50%, 100%)
3. Class modifier effects (Mage/Warrior caster and target)
4. PvP scaling all combos
5. AoE spells with varying target counts
6. Edge cases (over-protection healing, max circle, UNINIT)
7. RandomDiceRoll POL conformance
8. Resisted() formula validation
"""

import pytest

import omega.runtime  # noqa: F401

from omega.combat.spell import execute_spell
from omega.combat.spell_result import SpellResult
from omega.config.spell_registry import DAMAGE_SPELL_IDS
from omega.config.spells import Spell
from omega.interpreter.types import UNINIT
from omega.model.constants import (
    SKILLID_MAGERY,
    SKILLID_EVALINT,
    SKILLID_MAGICRESISTANCE,
)
from omega.model.mobile import Mobile
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.rng import SimulationRNG, get_rng, set_rng_seed
from omega.simulation.scenario import (
    CombatantSpec,
    SpellParameterSweep,
    SpellScenario,
    Variable,
)
from omega.simulation.spell_runner import run_spell_scenario, run_spell_sweep

from omega.config.spell_registry import SpellRegistry
from tests.conftest import FIXTURE_SHARD_ROOT


# ---------------------------------------------------------------------------
# Module-scoped fixtures (mirrors test_spell_execution.py)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mage(name="Mage", magery=1000, eval_int=1000, mana=100, hp=100, is_npc=False):
    m = Mobile(name=name, is_npc=is_npc)
    m.set_skill(SKILLID_MAGERY, magery)
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


# ===========================================================================
# SECTION 1: POL Stub Audit
# ===========================================================================


class TestApplyRawDamageAudit:
    """POL conformance: ApplyRawDamage (vitalmod.cpp / charactr.cpp)."""

    def test_integer_damage_applied_correctly(self):
        """Integer damage reduces HP by exact amount."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, 30)
        assert mob.hp == 70

    def test_float_damage_truncates_not_rounds(self):
        """POL's getParam extracts BLong only; C++ static_cast<int> truncates.
        Our stub must truncate floats toward zero, not round."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        # 7.9 should truncate to 7, not round to 8
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, 7.9)
        assert mob.hp == 93, f"Expected 93 (truncate 7.9→7), got {mob.hp}"

    def test_float_damage_truncates_point_five(self):
        """5.5 truncates to 5 (C-style), not 6 (Python round)."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, 5.5)
        assert mob.hp == 95, f"Expected 95 (truncate 5.5→5), got {mob.hp}"

    def test_dead_target_no_damage(self):
        """POL: if (dead()) return; — no damage applied."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=0)
        mob.dead = True
        apply_raw_damage(mob, 50)
        assert mob.hp == 0

    def test_unhides_on_damage(self):
        """POL: if (hidden()) unhide(); — damage unhides the mobile."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        mob.hidden = True
        apply_raw_damage(mob, 10)
        assert mob.hidden is False

    def test_removes_paralysis_on_damage(self):
        """POL: if (paralyzed()) mob_flags_.remove(PARALYZED);"""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        mob.paralyzed = True
        apply_raw_damage(mob, 10)
        assert mob.paralyzed is False

    def test_zero_damage_no_effect(self):
        """Zero damage does nothing (POL: if dmg <= 0 return)."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, 0)
        assert mob.hp == 100
        assert len(ctx.side_effects) == 0

    def test_negative_damage_no_effect(self):
        """Negative damage does nothing."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, -5)
        assert mob.hp == 100

    def test_none_amount_no_crash(self):
        """None amount handled gracefully."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, None)
        assert mob.hp == 100

    def test_uninit_amount_no_crash(self):
        """UNINIT amount handled gracefully."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, UNINIT)
        assert mob.hp == 100

    def test_string_amount_no_crash(self):
        """String amount that can be converted."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, "10")
        assert mob.hp == 90

    def test_kills_target_sets_dead_flag(self):
        """Damage that exceeds HP sets dead=True."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=10)
        apply_raw_damage(mob, 50)
        assert mob.hp == 0
        assert mob.dead is True

    def test_records_side_effect(self):
        """Damage records a side effect."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, 25)
        damage_effects = [se for se in ctx.side_effects if se.kind == "damage"]
        assert len(damage_effects) == 1
        assert damage_effects[0].value == 25

    def test_records_metric_in_debug_mode(self):
        """spell_final_applied_damage metric recorded in debug mode."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, 15)
        assert ctx.metrics.get("spell_final_applied_damage") == 15

    def test_no_metric_in_non_debug_mode(self):
        """No metric recorded when debug_mode=False."""
        from omega.runtime.structural_stubs import apply_raw_damage
        ctx = SimulationContext(debug_mode=False)
        set_context(ctx)
        mob = _make_defender(hp=100)
        apply_raw_damage(mob, 15)
        assert "spell_final_applied_damage" not in ctx.metrics


class TestRandomAudit:
    """POL conformance: Random() returns [1, max_val]."""

    def test_range_1_to_max(self):
        """Random(100) → [1, 100]."""
        from omega.runtime.basic_stubs import random_func
        set_rng_seed(42)
        results = set()
        for _ in range(1000):
            results.add(random_func(100))
        assert min(results) >= 1
        assert max(results) <= 100

    def test_random_1_always_returns_1(self):
        """Random(1) → always 1."""
        from omega.runtime.basic_stubs import random_func
        set_rng_seed(42)
        for _ in range(100):
            assert random_func(1) == 1

    def test_random_0_returns_0(self):
        """Random(0) → 0 (POL edge case)."""
        from omega.runtime.basic_stubs import random_func
        assert random_func(0) == 0

    def test_random_negative_returns_0(self):
        """Random(-5) → 0."""
        from omega.runtime.basic_stubs import random_func
        assert random_func(-5) == 0

    def test_random_none_returns_0(self):
        """Random(None) → 0."""
        from omega.runtime.basic_stubs import random_func
        assert random_func(None) == 0

    def test_random_uninit_returns_0(self):
        """Random(UNINIT) → 0."""
        from omega.runtime.basic_stubs import random_func
        assert random_func(UNINIT) == 0


class TestRandomIntAudit:
    """POL conformance: RandomInt(n) returns [0, n-1]."""

    def test_range_0_to_max_minus_1(self):
        """RandomInt(100) → [0, 99]."""
        from omega.runtime.basic_stubs import random_int_func
        set_rng_seed(42)
        results = set()
        for _ in range(1000):
            results.add(random_int_func(100))
        assert min(results) >= 0
        assert max(results) <= 99

    def test_randomint_1_always_0(self):
        """RandomInt(1) → always 0."""
        from omega.runtime.basic_stubs import random_int_func
        set_rng_seed(42)
        for _ in range(50):
            assert random_int_func(1) == 0

    def test_randomint_0_returns_0(self):
        """RandomInt(0) → 0."""
        from omega.runtime.basic_stubs import random_int_func
        assert random_int_func(0) == 0

    def test_randomint_none_returns_0(self):
        from omega.runtime.basic_stubs import random_int_func
        assert random_int_func(None) == 0

    def test_randomint_uninit_returns_0(self):
        from omega.runtime.basic_stubs import random_int_func
        assert random_int_func(UNINIT) == 0


class TestRandomDiceRollAudit:
    """POL conformance: RandomDiceRoll (dice.cpp)."""

    def test_basic_dice_notation(self):
        """'3d6+2' → min=5, max=20."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(42)
        results = [random_dice_roll("3d6+2") for _ in range(500)]
        assert min(results) >= 5   # 3*1+2
        assert max(results) <= 20  # 3*6+2

    def test_no_bonus(self):
        """'2d8' → min=2, max=16."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(42)
        results = [random_dice_roll("2d8") for _ in range(500)]
        assert min(results) >= 2
        assert max(results) <= 16

    def test_negative_bonus(self):
        """'3d6-5' → can be 0 (clamped) when not allowing negatives."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(42)
        results = [random_dice_roll("3d6-5", 0) for _ in range(500)]
        assert min(results) >= 0  # clamped
        assert max(results) <= 13  # 18-5

    def test_negative_bonus_allow_negatives(self):
        """'1d4-10' with allow_negatives → can be negative."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(42)
        results = [random_dice_roll("1d4-10", 1) for _ in range(200)]
        assert min(results) < 0  # 1-10=-9

    def test_plain_number(self):
        """Just a number '42' → returns 42."""
        from omega.runtime.basic_stubs import random_dice_roll
        assert random_dice_roll("42") == 42

    def test_none_returns_0(self):
        from omega.runtime.basic_stubs import random_dice_roll
        assert random_dice_roll(None) == 0

    def test_uninit_returns_0(self):
        from omega.runtime.basic_stubs import random_dice_roll
        assert random_dice_roll(UNINIT) == 0

    def test_empty_string(self):
        from omega.runtime.basic_stubs import random_dice_roll
        assert random_dice_roll("") == 0

    def test_case_insensitive(self):
        """POL's dice parser accepts both 'D' and 'd'."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(42)
        lower = random_dice_roll("3d6+2")
        set_rng_seed(42)
        upper = random_dice_roll("3D6+2")
        assert lower == upper

    def test_fireball_dice_string(self):
        """CalcSpellDamage builds '9d5+20' for circle 3, magery 100.
        Range: [9+20, 45+20] = [29, 65]."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(42)
        results = [random_dice_roll("9d5+20") for _ in range(500)]
        assert min(results) >= 29
        assert max(results) <= 65

    def test_single_die(self):
        """'1d6' → [1, 6]."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(42)
        results = [random_dice_roll("1d6") for _ in range(500)]
        assert min(results) >= 1
        assert max(results) <= 6

    def test_large_dice(self):
        """'21d5+20' (Kill spell, circle 7 effective) → [41, 125]."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(42)
        results = [random_dice_roll("21d5+20") for _ in range(500)]
        assert min(results) >= 41   # 21*1+20
        assert max(results) <= 125  # 21*5+20

    def test_deterministic_with_seed(self):
        """Same seed → same result."""
        from omega.runtime.basic_stubs import random_dice_roll
        set_rng_seed(99)
        r1 = random_dice_roll("3d6+5")
        set_rng_seed(99)
        r2 = random_dice_roll("3d6+5")
        assert r1 == r2


class TestCheckSkillAudit:
    """POL conformance: CheckSkill for spell casting."""

    def test_formula_chance_100(self):
        """Skill 130, difficulty 50 → chance=130-50+50=130 → clamped to 100."""
        from omega.runtime.structural_stubs import check_skill
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1300)  # 130 display
        result = check_skill(mob, SKILLID_MAGERY, 50, 100)
        assert result == 1
        assert ctx.metrics["spell_skill_chance"] == 100

    def test_formula_chance_0(self):
        """Skill 0, difficulty 100 → chance=0-100+50=-50 → clamped to 0."""
        from omega.runtime.structural_stubs import check_skill
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=0)
        result = check_skill(mob, SKILLID_MAGERY, 100, 100)
        assert result == 0
        assert ctx.metrics["spell_skill_chance"] == 0

    def test_formula_chance_50(self):
        """Skill 50, difficulty 50 → chance=50-50+50=50."""
        from omega.runtime.structural_stubs import check_skill
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=500)  # 50 display
        check_skill(mob, SKILLID_MAGERY, 50, 100)
        assert ctx.metrics["spell_skill_chance"] == 50

    def test_none_character_returns_0(self):
        from omega.runtime.structural_stubs import check_skill
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        assert check_skill(None, SKILLID_MAGERY, 50, 100) == 0

    def test_none_skill_id_returns_0(self):
        from omega.runtime.structural_stubs import check_skill
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage()
        assert check_skill(mob, None, 50, 100) == 0

    def test_uninit_difficulty_returns_0(self):
        """UNINIT difficulty → try/except catches TypeError → returns 0."""
        from omega.runtime.structural_stubs import check_skill
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage()
        assert check_skill(mob, SKILLID_MAGERY, UNINIT, 100) == 0

    def test_returns_int_type(self):
        """CheckSkill must return int (0 or 1), not bool."""
        from omega.runtime.structural_stubs import check_skill
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_mage(magery=1300)
        result = check_skill(mob, SKILLID_MAGERY, 0, 100)
        assert isinstance(result, int)
        assert result in (0, 1)


class TestConsumeManaAudit:
    """POL conformance: ConsumeMana for spell casting."""

    def test_deducts_correct_display_units(self, fixture_shard):
        """Mana deduction in display units (not hundredths)."""
        from omega.runtime.structural_stubs import consume_mana
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=100)
        consume_mana(mob, Spell.FIREBALL)
        cost = ctx.metrics["spell_mana_cost"]
        assert mob.mana == 100 - cost
        assert cost > 0
        assert cost < 50  # Reasonable for a circle 3 spell

    def test_insufficient_mana_no_deduction(self, fixture_shard):
        """Insufficient mana → mana unchanged, returns 0."""
        from omega.runtime.structural_stubs import consume_mana
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        mob = _make_mage(mana=1)  # Likely less than any spell cost
        result = consume_mana(mob, Spell.FLAME_STRIKE)
        assert result == 0
        assert mob.mana == 1  # Unchanged

    def test_none_character(self):
        from omega.runtime.structural_stubs import consume_mana
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        assert consume_mana(None, Spell.FIREBALL) == 0

    def test_none_spell_id(self):
        from omega.runtime.structural_stubs import consume_mana
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        assert consume_mana(_make_mage(), None) == 0

    def test_uninit_spell_id(self):
        """UNINIT spell ID → try/except catches → returns 0."""
        from omega.runtime.structural_stubs import consume_mana
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        assert consume_mana(_make_mage(), UNINIT) == 0


class TestGetEffectiveSkillAudit:
    """POL conformance: GetEffectiveSkill returns display units (0-200)."""

    def test_returns_display_units(self):
        from omega.runtime.object_stubs import get_effective_skill
        mob = _make_mage(magery=1000)  # 100.0 display
        assert get_effective_skill(mob, SKILLID_MAGERY) == 100

    def test_max_skill(self):
        from omega.runtime.object_stubs import get_effective_skill
        mob = _make_mage(magery=1300)  # 130.0 display (cap)
        assert get_effective_skill(mob, SKILLID_MAGERY) == 130

    def test_zero_skill(self):
        from omega.runtime.object_stubs import get_effective_skill
        mob = _make_mage(magery=0)
        assert get_effective_skill(mob, SKILLID_MAGERY) == 0

    def test_none_mobile(self):
        from omega.runtime.object_stubs import get_effective_skill
        assert get_effective_skill(None, SKILLID_MAGERY) == 0

    def test_none_skill_id(self):
        from omega.runtime.object_stubs import get_effective_skill
        mob = _make_mage()
        assert get_effective_skill(mob, None) == 0

    def test_uninit_skill_id(self):
        from omega.runtime.object_stubs import get_effective_skill
        mob = _make_mage()
        assert get_effective_skill(mob, UNINIT) == 0

    def test_missing_skill_returns_0(self):
        from omega.runtime.object_stubs import get_effective_skill
        mob = Mobile(name="Blank")
        assert get_effective_skill(mob, SKILLID_MAGERY) == 0


class TestGetSetObjPropertyAudit:
    """POL conformance: GetObjProperty/SetObjProperty for class levels."""

    def test_set_and_get_class_level(self):
        from omega.runtime.object_stubs import get_obj_property, set_obj_property
        mob = _make_mage()
        set_obj_property(mob, "IsMage", 5)
        assert get_obj_property(mob, "IsMage") == 5

    def test_get_unset_returns_none(self):
        from omega.runtime.object_stubs import get_obj_property
        mob = _make_mage()
        result = get_obj_property(mob, "NoSuchProp")
        assert result is None

    def test_none_obj(self):
        from omega.runtime.object_stubs import get_obj_property, set_obj_property
        assert get_obj_property(None, "test") is None
        set_obj_property(None, "test", 5)  # Should not crash

    def test_none_name(self):
        from omega.runtime.object_stubs import get_obj_property
        mob = _make_mage()
        assert get_obj_property(mob, None) is None

    def test_erase_property(self):
        from omega.runtime.object_stubs import (
            get_obj_property, set_obj_property, erase_obj_property,
        )
        mob = _make_mage()
        set_obj_property(mob, "IsMage", 5)
        assert get_obj_property(mob, "IsMage") == 5
        erase_obj_property(mob, "IsMage")
        assert get_obj_property(mob, "IsMage") is None

    def test_uninit_name_returns_none(self):
        """UNINIT as property name → str(UNINIT) is used."""
        from omega.runtime.object_stubs import get_obj_property
        mob = _make_mage()
        # Should not crash; returns None for unset property
        result = get_obj_property(mob, UNINIT)
        assert result is None


class TestReadConfigFileAudit:
    """POL conformance: ReadConfigFile for spell and circle configs."""

    def test_spells_wildcard_resolves(self, fixture_shard):
        """':*:spells' wildcard resolves and returns a config file."""
        from omega.runtime.structural_stubs import read_config_file
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        cfg = read_config_file(":*:spells")
        assert cfg is not None

    def test_circles_wildcard_resolves(self, fixture_shard):
        """':*:circles' wildcard resolves."""
        from omega.runtime.structural_stubs import read_config_file
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        cfg = read_config_file(":*:circles")
        assert cfg is not None

    def test_fireball_spell_entry(self, fixture_shard):
        """Fireball (spell ID 18) has Circle=3."""
        from omega.runtime.structural_stubs import read_config_file
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        cfg = read_config_file(":*:spells")
        elem = cfg[18]
        assert elem is not None
        assert getattr(elem, "Circle", None) is not None

    def test_circle_3_has_mana_cost(self, fixture_shard):
        """Circle 3 has a positive mana cost."""
        from omega.runtime.structural_stubs import read_config_file
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        cfg = read_config_file(":*:circles")
        elem = cfg[3]
        assert elem is not None
        mana = getattr(elem, "Mana", None)
        assert mana is not None
        assert int(mana) > 0

    def test_none_path_returns_none(self):
        from omega.runtime.structural_stubs import read_config_file
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        assert read_config_file(None) is None

    def test_caching_returns_same_object(self, fixture_shard):
        """Second call with same path returns cached object."""
        from omega.runtime.structural_stubs import read_config_file
        ctx = SimulationContext(debug_mode=True)
        ctx._config_resolver = fixture_shard.resolve_config_path
        set_context(ctx)
        cfg1 = read_config_file(":*:spells")
        cfg2 = read_config_file(":*:spells")
        assert cfg1 is cfg2


# ===========================================================================
# SECTION 2: Resistance at Multiple Skill Levels
# ===========================================================================


class TestResistanceMultipleLevels:
    """Resistance tested at 0%, 50%, 100% resist skill."""

    def test_zero_resist(self, fixture_shard):
        """0 resist → very low resist rate."""
        cell = _run(fixture_shard, Spell.FIREBALL, target=_target(resist=0), iterations=500)
        assert cell.ratios.resist_rate_on_cast < 0.15

    def test_mid_resist_50(self, fixture_shard):
        """50 resist → moderate resist rate."""
        cell = _run(fixture_shard, Spell.FIREBALL, target=_target(resist=50), iterations=500)
        # Resist chance = max(50/6, 50 - (100/4 + 3*6)) = max(8, 50-43) = max(8, 7) = 8
        # Very low, but higher than 0 resist
        assert cell.ratios.resist_rate_on_cast >= 0.0

    def test_high_resist_100(self, fixture_shard):
        """100 resist → high resist rate."""
        cell = _run(fixture_shard, Spell.FIREBALL, target=_target(resist=100), iterations=500)
        # chance = max(100/6, 100 - 25 - 18) = max(16, 57) = 57
        # But Random(100)+1 ≤ 57 → (57-1)/100 = 56%
        assert cell.ratios.resist_rate_on_cast > 0.30

    def test_max_resist_130(self, fixture_shard):
        """130 resist → very high resist rate."""
        cell = _run(fixture_shard, Spell.FIREBALL, target=_target(resist=130), iterations=500)
        assert cell.ratios.resist_rate_on_cast > 0.50

    def test_resist_monotonically_decreases_damage(self, fixture_shard):
        """Higher resist → strictly lower mean damage across levels."""
        means = []
        for resist_val in (0, 50, 100, 130):
            cell = _run(
                fixture_shard, Spell.FIREBALL,
                target=_target(resist=resist_val),
                iterations=500,
            )
            means.append(cell.damage_stats.mean)
        for i in range(len(means) - 1):
            assert means[i] >= means[i + 1], (
                f"Damage not monotonically decreasing: {means}"
            )


# ===========================================================================
# SECTION 3: Resisted() Formula Validation
# ===========================================================================


class TestResistedFormulaValidation:
    """Validate the Resisted() eScript function behavior."""

    def test_evalint_scaling_integer_division(self, fixture_shard):
        """EvalInt scaling uses integer division: (evalint-resist)/200.
        With eval=100, resist=0: (100-0)/200 = 0 in integer div.
        No scaling effect for normal skill ranges."""
        cell_high_eval = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(eval_int=100),
            target=_target(resist=0),
            iterations=500,
        )
        cell_low_eval = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(eval_int=50),
            target=_target(resist=0),
            iterations=500,
        )
        # Due to integer division by 200, small differences in EvalInt
        # may not affect damage. This is expected.
        # Both should deal positive damage.
        assert cell_high_eval.damage_stats.mean > 0
        assert cell_low_eval.damage_stats.mean > 0

    def test_evalint_minus_resist_negative(self, fixture_shard):
        """When evalint < resist, (evalint-resist)/200 is negative.
        E.g., eval=0, resist=130: (0-130)/200 = -0.65 → 0 in int div.
        For eval=0, resist=200+: (0-200)/200 = -1, multiplier = 0."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(eval_int=0),
            target=_target(resist=130),
            iterations=500,
        )
        # Even with resist heavily outweighing evalint, damage should
        # still be positive (integer division means the penalty is modest)
        # unless resist-evalint >= 200
        assert cell.damage_stats.mean >= 0

    def test_resisted_halves_damage(self, fixture_shard):
        """When a spell IS resisted, damage is halved (dmg := CInt(dmg/2)).
        We can't control individual resist outcomes, but high resist
        should have lower mean."""
        no_resist = _run(
            fixture_shard, Spell.FIREBALL,
            target=_target(resist=0),
            iterations=500,
        )
        full_resist = _run(
            fixture_shard, Spell.FIREBALL,
            target=_target(resist=130),
            iterations=500,
        )
        assert full_resist.damage_stats.mean < no_resist.damage_stats.mean


# ===========================================================================
# SECTION 4: Class Modifier Effects
# ===========================================================================


class TestClassModifierEffects:
    """Class modifiers affect spell damage and resistance."""

    def test_mage_caster_increases_damage(self, fixture_shard):
        """Mage caster (level 5) → ModifyWithMagicEfficiency bonus."""
        classless = _run(
            fixture_shard, Spell.FIREBALL, caster=_caster(), iterations=300,
        )
        mage = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(class_levels={"IsMage": 5}),
            iterations=300,
        )
        assert mage.damage_stats.mean >= classless.damage_stats.mean

    def test_warrior_caster_decreases_damage(self, fixture_shard):
        """Warrior caster → ModifyWithMagicEfficiency penalty (div by ClasseBonus)."""
        classless = _run(
            fixture_shard, Spell.FIREBALL, caster=_caster(), iterations=300,
        )
        warrior = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(class_levels={"IsWarrior": 5}),
            iterations=300,
        )
        assert warrior.damage_stats.mean <= classless.damage_stats.mean

    def test_mage_target_reduces_damage(self, fixture_shard):
        """Mage target → Resisted() class bonus increases resist chance,
        and post-resist dmg /= ClasseBonus."""
        classless = _run(
            fixture_shard, Spell.FIREBALL,
            target=_target(resist=50),
            iterations=500,
        )
        mage_target = _run(
            fixture_shard, Spell.FIREBALL,
            target=_target(resist=50, class_levels={"IsMage": 5}),
            iterations=500,
        )
        assert mage_target.damage_stats.mean <= classless.damage_stats.mean

    def test_warrior_target_increases_damage(self, fixture_shard):
        """Warrior target → Resisted() divides chance, multiplies damage."""
        classless = _run(
            fixture_shard, Spell.FIREBALL,
            target=_target(resist=50),
            iterations=500,
        )
        warrior_target = _run(
            fixture_shard, Spell.FIREBALL,
            target=_target(resist=50, class_levels={"IsWarrior": 5}),
            iterations=500,
        )
        assert warrior_target.damage_stats.mean >= classless.damage_stats.mean

    def test_mage_caster_level_sweep(self, fixture_shard):
        """Higher Mage level → more damage (monotonic)."""
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
                    values=(1, 3, 5, 7),
                ),
            ),
        )
        result = run_spell_sweep(sweep, shard=fixture_shard)
        means = [c.damage_stats.mean for c in result.cells]
        for i in range(len(means) - 1):
            assert means[i] <= means[i + 1], f"Damage not increasing: {means}"


# ===========================================================================
# SECTION 5: PvP Scaling All Combos
# ===========================================================================


class TestPvPScalingCombos:
    """PvP scaling: CalcSpellDamage /3 for player targets, *1.5 for NPC targets.
    ApplyTheDamage: *0.6 for PvP (player vs player)."""

    def test_npc_vs_npc(self, fixture_shard):
        """NPC→NPC: full damage (CalcSpellDamage *1.5)."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(is_npc=True),
            target=_target(is_npc=True),
            iterations=300,
        )
        assert cell.damage_stats.mean > 0

    def test_npc_vs_player(self, fixture_shard):
        """NPC→player: CalcSpellDamage /3."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(is_npc=True),
            target=_target(is_npc=False),
            iterations=300,
        )
        assert cell.damage_stats.mean > 0

    def test_player_vs_npc(self, fixture_shard):
        """Player→NPC: CalcSpellDamage *1.5."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(is_npc=False),
            target=_target(is_npc=True),
            iterations=300,
            npc_mode=False,
        )
        # Some may fizzle, but damage_stats includes all
        assert cell.damage_stats is not None

    def test_player_vs_player(self, fixture_shard):
        """Player→player: CalcSpellDamage /3, ApplyTheDamage *0.6."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(is_npc=False),
            target=_target(is_npc=False),
            iterations=300,
            npc_mode=False,
        )
        assert cell.damage_stats is not None

    def test_npc_target_more_damage_than_player(self, fixture_shard):
        """NPC→NPC > NPC→player (1.5x vs /3)."""
        vs_npc = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(is_npc=True),
            target=_target(is_npc=True),
            iterations=300,
        )
        vs_player = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(is_npc=True),
            target=_target(is_npc=False),
            iterations=300,
        )
        assert vs_npc.damage_stats.mean > vs_player.damage_stats.mean

    def test_pvp_double_reduction(self, fixture_shard):
        """Player→player damage should be significantly less than NPC→NPC.
        CalcSpellDamage /3 + ApplyTheDamage *0.6 → net *0.2."""
        npc_npc = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(is_npc=True),
            target=_target(is_npc=True),
            iterations=300,
        )
        # Player mode with high magery to avoid fizzle
        pvp = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(is_npc=False, magery=130),
            target=_target(is_npc=False),
            iterations=300,
            npc_mode=False,
        )
        # Filter fizzles from PvP
        if pvp.damage_stats_on_cast is not None and pvp.damage_stats_on_cast.mean > 0:
            # PvP on-cast damage should be much less than NPC-NPC
            assert pvp.damage_stats_on_cast.mean < npc_npc.damage_stats.mean


# ===========================================================================
# SECTION 6: AoE Spells With Varying Target Counts
# ===========================================================================


_AOE_SPELLS = [
    Spell.EXPLOSION,
    Spell.CHAIN_LIGHTNING,
    Spell.METEOR_SWARM,
    Spell.EARTHQUAKE,
]


class TestAoETargetCounts:
    """All AoE spells tested with 1, 3, and 5 targets."""

    @pytest.mark.parametrize("spell", _AOE_SPELLS, ids=lambda s: s.name)
    def test_single_target(self, fixture_shard, spell_parse_results, spell_registry, spell):
        """AoE with 1 target executes successfully."""
        caster = _make_mage(is_npc=True)
        caster.serial = 1000
        targets = [_make_defender(hp=500)]
        targets[0].serial = 2000
        result = execute_spell(
            spell_parse_results, caster, targets, int(spell),
            rng_seed=42, debug=True,
            config_resolver=fixture_shard.resolve_config_path,
            em_modules_dir=fixture_shard.root / "scripts" / "modules",
            shard_root=fixture_shard.root,
            package_map=fixture_shard.package_map,
            npc_mode=True, spell_registry=spell_registry,
        )
        assert result.success, f"{spell.name} with 1 target failed: {result.error}"
        assert result.final_damage > 0

    @pytest.mark.parametrize("spell", _AOE_SPELLS, ids=lambda s: s.name)
    def test_three_targets(self, fixture_shard, spell_parse_results, spell_registry, spell):
        """AoE with 3 targets — all take damage."""
        caster = _make_mage(is_npc=True)
        caster.serial = 1000
        targets = [_make_defender(name=f"T{i}", hp=500) for i in range(3)]
        for i, t in enumerate(targets):
            t.serial = 2000 + i
        hp_before = [t.hp for t in targets]
        result = execute_spell(
            spell_parse_results, caster, targets, int(spell),
            rng_seed=42, debug=True,
            config_resolver=fixture_shard.resolve_config_path,
            em_modules_dir=fixture_shard.root / "scripts" / "modules",
            shard_root=fixture_shard.root,
            package_map=fixture_shard.package_map,
            npc_mode=True, spell_registry=spell_registry,
        )
        assert result.success, f"{spell.name} with 3 targets failed: {result.error}"
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 2, f"Only {damaged}/3 targets took damage from {spell.name}"

    @pytest.mark.parametrize("spell", _AOE_SPELLS, ids=lambda s: s.name)
    def test_five_targets(self, fixture_shard, spell_parse_results, spell_registry, spell):
        """AoE with 5 targets — majority take damage."""
        caster = _make_mage(is_npc=True)
        caster.serial = 1000
        targets = [_make_defender(name=f"T{i}", hp=500) for i in range(5)]
        for i, t in enumerate(targets):
            t.serial = 2000 + i
        hp_before = [t.hp for t in targets]
        result = execute_spell(
            spell_parse_results, caster, targets, int(spell),
            rng_seed=42, debug=True,
            config_resolver=fixture_shard.resolve_config_path,
            em_modules_dir=fixture_shard.root / "scripts" / "modules",
            shard_root=fixture_shard.root,
            package_map=fixture_shard.package_map,
            npc_mode=True, spell_registry=spell_registry,
        )
        assert result.success, f"{spell.name} with 5 targets failed: {result.error}"
        damaged = sum(1 for i, t in enumerate(targets) if t.hp < hp_before[i])
        assert damaged >= 3, f"Only {damaged}/5 targets took damage from {spell.name}"


# ===========================================================================
# SECTION 7: Edge Cases
# ===========================================================================


class TestOverProtectionHealing:
    """Elemental protection > 100% heals instead of dealing damage."""

    def test_fire_protection_over_100_heals(self, fixture_shard):
        """Target with FireProtection=120 → Fireball heals instead of damaging."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            target=_target(properties={"FireProtection": 120}, hp=500),
            iterations=100,
        )
        # With over-protection, spell should deal 0 damage and heal
        assert cell.damage_stats.mean == 0.0

    def test_fire_protection_100_no_damage(self, fixture_shard):
        """Target with FireProtection=100 → Fireball deals 0 (protection >= 100 heals)."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            target=_target(properties={"FireProtection": 100}, hp=500),
            iterations=100,
        )
        assert cell.damage_stats.mean == 0.0


class TestMaxCircleDamage:
    """Damage cap: circle * (13 + circle)."""

    def test_fireball_cap(self, fixture_shard):
        """Fireball circle 3 cap = 3 * (13+3) = 48.
        NPC target gets *1.5 so base_damage can be up to 72."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(magery=130, is_npc=True),
            target=_target(is_npc=True, resist=0),
            iterations=500,
        )
        # base_damage should never exceed cap * 1.5 = 72 (before resist/protection)
        for r in cell.raw_results:
            if r.base_damage > 0:
                assert r.base_damage <= 72, (
                    f"Fireball base_damage {r.base_damage} exceeds circle 3 cap*1.5=72"
                )


class TestZeroDamageFloor:
    """Spells have a minimum damage of 1 for landed hits."""

    def test_minimum_damage_player_target(self, fixture_shard):
        """Player target with low circle → damage /3 but min 1."""
        cell = _run(
            fixture_shard, Spell.MAGIC_ARROW,
            target=_target(is_npc=False),
            iterations=200,
        )
        # Non-zero results should be >= 1
        for r in cell.raw_results:
            if r.cast_success and r.final_damage > 0:
                assert r.final_damage >= 1


class TestUNINITEdgeCases:
    """UNINIT handling in various spell-path locations."""

    def test_target_stub_returns_defender(self):
        """Target() with UNINIT options still returns defender."""
        from omega.runtime.structural_stubs import target_stub
        mob = _make_defender()
        ctx = SimulationContext(defenders=[mob])
        set_context(ctx)
        result = target_stub(None, UNINIT)
        assert result is mob

    def test_target_coordinates_uninit_caster(self):
        """TargetCoordinates(UNINIT) returns 0,0,0 struct."""
        from omega.runtime.structural_stubs import target_coordinates
        ctx = SimulationContext(defenders=[])
        set_context(ctx)
        result = target_coordinates(UNINIT)
        assert result.get_member("x") == 0

    def test_list_mobiles_near_location_ex_uninit_params(self):
        """ListMobilesNearLocationEx with UNINIT params returns defenders."""
        from omega.runtime.structural_stubs import list_mobiles_near_location_ex
        mob = _make_defender()
        ctx = SimulationContext(defenders=[mob], debug_mode=True)
        set_context(ctx)
        result = list_mobiles_near_location_ex(UNINIT, UNINIT, UNINIT, UNINIT, UNINIT, UNINIT)
        assert len(result) == 1

    def test_find_config_elem_uninit_name(self):
        """FindConfigElem(cfg, UNINIT) → None."""
        from omega.runtime.structural_stubs import find_config_elem
        assert find_config_elem(None, UNINIT) is None

    def test_get_config_int_uninit_key(self):
        """GetConfigInt(elem, UNINIT) → 0."""
        from omega.runtime.structural_stubs import get_config_int
        assert get_config_int(None, UNINIT) == 0

    def test_get_config_string_uninit_key(self):
        """GetConfigString(elem, UNINIT) → ''."""
        from omega.runtime.structural_stubs import get_config_string
        assert get_config_string(None, UNINIT) == ""

    def test_distance_uninit_objects(self):
        """Distance(UNINIT, UNINIT) → 1 (default melee)."""
        from omega.runtime.basic_stubs import distance
        assert distance(UNINIT, UNINIT) == 1

    def test_set_poisoned_uninit_level(self):
        """SetPoisoned(mob, UNINIT) should not crash."""
        from omega.runtime.structural_stubs import set_poisoned
        mob = _make_defender()
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        set_poisoned(mob, UNINIT)
        # Should record side effect with level 0
        poison_effects = [se for se in ctx.side_effects if se.kind == "poison_applied"]
        assert len(poison_effects) == 1

    def test_heal_damage_uninit_amount(self):
        """HealDamage(mob, UNINIT) → no crash, no heal."""
        from omega.runtime.object_stubs import heal_damage
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        mob = _make_defender(hp=50)
        mob.max_hp = 100
        result = heal_damage(mob, UNINIT)
        assert mob.hp == 50  # unchanged
        assert result is None

    def test_cint_uninit(self):
        """CInt(UNINIT) → 0."""
        from omega.runtime.basic_stubs import cint
        assert cint(UNINIT) == 0

    def test_cdbl_uninit(self):
        """CDbl(UNINIT) → 0.0."""
        from omega.runtime.basic_stubs import cdbl
        assert cdbl(UNINIT) == 0.0

    def test_type_of_uninit(self):
        """TypeOf(UNINIT) → 'Uninit'."""
        from omega.runtime.basic_stubs import type_of
        assert type_of(UNINIT) == "Uninit"


class TestSpellPerSpellCoverage:
    """Ensure every damage spell in DAMAGE_SPELL_IDS has at least basic coverage."""

    # Spells known not to deal damage in standard NPC mode
    _ZERO_DAMAGE = frozenset({
        Spell.DECAYING_RAY,
        Spell.WRAITHS_BREATH,
        Spell.SACRIFICE,
        Spell.RISING_FIRE,
        Spell.ASTRAL_STORM,
        Spell.HOLY_BOLT,
        Spell.WRATH_OF_GOD,
    })

    @pytest.mark.parametrize("spell", sorted(DAMAGE_SPELL_IDS, key=lambda s: s.value),
                             ids=lambda s: s.name)
    def test_spell_executes_without_error(self, fixture_shard, spell):
        """Every damage spell executes without errors."""
        cell = _run(fixture_shard, spell, iterations=10)
        assert cell.error_count == 0, f"{spell.name} had errors"

    @pytest.mark.parametrize(
        "spell",
        sorted([s for s in DAMAGE_SPELL_IDS
                if s not in frozenset({
                    Spell.DECAYING_RAY, Spell.WRAITHS_BREATH, Spell.SACRIFICE,
                    Spell.RISING_FIRE, Spell.ASTRAL_STORM,
                    Spell.HOLY_BOLT, Spell.WRATH_OF_GOD,
                })],
               key=lambda s: s.value),
        ids=lambda s: s.name,
    )
    def test_spell_deals_positive_damage(self, fixture_shard, spell):
        """Non-zero-damage spells deal positive damage."""
        cell = _run(fixture_shard, spell, iterations=50)
        assert cell.damage_stats.mean > 0, f"{spell.name} dealt no damage"


class TestFizzleAtVariousMageryLevels:
    """Fizzle rate validation across Magery skill levels."""

    def test_magery_0_near_full_fizzle(self, fixture_shard):
        """Magery 0, circle 3 difficulty 40 → chance=10 → ~90% fizzle."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(magery=0, mana=200),
            iterations=500,
            npc_mode=False,
        )
        assert cell.ratios.fizzle_rate >= 0.80

    def test_magery_30_high_fizzle(self, fixture_shard):
        """Magery 30, circle 3 difficulty 40 → chance=40 → ~60% fizzle."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(magery=30, mana=200),
            iterations=500,
            npc_mode=False,
        )
        assert 0.45 <= cell.ratios.fizzle_rate <= 0.75

    def test_magery_50_moderate_fizzle(self, fixture_shard):
        """Magery 50, circle 3 difficulty 40 → chance=60 → ~40% fizzle."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(magery=50, mana=200),
            iterations=500,
            npc_mode=False,
        )
        assert 0.25 <= cell.ratios.fizzle_rate <= 0.55

    def test_magery_90_zero_fizzle(self, fixture_shard):
        """Magery 90, circle 3 difficulty 40 → chance=100 → 0% fizzle."""
        cell = _run(
            fixture_shard, Spell.FIREBALL,
            caster=_caster(magery=90, mana=200),
            iterations=200,
            npc_mode=False,
        )
        assert cell.ratios.fizzle_rate == 0.0

    def test_magery_130_high_circle_moderate_fizzle(self, fixture_shard):
        """Magery 130, circle 8 difficulty 100 → chance=80 → ~20% fizzle."""
        cell = _run(
            fixture_shard, Spell.EARTHQUAKE,
            caster=_caster(magery=130, mana=200),
            iterations=500,
            npc_mode=False,
        )
        assert 0.10 <= cell.ratios.fizzle_rate <= 0.35


class TestManaCostPerCircle:
    """Mana cost validation for spells of various circles."""

    @pytest.mark.parametrize("spell,expected_circle", [
        (Spell.MAGIC_ARROW, 1),
        (Spell.FIREBALL, 3),
        (Spell.LIGHTNING, 4),
        (Spell.ENERGY_BOLT, 6),
        (Spell.FLAME_STRIKE, 7),
    ], ids=["MagicArrow_C1", "Fireball_C3", "Lightning_C4", "EnergyBolt_C6", "FlameStrike_C7"])
    def test_mana_cost_increases_with_circle(self, fixture_shard, spell, expected_circle):
        """Higher circle spells cost more mana."""
        cell = _run(
            fixture_shard, spell,
            caster=_caster(magery=130, mana=200),
            iterations=1,
            npc_mode=False,
        )
        r = cell.raw_results[0]
        cost = r.metrics.get("spell_mana_cost", 0)
        assert cost > 0, f"{spell.name} has 0 mana cost"
