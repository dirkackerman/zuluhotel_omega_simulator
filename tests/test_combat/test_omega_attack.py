"""Tests for OmegaAttack and the shard's CheckHitChance formula.

The Zuluhotel Omega shard replaces POL's core hit check with a custom
``CheckHitChance()`` function in ``omegaattack.inc``.  The formula is::

    hit_chance = (atk_skill / 214.29) * (1 + class_level * 0.0238)
              * (1 - hunger * 0.05)
    min 10%

Key differences from POL's core:
- Attacker skill only (no defender skill)
- Class level bonus
- Hunger penalty
- Thieves/Mages/Bards use their lowest class skill
- 10% minimum hit chance floor

These tests execute CheckHitChance through the eScript interpreter
to verify it produces correct results for the shard's balance model.
"""

from typing import Any

import pytest

from omega.config.dice import DiceSpec
from omega.interpreter.executor import Executor
from omega.model.constants import (
    ATTRIBUTEID_SWORDSMANSHIP,
    CLASSEID_MAGE,
    CLASSEID_THIEF,
    CLASSEID_WARRIOR,
    LAYER_HAND1,
    SKILLID_MAGERY,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
)
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.rng import set_rng_seed


@pytest.fixture
def shard(fixture_shard):
    return fixture_shard


@pytest.fixture
def combat_trees(fixture_parse_results):
    return fixture_parse_results


_cached_executors: dict[int, Any] = {}


def _get_executor(shard, combat_trees):
    """Get or create a cached executor for omegaattack tests."""
    shard_id = id(shard)
    if shard_id not in _cached_executors:
        _cached_executors[shard_id] = Executor(
            combat_trees,
            em_modules_dir=shard.root / "scripts" / "modules",
            shard_root=shard.root,
            package_map=shard.package_map,
        )
    return _cached_executors[shard_id]


def _run_check_hit_chance(shard, combat_trees, attacker, defender, *, rng_seed=42):
    """Execute CheckHitChance through the eScript interpreter.

    Parses omegaattack.inc and runs CheckHitChance(attacker, defender)
    as a sub-program call.
    """
    import omega.runtime  # noqa: F401 — ensure stubs are registered

    rng = set_rng_seed(rng_seed)

    ctx = SimulationContext(attacker=attacker, weapon=attacker.weapon, debug_mode=True)
    ctx.defender = defender
    ctx._config_resolver = shard.resolve_config_path
    ctx.global_properties["randomeroseed"] = rng_seed

    ctx.register_object(attacker)
    ctx.register_object(defender)
    if attacker.weapon:
        ctx.register_object(attacker.weapon)

    set_context(ctx)

    executor = _get_executor(shard, combat_trees)
    executor.reset()
    ctx.executor = executor

    executor.scopes.define_global("DEBUG_MODE", 1)

    # Load omegaattack.inc if not already loaded — it defines CheckHitChance
    # as a function that we can call directly
    # Load omegaattack.inc functions if not already loaded
    if not executor.functions.has("CheckHitChance"):
        from omega.parser.parser import parse_with_includes
        from omega.interpreter.functions import extract_functions, extract_constants, extract_use_declarations

        omegaattack_path = shard.root / "pkg" / "opt" / "shilhook" / "omegaattack.inc"
        if omegaattack_path.exists():
            results = parse_with_includes(
                omegaattack_path,
                shard.root,
                package_map=shard.package_map,
            )
            for fp, pr in results.items():
                if pr.tree is None:
                    continue
                for module in extract_use_declarations(pr.tree):
                    executor.functions.add_module(module)
                for func_def in extract_functions(pr.tree, source_file=str(fp)):
                    if not executor.functions.has(func_def.name):
                        executor.functions.register(func_def)
                for const_name, expr_ctx, _is_enum in extract_constants(pr.tree):
                    from omega.interpreter.types import UNINIT
                    if executor.scopes.get(const_name) is UNINIT and expr_ctx is not None:
                        value = executor._interpreter.visit(expr_ctx)
                        executor.scopes.define_global(const_name, value, const=True)

    return executor.call_function("CheckHitChance", [attacker, defender])


def _make_melee_attacker(*, skill=100, class_id=CLASSEID_WARRIOR, class_level=1, hunger=0):
    """Create an attacker with specified melee skill and class."""
    mob = Mobile(name="Attacker", is_npc=False)
    mob.str_base = 100
    mob.dex_base = 100
    mob.int_base = 25
    mob.hp = 200
    mob.max_hp = 200
    mob.mana = 25
    mob.max_mana = 25
    mob.stamina = 100
    mob.max_stamina = 100
    mob.set_skill(SKILLID_SWORDSMANSHIP, skill * 10)
    mob.set_skill(SKILLID_TACTICS, skill * 10)
    if class_level > 0:
        mob.set_property(class_id, class_level)
    if hunger > 0:
        mob.set_property("hunger", hunger)

    weapon = Weapon(
        name="Sword",
        damage=DiceSpec(3, 6, 2),
        attribute=ATTRIBUTEID_SWORDSMANSHIP,
        hitscript=":combat:mainhit",
    )
    mob.equip(LAYER_HAND1, weapon)
    return mob


def _make_defender():
    mob = Mobile(name="Defender", is_npc=True, npctemplate="test")
    mob.str_base = 50
    mob.dex_base = 50
    mob.int_base = 50
    mob.hp = 500
    mob.max_hp = 500
    return mob


# ---------------------------------------------------------------------------
# Mobile.weapon property
# ---------------------------------------------------------------------------


class TestMobileWeaponProperty:
    def test_weapon_returns_equipped_weapon(self):
        mob = Mobile(name="Test")
        sword = Weapon(name="Sword", attribute=ATTRIBUTEID_SWORDSMANSHIP)
        mob.equip(LAYER_HAND1, sword)
        assert mob.weapon is sword

    def test_weapon_returns_wrestling_when_unarmed(self):
        """Unarmed → returns wrestling fist weapon (matches POL intrinsic_weapon)."""
        mob = Mobile(name="Test")
        assert mob.weapon is not None
        assert mob.weapon.name == "Wrestling"
        assert mob.weapon.attribute == "Wrestling"

    def test_weapon_in_hand2(self):
        """Weapon in LAYER_HAND2 (e.g., two-handed) is found."""
        from omega.model.constants import LAYER_HAND2
        mob = Mobile(name="Test")
        bow = Weapon(name="Bow", attribute="Archery")
        mob.equip(LAYER_HAND2, bow)
        assert mob.weapon is bow

    def test_hand1_takes_priority_over_hand2(self):
        """If both hands have weapons, HAND1 wins (POL equip order)."""
        from omega.model.constants import LAYER_HAND2
        mob = Mobile(name="Test")
        sword = Weapon(name="Sword", attribute=ATTRIBUTEID_SWORDSMANSHIP)
        dagger = Weapon(name="Dagger", attribute="Fencing")
        mob.equip(LAYER_HAND1, sword)
        mob.equip(LAYER_HAND2, dagger)
        assert mob.weapon is sword

    def test_weapon_returns_wrestling_when_armor_in_hand(self):
        """Shield in LAYER_HAND1 → returns wrestling weapon (not the shield)."""
        mob = Mobile(name="Test")
        mob.equip(LAYER_HAND1, Armor(name="Shield", ar=10))
        assert mob.weapon is not None
        assert mob.weapon.name == "Wrestling"

    def test_shield_in_hand2_weapon_in_hand1(self):
        """Shield in HAND2 + weapon in HAND1 → returns the weapon."""
        from omega.model.constants import LAYER_HAND2
        mob = Mobile(name="Test")
        sword = Weapon(name="Sword", attribute=ATTRIBUTEID_SWORDSMANSHIP)
        mob.equip(LAYER_HAND1, sword)
        mob.equip(LAYER_HAND2, Armor(name="Shield", ar=15))
        assert mob.weapon is sword

    def test_weapon_attribute_accessible(self):
        """attacker.weapon.attribute should work (used by omegaattack)."""
        mob = Mobile(name="Test")
        sword = Weapon(name="Sword", attribute=ATTRIBUTEID_SWORDSMANSHIP)
        mob.equip(LAYER_HAND1, sword)
        assert mob.weapon.attribute == ATTRIBUTEID_SWORDSMANSHIP

    def test_weapon_hitscript_accessible(self):
        """attacker.weapon.hitscript should work (used by omegaattack)."""
        mob = Mobile(name="Test")
        sword = Weapon(name="Sword", hitscript=":combat:mainhit")
        mob.equip(LAYER_HAND1, sword)
        assert mob.weapon.hitscript == ":combat:mainhit"

    def test_weapon_objtype_accessible(self):
        """attacker.weapon.objtype should work (used by omegaattack for config lookup)."""
        mob = Mobile(name="Test")
        sword = Weapon(name="Sword", objtype=0x1234)
        mob.equip(LAYER_HAND1, sword)
        assert mob.weapon.objtype == 0x1234


# ---------------------------------------------------------------------------
# CheckHitChance formula tests
# ---------------------------------------------------------------------------


class TestCheckHitChanceFormula:
    """Verify the shard's CheckHitChance runs through the interpreter."""

    def test_high_skill_usually_hits(self, shard, combat_trees):
        """Skill 100 warrior → ~47% base + class bonus → should hit often."""
        attacker = _make_melee_attacker(skill=100, class_level=3)
        defender = _make_defender()

        hits = 0
        for seed in range(100):
            result = _run_check_hit_chance(shard, combat_trees, attacker, defender, rng_seed=seed)
            if result == 1:
                hits += 1

        # skill_chance = 100/214.29 ≈ 0.467
        # class_chance = 1 + 3*0.0238 = 1.071
        # hit_chance ≈ 0.467 * 1.071 ≈ 0.50
        assert hits > 30, f"High skill warrior hit only {hits}/100 times"

    def test_zero_skill_gets_min_10pct(self, shard, combat_trees):
        """Skill 0 → hit_chance clamped to min 10%."""
        attacker = _make_melee_attacker(skill=0, class_level=0)
        defender = _make_defender()

        hits = 0
        for seed in range(200):
            result = _run_check_hit_chance(shard, combat_trees, attacker, defender, rng_seed=seed)
            if result == 1:
                hits += 1

        # Min 10% → expect ~20 hits out of 200
        assert hits >= 5, f"Zero skill attacker hit only {hits}/200 (expected ≥10%)"
        assert hits < 60, f"Zero skill attacker hit {hits}/200 (expected ~10%, way too high)"

    def test_hunger_reduces_hit_chance(self, shard, combat_trees):
        """Hunger penalty: hunger=10 → multiplier 0.5 (50% reduction)."""
        # No hunger
        attacker_fed = _make_melee_attacker(skill=100, class_level=1, hunger=0)
        defender = _make_defender()
        hits_fed = sum(
            1 for seed in range(200)
            if _run_check_hit_chance(shard, combat_trees, attacker_fed, defender, rng_seed=seed) == 1
        )

        # Hungry (hunger=10 → penalty = 1 - 10*0.05 = 0.5)
        attacker_hungry = _make_melee_attacker(skill=100, class_level=1, hunger=10)
        hits_hungry = sum(
            1 for seed in range(200)
            if _run_check_hit_chance(shard, combat_trees, attacker_hungry, defender, rng_seed=seed) == 1
        )

        assert hits_hungry < hits_fed, (
            f"Hungry attacker hit {hits_hungry}/200 vs fed {hits_fed}/200 — hunger should reduce hits"
        )

    def test_class_level_increases_hit_chance(self, shard, combat_trees):
        """Higher class level → higher hit chance via class_factor."""
        # Level 1 warrior
        attacker_low = _make_melee_attacker(skill=80, class_level=1)
        defender = _make_defender()
        hits_low = sum(
            1 for seed in range(200)
            if _run_check_hit_chance(shard, combat_trees, attacker_low, defender, rng_seed=seed) == 1
        )

        # Level 5 warrior
        attacker_high = _make_melee_attacker(skill=80, class_level=5)
        hits_high = sum(
            1 for seed in range(200)
            if _run_check_hit_chance(shard, combat_trees, attacker_high, defender, rng_seed=seed) == 1
        )

        assert hits_high >= hits_low, (
            f"Level 5 hit {hits_high}/200 vs level 1 hit {hits_low}/200 — higher class should help"
        )

    def test_defender_skill_does_not_affect_chance(self, shard, combat_trees):
        """Shard formula ignores defender skill entirely."""
        attacker = _make_melee_attacker(skill=80, class_level=1)

        # Weak defender
        defender_weak = _make_defender()

        # Strong defender (high wrestling)
        defender_strong = _make_defender()
        defender_strong.set_skill(SKILLID_SWORDSMANSHIP, 1300)
        defender_strong.equip(LAYER_HAND1, Weapon(name="Sword", attribute=ATTRIBUTEID_SWORDSMANSHIP))

        hits_vs_weak = sum(
            1 for seed in range(200)
            if _run_check_hit_chance(shard, combat_trees, attacker, defender_weak, rng_seed=seed) == 1
        )
        hits_vs_strong = sum(
            1 for seed in range(200)
            if _run_check_hit_chance(shard, combat_trees, attacker, defender_strong, rng_seed=seed) == 1
        )

        # Should be approximately equal (defender skill doesn't matter)
        diff = abs(hits_vs_weak - hits_vs_strong)
        assert diff < 30, (
            f"Hit rates differ by {diff} (weak={hits_vs_weak}, strong={hits_vs_strong}). "
            f"Shard formula should ignore defender skill."
        )

    def test_deterministic_with_same_seed(self, shard, combat_trees):
        """Same seed → same result."""
        attacker = _make_melee_attacker(skill=80, class_level=1)
        defender = _make_defender()

        for seed in range(20):
            r1 = _run_check_hit_chance(shard, combat_trees, attacker, defender, rng_seed=seed)
            r2 = _run_check_hit_chance(shard, combat_trees, attacker, defender, rng_seed=seed)
            assert r1 == r2, f"Non-deterministic at seed {seed}"
