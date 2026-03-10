"""Tests for base damage rolling."""

from random import Random

from omega.combat.damage import roll_base_damage
from omega.config.dice import DiceSpec
from omega.model.items import Weapon


class TestRollBaseDamage:
    def test_deterministic_with_seed(self):
        weapon = Weapon(name="Sword", damage=DiceSpec(2, 6, 0))
        rng = Random(42)
        d1 = roll_base_damage(weapon, rng)
        rng2 = Random(42)
        d2 = roll_base_damage(weapon, rng2)
        assert d1 == d2

    def test_within_range(self):
        weapon = Weapon(name="Dagger", damage=DiceSpec(1, 4, 2))
        rng = Random(0)
        for _ in range(100):
            dmg = roll_base_damage(weapon, rng)
            assert 3 <= dmg <= 6  # 1d4+2 = [3, 6]

    def test_flat_damage(self):
        weapon = Weapon(name="Fist", damage=DiceSpec(0, 0, 5))
        dmg = roll_base_damage(weapon)
        assert dmg == 5

    def test_minimum_one(self):
        weapon = Weapon(name="Broken", damage=DiceSpec(1, 1, -5))
        dmg = roll_base_damage(weapon)
        assert dmg >= 1  # min(1d1-5) = -4, clamped to 1

    def test_default_weapon_damage(self):
        weapon = Weapon(name="Default")
        # Default DiceSpec is 1d4+0
        rng = Random(0)
        dmg = roll_base_damage(weapon, rng)
        assert 1 <= dmg <= 4
