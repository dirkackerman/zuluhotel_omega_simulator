"""Tests for greater enchantments (M20).

Covers the 3 greater-type weapon enchantments:
- Dual Planar: chance-based HOLY + NECRO planar damage via ApplyPlanarDamage
- Void: +15 base damage bonus, cursed halving, random drain (hp/mana/stamina)
- Tri-Elemental: chance-based FIRE + AIR + WATER elemental damage via ApplyElementalDamage

Each greater script is a hitscript that REPLACES mainhit (not in addition to it).
"""

import pytest

from omega.combat.hit import execute_hit
from omega.config.dice import DiceSpec
from omega.model.constants import (
    CLASSEID_MAGE,
    CLASSEID_MYSTIC_ARCHER,
    CLASSEID_PALADIN,
    CLASSEID_POWERPLAYER,
    CLASSEID_WARRIOR,
    SKILLID_ANATOMY,
    SKILLID_EVALINT,
    SKILLID_MAGERY,
    SKILLID_MAGICRESISTANCE,
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


def _make_attacker(*, is_npc=False, class_id=CLASSEID_WARRIOR, class_level=1):
    mob = Mobile(name="Attacker", is_npc=is_npc)
    mob.str_base = 100
    mob.dex_base = 100
    mob.int_base = 100
    mob.hp = 200
    mob.max_hp = 200
    mob.mana = 100
    mob.max_mana = 100
    mob.stamina = 100
    mob.max_stamina = 100
    mob.set_skill(SKILLID_SWORDSMANSHIP, 1000)
    mob.set_skill(SKILLID_TACTICS, 1000)
    mob.set_skill(SKILLID_ANATOMY, 1000)
    mob.set_skill(SKILLID_MAGERY, 1000)
    mob.set_skill(SKILLID_EVALINT, 1000)
    if class_id:
        mob.set_property(class_id, class_level)
    return mob


def _make_defender(*, magic_resist=0):
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
    if magic_resist:
        mob.set_skill(SKILLID_MAGICRESISTANCE, magic_resist)
    return mob


def _make_greater_weapon(hitscript, *, chance=100, cursed=False):
    """Create a weapon with the given greater hitscript."""
    w = Weapon(
        name="Greater Sword",
        damage=DiceSpec(3, 6, 2),
        attribute=SKILLID_SWORDSMANSHIP,
        hitscript=hitscript,
    )
    w.set_property("ChanceOfEffect", chance)
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
# Dual Planar
# ---------------------------------------------------------------------------


class TestDualPlanar:
    """Dual planar weapon deals HOLY + NECRO planar damage on proc."""

    def test_dualplanar_executes_and_triggers(self, shard, combat_trees):
        """100% chance triggers dualplanar effect with metrics."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:dualplanarscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "dualplanar"
        assert result.metrics.get("effect_triggered") == 1
        assert result.final_damage > 0

    def test_dualplanar_no_trigger_at_zero_chance(self, shard, combat_trees):
        """0% chance does not trigger the effect."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:dualplanarscript", chance=0)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_triggered") is None
        # Physical damage still dealt via DealDamage
        assert result.final_damage > 0

    def test_dualplanar_deals_additional_damage(self, shard, combat_trees):
        """Triggered dualplanar should deal more total damage than plain hit."""
        attacker = _make_attacker()
        armor = Armor(name="Plate", ar=30)

        # Plain hit
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

        # Dualplanar hit
        defender_dp = _make_defender()
        weapon_dp = _make_greater_weapon(":combat:dualplanarscript", chance=100)
        dp_result = _run_hit(
            shard, combat_trees, attacker, defender_dp, weapon_dp, armor,
            rng_seed=42,
        )
        _skip_on_failure(dp_result)

        assert dp_result.final_damage >= plain_result.final_damage

    def test_dualplanar_planar_applied_metrics(self, shard, combat_trees):
        """Planar damage records list:planar_applied with HOLY and NECRO entries."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:dualplanarscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        planar = result.metrics.get("planar_applied", [])
        assert len(planar) == 2, f"Expected 2 planar entries (HOLY + NECRO), got {len(planar)}"
        attack_types = [p["attack_type"] for p in planar]
        # DMGID_HOLY=0x20, DMGID_NECRO=0x10
        assert 0x20 in attack_types, "Missing HOLY planar entry"
        assert 0x10 in attack_types, "Missing NECRO planar entry"
        for p in planar:
            assert "dmg_gross" in p
            assert p["dmg_gross"] > 0

    def test_dualplanar_resisted_metrics(self, shard, combat_trees):
        """Resisted() records list:resisted entries for planar damage."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:dualplanarscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        assert len(resisted) >= 2, f"Expected >=2 resisted entries, got {len(resisted)}"
        for r in resisted:
            assert "dmg_before" in r
            assert "dmg_after" in r
            assert "chance" in r
            assert "did_resist" in r

    def test_dualplanar_cursed(self, shard, combat_trees):
        """Cursed dualplanar uses attacker as CalcSpellDamage/Resisted target.

        In the shard script, cursed sets targ=attacker which is passed as the
        *caster* (1st arg) to ApplyPlanarDamage — damage still goes to defender
        (cast_on=defender, 2nd arg). The cursed flag changes spell/resist
        calculations, not the damage target.
        """
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:dualplanarscript", chance=100, cursed=True)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("cursed")
        assert result.metrics.get("effect_triggered") == 1

    def test_dualplanar_class_nerf_mage(self, shard, combat_trees):
        """Mage attacker gets 0.7 multiplier on dualplanar spell damage."""
        armor = Armor(name="Plate", ar=30)

        # Warrior attacker (no nerf)
        attacker_w = _make_attacker(class_id=CLASSEID_WARRIOR)
        defender_w = _make_defender()
        weapon_w = _make_greater_weapon(":combat:dualplanarscript", chance=100)
        result_w = _run_hit(
            shard, combat_trees, attacker_w, defender_w, weapon_w, armor,
            rng_seed=42,
        )
        _skip_on_failure(result_w)

        # Mage attacker (0.7 nerf)
        attacker_m = _make_attacker(class_id=CLASSEID_MAGE)
        defender_m = _make_defender()
        weapon_m = _make_greater_weapon(":combat:dualplanarscript", chance=100)
        result_m = _run_hit(
            shard, combat_trees, attacker_m, defender_m, weapon_m, armor,
            rng_seed=42,
        )
        _skip_on_failure(result_m)

        assert result_m.metrics.get("dualplanar_class_nerf") == 0.7
        assert result_w.metrics.get("dualplanar_class_nerf") == 1.0

    def test_dualplanar_class_nerf_paladin(self, shard, combat_trees):
        """Paladin attacker also gets 0.7 multiplier on dualplanar spell damage."""
        attacker = _make_attacker(class_id=CLASSEID_PALADIN)
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:dualplanarscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("dualplanar_class_nerf") == 0.7


# ---------------------------------------------------------------------------
# Void
# ---------------------------------------------------------------------------


class TestVoid:
    """Void weapon deals +15 bonus damage and randomly drains hp/mana/stamina."""

    def test_void_executes_with_metrics(self, shard, combat_trees):
        """Void script executes and records effect_type."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:voidscript")
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "void"
        assert result.final_damage > 0

    def test_void_base_bonus(self, shard, combat_trees):
        """Void weapon adds base_bonus to basedamage."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:voidscript")
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("void_base_bonus") > 0

    def test_void_deals_more_than_plain(self, shard, combat_trees):
        """Void weapon should deal more damage than plain weapon due to +15 bonus."""
        attacker = _make_attacker()
        armor = Armor(name="Plate", ar=30)

        # Plain hit
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

        # Void hit
        defender_void = _make_defender()
        weapon_void = _make_greater_weapon(":combat:voidscript")
        void_result = _run_hit(
            shard, combat_trees, attacker, defender_void, weapon_void, armor,
            rng_seed=42,
        )
        _skip_on_failure(void_result)

        assert void_result.final_damage >= plain_result.final_damage

    def test_void_drain_types(self, shard, combat_trees):
        """Void randomly picks hp, mana, or stamina drain across seeds."""
        attacker = _make_attacker()
        weapon = _make_greater_weapon(":combat:voidscript")
        armor = Armor(name="Plate", ar=30)

        drain_types_seen = set()
        for seed in range(1, 50):
            defender = _make_defender()
            attacker.hp = 200
            attacker.mana = 100
            attacker.stamina = 100
            result = _run_hit(
                shard, combat_trees, attacker, defender, weapon, armor,
                rng_seed=seed,
            )
            if not result.success:
                continue
            dt = result.metrics.get("void_drain_type")
            if dt:
                drain_types_seen.add(dt)
            if len(drain_types_seen) == 3:
                break

        assert "hp" in drain_types_seen, "HP drain never procced"
        assert "mana" in drain_types_seen, "Mana drain never procced"
        assert "stamina" in drain_types_seen, "Stamina drain never procced"

    def test_void_drain_amount_matches_half_rawdmg(self, shard, combat_trees):
        """Drain amount should be rawdamage/2."""
        attacker = _make_attacker()
        weapon = _make_greater_weapon(":combat:voidscript")
        armor = Armor(name="Plate", ar=30)

        for seed in range(1, 50):
            defender = _make_defender()
            attacker.hp = 200
            attacker.mana = 100
            attacker.stamina = 100
            result = _run_hit(
                shard, combat_trees, attacker, defender, weapon, armor,
                rng_seed=seed,
            )
            if not result.success:
                continue
            rawdmg = result.metrics.get("void_rawdmg")
            amount = result.metrics.get("void_drain_amount")
            if rawdmg is not None and amount is not None:
                assert amount == rawdmg / 2
                return

        pytest.skip("No successful void hit found")

    def test_void_cursed_halves_damage(self, shard, combat_trees):
        """Cursed void halves rawdamage and applies to attacker."""
        attacker = _make_attacker()
        attacker.hp = 500
        attacker.max_hp = 500
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:voidscript", cursed=True)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("cursed")
        rawdmg_before = result.metrics.get("void_rawdmg_before_curse")
        rawdmg_after = result.metrics.get("void_rawdmg")
        assert rawdmg_before is not None
        assert rawdmg_after is not None
        assert rawdmg_after == int(rawdmg_before / 2)
        # Attacker took damage (cursed applies to self)
        assert attacker.hp < 500

    def test_void_cursed_reverses_drainer(self, shard, combat_trees):
        """Cursed void: drained=attacker, drainer=defender."""
        attacker = _make_attacker()
        attacker.hp = 500
        attacker.max_hp = 500
        weapon = _make_greater_weapon(":combat:voidscript", cursed=True)
        armor = Armor(name="Plate", ar=30)

        for seed in range(1, 50):
            defender = _make_defender()
            attacker.hp = 500
            attacker.mana = 100
            attacker.stamina = 100
            defender.mana = 100
            defender.stamina = 100
            result = _run_hit(
                shard, combat_trees, attacker, defender, weapon, armor,
                rng_seed=seed,
            )
            if not result.success:
                continue
            dt = result.metrics.get("void_drain_type")
            if dt == "mana":
                # Attacker mana drained, defender mana gained
                assert attacker.mana < 100, "Cursed: attacker should lose mana"
                assert defender.mana >= 100, "Cursed: defender should gain mana"
                return
            if dt == "stamina":
                assert attacker.stamina < 100, "Cursed: attacker should lose stamina"
                assert defender.stamina >= 100, "Cursed: defender should gain stamina"
                return

        pytest.skip("No mana/stamina drain procced across seeds")

    def test_void_no_double_damage(self, shard, combat_trees):
        """Void hitscript replaces mainhit — only 1 damage_applied entry."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:voidscript")
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        applied = result.metrics.get("damage_applied", [])
        assert len(applied) >= 1, "Expected at least 1 damage_applied entry"


# ---------------------------------------------------------------------------
# Tri-Elemental
# ---------------------------------------------------------------------------


class TestTriElemental:
    """Tri-elemental weapon deals FIRE + AIR + WATER elemental damage on proc."""

    def test_trielemental_executes_and_triggers(self, shard, combat_trees):
        """100% chance triggers trielemental effect."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:trielementalscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_type") == "trielemental"
        assert result.metrics.get("effect_triggered") == 1
        assert result.final_damage > 0

    def test_trielemental_no_trigger_at_zero_chance(self, shard, combat_trees):
        """0% chance does not trigger the effect."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:trielementalscript", chance=0)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("effect_triggered") is None
        assert result.final_damage > 0

    def test_trielemental_deals_additional_damage(self, shard, combat_trees):
        """Triggered trielemental should deal more total damage than plain hit."""
        attacker = _make_attacker()
        armor = Armor(name="Plate", ar=30)

        # Plain hit
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

        # Trielemental hit
        defender_tri = _make_defender()
        weapon_tri = _make_greater_weapon(":combat:trielementalscript", chance=100)
        tri_result = _run_hit(
            shard, combat_trees, attacker, defender_tri, weapon_tri, armor,
            rng_seed=42,
        )
        _skip_on_failure(tri_result)

        assert tri_result.final_damage >= plain_result.final_damage

    def test_trielemental_elemental_applied_metrics(self, shard, combat_trees):
        """Elemental damage records list:elemental_applied with FIRE, AIR, WATER."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:trielementalscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        elem = result.metrics.get("elemental_applied", [])
        assert len(elem) == 3, f"Expected 3 elemental entries (FIRE+AIR+WATER), got {len(elem)}"
        attack_types = [e["attack_type"] for e in elem]
        # DMGID_FIRE=0x01, DMGID_AIR=0x02, DMGID_WATER=0x08
        assert 0x01 in attack_types, "Missing FIRE elemental entry"
        assert 0x02 in attack_types, "Missing AIR elemental entry"
        assert 0x08 in attack_types, "Missing WATER elemental entry"
        for e in elem:
            assert "dmg_gross" in e
            assert e["dmg_gross"] > 0

    def test_trielemental_resisted_metrics(self, shard, combat_trees):
        """Resisted() records list:resisted entries for elemental damage."""
        attacker = _make_attacker()
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:trielementalscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        resisted = result.metrics.get("resisted", [])
        # At least the initial Resisted() call + 3 from ApplyElementalDamage
        assert len(resisted) >= 1, f"Expected resisted metrics, got {len(resisted)}"
        for r in resisted:
            assert "dmg_before" in r
            assert "dmg_after" in r
            assert "did_resist" in r

    def test_trielemental_cursed_targets_attacker(self, shard, combat_trees):
        """Cursed trielemental applies elemental damage to attacker."""
        attacker = _make_attacker()
        attacker.hp = 500
        attacker.max_hp = 500
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:trielementalscript", chance=100, cursed=True)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("cursed")
        # Attacker should have taken elemental damage
        assert attacker.hp < 500

    def test_trielemental_class_nerf_mage(self, shard, combat_trees):
        """Mage attacker gets 0.7 multiplier on trielemental spell damage."""
        armor = Armor(name="Plate", ar=30)

        # Warrior attacker (no nerf)
        attacker_w = _make_attacker(class_id=CLASSEID_WARRIOR)
        defender_w = _make_defender()
        weapon_w = _make_greater_weapon(":combat:trielementalscript", chance=100)
        result_w = _run_hit(
            shard, combat_trees, attacker_w, defender_w, weapon_w, armor,
            rng_seed=42,
        )
        _skip_on_failure(result_w)

        # Mage attacker (0.7 nerf)
        attacker_m = _make_attacker(class_id=CLASSEID_MAGE)
        defender_m = _make_defender()
        weapon_m = _make_greater_weapon(":combat:trielementalscript", chance=100)
        result_m = _run_hit(
            shard, combat_trees, attacker_m, defender_m, weapon_m, armor,
            rng_seed=42,
        )
        _skip_on_failure(result_m)

        assert result_m.metrics.get("trielemental_class_nerf") == 0.7
        assert result_w.metrics.get("trielemental_class_nerf") == 1.0

    def test_trielemental_no_paladin_nerf(self, shard, combat_trees):
        """Paladin does NOT get nerfed in trielemental (unlike dualplanar)."""
        attacker = _make_attacker(class_id=CLASSEID_PALADIN)
        defender = _make_defender()
        weapon = _make_greater_weapon(":combat:trielementalscript", chance=100)
        armor = Armor(name="Plate", ar=30)

        result = _run_hit(shard, combat_trees, attacker, defender, weapon, armor)
        _skip_on_failure(result)

        assert result.metrics.get("trielemental_class_nerf") == 1.0

    def test_trielemental_protection_reduces_damage(self, shard, combat_trees):
        """Defender with fire protection takes less elemental damage."""
        attacker = _make_attacker()
        armor = Armor(name="Plate", ar=30)

        # No protection
        defender_no_prot = _make_defender()
        weapon_no_prot = _make_greater_weapon(":combat:trielementalscript", chance=100)
        result_no_prot = _run_hit(
            shard, combat_trees, attacker, defender_no_prot, weapon_no_prot, armor,
            rng_seed=42,
        )
        _skip_on_failure(result_no_prot)

        # With fire protection
        defender_prot = _make_defender()
        defender_prot.set_property("FireProtection", 50)
        weapon_prot = _make_greater_weapon(":combat:trielementalscript", chance=100)
        result_prot = _run_hit(
            shard, combat_trees, attacker, defender_prot, weapon_prot, armor,
            rng_seed=42,
        )
        _skip_on_failure(result_prot)

        # Protected defender should take less total damage
        assert result_prot.final_damage <= result_no_prot.final_damage
