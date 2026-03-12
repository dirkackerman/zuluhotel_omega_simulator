"""Tests for POL-conformant swing delay calculation.

Verifies ``calculate_swing_delay()`` matches POL's ``Character::schedule_attack()``
in ``charactr.cpp:2832–2881``.

Test vectors are hand-computed from the C++ source:
- Speed-based: ``clocks = 1_500_000 // ((DEX + 100) * SPEED)``
- Delay-based: ``clocks = (max(0, delay + delay_mod) * 100) // 1000``
- SwingSpeedIncrease: ``clocks = c_round(clocks / (1 + ssi/100))``
- Convert: ``delay_ms = clocks * 10``
"""

import math

import pytest

from omega.combat.timing import (
    POLCLOCKS_PER_SEC,
    _c_round,
    calculate_swing_delay,
)
from omega.model.items import Armor, Weapon
from omega.model.mobile import Mobile


# ---------------------------------------------------------------------------
# Helper: create a test mobile with specific DEX and optional modifiers
# ---------------------------------------------------------------------------

def _mob(
    dex: int = 100,
    *,
    delay_mod: int = 0,
    ssi: int | None = None,
    equip_ssi: int | None = None,
) -> Mobile:
    """Create a test mobile with given DEX and optional swing speed modifiers."""
    m = Mobile(name="Test")
    m.dex_base = dex
    m.delay_mod = delay_mod
    if ssi is not None:
        m.set_property("SwingSpeedIncrease", ssi)
    if equip_ssi is not None:
        # Add an armor piece with SwingSpeedIncrease
        a = Armor(name="SSI Gloves")
        a.set_property("SwingSpeedIncrease", equip_ssi)
        m.equip(5, a)  # arbitrary layer
    return m


def _wpn(speed: int = 50, delay: int = 0) -> Weapon:
    """Create a test weapon with given speed/delay."""
    return Weapon(name="TestWeapon", speed=speed, delay=delay)


# ---------------------------------------------------------------------------
# _c_round — C++ round() semantics (half away from zero)
# ---------------------------------------------------------------------------

class TestCRound:
    """Verify _c_round matches C++ round() semantics."""

    def test_positive_half(self):
        # C++ round(0.5) = 1, Python round(0.5) = 0 (banker's rounding)
        assert _c_round(0.5) == 1

    def test_negative_half(self):
        # C++ round(-0.5) = -1, Python round(-0.5) = 0
        assert _c_round(-0.5) == -1

    def test_positive_half_large(self):
        # C++ round(66.5) = 67, Python round(66.5) = 66
        assert _c_round(66.5) == 67

    def test_positive_half_150(self):
        # C++ round(150.5) = 151, Python round(150.5) = 150
        assert _c_round(150.5) == 151

    def test_negative_half_large(self):
        # C++ round(-2.5) = -3, Python round(-2.5) = -2
        assert _c_round(-2.5) == -3

    def test_positive_integer(self):
        assert _c_round(5.0) == 5

    def test_negative_integer(self):
        assert _c_round(-3.0) == -3

    def test_positive_below_half(self):
        assert _c_round(2.3) == 2

    def test_positive_above_half(self):
        assert _c_round(2.7) == 3

    def test_negative_below_half(self):
        assert _c_round(-2.3) == -2

    def test_negative_above_half(self):
        assert _c_round(-2.7) == -3

    def test_zero(self):
        assert _c_round(0.0) == 0

    def test_very_small_positive(self):
        assert _c_round(0.0001) == 0

    def test_very_small_negative(self):
        assert _c_round(-0.0001) == 0

    def test_python_round_divergence_proof(self):
        """Demonstrate where Python round() differs from C++ round()."""
        # These are the cases where the distinction matters
        assert round(0.5) == 0    # Python: banker's rounding
        assert _c_round(0.5) == 1  # C++: half away from zero

        assert round(66.5) == 66
        assert _c_round(66.5) == 67

        assert round(150.5) == 150
        assert _c_round(150.5) == 151


# ---------------------------------------------------------------------------
# Speed-based path (weapon.delay == 0)
# ---------------------------------------------------------------------------

class TestSpeedBasedPath:
    """Test the speed-based swing delay calculation.

    Formula: clocks = 1_500_000 // ((DEX + 100) * SPEED)
    delay_ms = clocks * 10
    """

    def test_medium_weapon_mid_dex(self):
        """Speed 50, DEX 100 → 1_500_000 / (200*50) = 150 clocks = 1500ms."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        # C++: 1500000 / (200 * 50) = 1500000 / 10000 = 150 clocks
        assert delay == 1500.0

    def test_fast_weapon_high_dex(self):
        """Speed 98, DEX 130 → 1_500_000 / (230*98) = 66 clocks = 660ms.

        C++ integer division: 1500000 / 22540 = 66 (truncated from 66.548...)
        """
        mob = _mob(dex=130)
        wpn = _wpn(speed=98)
        delay = calculate_swing_delay(mob, wpn)
        # 1500000 / (230 * 98) = 1500000 / 22540 = 66.548... → truncated to 66
        expected_clocks = 1_500_000 // (230 * 98)
        assert expected_clocks == 66
        assert delay == 660.0

    def test_slow_weapon_low_dex(self):
        """Speed 15, DEX 10 → 1_500_000 / (110*15) = 909 clocks = 9090ms."""
        mob = _mob(dex=10)
        wpn = _wpn(speed=15)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = 1_500_000 // (110 * 15)
        assert expected_clocks == 909
        assert delay == 9090.0

    def test_max_dex_fast_weapon(self):
        """Speed 98, DEX 255 — very fast swing."""
        mob = _mob(dex=255)
        wpn = _wpn(speed=98)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = 1_500_000 // (355 * 98)
        assert expected_clocks == 43  # 1500000 / 34790 = 43.11... → 43
        assert delay == 430.0

    def test_min_dex_slow_weapon(self):
        """Speed 15, DEX 0 — very slow swing."""
        mob = _mob(dex=0)
        wpn = _wpn(speed=15)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = 1_500_000 // (100 * 15)
        assert expected_clocks == 1000
        assert delay == 10000.0

    def test_speed_1_dex_0(self):
        """Extreme: Speed 1, DEX 0 — slowest possible."""
        mob = _mob(dex=0)
        wpn = _wpn(speed=1)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = 1_500_000 // (100 * 1)
        assert expected_clocks == 15000
        assert delay == 150000.0

    def test_dex_affects_delay(self):
        """Higher DEX produces lower delay."""
        wpn = _wpn(speed=50)
        delay_low = calculate_swing_delay(_mob(dex=50), wpn)
        delay_high = calculate_swing_delay(_mob(dex=100), wpn)
        assert delay_high < delay_low

    def test_speed_affects_delay(self):
        """Higher speed produces lower delay."""
        mob = _mob(dex=100)
        delay_slow = calculate_swing_delay(mob, _wpn(speed=25))
        delay_fast = calculate_swing_delay(mob, _wpn(speed=75))
        assert delay_fast < delay_slow

    def test_integer_truncation_exact(self):
        """Verify integer division truncation matches C++ for non-round division.

        1_500_000 / (150 * 35) = 1_500_000 / 5250 = 285.714... → 285
        """
        mob = _mob(dex=50)
        wpn = _wpn(speed=35)
        delay = calculate_swing_delay(mob, wpn)
        assert 1_500_000 // (150 * 35) == 285
        assert delay == 2850.0


# ---------------------------------------------------------------------------
# Delay-based path (weapon.delay > 0)
# ---------------------------------------------------------------------------

class TestDelayBasedPath:
    """Test the delay-based swing delay calculation.

    Formula: clocks = (max(0, delay + delay_mod) * 100) // 1000
    delay_ms = clocks * 10
    """

    def test_basic_delay(self):
        """Delay 2000ms, no modifier → clocks = (2000 * 100) / 1000 = 200 → 2000ms."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=50, delay=2000)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = (2000 * 100) // 1000
        assert expected_clocks == 200
        assert delay == 2000.0

    def test_delay_with_negative_mod(self):
        """Delay 2000, delay_mod -500 → delay_sum = 1500.

        clocks = (1500 * 100) / 1000 = 150 → 1500ms.
        """
        mob = _mob(dex=100, delay_mod=-500)
        wpn = _wpn(speed=50, delay=2000)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = (1500 * 100) // 1000
        assert expected_clocks == 150
        assert delay == 1500.0

    def test_delay_with_positive_mod(self):
        """Delay 1000, delay_mod +500 → delay_sum = 1500."""
        mob = _mob(dex=100, delay_mod=500)
        wpn = _wpn(speed=50, delay=1000)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = (1500 * 100) // 1000
        assert expected_clocks == 150
        assert delay == 1500.0

    def test_delay_mod_clamp_to_zero(self):
        """Delay 500, delay_mod -1000 → delay_sum clamped to 0.

        C++ line 2856–2857: ``if (delay_sum < 0) delay_sum = 0;``
        """
        mob = _mob(dex=100, delay_mod=-1000)
        wpn = _wpn(speed=50, delay=500)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 0.0  # 0 clocks → 0 ms

    def test_delay_ignores_dex(self):
        """Delay-based path doesn't use DEX — same delay for any DEX."""
        wpn = _wpn(speed=50, delay=1500)
        d1 = calculate_swing_delay(_mob(dex=10), wpn)
        d2 = calculate_swing_delay(_mob(dex=255), wpn)
        assert d1 == d2

    def test_delay_integer_truncation(self):
        """Non-round delay: 1234ms → clocks = (1234 * 100) // 1000 = 123.

        C++ integer division truncates: 123400 / 1000 = 123.
        """
        mob = _mob(dex=100)
        wpn = _wpn(speed=50, delay=1234)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = (1234 * 100) // 1000
        assert expected_clocks == 123
        assert delay == 1230.0

    def test_delay_small_value(self):
        """Delay 50ms → clocks = (50 * 100) // 1000 = 5 → 50ms."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=50, delay=50)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 50.0

    def test_delay_1ms(self):
        """Delay 1ms → clocks = (1 * 100) // 1000 = 0 → 0ms.

        Sub-10ms delays get truncated to 0 clocks due to integer division.
        """
        mob = _mob(dex=100)
        wpn = _wpn(speed=50, delay=1)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 0.0

    def test_delay_9ms(self):
        """Delay 9ms → clocks = (9 * 100) // 1000 = 0 → 0ms."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=50, delay=9)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 0.0

    def test_delay_10ms(self):
        """Delay 10ms → clocks = (10 * 100) // 1000 = 1 → 10ms."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=50, delay=10)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 10.0


# ---------------------------------------------------------------------------
# SwingSpeedIncrease modifier
# ---------------------------------------------------------------------------

class TestSwingSpeedIncrease:
    """Test SwingSpeedIncrease modifier application.

    Applied after base delay calculation:
    modifier = ssi / 100.0 (clamped to >= -0.99)
    clocks = c_round(clocks / (1 + modifier))
    """

    def test_ssi_25_percent(self):
        """SSI 25 → 25% faster. Base 150 clocks / 1.25 = 120 → 1200ms."""
        mob = _mob(dex=100, ssi=25)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        # Base: 1500000 // (200*50) = 150 clocks
        # Modified: c_round(150 / 1.25) = c_round(120.0) = 120
        assert delay == 1200.0

    def test_ssi_50_percent(self):
        """SSI 50 → 50% faster. Base 150 / 1.5 = 100 → 1000ms."""
        mob = _mob(dex=100, ssi=50)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 1000.0

    def test_ssi_100_percent(self):
        """SSI 100 → 100% faster (half delay). 150 / 2.0 = 75 → 750ms."""
        mob = _mob(dex=100, ssi=100)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 750.0

    def test_ssi_negative_slows_down(self):
        """SSI -25 → 25% slower. 150 / 0.75 = 200 → 2000ms."""
        mob = _mob(dex=100, ssi=-25)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 2000.0

    def test_ssi_clamp_at_negative_99(self):
        """SSI -150 → clamped to -0.99. 150 / 0.01 = 15000 → 150000ms.

        C++ line 2868: ``if (speed_modifier < -0.99) speed_modifier = -0.99;``
        """
        mob = _mob(dex=100, ssi=-150)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        # 150 / 0.01 = 15000 → c_round(15000.0) = 15000
        assert delay == 150000.0

    def test_ssi_exactly_negative_99(self):
        """SSI -99 → modifier = -0.99. 150 / 0.01 = 15000."""
        mob = _mob(dex=100, ssi=-99)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 150000.0

    def test_ssi_negative_98(self):
        """SSI -98 → modifier = -0.98. 150 / 0.02 = 7500 → 75000ms."""
        mob = _mob(dex=100, ssi=-98)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 75000.0

    def test_ssi_from_equipment(self):
        """SSI from an equipped item contributes to swing speed."""
        mob = _mob(dex=100, equip_ssi=25)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        # Same as SSI 25: 150 / 1.25 = 120 → 1200ms
        assert delay == 1200.0

    def test_ssi_stacks_mobile_plus_equipment(self):
        """SSI from mobile property + equipment stack additively."""
        mob = _mob(dex=100, ssi=10, equip_ssi=15)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        # Total SSI = 25. Same as test_ssi_25_percent: 1200ms
        assert delay == 1200.0

    def test_ssi_zero_no_change(self):
        """SSI 0 → no change from base delay."""
        mob = _mob(dex=100, ssi=0)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 1500.0

    def test_ssi_with_delay_based(self):
        """SSI applies to delay-based path too."""
        mob = _mob(dex=100, ssi=50)
        wpn = _wpn(speed=50, delay=2000)
        delay = calculate_swing_delay(mob, wpn)
        # Base: (2000 * 100) // 1000 = 200 clocks
        # Modified: c_round(200 / 1.5) = c_round(133.333...) = 133
        assert delay == 1330.0

    def test_ssi_rounding_half_away_from_zero(self):
        """Verify C++ round semantics when SSI produces .5 result.

        Speed 98, DEX 130, SSI 0:
        Base clocks = 1500000 // (230 * 98) = 66
        With SSI = 33: modifier = 0.33, clocks = 66 / 1.33 = 49.624... → 50
        """
        mob = _mob(dex=130, ssi=33)
        wpn = _wpn(speed=98)
        delay = calculate_swing_delay(mob, wpn)
        # 66 / 1.33 = 49.624... → c_round = 50
        assert delay == 500.0

    def test_ssi_rounding_banker_divergence(self):
        """Find a case where banker's rounding would give wrong result.

        We need clocks / (1 + modifier) to produce exactly X.5 where X is even.
        Speed 50, DEX 100 → base 150 clocks.
        SSI = 13 → 150 / 1.13 = 132.7433... → no exact .5
        Let's find one: base 133, SSI = 0 → try delay-based.
        Delay 1330 → clocks = 133. SSI=0 → 133. That's not .5 rounding.

        Actually, construct: delay 2650 → clocks = 265.
        SSI = 100 → 265 / 2.0 = 132.5. C++ round = 133, Python round = 132.
        """
        mob = _mob(dex=100, ssi=100)
        wpn = _wpn(speed=50, delay=2650)
        delay = calculate_swing_delay(mob, wpn)
        # clocks = (2650 * 100) // 1000 = 265
        # 265 / 2.0 = 132.5 → C++ round = 133, Python round = 132
        assert delay == 1330.0  # 133 * 10


# ---------------------------------------------------------------------------
# Edge cases and defensive checks
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases, boundary conditions, and defensive checks."""

    def test_weapon_speed_zero_guard(self):
        """Weapon speed 0 with delay 0 → division by zero guard."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=0)
        delay = calculate_swing_delay(mob, wpn)
        # Should return a large delay, not crash
        assert delay >= 100_000.0

    def test_no_minimum_floor(self):
        """POL does NOT enforce a minimum floor — verify we don't either.

        Line 2872 is a debug log, not a clamp.
        """
        # Speed 98, DEX 255 → 1500000 // (355 * 98) = 43 clocks = 430ms
        # This is below 200ms (20 clocks) but should NOT be clamped
        mob = _mob(dex=255)
        wpn = _wpn(speed=98)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 430.0  # < 200ms threshold, but not clamped

    def test_delay_zero_uses_speed_path(self):
        """Weapon with delay=0 uses speed path (default)."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=50, delay=0)
        delay = calculate_swing_delay(mob, wpn)
        assert delay == 1500.0  # Speed path result

    def test_returns_float(self):
        """Result is always a float."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        assert isinstance(delay, float)

    def test_result_non_negative(self):
        """Result is never negative."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        assert delay >= 0.0

    def test_delay_mod_default_zero(self):
        """Mobile delay_mod defaults to 0."""
        mob = Mobile(name="Test")
        assert mob.delay_mod == 0

    def test_weapon_delay_default_zero(self):
        """Weapon delay defaults to 0 (speed-based path)."""
        wpn = Weapon(name="Test")
        assert wpn.delay == 0

    def test_default_mobile_values(self):
        """Mobile with default stats (dex=10) + standard weapon → reasonable delay."""
        mob = Mobile(name="Test")
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        # dex_base=10, so (10+100)*50 = 5500, 1500000//5500 = 272 clocks = 2720ms
        assert delay == 2720.0
        assert delay > 0


# ---------------------------------------------------------------------------
# Mobile.swing_speed_increase property
# ---------------------------------------------------------------------------

class TestSwingSpeedIncreaseProperty:
    """Test Mobile.swing_speed_increase aggregation."""

    def test_no_ssi_returns_zero(self):
        """No SwingSpeedIncrease anywhere → 0."""
        mob = Mobile(name="Test")
        assert mob.swing_speed_increase == 0

    def test_mobile_property_only(self):
        """SSI from mobile property bag only."""
        mob = Mobile(name="Test")
        mob.set_property("SwingSpeedIncrease", 25)
        assert mob.swing_speed_increase == 25

    def test_equipment_only(self):
        """SSI from equipped item only."""
        mob = Mobile(name="Test")
        a = Armor(name="Gloves")
        a.set_property("SwingSpeedIncrease", 15)
        mob.equip(5, a)
        assert mob.swing_speed_increase == 15

    def test_stacks_mobile_and_equipment(self):
        """SSI from mobile + equipment stack."""
        mob = Mobile(name="Test")
        mob.set_property("SwingSpeedIncrease", 10)
        a = Armor(name="Gloves")
        a.set_property("SwingSpeedIncrease", 15)
        mob.equip(5, a)
        assert mob.swing_speed_increase == 25

    def test_multiple_equipment_stack(self):
        """SSI from multiple equipped items all stack."""
        mob = Mobile(name="Test")
        a1 = Armor(name="Gloves")
        a1.set_property("SwingSpeedIncrease", 10)
        mob.equip(5, a1)
        a2 = Armor(name="Ring")
        a2.set_property("SwingSpeedIncrease", 5)
        mob.equip(6, a2)
        w = Weapon(name="Sword")
        w.set_property("SwingSpeedIncrease", 8)
        mob.equip(1, w)
        assert mob.swing_speed_increase == 23

    def test_negative_ssi(self):
        """Negative SSI values work (make attacks slower)."""
        mob = Mobile(name="Test")
        mob.set_property("SwingSpeedIncrease", -25)
        assert mob.swing_speed_increase == -25

    def test_non_numeric_ssi_ignored(self):
        """Non-numeric SSI values are silently ignored."""
        mob = Mobile(name="Test")
        mob.set_property("SwingSpeedIncrease", "not_a_number")
        assert mob.swing_speed_increase == 0

    def test_none_ssi_ignored(self):
        """None SSI from equipment is ignored (property not set)."""
        mob = Mobile(name="Test")
        a = Armor(name="Gloves")
        # Don't set SwingSpeedIncrease on armor
        mob.equip(5, a)
        assert mob.swing_speed_increase == 0

    def test_float_ssi_truncated(self):
        """Float SSI is truncated to int."""
        mob = Mobile(name="Test")
        mob.set_property("SwingSpeedIncrease", 25.7)
        assert mob.swing_speed_increase == 25


# ---------------------------------------------------------------------------
# Snapshot / restore of delay_mod
# ---------------------------------------------------------------------------

class TestSnapshotDelayMod:
    """Verify delay_mod is properly captured and restored."""

    def test_snapshot_captures_delay_mod(self):
        from omega.model.snapshot import snapshot, restore
        mob = Mobile(name="Test")
        mob.delay_mod = 500
        snap = snapshot(mob)
        assert snap.delay_mod == 500

    def test_restore_resets_delay_mod(self):
        from omega.model.snapshot import snapshot, restore
        mob = Mobile(name="Test")
        mob.delay_mod = 0
        snap = snapshot(mob)
        mob.delay_mod = 999
        restore(mob, snap)
        assert mob.delay_mod == 0


# ---------------------------------------------------------------------------
# HitResult.swing_delay_ms
# ---------------------------------------------------------------------------

class TestHitResultTiming:
    """Verify swing_delay_ms is populated on HitResult."""

    def test_default_zero(self):
        from omega.combat.result import HitResult
        r = HitResult()
        assert r.swing_delay_ms == 0.0

    def test_populated_by_execute_hit(self):
        """execute_hit populates swing_delay_ms on the result."""
        from omega.combat.hit import execute_hit
        from omega.parser.parser import parse_text, ParseResult
        from pathlib import Path

        source = """
        use uo;
        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        result = parse_text(source, file="<test>")
        trees = {Path("<test>"): result}

        attacker = Mobile(name="Attacker")
        attacker.dex_base = 100
        defender = Mobile(name="Defender")
        defender.hp = 100
        defender.max_hp = 100
        weapon = Weapon(name="Sword", speed=50)
        armor = Armor(name="None", ar=0)

        import omega.runtime  # noqa: F401
        hit_result = execute_hit(
            trees, attacker, defender, weapon, armor,
            base_damage=25, core_hit_check=False,
        )

        # Speed 50, DEX 100 → 1500ms
        assert hit_result.swing_delay_ms == 1500.0

    def test_populated_on_miss(self):
        """swing_delay_ms is populated even when hit check fails (miss)."""
        from omega.combat.hit import execute_hit
        from omega.parser.parser import parse_text, ParseResult
        from pathlib import Path

        source = """
        use uo;
        program mainhit(attacker, defender, weapon, armor, basedamage, rawdamage)
            ApplyRawDamage(defender, rawdamage);
        endprogram
        """
        result = parse_text(source, file="<test>")
        trees = {Path("<test>"): result}

        attacker = Mobile(name="Attacker")
        attacker.dex_base = 100
        # Very low skill → guaranteed miss with seed 0
        attacker.set_skill(40, 0)  # Swordsmanship = 0
        defender = Mobile(name="Defender")
        defender.hp = 100
        defender.max_hp = 100
        defender.set_skill(40, 2000)  # Max skill → high defense
        weapon = Weapon(name="Sword", speed=50, attribute=40)
        armor = Armor(name="None", ar=0)

        import omega.runtime  # noqa: F401
        hit_result = execute_hit(
            trees, attacker, defender, weapon, armor,
            base_damage=25, core_hit_check=True, rng_seed=42,
        )

        # Timing is always calculated, regardless of hit/miss
        assert hit_result.swing_delay_ms == 1500.0


# ---------------------------------------------------------------------------
# TimingStats and DPS computation in aggregate_cell
# ---------------------------------------------------------------------------

class TestTimingStats:
    """Verify DPS computation in aggregate_cell."""

    def test_timing_from_results(self):
        from omega.combat.result import HitResult
        from omega.simulation.stats import aggregate_cell

        results = [
            HitResult(final_damage=10.0, swing_delay_ms=1500.0, base_damage=10, success=True),
            HitResult(final_damage=20.0, swing_delay_ms=1500.0, base_damage=20, success=True),
            HitResult(final_damage=0.0, swing_delay_ms=1500.0, base_damage=15, success=True),
        ]
        cell = aggregate_cell(results)

        assert cell.timing is not None
        assert cell.timing.swing_delay_ms == 1500.0
        assert cell.timing.swings_per_second == pytest.approx(1000.0 / 1500.0)

    def test_dps_mean(self):
        """dps_mean = mean_damage * swings_per_second."""
        from omega.combat.result import HitResult
        from omega.simulation.stats import aggregate_cell

        # 3 hits with known damages: mean = 10
        results = [
            HitResult(final_damage=10.0, swing_delay_ms=1000.0, base_damage=10, success=True),
            HitResult(final_damage=10.0, swing_delay_ms=1000.0, base_damage=10, success=True),
            HitResult(final_damage=10.0, swing_delay_ms=1000.0, base_damage=10, success=True),
        ]
        cell = aggregate_cell(results)

        ts = cell.timing
        assert ts is not None
        # 1 swing/sec, 10 mean damage → DPS = 10
        assert ts.dps_mean == pytest.approx(10.0)

    def test_dps_with_misses(self):
        """DPS accounts for misses (0 damage) in the mean."""
        from omega.combat.result import HitResult
        from omega.simulation.stats import aggregate_cell

        results = [
            HitResult(final_damage=20.0, swing_delay_ms=1000.0, base_damage=20, success=True),
            HitResult(final_damage=0.0, swing_delay_ms=1000.0, base_damage=20, success=True),
        ]
        cell = aggregate_cell(results)

        ts = cell.timing
        assert ts is not None
        # Mean damage = 10, 1 swing/sec → DPS = 10
        assert ts.dps_mean == pytest.approx(10.0)
        # On-hit DPS = 20 damage * 1 swing/sec = 20
        assert ts.dps_on_hit == pytest.approx(20.0)
        # Effective DPS = hit_rate * on_hit_mean * swings/sec = 0.5 * 20 * 1 = 10
        assert ts.effective_dps == pytest.approx(10.0)

    def test_no_timing_when_delay_zero(self):
        """No timing stats when swing_delay_ms is 0 (shouldn't normally happen)."""
        from omega.combat.result import HitResult
        from omega.simulation.stats import aggregate_cell

        results = [
            HitResult(final_damage=10.0, swing_delay_ms=0.0, base_damage=10, success=True),
        ]
        cell = aggregate_cell(results)
        assert cell.timing is None

    def test_timing_empty_results(self):
        """No timing stats for empty results."""
        from omega.simulation.stats import aggregate_cell
        cell = aggregate_cell([])
        assert cell.timing is None

    def test_timing_all_errors(self):
        """No timing when all results are errors."""
        from omega.combat.result import HitResult
        from omega.simulation.stats import aggregate_cell

        results = [
            HitResult(success=False, error="test error", swing_delay_ms=1500.0),
        ]
        cell = aggregate_cell(results)
        assert cell.timing is None

    def test_dps_scales_with_speed(self):
        """Faster weapons produce higher DPS for same damage."""
        from omega.combat.result import HitResult
        from omega.simulation.stats import aggregate_cell

        slow = [HitResult(final_damage=10.0, swing_delay_ms=2000.0, base_damage=10, success=True)]
        fast = [HitResult(final_damage=10.0, swing_delay_ms=1000.0, base_damage=10, success=True)]

        slow_cell = aggregate_cell(slow)
        fast_cell = aggregate_cell(fast)

        assert fast_cell.timing.dps_mean > slow_cell.timing.dps_mean
        assert fast_cell.timing.dps_mean == pytest.approx(2.0 * slow_cell.timing.dps_mean)


# ---------------------------------------------------------------------------
# Table reporting integration
# ---------------------------------------------------------------------------

class TestTableReporting:
    """Verify DPS columns appear in summary tables."""

    def test_get_stat_timing_columns(self):
        from omega.reporting.tables import _get_stat
        from omega.combat.result import HitResult
        from omega.simulation.stats import aggregate_cell

        results = [
            HitResult(final_damage=10.0, swing_delay_ms=1500.0, base_damage=10, success=True),
        ]
        cell = aggregate_cell(results)

        assert _get_stat(cell, "swing_delay_ms") == 1500.0
        assert _get_stat(cell, "swings_per_sec") == pytest.approx(1000.0 / 1500.0)
        assert _get_stat(cell, "dps_mean") == pytest.approx(10.0 * 1000.0 / 1500.0)
        assert _get_stat(cell, "effective_dps") == pytest.approx(10.0 * 1000.0 / 1500.0)

    def test_get_stat_no_timing(self):
        """When timing is None, DPS columns return 0.0."""
        from omega.reporting.tables import _get_stat
        from omega.combat.result import HitResult
        from omega.simulation.stats import aggregate_cell

        results = [
            HitResult(final_damage=10.0, swing_delay_ms=0.0, base_damage=10, success=True),
        ]
        cell = aggregate_cell(results)
        assert cell.timing is None

        assert _get_stat(cell, "swing_delay_ms") == 0.0
        assert _get_stat(cell, "dps_mean") == 0.0


# ---------------------------------------------------------------------------
# WeaponSpec delay field
# ---------------------------------------------------------------------------

class TestWeaponSpecDelay:
    """Test delay field on WeaponSpec and materialization."""

    def test_default_zero(self):
        from omega.simulation.scenario import WeaponSpec
        spec = WeaponSpec()
        assert spec.delay == 0

    def test_custom_delay(self):
        from omega.simulation.scenario import WeaponSpec
        spec = WeaponSpec(delay=2000)
        assert spec.delay == 2000

    def test_build_weapon_passes_delay(self):
        from omega.simulation.scenario import WeaponSpec, build_weapon
        spec = WeaponSpec(delay=1500)
        w = build_weapon(spec)
        assert w.delay == 1500

    def test_build_weapon_default_delay(self):
        from omega.simulation.scenario import WeaponSpec, build_weapon
        spec = WeaponSpec()
        w = build_weapon(spec)
        assert w.delay == 0


# ---------------------------------------------------------------------------
# Real-world weapon examples from ZH shard
# ---------------------------------------------------------------------------

class TestRealWorldWeapons:
    """Test with realistic weapon speed values from the ZH shard.

    Speed values from fixtures/shard/pkg/systems/combat/config/itemdesc.cfg:
    - Two-handed axe: Speed 15
    - Mace: Speed 30
    - Longsword: Speed 50
    - Whip: Speed 70
    - Short bow: Speed 98
    """

    def test_two_handed_axe_warrior(self):
        """Two-handed axe (Speed 15) with DEX 75 warrior."""
        mob = _mob(dex=75)
        wpn = _wpn(speed=15)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = 1_500_000 // (175 * 15)
        assert expected_clocks == 571  # 1500000/2625 = 571.42... → 571
        assert delay == 5710.0

    def test_mace_avg_player(self):
        """Mace (Speed 30) with DEX 100."""
        mob = _mob(dex=100)
        wpn = _wpn(speed=30)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = 1_500_000 // (200 * 30)
        assert expected_clocks == 250
        assert delay == 2500.0

    def test_longsword_high_dex(self):
        """Longsword (Speed 50) with DEX 130."""
        mob = _mob(dex=130)
        wpn = _wpn(speed=50)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = 1_500_000 // (230 * 50)
        assert expected_clocks == 130  # 1500000/11500 = 130.43... → 130
        assert delay == 1300.0

    def test_short_bow_maxed(self):
        """Short bow (Speed 98) with DEX 130."""
        mob = _mob(dex=130)
        wpn = _wpn(speed=98)
        delay = calculate_swing_delay(mob, wpn)
        expected_clocks = 1_500_000 // (230 * 98)
        assert expected_clocks == 66
        assert delay == 660.0

    def test_dps_comparison_axe_vs_bow(self):
        """Bow has higher DPS than axe despite lower per-hit damage."""
        mob = _mob(dex=100)
        axe_delay = calculate_swing_delay(mob, _wpn(speed=15))
        bow_delay = calculate_swing_delay(mob, _wpn(speed=98))
        # Axe: 5710ms between swings, bow: 750ms
        # Even if axe does 5x damage, bow still swings ~7.6x faster
        assert bow_delay < axe_delay


# ---------------------------------------------------------------------------
# POLCLOCKS_PER_SEC constant
# ---------------------------------------------------------------------------

class TestConstants:
    """Verify timing constants match POL."""

    def test_polclocks_per_sec(self):
        assert POLCLOCKS_PER_SEC == 100
