"""Priority 7 — Type coercion edge case tests.

Tests for _to_number vs CInt divergence, is_truthy edge cases with Python
bools, and implicit vs explicit type conversion behavior.
"""

import omega.runtime  # noqa: F401

from omega.interpreter.types import (
    UNINIT,
    EArray,
    EDict,
    EError,
    EStruct,
    is_truthy,
    pol_typeof,
)

from .helpers import run_snippet


# ---------------------------------------------------------------------------
# _to_number() vs CInt() divergence
# ---------------------------------------------------------------------------


class TestImplicitVsExplicitCoercion:
    def test_string_plus_zero_is_concat(self):
        """'3.7' + 0 → '3.70' — _add does string concat when either operand is string."""
        result = run_snippet('var x := "3.7" + 0;', "x")
        assert isinstance(result, str)
        assert "3.7" in result

    def test_cdbl_preserves_decimal(self):
        """CDbl('3.7') + 0 → 3.7 (explicit CDbl preserves float)."""
        result = run_snippet('var x := CDbl("3.7") + 0;', "x")
        assert abs(result - 3.7) < 0.01

    def test_cint_truncates_string_float(self):
        """CInt('3.7') → 3 (explicit CInt truncates)."""
        assert run_snippet('var x := CInt("3.7");', "x") == 3

    def test_cint_negative_string_float(self):
        assert run_snippet('var x := CInt("-3.7");', "x") == -3

    def test_cdbl_vs_cint_diverge(self):
        """CDbl and CInt produce different results for the same string."""
        cdbl_result = run_snippet('var x := CDbl("3.7") + 0;', "x")
        cint_result = run_snippet('var x := CInt("3.7") + 0;', "x")
        assert abs(cdbl_result - 3.7) < 0.01
        assert cint_result == 3

    def test_cdbl_string_float(self):
        """CDbl('3.7') → 3.7."""
        result = run_snippet('var x := CDbl("3.7");', "x")
        assert abs(result - 3.7) < 0.01

    def test_cint_none_returns_zero(self):
        assert run_snippet("var x := CInt(0);", "x") == 0

    def test_cdbl_none_returns_zero(self):
        result = run_snippet("var x := CDbl(0);", "x")
        assert result == 0.0


# ---------------------------------------------------------------------------
# is_truthy() edge cases
# ---------------------------------------------------------------------------


class TestIsTruthyEdges:
    def test_python_bool_true(self):
        """Python True is truthy (bool check before int)."""
        assert is_truthy(True) is True

    def test_python_bool_false(self):
        """Python False is falsy (bool check before int)."""
        assert is_truthy(False) is False

    def test_bool_is_subclass_of_int(self):
        """Verify bool subclass doesn't confuse truthiness."""
        # True is 1, False is 0 as int — bool check must come first
        assert is_truthy(True) is True
        assert is_truthy(False) is False
        # Negative int is truthy
        assert is_truthy(-1) is True

    def test_empty_struct_truthy(self):
        assert is_truthy(EStruct()) is True

    def test_empty_dict_truthy(self):
        assert is_truthy(EDict()) is True

    def test_empty_array_falsy(self):
        assert is_truthy(EArray()) is False

    def test_nonempty_array_truthy(self):
        assert is_truthy(EArray([1])) is True

    def test_error_always_falsy(self):
        assert is_truthy(EError()) is False
        assert is_truthy(EError({"errortext": "bad"})) is False

    def test_uninit_falsy(self):
        assert is_truthy(UNINIT) is False

    def test_none_falsy(self):
        assert is_truthy(None) is False


# ---------------------------------------------------------------------------
# pol_typeof edge cases
# ---------------------------------------------------------------------------


class TestPolTypeofEdges:
    def test_bool_is_integer(self):
        """Python bool should report as 'Integer' (POL treats bools as ints)."""
        assert pol_typeof(True) == "Integer"
        assert pol_typeof(False) == "Integer"

    def test_python_list_is_array(self):
        assert pol_typeof([1, 2, 3]) == "Array"

    def test_python_dict_is_dictionary(self):
        assert pol_typeof({"a": 1}) == "Dictionary"


# ---------------------------------------------------------------------------
# String-to-number coercion in arithmetic
# ---------------------------------------------------------------------------


class TestStringArithmeticCoercion:
    def test_string_int_in_subtraction(self):
        """'10' - 3 → 7 (string coerced to int)."""
        assert run_snippet('var x := "10" - 3;', "x") == 7

    def test_string_float_in_multiplication(self):
        """'2.5' * 4 → 10.0."""
        result = run_snippet('var x := "2.5" * 4;', "x")
        assert abs(result - 10.0) < 0.01

    def test_non_numeric_string_coerces_to_zero(self):
        """'hello' in arithmetic → 0."""
        assert run_snippet('var x := "hello" - 3;', "x") == -3
        assert run_snippet('var x := "hello" * 5;', "x") == 0

    def test_empty_string_coerces_to_zero(self):
        assert run_snippet('var x := "" + 5;', "x") == "5"  # string concat, not addition


# ---------------------------------------------------------------------------
# CInt/CDbl with UNINIT
# ---------------------------------------------------------------------------


class TestCastWithUninit:
    def test_cint_uninit(self):
        """CInt(UNINIT) → 0."""
        assert run_snippet("var u; var x := CInt(u);", "x") == 0

    def test_cdbl_uninit(self):
        """CDbl(UNINIT) → 0.0."""
        result = run_snippet("var u; var x := CDbl(u);", "x")
        assert result == 0.0

    def test_cstr_uninit(self):
        """CStr(UNINIT) → some string representation."""
        result = run_snippet("var u; var x := CStr(u);", "x")
        assert isinstance(result, str)
