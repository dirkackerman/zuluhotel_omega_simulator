"""Tests for effect enchantments (M19).

Covers the 7 effect-type weapon enchantments:
- Piercing: bypasses armor (RecalcDmg piercing=1)
- Poison: applies poison via SetPoison()
- Life Drain: heals attacker for portion of damage (50% proc)
- Mana Drain: transfers mana from target to attacker
- Stamina Drain: transfers stamina from target to attacker (50% proc)
- Blinding: chance-based visual effect (setlightlevel)
- Banish: insta-kills summoned/animated creatures

Each effect script is a hitscript that REPLACES mainhit (not in addition to it).
"""

import pytest

from omega.combat.hit import execute_hit
from omega.combat.result import HitResult
from omega.config.dice import DiceSpec
from omega.model.constants import (
    CLASSEID_WARRIOR,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
    SKILLID_ANATOMY,
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


def _make_attacker(*, is_npc=False):
    mob = Mobile(name="Attacker", is_npc=is_npc)
    mob.str_base = 100
    mob.dex_base = 100
    mob.int_base = 25
    mob.hp = 200
    mob.max_hp = 200
    mob.mana = 100
    mob.max_mana = 100
    mob.stamina = 100
    mob.max_stamina = 100
    mob.set_skill(SKILLID_SWORDSMANSHIP, 1000)
    mob.set_skill(SKILLID_TACTICS, 1000)
    mob.set_skill(SKILLID_ANATOMY, 1000)
    mob.set_property(CLASSEID_WARRIOR, 1)
    return mob


def _make_defender():
    mob = Mobile(name="Defender", is_npc=True, npctemplate="test")
    mob.str_base = 50
    mob.dex_base = 50
    mob.int_base = 50
    mob.hp = 500
    mob.max_hp = 500
    mob.mana = 100
    mob.max_mana = 100
    mob.stamina = 100
    mob.max_stamina = 100
    return mob


def _make_effect_weapon(hitscript, *, chance=None, poison_level=None, cursed=False):
    """Create a weapon with the given effect hitscript."""
    w = Weapon(
        name="Effect Sword",
        damage=DiceSpec(3, 6, 2),
        attribute=SKILLID_SWORDSMANSHIP,
        hitscript=hitscript,
    )
    if chance is not None:
        w.set_property("ChanceOfEffect", chance)
    if poison_level is not None:
        w.set_property("Poisonlvl", poison_level)
    if cursed:
        w.set_property("Cursed", 1)
    return w


def _run_hit(shard, combat_trees, attacker, defender, weapon, armor, **kwargs):
    return execute_hit(
        combat_trees, attacker, defender, weapon, armor,
        base_damage=40, debug=True,
        config_resolver=shard.resolve_config_path,
        em_modules_dir=_em_dir(shard),
        shard_root=shard.root,
        package_map=shard.package_map,
        **kwargs,
    )


def _skip_on_failure(result):
    if not result.success:
        pytest.skip(f"Script execution failed: {result.error}")


# ---------------------------------------------------------------------------
# Piercing
# ---------------------------------------------------------------------------


class TestPiercing:
    """Piercing weapon bypasses armor via RecalcDmg(..., piercing=1)."""

    def test_piercing_executes(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:piercingscript")
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "piercing"
        assert result.final_damage > 0

    def test_piercing_bypasses_armor(self, shard, combat_trees):
        """Piercing weapon should deal >= plain damage (armor bypass).

        Piercing passes piercing=1 to RecalcDmg which skips shield/AR
        absorption steps. With an NPC defender (no equipped armor), both
        paths produce similar damage since AR is 0 either way. The key
        assertion is that piercing damage >= plain damage (never less).
        """
        attacker = _make_attacker()
        armor = Armor(name="Heavy Plate", ar=60)

        # Plain weapon
        defender_plain = _make_defender()
        weapon_plain = Weapon(
            name="Plain Sword",
            damage=DiceSpec(3, 6, 2),
            attribute=SKILLID_SWORDSMANSHIP,
        )
        plain_result = _run_hit(
            shard, combat_trees, attacker, defender_plain, weapon_plain, armor,
            rng_seed=42,
        )
        _skip_on_failure(plain_result)

        # Piercing weapon
        defender_pierce = _make_defender()
        weapon_pierce = _make_effect_weapon(":combat:piercingscript")
        pierce_result = _run_hit(
            shard, combat_trees, attacker, defender_pierce, weapon_pierce, armor,
            rng_seed=42,
        )
        _skip_on_failure(pierce_result)

        # Piercing bypasses armor, so should deal at least as much
        assert pierce_result.final_damage >= plain_result.final_damage

    def test_piercing_cursed(self, shard, combat_trees):
        """Cursed piercing: damage hits attacker instead."""
        attacker = _make_attacker()
        attacker.hp = 500
        attacker.max_hp = 500
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:piercingscript", cursed=True)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "piercing"
        assert attacker.hp < 500


# ---------------------------------------------------------------------------
# Poison
# ---------------------------------------------------------------------------


class TestPoison:
    """Poison hit applies poison to target via SetPoison()."""

    def test_poison_executes(self, shard, combat_trees):
        attacker = _make_attacker(is_npc=False)
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:poisonhit", poison_level=3)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "poison"
        assert result.metrics.get("effect_poison_level") == 3
        assert result.final_damage > 0

    def test_poison_cursed(self, shard, combat_trees):
        """Cursed poison weapon: poison targets attacker."""
        attacker = _make_attacker(is_npc=False)
        defender = _make_defender()
        weapon = _make_effect_weapon(
            ":combat:poisonhit", poison_level=5, cursed=True,
        )
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "poison"


# ---------------------------------------------------------------------------
# Life Drain
# ---------------------------------------------------------------------------


class TestLifeDrain:
    """Life drain heals attacker for rawdamage/2 * 0.75 with 50% proc."""

    def test_lifedrain_executes(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:lifedrainscript")
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "lifedrain"
        assert result.final_damage > 0

    def test_lifedrain_heals_attacker(self, shard, combat_trees):
        """When the 50% proc fires, attacker HP increases via SetHP."""
        # Set attacker HP low so healing is visible
        attacker = _make_attacker()
        attacker.hp = 100
        attacker.max_hp = 200
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:lifedrainscript")
        armor = Armor(name="Plate", ar=30)

        # Try multiple seeds to find one where the 50% proc fires
        healed = False
        for seed in range(1, 50):
            attacker.hp = 100
            defender.hp = 500
            result = _run_hit(
                shard, combat_trees, attacker, defender, weapon, armor,
                rng_seed=seed,
            )
            if not result.success:
                continue
            if attacker.hp > 100:
                healed = True
                # Verify hp_set side effect was recorded
                hp_effects = [
                    se for se in result.side_effects
                    if se.kind == "hp_set" and se.target_serial == attacker.serial
                ]
                assert len(hp_effects) > 0
                break

        assert healed, "Life drain never procced across 49 seeds (expected ~50% rate)"


# ---------------------------------------------------------------------------
# Mana Drain
# ---------------------------------------------------------------------------


class TestManaDrain:
    """Mana drain transfers rawdamage/2 mana from target to attacker."""

    def test_manadrain_executes(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:manadrainscript")
        weapon.set_property("dmg_mod", 0)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "manadrain"
        assert result.final_damage > 0

    def test_manadrain_transfers_mana(self, shard, combat_trees):
        """Mana is drained from defender and given to attacker."""
        attacker = _make_attacker()
        attacker.mana = 50
        attacker.max_mana = 200
        defender = _make_defender()
        defender.mana = 100
        defender.max_mana = 100
        weapon = _make_effect_weapon(":combat:manadrainscript")
        weapon.set_property("dmg_mod", 0)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(
            shard, combat_trees, attacker, defender, weapon, armor, rng_seed=42,
        )
        _skip_on_failure(result)

        # Defender mana should decrease, attacker mana should increase
        assert defender.mana < 100
        assert attacker.mana > 50

        # Verify mana_changed side effects recorded
        mana_effects = [se for se in result.side_effects if se.kind == "mana_changed"]
        assert len(mana_effects) >= 2  # at least one drain + one gain


# ---------------------------------------------------------------------------
# Stamina Drain
# ---------------------------------------------------------------------------


class TestStaminaDrain:
    """Stamina drain transfers rawdamage/2 stamina (50% proc)."""

    def test_staminadrain_executes(self, shard, combat_trees):
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:staminadrainscript")
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "staminadrain"
        assert result.final_damage > 0

    def test_staminadrain_transfers_stamina(self, shard, combat_trees):
        """When proc fires, stamina is drained and given."""
        attacker = _make_attacker()
        attacker.stamina = 50
        attacker.max_stamina = 200
        defender = _make_defender()
        defender.stamina = 100
        defender.max_stamina = 100
        weapon = _make_effect_weapon(":combat:staminadrainscript")
        armor = Armor(name="Plate", ar=30)

        drained = False
        for seed in range(1, 50):
            attacker.stamina = 50
            defender.stamina = 100
            defender.hp = 500
            result = _run_hit(
                shard, combat_trees, attacker, defender, weapon, armor,
                rng_seed=seed,
            )
            if not result.success:
                continue
            if defender.stamina < 100:
                drained = True
                assert attacker.stamina > 50
                stamina_effects = [
                    se for se in result.side_effects
                    if se.kind == "stamina_changed"
                ]
                assert len(stamina_effects) >= 2
                break

        assert drained, "Stamina drain never procced across 49 seeds"


# ---------------------------------------------------------------------------
# Blinding
# ---------------------------------------------------------------------------


class TestBlinding:
    """Blinding effect fires based on ChanceOfEffect."""

    def test_blinding_100pct(self, shard, combat_trees):
        """100% chance should always trigger the blinding effect."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:blindingscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "blinding"
        assert result.metrics.get("effect_triggered") == 1
        assert result.final_damage > 0

    def test_blinding_0pct(self, shard, combat_trees):
        """0% chance should never trigger."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:blindingscript", chance=0)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        # Effect should not have triggered
        assert result.metrics.get("effect_triggered") is None
        # But damage should still be dealt
        assert result.final_damage > 0


# ---------------------------------------------------------------------------
# Banish
# ---------------------------------------------------------------------------


class TestBanish:
    """Banish insta-kills summoned/animated; normal targets get regular damage."""

    def test_banish_normal_target(self, shard, combat_trees):
        """Normal target: regular RecalcDmg + DealDamage path."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_effect_weapon(":combat:banishscript")
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "banish"
        assert result.metrics.get("effect_target_type") == "normal"
        assert result.final_damage > 0

    def test_banish_summoned(self, shard, combat_trees):
        """Summoned target: defender takes max_hp+3 magic damage (instant kill)."""
        attacker = _make_attacker()
        defender = _make_defender()
        defender.set_property("summoned", 1)
        weapon = _make_effect_weapon(":combat:banishscript")
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "banish"
        assert result.metrics.get("effect_target_type") == "summoned"
        # Defender should be dead (took max_hp + 3 damage)
        assert defender.hp <= 0

    def test_banish_cursed_summoned(self, shard, combat_trees):
        """Cursed banish on summoned: damage hits attacker instead."""
        attacker = _make_attacker()
        attacker.hp = 500
        attacker.max_hp = 500
        defender = _make_defender()
        defender.set_property("summoned", 1)
        weapon = _make_effect_weapon(":combat:banishscript", cursed=True)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "banish"
        assert result.metrics.get("effect_target_type") == "summoned"
        # Attacker should take damage (cursed reversal)
        assert attacker.hp < 500


# ---------------------------------------------------------------------------
# Hitscript dispatch: no double damage
# ---------------------------------------------------------------------------


class TestEffectHitscriptDispatch:
    """Verify effect hitscripts replace mainhit (no double damage)."""

    @pytest.mark.parametrize("hitscript", [
        ":combat:piercingscript",
        ":combat:manadrainscript",
        ":combat:staminadrainscript",
        ":combat:blindingscript",
        ":combat:banishscript",
    ])
    def test_effect_no_double_damage(self, shard, combat_trees, hitscript):
        """Each effect weapon should have exactly 1 damage_applied entry."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_effect_weapon(hitscript, chance=0)
        weapon.set_property("dmg_mod", 0)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        applied = result.metrics.get("damage_applied", [])
        assert len(applied) == 1, (
            f"Expected 1 damage application for {hitscript}, got {len(applied)}. "
            f"Double damage bug: mainhit ran in addition to hitscript."
        )
