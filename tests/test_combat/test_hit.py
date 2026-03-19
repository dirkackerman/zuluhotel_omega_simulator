"""Integration tests for execute_hit with eScript combat scripts."""

import omega.runtime  # noqa: F401

import pytest

from omega.combat.hit import check_hit, execute_hit, _weapon_skill
from omega.combat.result import HitResult
from omega.interpreter.types import EArray
from omega.model.constants import (
    LAYER_HAND1,
    SKILLID_ARCHERY,
    SKILLID_MACEFIGHTING,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
    SKILLID_WRESTLING,
)
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.parser.parser import parse_text, ParseResult
from omega.runtime.rng import SimulationRNG
from pathlib import Path


def _parse_source(source: str) -> dict[Path, ParseResult]:
    """Parse a source string as if it were a single file."""
    result = parse_text(source, file="<test>")
    return {Path("<test>"): result}


class TestExecuteHitSimple:
    """Test execute_hit with simple inline eScript programs."""

    def test_basic_damage_application(self):
        """Simplest case: program applies raw damage directly."""
        source = """
        use uo;
        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="Attacker")
        defender = Mobile(name="Defender")
        defender.hp = 100
        defender.max_hp = 100
        weapon = Weapon(name="Sword")
        armor = Armor(name="Shield", ar=10)

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=25, core_hit_check=False)

        assert result.success
        assert result.base_damage == 25
        assert result.final_damage == 25.0
        assert defender.hp == 75
        assert result.defender_hp_before == 100
        assert result.defender_hp_after == 75

    def test_damage_with_multiplier(self):
        """Program doubles damage before applying."""
        source = """
        use uo;
        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            rawdamage := rawdamage * 2;
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="Attacker")
        defender = Mobile(name="Defender")
        defender.hp = 100
        defender.max_hp = 100
        weapon = Weapon(name="Sword")
        armor = Armor(name="Shield")

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=20, core_hit_check=False)
        assert result.final_damage == 40.0
        assert defender.hp == 60

    def test_zero_damage(self):
        """No damage applied when rawdamage is 0."""
        source = """
        use uo;
        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            ApplyRawDamage(defender, 0);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="Attacker")
        defender = Mobile(name="Defender")
        defender.hp = 100
        defender.max_hp = 100

        result = execute_hit(
            trees, attacker, defender,
            Weapon(name="W"), Armor(name="A"),
            base_damage=10, core_hit_check=False,
        )
        assert result.final_damage == 0.0
        assert defender.hp == 100

    def test_error_handling(self):
        """Invalid parse still produces a HitResult with error."""
        # Empty program — should fail on "no program declaration"
        source = """
        use uo;
        function helper()
        endfunction
        """
        trees = _parse_source(source)
        attacker = Mobile(name="A")
        defender = Mobile(name="D")
        defender.hp = 100
        defender.max_hp = 100

        result = execute_hit(
            trees, attacker, defender,
            Weapon(name="W"), Armor(name="A"),
            base_damage=10, core_hit_check=False,
        )
        assert not result.success
        assert result.error is not None


class TestExecuteHitWithFunctions:
    """Test execute_hit with programs that call user-defined functions."""

    def test_ar_absorption_pattern(self):
        """ArAbsorptionCalc: percent = (ar/5)^0.5 * 0.05, capped at 0.90.

        With ar=50, basedamage=100:
        percent = (50/5)^0.5 * 0.05 = 10^0.5 * 0.05 = 3.162 * 0.05 = 0.158
        absorbed = CInt(100 * 0.158) = 15
        final = 100 - 15 = 85
        """
        source = """
        use uo;

        function ArAbsorptionCalc(ar, basedamage, divider := 5, multiplier := 0.05, exponent := 0.5)
            var percent := Pow(( ar / divider ), exponent) * multiplier;
            if (percent > 0.90)
                percent := 0.90;
            endif
            var absorbed := CInt(basedamage * percent);
            return absorbed;
        endfunction

        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            var ar := armor.ar;
            var absorbed := ArAbsorptionCalc(ar, rawdamage);
            rawdamage := rawdamage - absorbed;
            if (rawdamage < 1)
                rawdamage := 1;
            endif
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="Attacker")
        defender = Mobile(name="Defender")
        defender.hp = 200
        defender.max_hp = 200
        weapon = Weapon(name="Sword")
        armor = Armor(name="Plate", ar=50)

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=100, core_hit_check=False)

        assert result.success
        # absorbed = CInt(100 * 0.158) = 15
        # final = 100 - 15 = 85
        assert result.final_damage == 85.0
        assert defender.hp == 115

    def test_pvp_scaling(self):
        """PvP scaling: damage * 0.60."""
        source = """
        use uo;

        function ApplyPvPScaling(damage, is_pvp)
            if (is_pvp)
                damage := CInt(damage * 0.60);
            endif
            if (damage < 1)
                damage := 1;
            endif
            return damage;
        endfunction

        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            rawdamage := ApplyPvPScaling(rawdamage, 1);
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="Player1")
        defender = Mobile(name="Player2")
        defender.hp = 100
        defender.max_hp = 100

        result = execute_hit(
            trees, attacker, defender,
            Weapon(name="W"), Armor(name="A"),
            base_damage=100, core_hit_check=False,
        )
        assert result.success
        # CInt(100 * 0.60) = 60
        assert result.final_damage == 60.0

    def test_slayer_check(self):
        """Slayer weapon doubles damage against matching type."""
        source = """
        use uo;

        function GetSlayMultiplier(weapon, defender)
            var slaytype := GetObjProperty(weapon, "SlayType");
            if (!slaytype)
                return 1;
            endif
            var def_type := GetObjProperty(defender, "CreatureType");
            if (!def_type)
                return 1;
            endif
            var types := SplitWords(slaytype);
            foreach creature in types
                if (def_type == creature)
                    return 2;
                endif
            endforeach
            return 1;
        endfunction

        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            var mult := GetSlayMultiplier(weapon, defender);
            rawdamage := rawdamage * mult;
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="Hunter")
        defender = Mobile(name="Undead")
        defender.hp = 100
        defender.max_hp = 100
        defender.set_property("CreatureType", "Undead")
        weapon = Weapon(name="SlayerSword")
        weapon.set_property("SlayType", "Undead Demon")
        armor = Armor(name="A")

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=30, core_hit_check=False)
        assert result.success
        assert result.final_damage == 60.0  # 30 * 2

    def test_class_bonus_pattern(self):
        """ClasseBonusByLevel(level) = 1.0 + 0.25 * level."""
        source = """
        use uo;

        function ClasseBonusByLevel(level)
            return 1.0 + 0.25 * level;
        endfunction

        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            var class_level := GetObjProperty(attacker, "IsWarrior");
            if (!class_level)
                class_level := 0;
            endif
            var bonus := ClasseBonusByLevel(class_level);
            rawdamage := CInt(rawdamage * bonus);
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="Warrior")
        attacker.set_property("IsWarrior", 6)
        defender = Mobile(name="Target")
        defender.hp = 500
        defender.max_hp = 500

        result = execute_hit(
            trees, attacker, defender,
            Weapon(name="W"), Armor(name="A"),
            base_damage=100, core_hit_check=False,
        )
        assert result.success
        # bonus = 1.0 + 0.25 * 6 = 2.5
        # CInt(100 * 2.5) = 250
        assert result.final_damage == 250.0


class TestExecuteHitParms:
    """Test the parms-array unpacking pattern."""

    def test_parms_array_pattern(self):
        """mainhit receiving parameters as a single array (deflectiononhit pattern)."""
        source = """
        use uo;

        program mainhit(parms)
            var attacker    := parms[1];
            var defender    := parms[2];
            var weapon      := parms[3];
            var armor       := parms[4];
            var basedamage  := parms[5];
            var rawdamage   := parms[6];
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="A")
        defender = Mobile(name="D")
        defender.hp = 100
        defender.max_hp = 100
        weapon = Weapon(name="W")
        armor = Armor(name="A")

        # Build the parms array as mainhit would receive it
        parms = EArray([attacker, defender, weapon, armor, 50, 25])

        from omega.runtime.context import SimulationContext, set_context

        ctx = SimulationContext(attacker=attacker, weapon=weapon)
        ctx.defender = defender
        ctx.register_object(attacker)
        ctx.register_object(defender)
        set_context(ctx)

        from omega.interpreter.executor import Executor

        executor = Executor(trees)
        executor.run_program({"parms": parms})

        assert defender.hp == 75
        assert ctx.total_damage_dealt == 25.0


class TestExecuteHitSideEffects:
    """Test side effect recording during hit execution."""

    def test_poison_side_effect(self):
        source = """
        use uo;
        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            SetPoisoned(defender, 3);
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="A")
        defender = Mobile(name="D")
        defender.hp = 100
        defender.max_hp = 100

        result = execute_hit(
            trees, attacker, defender,
            Weapon(name="W"), Armor(name="A"),
            base_damage=10, core_hit_check=False,
        )
        assert result.success
        assert any(se.kind == "poison_applied" for se in result.side_effects)
        assert any(se.kind == "damage" for se in result.side_effects)

    def test_cursed_armor_doubles_damage(self):
        """Deflection pattern: cursed armor doubles rawdamage."""
        source = """
        use uo;

        function ApplyTheDamage(defender, attacker, rawdamage)
            ApplyRawDamage(defender, rawdamage);
        endfunction

        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            if (GetObjProperty(armor, "Cursed"))
                rawdamage := rawdamage * 2;
            endif
            ApplyTheDamage(defender, attacker, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        attacker = Mobile(name="Attacker")
        defender = Mobile(name="Defender")
        defender.hp = 100
        defender.max_hp = 100
        weapon = Weapon(name="Sword")
        armor = Armor(name="Cursed Shield")
        armor.set_property("Cursed", 1)

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=25, core_hit_check=False)
        assert result.success
        assert result.final_damage == 50.0  # 25 * 2
        assert defender.hp == 50


class TestCoreHitCheck:
    """Test POL's core hit/miss check.

    Formula: hit_chance = (atk_skill + 50) / (2 * (def_skill + 50))
    """

    def test_weapon_skill_from_weapon_attribute(self):
        mob = Mobile(name="Swordsman")
        mob.set_skill(SKILLID_SWORDSMANSHIP, 1000)  # 100 display
        weapon = Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP)
        assert _weapon_skill(mob, weapon) == 100

    def test_weapon_skill_fallback_to_wrestling(self):
        mob = Mobile(name="Unarmed")
        mob.set_skill(SKILLID_WRESTLING, 500)  # 50 display
        weapon = Weapon(name="Fist", attribute=0)
        assert _weapon_skill(mob, weapon) == 50

    def test_weapon_skill_no_skills(self):
        mob = Mobile(name="Dummy")
        weapon = Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP)
        assert _weapon_skill(mob, weapon) == 0

    def test_equal_skill_50_percent(self):
        """Equal skills → 50% hit chance."""
        atk = Mobile(name="A")
        atk.set_skill(SKILLID_SWORDSMANSHIP, 1000)
        defn = Mobile(name="D")
        defn.set_skill(SKILLID_SWORDSMANSHIP, 1000)
        defn.equip(0x01, Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP))
        weapon = Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP)

        hits = sum(
            check_hit(atk, defn, weapon, SimulationRNG(i))
            for i in range(1000)
        )
        # Should be around 500 ± ~50
        assert 350 < hits < 650

    def test_high_attacker_skill_nearly_always_hits(self):
        """Attacker skill >> defender skill → nearly 100% hit rate."""
        atk = Mobile(name="A")
        atk.set_skill(SKILLID_SWORDSMANSHIP, 1300)  # 130
        defn = Mobile(name="D")
        # Defender has no weapon skill (0)
        weapon = Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP)

        # hit_chance = (130 + 50) / (2 * (0 + 50)) = 180/100 = 1.8 → always hit
        hits = sum(
            check_hit(atk, defn, weapon, SimulationRNG(i))
            for i in range(100)
        )
        assert hits == 100

    def test_zero_attacker_skill_vs_high_defender(self):
        """Unskilled attacker vs skilled defender → low hit rate."""
        atk = Mobile(name="A")
        # No skills
        defn = Mobile(name="D")
        defn.set_skill(SKILLID_SWORDSMANSHIP, 1300)  # 130
        defn.equip(0x01, Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP))
        weapon = Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP)

        # hit_chance = (0 + 50) / (2 * (130 + 50)) = 50/360 ≈ 0.139
        hits = sum(
            check_hit(atk, defn, weapon, SimulationRNG(i))
            for i in range(1000)
        )
        assert 50 < hits < 250  # ~14% expected

    def test_miss_returns_zero_damage(self):
        """A missed hit returns final_damage=0 without running the script."""
        source = """
        use uo;
        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        trees = _parse_source(source)
        # Both have 0 skill → 50% hit rate. Use a seed that misses.
        atk = Mobile(name="A")
        defn = Mobile(name="D")
        defn.hp = 100
        defn.max_hp = 100
        weapon = Weapon(name="Sword")
        armor = Armor(name="A")

        # Run many iterations — some should miss
        misses = 0
        for seed in range(50):
            defn.hp = 100
            result = execute_hit(
                trees, atk, defn, weapon, armor,
                base_damage=10, rng_seed=seed, core_hit_check=True,
            )
            if result.final_damage == 0.0 and defn.hp == 100:
                misses += 1
        # With 50% hit chance and 50 trials, should have some misses
        assert misses > 5


# ---------------------------------------------------------------------------
# Detailed check_hit formula verification (POL's Character::attack())
# ---------------------------------------------------------------------------


class TestCheckHitFormulaExact:
    """Verify check_hit matches POL's exact formula from charactr.cpp:3357.

    POL formula::

        hit_chance = (weapon_attribute().effective() + 50.0)
                   / (2.0 * (opponent->weapon_attribute().effective() + 50.0))

    Note: The Zuluhotel Omega shard overrides this with a custom
    ``CheckHitChance()`` in ``omegaattack.inc`` that uses a completely
    different formula (attacker-only skill, class level, hunger).
    The ``core_hit_check=True`` mode in execute_hit() implements POL's
    core formula, NOT the shard's custom formula.
    """

    def _calc_pol_hit_chance(self, atk_skill: int, def_skill: int) -> float:
        """Calculate POL's exact hit chance from C++ source."""
        return (atk_skill + 50.0) / (2.0 * (def_skill + 50.0))

    def test_equal_skills_exact_50_pct(self):
        """Equal skills → hit_chance = exactly 0.5."""
        assert self._calc_pol_hit_chance(100, 100) == 0.5

    def test_zero_vs_zero_exact_50_pct(self):
        """Both 0 skill → (0+50)/(2*(0+50)) = 50/100 = 0.5."""
        assert self._calc_pol_hit_chance(0, 0) == 0.5

    def test_max_vs_zero(self):
        """130 vs 0 → (180)/(100) = 1.8 → always hits."""
        chance = self._calc_pol_hit_chance(130, 0)
        assert chance == 1.8
        # Any roll in [0,1) will be < 1.8

    def test_zero_vs_max(self):
        """0 vs 130 → (50)/(360) ≈ 0.139."""
        chance = self._calc_pol_hit_chance(0, 130)
        assert abs(chance - 50.0 / 360.0) < 1e-10

    def test_skill_50_vs_100(self):
        """50 vs 100 → (100)/(300) = 0.333."""
        chance = self._calc_pol_hit_chance(50, 100)
        assert abs(chance - 100.0 / 300.0) < 1e-10

    def test_skill_100_vs_50(self):
        """100 vs 50 → (150)/(200) = 0.75."""
        chance = self._calc_pol_hit_chance(100, 50)
        assert abs(chance - 150.0 / 200.0) < 1e-10

    def test_check_hit_uses_weapon_attribute(self):
        """check_hit reads the weapon's attribute for attacker skill."""
        atk = Mobile(name="A")
        atk.set_skill(SKILLID_SWORDSMANSHIP, 1000)  # 100 display
        atk.set_skill(SKILLID_MACEFIGHTING, 500)  # 50 display
        defn = Mobile(name="D")
        # Defender has no weapon → uses WRESTLING (0 skill)

        # Sword weapon → uses swordsmanship (100)
        sword = Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP)
        # hit_chance = (100+50)/(2*(0+50)) = 150/100 = 1.5 → always hit
        hits_sword = sum(check_hit(atk, defn, sword, SimulationRNG(i)) for i in range(100))
        assert hits_sword == 100

        # Mace weapon → uses macefighting (50)
        mace = Weapon(name="Mace", attribute=SKILLID_MACEFIGHTING)
        # hit_chance = (50+50)/(2*(0+50)) = 100/100 = 1.0 → always hit (>= 1.0)
        # Actually roll < 1.0, so some might miss at exactly 1.0... no:
        # random_float returns [0, 1), so roll < 1.0 is always True
        hits_mace = sum(check_hit(atk, defn, mace, SimulationRNG(i)) for i in range(100))
        assert hits_mace == 100

    def test_defender_weapon_skill_used_from_equipped(self):
        """Defender's skill comes from their equipped weapon's attribute."""
        atk = Mobile(name="A")
        atk.set_skill(SKILLID_SWORDSMANSHIP, 500)  # 50 display
        defn = Mobile(name="D")
        defn.set_skill(SKILLID_SWORDSMANSHIP, 1000)  # 100 display
        defn.set_skill(SKILLID_WRESTLING, 200)  # 20 display
        # Equip defender with a sword → their defense skill is 100
        defn.equip(LAYER_HAND1, Weapon(name="Def Sword", attribute=SKILLID_SWORDSMANSHIP))

        weapon = Weapon(name="Atk Sword", attribute=SKILLID_SWORDSMANSHIP)
        # hit_chance = (50+50)/(2*(100+50)) = 100/300 = 0.333
        hits = sum(check_hit(atk, defn, weapon, SimulationRNG(i)) for i in range(3000))
        expected = 3000 * (100.0 / 300.0)
        assert abs(hits - expected) < 150  # ~33% ± 5%

    def test_defender_no_weapon_uses_wrestling(self):
        """Unarmed defender uses Wrestling skill for defense."""
        atk = Mobile(name="A")
        atk.set_skill(SKILLID_SWORDSMANSHIP, 1000)  # 100
        defn = Mobile(name="D")
        defn.set_skill(SKILLID_WRESTLING, 1000)  # 100
        # No weapon equipped → defender uses wrestling

        weapon = Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP)
        # hit_chance = (100+50)/(2*(100+50)) = 150/300 = 0.5
        hits = sum(check_hit(atk, defn, weapon, SimulationRNG(i)) for i in range(2000))
        assert abs(hits - 1000) < 150  # ~50% ± 7.5%

    def test_deterministic_with_same_seed(self):
        """Same seed → same hit/miss result."""
        atk = Mobile(name="A")
        atk.set_skill(SKILLID_SWORDSMANSHIP, 500)
        defn = Mobile(name="D")
        defn.set_skill(SKILLID_SWORDSMANSHIP, 500)
        defn.equip(LAYER_HAND1, Weapon(name="S", attribute=SKILLID_SWORDSMANSHIP))
        weapon = Weapon(name="S", attribute=SKILLID_SWORDSMANSHIP)

        for seed in range(50):
            r1 = check_hit(atk, defn, weapon, SimulationRNG(seed))
            r2 = check_hit(atk, defn, weapon, SimulationRNG(seed))
            assert r1 == r2, f"Non-deterministic at seed {seed}"


class TestWeaponSkillEdgeCases:
    """Edge cases in _weapon_skill resolution."""

    def test_weapon_attribute_zero_falls_back_to_wrestling(self):
        """Weapon with attribute=0 should fall back to Wrestling."""
        mob = Mobile(name="Test")
        mob.set_skill(SKILLID_WRESTLING, 800)  # 80 display
        weapon = Weapon(name="Fist", attribute=0)
        assert _weapon_skill(mob, weapon) == 80

    def test_weapon_none_uses_equipped(self):
        """weapon=None → use equipped weapon's attribute."""
        mob = Mobile(name="Test")
        mob.set_skill(SKILLID_SWORDSMANSHIP, 600)  # 60 display
        mob.equip(LAYER_HAND1, Weapon(name="Sword", attribute=SKILLID_SWORDSMANSHIP))
        assert _weapon_skill(mob, None) == 60

    def test_weapon_none_no_equipped_uses_wrestling(self):
        """weapon=None, nothing equipped → Wrestling."""
        mob = Mobile(name="Test")
        mob.set_skill(SKILLID_WRESTLING, 400)  # 40 display
        assert _weapon_skill(mob, None) == 40

    def test_weapon_skill_unset_returns_zero(self):
        """Skill not set on mobile → 0."""
        mob = Mobile(name="Test")
        weapon = Weapon(name="Bow", attribute=SKILLID_ARCHERY)
        assert _weapon_skill(mob, weapon) == 0

    def test_weapon_none_armor_equipped_uses_wrestling(self):
        """Armor on LAYER_HAND1 (shield) → falls back to Wrestling."""
        mob = Mobile(name="Test")
        mob.set_skill(SKILLID_WRESTLING, 300)  # 30 display
        mob.equip(LAYER_HAND1, Armor(name="Shield", ar=10))
        assert _weapon_skill(mob, None) == 30

    def test_short_name_attribute_resolves_swords(self):
        """Config short name 'Swords' resolves to Swordsmanship skill."""
        mob = Mobile(name="Test")
        mob.set_skill(SKILLID_SWORDSMANSHIP, 800)  # 80 display
        weapon = Weapon(name="Katana", attribute="Swords")  # short name from cfg
        assert _weapon_skill(mob, weapon) == 80

    def test_short_name_attribute_resolves_mace(self):
        """Config short name 'Mace' resolves to Macefighting skill."""
        mob = Mobile(name="Test")
        mob.set_skill(SKILLID_MACEFIGHTING, 600)  # 60 display
        weapon = Weapon(name="Hammer", attribute="Mace")
        assert _weapon_skill(mob, weapon) == 60

    def test_full_name_attribute_resolves(self):
        """Full ATTRIBUTEID name 'Swordsmanship' also resolves."""
        mob = Mobile(name="Test")
        mob.set_skill(SKILLID_SWORDSMANSHIP, 700)  # 70 display
        weapon = Weapon(name="Sword", attribute="Swordsmanship")
        assert _weapon_skill(mob, weapon) == 70
