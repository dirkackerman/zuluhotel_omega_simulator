"""Tests for parsing individual eScript language constructs."""

from omega.parser import parse_text


class TestVariables:
    def test_var_declaration(self):
        r = parse_text("var x;")
        assert r.success

    def test_var_with_initializer(self):
        r = parse_text("var x := 5;")
        assert r.success

    def test_var_multiple(self):
        r = parse_text("var x := 1, y := 2, z;")
        assert r.success

    def test_const(self):
        r = parse_text("const MY_VAL := 42;")
        assert r.success

    def test_var_array_initializer(self):
        r = parse_text("var x := array{1, 2, 3};")
        assert r.success

    def test_var_struct_initializer(self):
        r = parse_text('var s := struct{"name" := "foo", "value" := 5};')
        assert r.success

    def test_var_dictionary_initializer(self):
        r = parse_text('var d := dictionary{"a" -> 1, "b" -> 2};')
        assert r.success


class TestControlFlow:
    def test_if_endif(self):
        r = parse_text("if (x) var y := 1; endif")
        assert r.success

    def test_if_then_endif(self):
        r = parse_text("if (x) then var y := 1; endif")
        assert r.success

    def test_if_else_endif(self):
        r = parse_text("if (x) var y := 1; else var y := 2; endif")
        assert r.success

    def test_if_elseif_else_endif(self):
        r = parse_text("if (x) var a := 1; elseif (y) var b := 2; else var c := 3; endif")
        assert r.success

    def test_while_endwhile(self):
        r = parse_text("while (x > 0) x := x - 1; endwhile")
        assert r.success

    def test_do_dowhile(self):
        r = parse_text("do x := x + 1; dowhile (x < 10);")
        assert r.success

    def test_for_cstyle(self):
        r = parse_text("for (i := 0; i < 10; i := i + 1) var x := i; endfor")
        assert r.success

    def test_for_basic(self):
        r = parse_text("for i := 1 to 10 var x := i; endfor")
        assert r.success

    def test_foreach(self):
        r = parse_text("foreach item in myarray var x := item; endforeach")
        assert r.success

    def test_repeat_until(self):
        r = parse_text("repeat x := x + 1; until (x >= 10);")
        assert r.success

    def test_case_endcase(self):
        r = parse_text('case (x) 1: var a := 1; 2: var b := 2; default: var c := 0; endcase')
        assert r.success

    def test_break(self):
        r = parse_text("while (1) break; endwhile")
        assert r.success

    def test_continue(self):
        r = parse_text("while (1) continue; endwhile")
        assert r.success

    def test_return(self):
        r = parse_text("function foo() return 5; endfunction")
        assert r.success

    def test_exit(self):
        r = parse_text("program main() exit; endprogram")
        assert r.success


class TestFunctions:
    def test_simple_function(self):
        r = parse_text("function add(a, b) return a + b; endfunction")
        assert r.success

    def test_exported_function(self):
        r = parse_text("exported function MyFunc() return 1; endfunction")
        assert r.success

    def test_function_byref_param(self):
        r = parse_text("function modify(byref x) x := x + 1; endfunction")
        assert r.success

    def test_function_default_param(self):
        r = parse_text("function greet(name := \"world\") return name; endfunction")
        assert r.success

    def test_function_unused_param(self):
        r = parse_text("function foo(unused bar) return 1; endfunction")
        assert r.success

    def test_program_block(self):
        r = parse_text("program main(attacker, defender) var x := 1; endprogram")
        assert r.success

    def test_program_unused_param(self):
        r = parse_text("program test(unused param1) endprogram")
        assert r.success


class TestExpressions:
    def test_arithmetic(self):
        r = parse_text("var x := 1 + 2 * 3 - 4 / 2;")
        assert r.success

    def test_comparison(self):
        r = parse_text("var x := a > b;")
        assert r.success

    def test_logical_operators(self):
        r = parse_text("var x := a && b || !c;")
        assert r.success

    def test_logical_word_operators(self):
        r = parse_text("var x := a and b or not c;")
        assert r.success

    def test_assignment_operators(self):
        for op in [":=", "+=", "-=", "*=", "/=", "%="]:
            r = parse_text(f"x {op} 5;")
            assert r.success, f"Failed for operator {op}"

    def test_member_access(self):
        r = parse_text("var x := obj.property;")
        assert r.success

    def test_method_call(self):
        r = parse_text("var x := obj.method(a, b);")
        assert r.success

    def test_array_indexing(self):
        r = parse_text("var x := arr[1];")
        assert r.success

    def test_function_call(self):
        r = parse_text("var x := foo(1, 2, 3);")
        assert r.success

    def test_scoped_function_call(self):
        r = parse_text("var x := uo::GetObjProperty(obj, name);")
        assert r.success

    def test_isa_method(self):
        r = parse_text("var x := obj.isa(POLCLASS_NPC);")
        assert r.success

    def test_elvis_operator(self):
        r = parse_text("var x := a ?: b;")
        assert r.success

    def test_in_operator(self):
        r = parse_text("var x := item in container;")
        assert r.success

    def test_bitwise_operators(self):
        r = parse_text("var x := a & b | c ^ d;")
        assert r.success

    def test_string_literal(self):
        r = parse_text('var x := "hello world";')
        assert r.success

    def test_hex_literal(self):
        r = parse_text("var x := 0xFF01;")
        assert r.success

    def test_unary_operators(self):
        r = parse_text("var x := -a; var y := ~b;")
        assert r.success

    def test_nested_member_access(self):
        r = parse_text("var x := attacker.weapon.damage;")
        assert r.success

    def test_function_reference(self):
        r = parse_text("var f := @myfunction;")
        assert r.success

    def test_member_add_remove(self):
        r = parse_text("x .+ y; x .- z; x .? w;")
        assert r.success


class TestModules:
    def test_use_declaration(self):
        r = parse_text('use uo;')
        assert r.success

    def test_use_string(self):
        r = parse_text('use "cfgfile";')
        assert r.success

    def test_include_declaration(self):
        r = parse_text('include "include/damages";')
        assert r.success

    def test_include_package(self):
        r = parse_text('include ":combat:hitscriptinc";')
        assert r.success


class TestEnum:
    def test_enum(self):
        r = parse_text("enum MyEnum A, B := 5, C endenum")
        assert r.success


class TestComposite:
    """Test patterns that appear in real shard scripts."""

    def test_typical_hitscript_pattern(self):
        code = """
use uo;
use os;

include ":combat:hitscriptinc";
include "include/damages";

program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
    if (TypeOf(attacker) == "Array")
        defender := attacker[2];
        weapon := attacker[3];
    endif

    rawdamage := RecalcDmg(attacker, defender, weapon, armor, basedamage);
    DealDamage(attacker, defender, weapon, armor, basedamage, rawdamage);
endprogram
"""
        r = parse_text(code)
        assert r.success, f"Errors: {r.errors}"

    def test_property_access_pattern(self):
        code = """
function GetSlayMultiplier(weapon, defender)
    var slaytype := GetObjProperty(weapon, "SlayType");
    var deftype := GetObjProperty(defender, "Type");
    if (!slaytype || !deftype)
        return 1.0;
    endif
    if (slaytype == deftype)
        return 2.0;
    endif
    return 1.0;
endfunction
"""
        r = parse_text(code)
        assert r.success, f"Errors: {r.errors}"

    def test_foreach_with_method_calls(self):
        code = """
function CheckItems(mobile)
    foreach item in ListEquippedItems(mobile)
        if (item.isa(POLCLASS_ARMOR))
            var ar := GetObjProperty(item, "AR");
            if (ar > 0)
                return ar;
            endif
        endif
    endforeach
    return 0;
endfunction
"""
        r = parse_text(code)
        assert r.success, f"Errors: {r.errors}"
