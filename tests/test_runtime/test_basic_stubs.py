"""Tests for Batch 1 — trivial POL built-in stubs."""

import math as pymath

import omega.runtime  # noqa: F401
from omega.interpreter.types import UNINIT
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.registry import call_builtin
from omega.runtime.rng import set_rng_seed


# ---------------------------------------------------------------------------
# Type casts
# ---------------------------------------------------------------------------


class TestTypeCasts:
    def test_cint_string(self):
        assert call_builtin("", "CInt", ["42"]) == 42

    def test_cint_float(self):
        assert call_builtin("", "CInt", [3.7]) == 3

    def test_cint_none(self):
        assert call_builtin("", "CInt", [None]) == 0

    def test_cint_uninit(self):
        assert call_builtin("", "CInt", [UNINIT]) == 0

    def test_cint_negative_string(self):
        assert call_builtin("", "CInt", ["-42"]) == -42

    def test_cint_float_string(self):
        """POL CInt('3.7') → 3 via strtol. Must not return 0."""
        assert call_builtin("", "CInt", ["3.7"]) == 3

    def test_cint_negative_float_string(self):
        assert call_builtin("", "CInt", ["-3.7"]) == -3

    def test_cdbl_string(self):
        assert call_builtin("", "CDbl", ["3.14"]) == 3.14

    def test_cdbl_int(self):
        assert call_builtin("", "CDbl", [5]) == 5.0

    def test_cdbl_none(self):
        assert call_builtin("", "CDbl", [None]) == 0.0

    def test_cdbl_uninit(self):
        assert call_builtin("", "CDbl", [UNINIT]) == 0.0

    def test_cdbl_negative(self):
        assert call_builtin("", "CDbl", ["-3.14"]) == -3.14

    def test_cstr(self):
        assert call_builtin("", "CStr", [42]) == "42"

    def test_cstr_none(self):
        assert call_builtin("", "CStr", [None]) == ""

    def test_cstr_uninit(self):
        result = call_builtin("", "CStr", [UNINIT])
        assert isinstance(result, str)

    def test_cstr_float(self):
        assert call_builtin("", "CStr", [3.14]) == "3.14"

    def test_hex(self):
        assert call_builtin("", "Hex", [255]) == "0xff"

    def test_hex_uninit(self):
        assert call_builtin("", "Hex", [UNINIT]) == "0x0"

    def test_hex_negative(self):
        result = call_builtin("", "Hex", [-1])
        assert isinstance(result, str)

    def test_max_returns_float(self):
        """POL Max coerces to Double."""
        result = call_builtin("", "Max", [3, 7])
        assert result == 7.0
        assert isinstance(result, float)

    def test_min_returns_float(self):
        """POL Min coerces to Double."""
        result = call_builtin("", "Min", [3, 7])
        assert result == 3.0
        assert isinstance(result, float)

    def test_max_uninit_a(self):
        assert call_builtin("", "Max", [UNINIT, 5]) == 5.0

    def test_max_uninit_b(self):
        assert call_builtin("", "Max", [5, UNINIT]) == 5.0

    def test_min_uninit(self):
        assert call_builtin("", "Min", [UNINIT, 5]) == 0.0

    def test_max_floats(self):
        assert call_builtin("", "Max", [3.5, 2.1]) == 3.5

    def test_min_floats(self):
        assert call_builtin("", "Min", [3.5, 2.1]) == 2.1

    def test_max_mixed_int_float(self):
        assert call_builtin("", "Max", [3, 3.5]) == 3.5


# ---------------------------------------------------------------------------
# Type queries
# ---------------------------------------------------------------------------


class TestTypeQueries:
    def test_typeof_int(self):
        assert call_builtin("", "TypeOf", [42]) == "Integer"

    def test_typeof_float(self):
        assert call_builtin("", "TypeOf", [3.14]) == "Double"

    def test_typeof_string(self):
        assert call_builtin("", "TypeOf", ["hello"]) == "String"

    def test_typeof_array(self):
        assert call_builtin("", "TypeOf", [[1, 2]]) == "Array"

    def test_typeof_none(self):
        assert call_builtin("", "TypeOf", [None]) == "Uninit"

    def test_typeof_dict(self):
        assert call_builtin("", "TypeOf", [{"a": 1}]) == "Dictionary"

    def test_typeof_uninit(self):
        assert call_builtin("", "TypeOf", [UNINIT]) == "Uninit"

    def test_typeof_bool(self):
        assert call_builtin("", "TypeOf", [True]) == "Integer"

    def test_len_array(self):
        assert call_builtin("", "Len", [[1, 2, 3]]) == 3

    def test_len_string(self):
        assert call_builtin("", "Len", ["hello"]) == 5

    def test_len_none(self):
        assert call_builtin("", "Len", [None]) == 0

    def test_len_dict(self):
        assert call_builtin("", "Len", [{"a": 1, "b": 2}]) == 2

    def test_len_uninit(self):
        assert call_builtin("", "Len", [UNINIT]) == 0

    def test_len_int(self):
        assert call_builtin("", "Len", [42]) == 0


# ---------------------------------------------------------------------------
# Math
# ---------------------------------------------------------------------------


class TestMathOps:
    def test_pow(self):
        result = call_builtin("math", "Pow", [2, 10])
        assert result == 1024.0

    def test_pow_fractional(self):
        result = call_builtin("math", "Pow", [25, 0.5])
        assert abs(result - 5.0) < 0.001

    def test_pow_returns_float(self):
        """POL Pow() always returns Double."""
        result = call_builtin("math", "Pow", [2, 3])
        assert result == 8.0
        assert isinstance(result, float)

    def test_pow_uninit_base(self):
        assert call_builtin("math", "Pow", [UNINIT, 2]) == 0.0

    def test_pow_uninit_exp(self):
        assert call_builtin("math", "Pow", [2, UNINIT]) == 0.0

    def test_pow_zero_exp(self):
        assert call_builtin("math", "Pow", [5, 0]) == 1.0

    def test_pow_negative_exp(self):
        assert call_builtin("math", "Pow", [2, -1]) == 0.5

    def test_abs_negative(self):
        assert call_builtin("", "Abs", [-42]) == 42

    def test_abs_positive(self):
        assert call_builtin("", "Abs", [42]) == 42

    def test_abs_uninit(self):
        assert call_builtin("", "Abs", [UNINIT]) == 0

    def test_abs_float(self):
        assert call_builtin("", "Abs", [-3.14]) == 3.14

    def test_sqrt(self):
        result = call_builtin("math", "Sqrt", [16])
        assert abs(result - 4.0) < 0.001

    def test_sqrt_negative(self):
        assert call_builtin("math", "Sqrt", [-1]) == 0.0

    def test_sqrt_uninit(self):
        assert call_builtin("math", "Sqrt", [UNINIT]) == 0.0

    def test_sqrt_zero(self):
        assert call_builtin("math", "Sqrt", [0]) == 0.0

    def test_sqrt_float(self):
        result = call_builtin("math", "Sqrt", [2.0])
        assert abs(result - 1.41421) < 0.001

    def test_log_e_positive(self):
        result = call_builtin("math", "LogE", [pymath.e])
        assert abs(result - 1.0) < 0.001

    def test_log_e_one(self):
        assert call_builtin("math", "LogE", [1]) == 0.0

    def test_log_e_uninit(self):
        assert call_builtin("math", "LogE", [UNINIT]) == 0.0

    def test_log_e_zero(self):
        assert call_builtin("math", "LogE", [0]) == 0.0

    def test_log_e_negative(self):
        assert call_builtin("math", "LogE", [-5]) == 0.0

    def test_sin_zero(self):
        assert call_builtin("math", "Sin", [0]) == 0.0

    def test_cos_zero(self):
        assert call_builtin("math", "Cos", [0]) == 1.0

    def test_sin_uninit(self):
        assert call_builtin("math", "Sin", [UNINIT]) == 0.0

    def test_cos_uninit(self):
        assert call_builtin("math", "Cos", [UNINIT]) == 0.0


# ---------------------------------------------------------------------------
# Random
# ---------------------------------------------------------------------------


class TestRandom:
    def test_random_deterministic(self):
        set_rng_seed(42)
        val1 = call_builtin("", "Random", [100])

        set_rng_seed(42)
        val2 = call_builtin("", "Random", [100])

        assert val1 == val2

    def test_random_bounds(self):
        set_rng_seed(0)
        for _ in range(50):
            val = call_builtin("", "Random", [10])
            assert 1 <= val <= 10

    def test_random_int_bounds(self):
        set_rng_seed(0)
        for _ in range(50):
            val = call_builtin("", "RandomInt", [10])
            assert 0 <= val <= 9

    def test_random_uninit(self):
        assert call_builtin("", "Random", [UNINIT]) == 0

    def test_random_int_uninit(self):
        assert call_builtin("", "RandomInt", [UNINIT]) == 0

    def test_random_zero(self):
        assert call_builtin("", "Random", [0]) == 0

    def test_random_negative(self):
        assert call_builtin("", "Random", [-5]) == 0

    def test_random_int_zero(self):
        assert call_builtin("", "RandomInt", [0]) == 0

    def test_random_string(self):
        set_rng_seed(0)
        val = call_builtin("", "Random", ["10"])
        assert 1 <= val <= 10

    def test_random_float_val(self):
        set_rng_seed(0)
        val = call_builtin("", "Random", [10.7])
        assert 1 <= val <= 10  # int(10.7) = 10

    def test_random_float_func(self):
        set_rng_seed(0)
        val = call_builtin("", "RandomFloat", [])
        assert isinstance(val, float)
        assert 0.0 <= val < 1.0

    def test_random_float_uninit(self):
        set_rng_seed(0)
        val = call_builtin("", "RandomFloat", [UNINIT])
        assert isinstance(val, float)
        assert 0.0 <= val < 1.0  # defaults to limit=1.0

    def test_random_float_limit(self):
        set_rng_seed(0)
        val = call_builtin("", "RandomFloat", [5.0])
        assert isinstance(val, float)
        assert 0.0 <= val < 5.0


# ---------------------------------------------------------------------------
# RandomDiceRoll
# ---------------------------------------------------------------------------


class TestRandomDiceRoll:
    def test_dice_simple(self):
        set_rng_seed(42)
        val = call_builtin("", "RandomDiceRoll", ["1d6"])
        assert 1 <= val <= 6

    def test_dice_multiple(self):
        set_rng_seed(42)
        val = call_builtin("", "RandomDiceRoll", ["3d6"])
        assert 3 <= val <= 18

    def test_dice_bonus(self):
        set_rng_seed(42)
        val = call_builtin("", "RandomDiceRoll", ["2d6+4"])
        assert 6 <= val <= 16

    def test_dice_penalty_clamped(self):
        """With allow_negatives=0, result is clamped to 0."""
        set_rng_seed(42)
        val = call_builtin("", "RandomDiceRoll", ["1d6-100", 0])
        assert val == 0

    def test_dice_penalty_allowed(self):
        """With allow_negatives=1, result can be negative."""
        set_rng_seed(42)
        val = call_builtin("", "RandomDiceRoll", ["1d6-100", 1])
        assert val < 0

    def test_dice_none(self):
        assert call_builtin("", "RandomDiceRoll", [None]) == 0

    def test_dice_uninit(self):
        # str(UNINIT) = "UNINIT", no match, falls through to int("uninit") → 0
        assert call_builtin("", "RandomDiceRoll", [UNINIT]) == 0

    def test_dice_plain_number(self):
        assert call_builtin("", "RandomDiceRoll", ["10"]) == 10

    def test_dice_deterministic(self):
        set_rng_seed(99)
        val1 = call_builtin("", "RandomDiceRoll", ["3d6+2"])
        set_rng_seed(99)
        val2 = call_builtin("", "RandomDiceRoll", ["3d6+2"])
        assert val1 == val2

    def test_dice_zero_faces(self):
        set_rng_seed(0)
        # "1d0" — faces=0, each die contributes 0, total = bonus + num_dice
        val = call_builtin("", "RandomDiceRoll", ["1d0"])
        assert val == 1  # bonus=0 + num_dice=1 + 0 per die


# ---------------------------------------------------------------------------
# String operations
# ---------------------------------------------------------------------------


class TestStringOps:
    def test_split_words(self):
        result = call_builtin("", "SplitWords", ["FIRE:50 PHYSICAL:50"])
        assert result == ["FIRE:50", "PHYSICAL:50"]

    def test_split_words_delim(self):
        result = call_builtin("", "SplitWords", ["a:b:c", ":"])
        assert result == ["a", "b", "c"]

    def test_split_words_uninit_delim(self):
        """UNINIT delimiter should fall back to whitespace split."""
        result = call_builtin("", "SplitWords", ["a b", UNINIT])
        assert result == ["a", "b"]

    def test_split_words_empty(self):
        assert call_builtin("", "SplitWords", [""]) == []

    def test_split_words_uninit_text(self):
        result = call_builtin("", "SplitWords", [UNINIT])
        assert isinstance(result, list)

    def test_lower(self):
        assert call_builtin("", "Lower", ["HELLO"]) == "hello"

    def test_upper(self):
        assert call_builtin("", "Upper", ["hello"]) == "HELLO"

    def test_lower_uninit(self):
        result = call_builtin("", "Lower", [UNINIT])
        assert isinstance(result, str)

    def test_upper_uninit(self):
        result = call_builtin("", "Upper", [UNINIT])
        assert isinstance(result, str)

    def test_lower_none(self):
        assert call_builtin("", "Lower", [None]) == ""

    def test_upper_none(self):
        assert call_builtin("", "Upper", [None]) == ""

    def test_substr(self):
        # POL uses 1-based indexing
        assert call_builtin("", "SubStr", ["Hello", 1, 3]) == "Hel"

    def test_substr_no_length(self):
        assert call_builtin("", "SubStr", ["Hello", 2]) == "ello"

    def test_substr_uninit_start(self):
        """UNINIT start defaults to beginning of string."""
        result = call_builtin("", "SubStr", ["hello", UNINIT])
        assert result == "hello"

    def test_substr_uninit_length(self):
        """UNINIT length returns rest of string."""
        result = call_builtin("", "SubStr", ["hello", 1, UNINIT])
        assert result == "hello"

    def test_substr_zero_start(self):
        """start=0 should clamp to beginning, not return last char."""
        result = call_builtin("", "SubStr", ["hello", 0])
        assert result == "hello"

    def test_substr_negative_start(self):
        """Negative start clamps to beginning."""
        result = call_builtin("", "SubStr", ["hello", -1])
        assert result == "hello"

    def test_find_basic(self):
        assert call_builtin("", "Find", ["Hello World", "World"]) == 7

    def test_find_not_found(self):
        assert call_builtin("", "Find", ["Hello", "xyz"]) == 0

    def test_find_start_offset(self):
        assert call_builtin("", "Find", ["abcabc", "abc", 2]) == 4

    def test_find_uninit_start(self):
        """UNINIT start defaults to offset=0 (search from beginning)."""
        result = call_builtin("", "Find", ["hello", "h", UNINIT])
        assert result == 1

    def test_find_empty_needle(self):
        """Empty string is found at position 1."""
        assert call_builtin("", "Find", ["hello", ""]) == 1

    def test_find_uninit_text(self):
        # str(UNINIT) → "UNINIT", search for "x" → 0
        result = call_builtin("", "Find", [UNINIT, "x"])
        assert result == 0

    def test_find_uninit_search(self):
        # str(UNINIT) → "UNINIT", search for "UNINIT" in text
        result = call_builtin("", "Find", ["hello", UNINIT])
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------


class TestTime:
    def test_read_game_clock(self):
        ctx = SimulationContext(game_clock=5000)
        set_context(ctx)
        result = call_builtin("os", "ReadGameClock", [])
        assert result == 5000


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------


class TestMessaging:
    def test_send_sys_message_silent_by_default(self):
        """No error when debug_mode is off."""
        ctx = SimulationContext(debug_mode=False)
        set_context(ctx)
        call_builtin("uo", "SendSysMessage", [None, "test message"])

    def test_send_sys_message_debug_mode(self):
        """No error when debug_mode is on."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        call_builtin("uo", "SendSysMessage", [None, "debug output"])


# ---------------------------------------------------------------------------
# No-ops
# ---------------------------------------------------------------------------


class TestNoOps:
    def test_perform_action(self):
        call_builtin("uo", "PerformAction", [None, 0x20])

    def test_play_sound(self):
        call_builtin("uo", "PlaySoundEffect", [None, 0x100])

    def test_inc_revision(self):
        call_builtin("uo", "IncRevision", [None])

    def test_set_critical(self):
        call_builtin("os", "set_critical", [1])

    def test_sleepms(self):
        call_builtin("os", "Sleepms", [100])

    def test_distance(self):
        result = call_builtin("uo", "Distance", [None, None])
        assert result == 1

    def test_set_priority_returns_0(self):
        assert call_builtin("os", "set_priority", [1]) == 0

    def test_detach_no_crash(self):
        call_builtin("os", "detach", [])

    def test_set_war_mode_no_crash(self):
        call_builtin("uo", "SetWarMode", [None, 1])

    def test_sleep(self):
        result = call_builtin("os", "Sleep", [10])
        assert result is None

    def test_sleep_no_args(self):
        result = call_builtin("", "Sleep", [])
        assert result is None

    def test_sleep_uninit(self):
        result = call_builtin("os", "Sleep", [UNINIT])
        assert result is None

    def test_set_script_option(self):
        result = call_builtin("os", "set_script_option", [1, 1])
        assert result is None

    def test_set_script_option_uninit(self):
        result = call_builtin("os", "set_script_option", [UNINIT, UNINIT])
        assert result is None
