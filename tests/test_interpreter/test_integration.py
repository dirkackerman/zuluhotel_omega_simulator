"""Integration tests for the interpreter — real eScript patterns from combat scripts."""

import omega.runtime  # noqa: F401

from omega.interpreter.types import EArray
from omega.model.mobile import Mobile
from omega.model.items import Weapon, Armor
from omega.runtime.context import SimulationContext, set_context

from .helpers import run_function, run_program_with_args, run_snippet


class TestCombatPatterns:
    def test_ar_absorption_calc(self):
        """ArAbsorptionCalc from hitscriptinc.inc."""
        funcs = """
        function ArAbsorptionCalc(ar, basedamage, divider := 5, multiplier := 0.05, exponent := 0.5)
            var percent := Pow(( ar / divider ), exponent) * multiplier;
            if (percent > 0.90)
                percent := 0.90;
            endif
            var absorbed := CInt(basedamage * percent);
            return absorbed;
        endfunction
        """
        result = run_function(funcs, "var x := ArAbsorptionCalc(50, 100);", "x")
        assert isinstance(result, int)
        assert result > 0

    def test_slayer_check_pattern(self):
        """The slayer multiplier check from hitscriptinc.inc."""
        funcs = """
        function CheckSlayer(slaytype, def_type)
            if (!slaytype)
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
        """
        # No slayer
        result = run_function(funcs, "var x := CheckSlayer(0, \"Human\");", "x")
        assert result == 1

        # Matching slayer
        result = run_function(funcs, 'var x := CheckSlayer("Human Undead", "Human");', "x")
        assert result == 2

        # Non-matching slayer
        result = run_function(funcs, 'var x := CheckSlayer("Undead Demon", "Human");', "x")
        assert result == 1

    def test_elemental_damage_parsing(self):
        """Parsing ElementalDamage string like 'FIRE:50 PHYSICAL:50'."""
        funcs = """
        function ParseElements(elemStr)
            var elements := SplitWords(elemStr);
            var total := 0;
            foreach element in elements
                var parts := SplitWords(element, ":");
                var amount := CInt(parts[2]);
                total := total + amount;
            endforeach
            return total;
        endfunction
        """
        result = run_function(
            funcs, 'var x := ParseElements("FIRE:50 PHYSICAL:50");', "x"
        )
        assert result == 100

    def test_case_with_string_labels(self):
        """Case statement dispatching on damage type strings."""
        funcs = """
        function GetElementId(name)
            var element_ID := 0;
            case (name)
                "FIRE":     element_ID := 1;
                "AIR":      element_ID := 2;
                "EARTH":    element_ID := 4;
                "WATER":    element_ID := 8;
                default:    element_ID := 0;
            endcase
            return element_ID;
        endfunction
        """
        assert run_function(funcs, 'var x := GetElementId("FIRE");', "x") == 1
        assert run_function(funcs, 'var x := GetElementId("WATER");', "x") == 8
        assert run_function(funcs, 'var x := GetElementId("UNKNOWN");', "x") == 0

    def test_class_level_calculation(self):
        """Simplified class level calculation from classes.inc."""
        funcs = """
        function CalcLevel(total, count)
            var level := 0;
            var threshold := CInt(total / count);
            var current := 0;
            while (current < threshold && level < 6)
                level := level + 1;
                current := current + 100;
            endwhile
            return level;
        endfunction
        """
        result = run_function(funcs, "var x := CalcLevel(600, 2);", "x")
        assert result == 3  # threshold=300, 0<300→1, 100<300→2, 200<300→3

    def test_pvp_scaling(self):
        """PvP 60% damage scaling."""
        funcs = """
        function ApplyPvPScaling(damage, is_pvp)
            if (is_pvp)
                damage := CInt(damage * 0.60);
            endif
            if (damage < 1)
                damage := 1;
            endif
            return damage;
        endfunction
        """
        assert run_function(funcs, "var x := ApplyPvPScaling(100, 1);", "x") == 60
        assert run_function(funcs, "var x := ApplyPvPScaling(100, 0);", "x") == 100
        assert run_function(funcs, "var x := ApplyPvPScaling(1, 1);", "x") == 1


class TestGameObjectInteraction:
    def test_mobile_member_access(self):
        """Access mobile properties from eScript."""
        source = """
        program test(mob)
            var h := mob.hp;
            var n := mob.name;
        endprogram
        """
        m = Mobile(name="Warrior")
        m.hp = 100
        executor = run_program_with_args(source, {"mob": m})
        assert executor.scopes.get("h") == 100
        assert executor.scopes.get("n") == "Warrior"

    def test_builtin_get_obj_property(self):
        """GetObjProperty/SetObjProperty from eScript."""
        source = """
        program test(mob)
            SetObjProperty(mob, "SlayType", "Undead");
            var x := GetObjProperty(mob, "SlayType");
        endprogram
        """
        m = Mobile(name="Test")
        executor = run_program_with_args(source, {"mob": m})
        assert executor.scopes.get("x") == "Undead"

    def test_isa_method(self):
        """obj.isa(POLCLASS) from eScript."""
        source = """
        program test(mob)
            var is_mob := mob.isa("Mobile");
        endprogram
        """
        m = Mobile(name="Test")
        executor = run_program_with_args(source, {"mob": m})
        assert executor.scopes.get("is_mob") == 1

    def test_apply_raw_damage(self):
        """ApplyRawDamage recording in simulation context."""
        source = """
        program test(defender)
            ApplyRawDamage(defender, 30);
        endprogram
        """
        m = Mobile(name="Target")
        m.hp = 100
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)

        executor = run_program_with_args(source, {"defender": m})
        assert m.hp == 70
        assert ctx.total_damage_dealt == 30.0


class TestDeflectionOnHitPattern:
    def test_deflection_pattern(self):
        """The full deflectiononhit.src pattern with parms array."""
        source = """
        function ApplyTheDamage(defender, attacker, rawdamage)
            ApplyRawDamage(defender, rawdamage);
        endfunction

        program deflectiononhit(parms)
            var attacker    := parms[1];
            var defender    := parms[2];
            var weapon      := parms[3];
            var armor       := parms[4];
            var basedamage  := parms[5];
            var rawdamage   := parms[6];

            var chance := GetObjProperty(armor, "ChanceOfEffect");
            if (!chance)
                chance := 0;
            endif

            if (GetObjProperty(armor, "Cursed"))
                rawdamage := rawdamage * 2;
            endif

            ApplyTheDamage(defender, attacker, rawdamage);
        endprogram
        """
        attacker = Mobile(name="Attacker")
        defender = Mobile(name="Defender")
        defender.hp = 100
        defender.max_hp = 100
        weapon = Weapon(name="Sword")
        armor = Armor(name="Shield", ar=10)
        armor.set_property("Cursed", 1)

        ctx = SimulationContext()
        set_context(ctx)

        parms = EArray([attacker, defender, weapon, armor, 50, 25])
        executor = run_program_with_args(source, {"parms": parms})

        # Cursed doubles rawdamage: 25*2=50
        assert defender.hp == 50
        assert ctx.total_damage_dealt == 50.0
