"""Priority 3 — Bitwise operator edge case tests.

Tests XOR, NOT, shifts, and damage-type flag patterns that the combat
path relies on.  &/| are already tested; this adds ^, ~, <<, >> and
compound patterns.
"""

import omega.runtime  # noqa: F401

from .helpers import run_snippet


class TestBitwiseXOR:
    def test_xor_basic(self):
        assert run_snippet("var x := 0x01 ^ 0x03;", "x") == 0x02

    def test_xor_same_is_zero(self):
        assert run_snippet("var x := 0xFF ^ 0xFF;", "x") == 0

    def test_xor_with_zero(self):
        assert run_snippet("var x := 42 ^ 0;", "x") == 42


class TestBitwiseNOT:
    def test_not_zero(self):
        assert run_snippet("var x := ~0;", "x") == -1

    def test_not_one(self):
        assert run_snippet("var x := ~1;", "x") == -2

    def test_not_0x01(self):
        """~0x01 → -2 (two's complement)."""
        assert run_snippet("var x := ~0x01;", "x") == -2

    def test_not_ff(self):
        assert run_snippet("var x := ~0xFF;", "x") == -256

    def test_double_not_identity(self):
        """~~x == x for any integer."""
        assert run_snippet("var x := ~~42;", "x") == 42


class TestBitwiseShifts:
    def test_shift_left_basic(self):
        assert run_snippet("var x := 1 << 8;", "x") == 256

    def test_shift_left_by_4(self):
        assert run_snippet("var x := 1 << 4;", "x") == 16

    def test_shift_right_basic(self):
        assert run_snippet("var x := 256 >> 4;", "x") == 16

    def test_shift_right_by_8(self):
        assert run_snippet("var x := 256 >> 8;", "x") == 1

    def test_shift_left_zero(self):
        assert run_snippet("var x := 1 << 0;", "x") == 1

    def test_shift_right_zero(self):
        assert run_snippet("var x := 42 >> 0;", "x") == 42


class TestBitwiseNegative:
    def test_negative_and_mask(self):
        """-1 & 0xFF → 255 (all bits set, masked to byte)."""
        assert run_snippet("var x := -1 & 0xFF;", "x") == 255


class TestDamageTypeFlags:
    """Damage type bitflags from damages.inc — the core use case for bitwise ops."""

    def test_fire_or_earth(self):
        """FIRE(0x01) | EARTH(0x04) → 0x05."""
        code = """
        var FIRE := 0x01;
        var EARTH := 0x04;
        var x := FIRE | EARTH;
        """
        assert run_snippet(code, "x") == 0x05

    def test_combined_flag_check(self):
        """(FIRE | EARTH) & FIRE → 0x01 (fire is set)."""
        code = """
        var FIRE := 0x01;
        var EARTH := 0x04;
        var combined := FIRE | EARTH;
        var x := combined & FIRE;
        """
        assert run_snippet(code, "x") == 0x01

    def test_flag_not_set(self):
        """(FIRE | EARTH) & WATER → 0x00 (water not set)."""
        code = """
        var FIRE := 0x01;
        var EARTH := 0x04;
        var WATER := 0x08;
        var combined := FIRE | EARTH;
        var x := combined & WATER;
        """
        assert run_snippet(code, "x") == 0x00

    def test_all_damage_flags(self):
        """Combine all damage types and verify individual checks."""
        code = """
        var PHYSICAL := 0x100;
        var FIRE := 0x01;
        var AIR := 0x02;
        var flags := PHYSICAL | FIRE | AIR;
        var has_fire := flags & FIRE;
        var has_air := flags & AIR;
        var has_phys := flags & PHYSICAL;
        var has_water := flags & 0x08;
        """
        assert run_snippet(code, "has_fire") == 0x01
        assert run_snippet(code, "has_air") == 0x02
        assert run_snippet(code, "has_phys") == 0x100
        assert run_snippet(code, "has_water") == 0x00
