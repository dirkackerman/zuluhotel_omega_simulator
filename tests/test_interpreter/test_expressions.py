"""Tests for expression evaluation in the interpreter."""

import omega.runtime  # noqa: F401  — register stubs
from omega.interpreter.executor import Executor
from omega.interpreter.types import UNINIT, EArray, EDict, EError, EStruct
from omega.parser.parser import parse_text

from .helpers import eval_expr, run_snippet


class TestLiterals:
    def test_integer(self):
        assert eval_expr("42") == 42

    def test_hex(self):
        assert eval_expr("0xFF") == 255

    def test_float(self):
        assert eval_expr("3.14") == 3.14

    def test_string(self):
        assert eval_expr('"hello"') == "hello"

    def test_zero_literal(self):
        assert eval_expr("0") == 0


class TestArithmetic:
    def test_add(self):
        assert run_snippet("var x := 2 + 3;", "x") == 5

    def test_sub(self):
        assert run_snippet("var x := 10 - 4;", "x") == 6

    def test_mul(self):
        assert run_snippet("var x := 3 * 7;", "x") == 21

    def test_div(self):
        assert run_snippet("var x := 10 / 3;", "x") == 10 / 3

    def test_div_exact(self):
        assert run_snippet("var x := 10 / 2;", "x") == 5

    def test_mod(self):
        assert run_snippet("var x := 10 % 3;", "x") == 1

    def test_precedence(self):
        assert run_snippet("var x := 2 + 3 * 4;", "x") == 14

    def test_parens(self):
        assert run_snippet("var x := (2 + 3) * 4;", "x") == 20

    def test_unary_minus(self):
        assert run_snippet("var x := -5;", "x") == -5


class TestStringConcat:
    def test_string_plus_string(self):
        assert run_snippet('var x := "hello" + " " + "world";', "x") == "hello world"

    def test_string_plus_int(self):
        assert run_snippet('var x := "value: " + 42;', "x") == "value: 42"

    def test_int_plus_string(self):
        assert run_snippet('var x := 10 + " items";', "x") == "10 items"


class TestComparison:
    def test_equal(self):
        assert run_snippet("var x := (5 == 5);", "x") == 1

    def test_not_equal(self):
        assert run_snippet("var x := (5 != 3);", "x") == 1

    def test_less_than(self):
        assert run_snippet("var x := (3 < 5);", "x") == 1

    def test_greater_than(self):
        assert run_snippet("var x := (5 > 3);", "x") == 1

    def test_lte(self):
        assert run_snippet("var x := (5 <= 5);", "x") == 1

    def test_gte(self):
        assert run_snippet("var x := (5 >= 6);", "x") == 0

    def test_diamond_ne(self):
        assert run_snippet("var x := (1 <> 2);", "x") == 1


class TestLogical:
    def test_and_true(self):
        assert run_snippet("var x := (1 && 2);", "x") == 2

    def test_and_false(self):
        assert run_snippet("var x := (0 && 2);", "x") == 0

    def test_or_true(self):
        assert run_snippet("var x := (0 || 5);", "x") == 5

    def test_or_short_circuit(self):
        assert run_snippet("var x := (3 || 0);", "x") == 3

    def test_not(self):
        assert run_snippet("var x := !1;", "x") == 0

    def test_not_zero(self):
        assert run_snippet("var x := !0;", "x") == 1

    def test_and_keyword(self):
        assert run_snippet("var x := (1 and 2);", "x") == 2

    def test_or_keyword(self):
        assert run_snippet("var x := (0 or 5);", "x") == 5


class TestBitwise:
    def test_and(self):
        assert run_snippet("var x := 0xFF & 0x0F;", "x") == 0x0F

    def test_or(self):
        assert run_snippet("var x := 0xF0 | 0x0F;", "x") == 0xFF

    def test_shift_left(self):
        assert run_snippet("var x := 1 << 4;", "x") == 16

    def test_shift_right(self):
        assert run_snippet("var x := 16 >> 4;", "x") == 1

    def test_tilde(self):
        assert run_snippet("var x := ~0;", "x") == -1


class TestAssignment:
    def test_assign(self):
        assert run_snippet("var x := 0; x := 42;", "x") == 42

    def test_add_assign(self):
        assert run_snippet("var x := 10; x += 5;", "x") == 15

    def test_sub_assign(self):
        assert run_snippet("var x := 10; x -= 3;", "x") == 7

    def test_mul_assign(self):
        assert run_snippet("var x := 5; x *= 3;", "x") == 15

    def test_div_assign(self):
        assert run_snippet("var x := 10; x /= 2;", "x") == 5


class TestElvis:
    def test_truthy(self):
        assert run_snippet("var x := 5 ?: 10;", "x") == 5

    def test_falsy(self):
        assert run_snippet("var x := 0 ?: 10;", "x") == 10


class TestInOperator:
    def test_in_array(self):
        assert run_snippet("var x := (2 in {1, 2, 3});", "x") == 1

    def test_not_in_array(self):
        assert run_snippet("var x := (5 in {1, 2, 3});", "x") == 0


class TestInitializers:
    def test_bare_array(self):
        result = run_snippet("var x := {10, 20, 30};", "x")
        assert isinstance(result, EArray)
        assert result.get(1) == 10
        assert result.get(3) == 30

    def test_explicit_array(self):
        result = run_snippet("var x := array{1, 2};", "x")
        assert isinstance(result, EArray)
        assert len(result) == 2

    def test_empty_array(self):
        result = run_snippet("var x := array;", "x")
        assert isinstance(result, EArray)
        assert len(result) == 0

    def test_struct(self):
        result = run_snippet('var x := struct{ name := "test", value := 42 };', "x")
        assert isinstance(result, EStruct)
        assert result.get_member("name") == "test"
        assert result.get_member("value") == 42

    def test_dictionary(self):
        result = run_snippet("var x := dictionary;", "x")
        assert isinstance(result, EDict)

    def test_error(self):
        result = run_snippet('var x := error{ errortext := "bad" };', "x")
        assert isinstance(result, EError)
        assert result.errortext == "bad"
