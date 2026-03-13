"""Priority 1 — UNINIT consistency tests.

Verifies that UNINIT behaves correctly in all interpreter code paths:
comparisons, logical operators, arithmetic, member access, and indexing.
These test the general principle — every UNINIT interaction is verified.
"""

import omega.runtime  # noqa: F401

from omega.interpreter.types import UNINIT, EArray, EError, EStruct, is_truthy

from .helpers import eval_expr, run_snippet


# ---------------------------------------------------------------------------
# UNINIT Comparisons
# ---------------------------------------------------------------------------


class TestUninitComparisons:
    """UNINIT == UNINIT is true; UNINIT == anything_else is false.
    All comparisons return 1/0 (int), not True/False (bool)."""

    def test_uninit_eq_zero(self):
        assert run_snippet("var u; var x := (u == 0);", "x") == 0

    def test_uninit_eq_empty_string(self):
        assert run_snippet('var u; var x := (u == "");', "x") == 0

    def test_uninit_ne_zero(self):
        assert run_snippet("var u; var x := (u != 0);", "x") == 1

    def test_uninit_ne_empty_string(self):
        assert run_snippet('var u; var x := (u != "");', "x") == 1

    def test_uninit_eq_uninit(self):
        assert run_snippet("var u; var v; var x := (u == v);", "x") == 1

    def test_zero_eq_uninit(self):
        assert run_snippet("var u; var x := (0 == u);", "x") == 0

    def test_empty_string_eq_uninit(self):
        assert run_snippet('var u; var x := ("" == u);', "x") == 0

    def test_uninit_lt_number(self):
        """UNINIT coerces to 0 in _compare, so UNINIT < 5 → 0 < 5 → true."""
        assert run_snippet("var u; var x := (u < 5);", "x") == 1

    def test_uninit_gt_zero(self):
        """UNINIT coerces to 0 in _compare, so UNINIT > 0 → 0 > 0 → false."""
        assert run_snippet("var u; var x := (u > 0);", "x") == 0

    def test_uninit_lte_zero(self):
        """UNINIT coerces to 0, so UNINIT <= 0 → 0 <= 0 → true."""
        assert run_snippet("var u; var x := (u <= 0);", "x") == 1

    def test_uninit_gte_one(self):
        """UNINIT coerces to 0, so UNINIT >= 1 → 0 >= 1 → false."""
        assert run_snippet("var u; var x := (u >= 1);", "x") == 0

    def test_uninit_gt_negative(self):
        """UNINIT coerces to 0, so UNINIT > -1 → 0 > -1 → true."""
        assert run_snippet("var u; var x := (u > -1);", "x") == 1

    def test_comparison_returns_int_not_bool(self):
        """Comparisons return 1/0 (int), not True/False (Python bool)."""
        result = run_snippet("var x := (5 == 5);", "x")
        assert result == 1
        assert isinstance(result, int)
        assert type(result) is int  # not bool subclass


# ---------------------------------------------------------------------------
# UNINIT Logical Operators
# ---------------------------------------------------------------------------


class TestUninitLogical:
    """Short-circuit logical operators with UNINIT. UNINIT is falsy,
    so && short-circuits and || falls through."""

    def test_uninit_and_number(self):
        """UNINIT && 5 → UNINIT (short-circuit, left is falsy)."""
        result = run_snippet("var u; var x := (u && 5);", "x")
        assert result is UNINIT

    def test_uninit_or_number(self):
        """UNINIT || 5 → 5 (left falsy, return right)."""
        assert run_snippet("var u; var x := (u || 5);", "x") == 5

    def test_number_and_uninit(self):
        """5 && UNINIT → UNINIT (left truthy, return right)."""
        result = run_snippet("var u; var x := (5 && u);", "x")
        assert result is UNINIT

    def test_number_or_uninit(self):
        """5 || UNINIT → 5 (short-circuit, left truthy)."""
        assert run_snippet("var u; var x := (5 || u);", "x") == 5

    def test_not_uninit(self):
        """!UNINIT → 1 (UNINIT is falsy, negation is truthy)."""
        assert run_snippet("var u; var x := !u;", "x") == 1

    def test_uninit_and_uninit(self):
        """UNINIT && UNINIT → UNINIT (short-circuit on first)."""
        result = run_snippet("var u; var v; var x := (u && v);", "x")
        assert result is UNINIT

    def test_uninit_or_uninit(self):
        """UNINIT || UNINIT → UNINIT (both falsy, returns right)."""
        result = run_snippet("var u; var v; var x := (u || v);", "x")
        assert result is UNINIT

    def test_guard_pattern_uninit_object(self):
        """obj && obj.field — if obj is UNINIT, short-circuits before .field access."""
        result = run_snippet("var obj; var x := (obj && obj.name);", "x")
        assert result is UNINIT

    def test_or_default_pattern(self):
        """value || default_value — common pattern for fallback values."""
        assert run_snippet("var u; var x := (u || 42);", "x") == 42


# ---------------------------------------------------------------------------
# UNINIT Arithmetic
# ---------------------------------------------------------------------------


class TestUninitArithmetic:
    """UNINIT coerces to 0 in arithmetic via _to_number."""

    def test_uninit_plus_number(self):
        assert run_snippet("var u; var x := u + 5;", "x") == 5

    def test_uninit_minus_number(self):
        assert run_snippet("var u; var x := u - 1;", "x") == -1

    def test_uninit_times_number(self):
        assert run_snippet("var u; var x := u * 3;", "x") == 0

    def test_uninit_div_number(self):
        assert run_snippet("var u; var x := u / 2;", "x") == 0

    def test_number_plus_uninit(self):
        assert run_snippet("var u; var x := 5 + u;", "x") == 5

    def test_number_minus_uninit(self):
        assert run_snippet("var u; var x := 5 - u;", "x") == 5

    def test_number_times_uninit(self):
        assert run_snippet("var u; var x := 5 * u;", "x") == 0

    def test_number_div_uninit(self):
        """5 / UNINIT → 5 / 0 → 0 (div by zero returns 0)."""
        assert run_snippet("var u; var x := 5 / u;", "x") == 0

    def test_uninit_mod_number(self):
        """UNINIT % 3 → 0 % 3 → 0."""
        assert run_snippet("var u; var x := u % 3;", "x") == 0

    def test_uninit_compound_add(self):
        """var x; x += 5; → UNINIT coerces to 0, so x = 5."""
        assert run_snippet("var x; x += 5;", "x") == 5


# ---------------------------------------------------------------------------
# UNINIT Member/Index Access
# ---------------------------------------------------------------------------


class TestUninitMemberIndex:
    """Accessing members or indexing UNINIT returns UNINIT."""

    def test_uninit_member_access(self):
        """UNINIT.field → UNINIT."""
        result = run_snippet("var u; var x := u.name;", "x")
        assert result is UNINIT

    def test_uninit_index_access(self):
        """UNINIT[1] → UNINIT (falls through to UNINIT check)."""
        result = run_snippet("var u; var x := u[1];", "x")
        assert result is UNINIT

    def test_uninit_chained_member(self):
        """UNINIT.field.subfield → UNINIT at each step."""
        result = run_snippet("var u; var x := u.a.b;", "x")
        assert result is UNINIT

    def test_uninit_in_struct_member(self):
        """Struct member that doesn't exist returns UNINIT."""
        code = 'var s := struct{ name := "test" }; var x := s.missing;'
        result = run_snippet(code, "x")
        assert result is UNINIT


# ---------------------------------------------------------------------------
# UNINIT in Conditionals (shard patterns)
# ---------------------------------------------------------------------------


class TestUninitConditionalPatterns:
    """Common shard patterns that depend on UNINIT behavior."""

    def test_if_uninit_is_falsy(self):
        """if (uninit_var) should not execute the body."""
        code = """
        var u;
        var x := 0;
        if (u)
            x := 1;
        endif
        """
        assert run_snippet(code, "x") == 0

    def test_if_not_uninit_is_truthy(self):
        """if (!uninit_var) should execute the body."""
        code = """
        var u;
        var x := 0;
        if (!u)
            x := 1;
        endif
        """
        assert run_snippet(code, "x") == 1

    def test_uninit_in_while_condition(self):
        """while (uninit_var) should not execute."""
        code = """
        var u;
        var x := 0;
        while (u)
            x := x + 1;
        endwhile
        """
        assert run_snippet(code, "x") == 0

    def test_uninit_elvis(self):
        """UNINIT ?: default → default (UNINIT is falsy)."""
        assert run_snippet("var u; var x := u ?: 42;", "x") == 42

    def test_uninit_ne_check(self):
        """if (variable != 0) with UNINIT — UNINIT != 0 is true."""
        code = """
        var u;
        var x := 0;
        if (u != 0)
            x := 1;
        endif
        """
        assert run_snippet(code, "x") == 1
