"""Tests for expression evaluation in the interpreter."""

import pytest

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
        # eScript: int / int → integer truncation (like C), not float division
        assert run_snippet("var x := 10 / 3;", "x") == 3

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


# ── Integer division edge cases ─────────────────────────────────────────


class TestIntegerDivisionEdgeCases:
    """eScript int/int division truncates toward zero (C-style).
    This is exercised heavily in the shard: CInt(x / 10), CInt(x / 100),
    damage formulas, PRNG sequences."""

    def test_truncation_basic(self):
        assert run_snippet("var x := 10 / 3;", "x") == 3
        assert run_snippet("var x := 7 / 2;", "x") == 3
        assert run_snippet("var x := 1 / 3;", "x") == 0

    def test_exact_division(self):
        assert run_snippet("var x := 10 / 2;", "x") == 5
        assert run_snippet("var x := 100 / 10;", "x") == 10

    def test_result_type_is_int(self):
        result = run_snippet("var x := 42 / 44488;", "x")
        assert result == 0
        assert isinstance(result, int)

    def test_negative_truncates_toward_zero(self):
        # C-style: -7/2 = -3 (not -4 like Python floor division)
        assert run_snippet("var x := -7 / 2;", "x") == -3
        assert run_snippet("var x := 7 / -2;", "x") == -3
        assert run_snippet("var x := -7 / -2;", "x") == 3

    def test_float_operand_preserves_float(self):
        result = run_snippet("var x := 10.0 / 3;", "x")
        assert isinstance(result, float)
        assert abs(result - 3.333) < 0.01

    def test_float_divisor_preserves_float(self):
        result = run_snippet("var x := 10 / 3.0;", "x")
        assert isinstance(result, float)

    def test_div_by_zero_returns_zero(self):
        assert run_snippet("var x := 10 / 0;", "x") == 0

    def test_div_assign_truncates(self):
        """Compound /= uses the same integer truncation."""
        assert run_snippet("var x := 10; x /= 3;", "x") == 3
        assert run_snippet("var x := 7; x /= 2;", "x") == 3

    def test_div_assign_negative(self):
        assert run_snippet("var x := -7; x /= 2;", "x") == -3

    def test_large_integer_division(self):
        """Large ints from shard PRNG: 44488 * N / M patterns."""
        assert run_snippet("var x := 2836 * 44488;", "x") == 2836 * 44488
        result = run_snippet("var x := 126159 / 44488;", "x")
        assert result == int(126159 / 44488)
        assert isinstance(result, int)

    def test_cint_wrapping_division(self):
        """CInt(x / 10) pattern from attributes.inc — stat conversions."""
        assert run_snippet("var x := CInt(1050 / 10);", "x") == 105
        assert run_snippet("var x := CInt(999 / 100);", "x") == 9
        assert run_snippet("var x := CInt(15000 / 100);", "x") == 150

    def test_nested_division(self):
        """Multi-division: x * y / z (all ints)."""
        # 5 * 6 / 100 = 30 / 100 = 0 (truncated)
        assert run_snippet("var x := 5 * 6 / 100;", "x") == 0
        # (5 * 6) / 100 = 30 / 100 = 0
        assert run_snippet("var x := (5 * 6) / 100;", "x") == 0


# ── Modulo edge cases ───────────────────────────────────────────────────


class TestModuloEdgeCases:
    """eScript modulo follows C/C++ semantics: remainder sign follows the
    dividend (truncation toward zero), not Python's (sign follows divisor)."""

    def test_positive_mod(self):
        assert run_snippet("var x := 10 % 3;", "x") == 1
        assert run_snippet("var x := 7 % 2;", "x") == 1

    def test_negative_dividend(self):
        # C: -7 % 2 = -1 (Python would give 1)
        assert run_snippet("var x := -7 % 2;", "x") == -1

    def test_negative_divisor(self):
        # C: 7 % -2 = 1 (Python would give -1)
        assert run_snippet("var x := 7 % -2;", "x") == 1

    def test_both_negative(self):
        # C: -7 % -2 = -1 (Python would give -1 too, but for different reason)
        assert run_snippet("var x := -7 % -2;", "x") == -1

    def test_mod_by_zero(self):
        assert run_snippet("var x := 10 % 0;", "x") == 0

    def test_mod_assign(self):
        assert run_snippet("var x := 10; x %= 3;", "x") == 1

    def test_mod_assign_negative(self):
        assert run_snippet("var x := -7; x %= 2;", "x") == -1

    def test_mod_assign_by_zero(self):
        assert run_snippet("var x := 10; x %= 0;", "x") == 0

    def test_zero_mod_n(self):
        assert run_snippet("var x := 0 % 5;", "x") == 0

    def test_exact_multiple(self):
        assert run_snippet("var x := 9 % 3;", "x") == 0

    def test_identity_with_division(self):
        """Verify: a == (a / b) * b + (a % b) for C-style truncation."""
        # 10 == (10/3)*3 + (10%3) → 10 == 3*3 + 1 == 10 ✓
        result = run_snippet(
            "var a := 10; var b := 3; var x := (a / b) * b + (a % b);", "x"
        )
        assert result == 10

    def test_identity_negative(self):
        """Same identity for negative: -7 == (-7/2)*2 + (-7%2)."""
        result = run_snippet(
            "var a := -7; var b := 2; var x := (a / b) * b + (a % b);", "x"
        )
        assert result == -7


# ── String indexing edge cases ──────────────────────────────────────────


class TestStringIndexing:
    """eScript string[n] returns the character at 1-based position n.
    str[start, length] returns a substring (tested in TestStringSlicing in
    test_v15_integration.py)."""

    def test_single_index_first_char(self):
        assert run_snippet('var x := "hello"[1];', "x") == "h"

    def test_single_index_middle(self):
        assert run_snippet('var x := "hello"[3];', "x") == "l"

    def test_single_index_last(self):
        assert run_snippet('var x := "hello"[5];', "x") == "o"

    def test_single_index_out_of_bounds(self):
        """Out-of-bounds returns empty string."""
        assert run_snippet('var x := "hello"[6];', "x") == ""
        assert run_snippet('var x := "hello"[0];', "x") == ""

    def test_single_index_negative(self):
        """Negative index is out of bounds."""
        assert run_snippet('var x := "hello"[-1];', "x") == ""

    def test_two_index_slice(self):
        """str[start, length] — 1-based start, second arg is length."""
        assert run_snippet('var x := "hello"[1, 3];', "x") == "hel"
        assert run_snippet('var x := "1d100"[3, 3];', "x") == "100"

    def test_two_index_length_zero(self):
        assert run_snippet('var x := "hello"[1, 0];', "x") == ""

    def test_two_index_length_exceeds(self):
        """Length beyond end of string just truncates."""
        assert run_snippet('var x := "hi"[1, 10];', "x") == "hi"

    def test_array_index_stays_one_based(self):
        """Array indexing must remain 1-based (not broken by string fix)."""
        result = run_snippet("var a := {10, 20, 30}; var x := a[1];", "x")
        assert result == 10
        result2 = run_snippet("var a := {10, 20, 30}; var x := a[3];", "x")
        assert result2 == 30

    def test_list_index_stays_one_based(self):
        """Python list indexing through _get_index is 1-based."""
        result = run_snippet("var a := {10, 20, 30}; var x := a[2];", "x")
        assert result == 20


# ── Type coercion in arithmetic ─────────────────────────────────────────


class TestTypeCoercionArithmetic:
    """Tests for _to_number / _to_int coercion paths exercised by arithmetic
    operators. The shard relies on implicit coercion in expressions like
    CInt(GetAttributeBaseValue(...) / 10)."""

    def test_string_number_in_division(self):
        """String operands coerced to numbers for arithmetic."""
        # "10" / "3" → both coerced to int → 10 / 3 = 3
        assert run_snippet('var x := CInt("10") / CInt("3");', "x") == 3

    def test_string_float_in_arithmetic(self):
        assert run_snippet('var x := CDbl("3.14") * 2;', "x") == pytest.approx(6.28)

    def test_uninit_in_addition(self):
        """UNINIT coerces to 0 in arithmetic."""
        result = run_snippet("var u; var x := u + 5;", "x")
        assert result == 5

    def test_uninit_in_multiplication(self):
        result = run_snippet("var u; var x := u * 10;", "x")
        assert result == 0

    def test_uninit_in_division(self):
        result = run_snippet("var u; var x := u / 5;", "x")
        assert result == 0

    def test_int_plus_float_returns_float(self):
        result = run_snippet("var x := 5 + 3.14;", "x")
        assert isinstance(result, float)

    def test_int_mul_float_returns_float(self):
        result = run_snippet("var x := 5 * 0.005;", "x")
        assert isinstance(result, float)
        assert abs(result - 0.025) < 0.001

    def test_mul_assign_with_float(self):
        """basedamage *= 0.4 pattern from shard PvP scaling."""
        result = run_snippet("var x := 100; x *= 0.4;", "x")
        assert isinstance(result, float)
        assert abs(result - 40.0) < 0.001

    def test_mul_assign_chain(self):
        """basedamage *= factor1; basedamage *= factor2 (two-stage PvP scaling)."""
        result = run_snippet("var x := 100; x *= 0.4; x *= 0.6;", "x")
        assert abs(result - 24.0) < 0.001

    def test_cint_truncation_on_float(self):
        """CInt applied to float result truncates toward zero."""
        assert run_snippet("var x := CInt(3.7);", "x") == 3
        assert run_snippet("var x := CInt(3.2);", "x") == 3
        assert run_snippet("var x := CInt(-3.7);", "x") == -3


# ── Compound assignment edge cases ──────────────────────────────────────


class TestCompoundAssignment:
    """Compound assignment operators must follow the same semantics as their
    binary counterparts (integer truncation for /=, C-style for %=, etc.)."""

    def test_add_assign_string_concat(self):
        """+=  with strings concatenates."""
        result = run_snippet('var x := "hello"; x += " world";', "x")
        assert result == "hello world"

    def test_add_assign_mixed_type(self):
        """string += int → concatenation."""
        result = run_snippet('var x := "value: "; x += 42;', "x")
        assert result == "value: 42"

    def test_sub_assign_type_coercion(self):
        result = run_snippet("var x := 10; x -= 3.5;", "x")
        assert isinstance(result, float)
        assert abs(result - 6.5) < 0.001

    def test_mul_assign_type_promotion(self):
        """int *= float promotes to float."""
        result = run_snippet("var x := 100; x *= 1.5;", "x")
        assert isinstance(result, float)
        assert abs(result - 150.0) < 0.001

    def test_div_assign_int_truncation(self):
        """/= with int/int truncates."""
        assert run_snippet("var x := 10; x /= 3;", "x") == 3
        assert run_snippet("var x := -7; x /= 2;", "x") == -3

    def test_div_assign_by_zero(self):
        assert run_snippet("var x := 10; x /= 0;", "x") == 0

    def test_mod_assign_c_style(self):
        assert run_snippet("var x := -7; x %= 2;", "x") == -1

    def test_mod_assign_by_zero(self):
        assert run_snippet("var x := 10; x %= 0;", "x") == 0


# ── String concatenation edge cases ─────────────────────────────────────


class TestStringConcatEdgeCases:
    """Edge cases in _add when one or both operands are strings.
    The shard uses string + int extensively in debug messages."""

    def test_float_plus_string(self):
        result = run_snippet('var x := 3.14 + " meters";', "x")
        assert "3.14" in result

    def test_zero_plus_string(self):
        result = run_snippet('var x := 0 + " items";', "x")
        assert result == "0 items"

    def test_string_interpolation_ops(self):
        """The .+ .? .- operators all produce string concatenation."""
        assert run_snippet('var x := "a" .+ "b";', "x") == "ab"

    def test_negative_number_concat(self):
        result = run_snippet('var x := "temp: " + -5;', "x")
        assert result == "temp: -5"

    def test_concat_preserves_int_format(self):
        """Integer concatenation should not add .0 suffix."""
        result = run_snippet('var x := "AR is: " + 30;', "x")
        assert result == "AR is: 30"

    def test_concat_chain(self):
        """Chained concatenation (common in shard debug messages)."""
        result = run_snippet(
            'var x := "Damage: " + 42 + " absorbed: " + 10;', "x"
        )
        assert result == "Damage: 42 absorbed: 10"


# ── Increment / Decrement ───────────────────────────────────────────────


class TestIncrementDecrement:
    """Prefix ++ and -- operators used in shard loop counters."""

    def test_prefix_increment(self):
        assert run_snippet("var x := 5; ++x;", "x") == 6

    def test_prefix_decrement(self):
        assert run_snippet("var x := 5; --x;", "x") == 4

    def test_prefix_increment_returns_new_value(self):
        assert run_snippet("var x := 5; var y := ++x;", "y") == 6

    def test_prefix_decrement_returns_new_value(self):
        assert run_snippet("var x := 5; var y := --x;", "y") == 4
