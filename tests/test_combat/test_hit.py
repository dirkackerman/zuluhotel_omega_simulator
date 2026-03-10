"""Integration tests for execute_hit with eScript combat scripts."""

import omega.runtime  # noqa: F401

from omega.combat.hit import execute_hit
from omega.combat.result import HitResult
from omega.interpreter.types import EArray
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile
from omega.parser.parser import parse_text, ParseResult
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

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=25)

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

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=20)
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
            base_damage=10,
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
            base_damage=10,
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

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=100)

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
            base_damage=100,
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

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=30)
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
            base_damage=100,
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

        ctx = SimulationContext(attacker=attacker, defender=defender, weapon=weapon)
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
            base_damage=10,
        )
        assert result.success
        assert any(se.kind == "poison" for se in result.side_effects)
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

        result = execute_hit(trees, attacker, defender, weapon, armor, base_damage=25)
        assert result.success
        assert result.final_damage == 50.0  # 25 * 2
        assert defender.hp == 50
