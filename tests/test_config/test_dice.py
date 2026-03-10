"""Tests for the dice notation parser."""

from random import Random

import pytest

from omega.config.dice import DiceSpec, parse_dice, roll_dice


class TestParseDice:
    def test_full_notation(self):
        spec = parse_dice("3d5+2")
        assert spec == DiceSpec(count=3, sides=5, bonus=2)

    def test_negative_bonus(self):
        spec = parse_dice("2d6-1")
        assert spec == DiceSpec(count=2, sides=6, bonus=-1)

    def test_no_bonus(self):
        spec = parse_dice("1d4")
        assert spec == DiceSpec(count=1, sides=4, bonus=0)

    def test_flat_damage(self):
        spec = parse_dice("5")
        assert spec == DiceSpec(count=0, sides=0, bonus=5)

    def test_large_dice(self):
        spec = parse_dice("10d10+5")
        assert spec == DiceSpec(count=10, sides=10, bonus=5)

    def test_whitespace_stripped(self):
        spec = parse_dice("  3d5+2  ")
        assert spec == DiceSpec(count=3, sides=5, bonus=2)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_dice("abc")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_dice("")


class TestDiceSpecProperties:
    def test_min_value(self):
        spec = DiceSpec(count=3, sides=5, bonus=2)
        assert spec.min_value == 5  # 3*1 + 2

    def test_max_value(self):
        spec = DiceSpec(count=3, sides=5, bonus=2)
        assert spec.max_value == 17  # 3*5 + 2

    def test_mean_value(self):
        spec = DiceSpec(count=3, sides=5, bonus=2)
        assert spec.mean_value == 11.0  # 3 * 3.0 + 2

    def test_flat_min_max_mean(self):
        spec = DiceSpec(count=0, sides=0, bonus=5)
        assert spec.min_value == 5
        assert spec.max_value == 5
        assert spec.mean_value == 5.0

    def test_str_representation(self):
        assert str(DiceSpec(3, 5, 2)) == "3d5+2"
        assert str(DiceSpec(2, 6, -1)) == "2d6-1"
        assert str(DiceSpec(1, 4, 0)) == "1d4"
        assert str(DiceSpec(0, 0, 5)) == "5"


class TestRollDice:
    def test_deterministic_with_seed(self):
        spec = parse_dice("3d5+2")
        rng1 = Random(42)
        rng2 = Random(42)
        assert roll_dice(spec, rng1) == roll_dice(spec, rng2)

    def test_flat_damage(self):
        spec = parse_dice("5")
        assert roll_dice(spec, Random(0)) == 5

    def test_within_bounds(self):
        spec = parse_dice("3d5+2")
        rng = Random(123)
        for _ in range(100):
            val = roll_dice(spec, rng)
            assert spec.min_value <= val <= spec.max_value

    def test_single_die(self):
        spec = parse_dice("1d6")
        rng = Random(456)
        results = {roll_dice(spec, rng) for _ in range(1000)}
        # Should eventually hit all values 1-6
        assert results == {1, 2, 3, 4, 5, 6}
