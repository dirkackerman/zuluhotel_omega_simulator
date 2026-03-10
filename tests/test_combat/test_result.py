"""Tests for HitResult dataclass."""

from omega.combat.result import HitResult
from omega.runtime.context import SideEffect


class TestHitResult:
    def test_defaults(self):
        r = HitResult()
        assert r.base_damage == 0
        assert r.raw_damage == 0
        assert r.final_damage == 0.0
        assert r.absorbed == 0.0
        assert r.success is True
        assert r.error is None
        assert r.side_effects == []
        assert r.hit_log == []

    def test_with_values(self):
        r = HitResult(
            base_damage=15,
            raw_damage=15,
            final_damage=12.0,
            absorbed=3.0,
            attacker_name="Warrior",
            defender_name="Goblin",
            defender_hp_before=100,
            defender_hp_after=88,
        )
        assert r.base_damage == 15
        assert r.final_damage == 12.0
        assert r.attacker_name == "Warrior"

    def test_with_side_effects(self):
        se = SideEffect(kind="poison", target_serial=1, value=3)
        r = HitResult(side_effects=[se])
        assert len(r.side_effects) == 1
        assert r.side_effects[0].kind == "poison"

    def test_error_state(self):
        r = HitResult(success=False, error="RuntimeError: oops")
        assert not r.success
        assert "oops" in r.error
