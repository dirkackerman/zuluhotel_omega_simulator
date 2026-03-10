"""Tests for Batch 1 — trivial POL built-in stubs."""

import omega.runtime  # noqa: F401
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.registry import call_builtin
from omega.runtime.rng import set_rng_seed


class TestTypeCasts:
    def test_cint_string(self):
        assert call_builtin("", "CInt", ["42"]) == 42

    def test_cint_float(self):
        assert call_builtin("", "CInt", [3.7]) == 3

    def test_cint_none(self):
        assert call_builtin("", "CInt", [None]) == 0

    def test_cdbl_string(self):
        assert call_builtin("", "CDbl", ["3.14"]) == 3.14

    def test_cdbl_int(self):
        assert call_builtin("", "CDbl", [5]) == 5.0

    def test_cdbl_none(self):
        assert call_builtin("", "CDbl", [None]) == 0.0

    def test_cstr(self):
        assert call_builtin("", "CStr", [42]) == "42"

    def test_cstr_none(self):
        assert call_builtin("", "CStr", [None]) == ""

    def test_hex(self):
        assert call_builtin("", "Hex", [255]) == "0xff"

    def test_max(self):
        assert call_builtin("", "Max", [3, 7]) == 7

    def test_min(self):
        assert call_builtin("", "Min", [3, 7]) == 3


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

    def test_len_array(self):
        assert call_builtin("", "Len", [[1, 2, 3]]) == 3

    def test_len_string(self):
        assert call_builtin("", "Len", ["hello"]) == 5

    def test_len_none(self):
        assert call_builtin("", "Len", [None]) == 0


class TestMathOps:
    def test_pow(self):
        result = call_builtin("math", "Pow", [2, 10])
        assert result == 1024.0

    def test_pow_fractional(self):
        result = call_builtin("math", "Pow", [25, 0.5])
        assert abs(result - 5.0) < 0.001

    def test_abs_negative(self):
        assert call_builtin("", "Abs", [-42]) == 42

    def test_abs_positive(self):
        assert call_builtin("", "Abs", [42]) == 42

    def test_sqrt(self):
        result = call_builtin("math", "Sqrt", [16])
        assert abs(result - 4.0) < 0.001

    def test_sqrt_negative(self):
        assert call_builtin("math", "Sqrt", [-1]) == 0.0


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


class TestStringOps:
    def test_split_words(self):
        result = call_builtin("", "SplitWords", ["FIRE:50 PHYSICAL:50"])
        assert result == ["FIRE:50", "PHYSICAL:50"]

    def test_split_words_delim(self):
        result = call_builtin("", "SplitWords", ["a:b:c", ":"])
        assert result == ["a", "b", "c"]

    def test_lower(self):
        assert call_builtin("", "Lower", ["HELLO"]) == "hello"

    def test_upper(self):
        assert call_builtin("", "Upper", ["hello"]) == "HELLO"

    def test_substr(self):
        # POL uses 1-based indexing
        assert call_builtin("", "SubStr", ["Hello", 1, 3]) == "Hel"

    def test_substr_no_length(self):
        assert call_builtin("", "SubStr", ["Hello", 2]) == "ello"


class TestTime:
    def test_read_game_clock(self):
        ctx = SimulationContext(game_clock=5000)
        set_context(ctx)
        result = call_builtin("os", "ReadGameClock", [])
        assert result == 5000


class TestMessaging:
    def test_send_sys_message_silent_by_default(self):
        """No error when debug_mode is off."""
        ctx = SimulationContext(debug_mode=False)
        set_context(ctx)
        # Should not raise
        call_builtin("uo", "SendSysMessage", [None, "test message"])

    def test_send_sys_message_debug_mode(self):
        """No error when debug_mode is on."""
        ctx = SimulationContext(debug_mode=True)
        set_context(ctx)
        call_builtin("uo", "SendSysMessage", [None, "debug output"])


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
