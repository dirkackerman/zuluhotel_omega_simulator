"""Tests for simulation context and side effect tracking."""

from omega.runtime.context import SimulationContext, set_context


class TestSimulationContext:
    def test_default_values(self):
        ctx = SimulationContext()
        assert ctx.attacker is None
        assert ctx.defender is None
        assert ctx.iteration == 0
        assert ctx.debug_mode is False
        assert ctx.total_damage_dealt == 0.0
        assert ctx.side_effects == []

    def test_record_side_effect(self):
        ctx = SimulationContext()
        ctx.record_side_effect("poison", target_serial=123, value=3)
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "poison"
        assert ctx.side_effects[0].target_serial == 123
        assert ctx.side_effects[0].value == 3

    def test_record_damage(self):
        ctx = SimulationContext()
        ctx.record_damage(50.0)
        ctx.record_damage(25.0)
        assert ctx.total_damage_dealt == 75.0

    def test_record_absorption(self):
        ctx = SimulationContext()
        ctx.record_absorption(10.0)
        assert ctx.damage_absorbed == 10.0

    def test_reset_hit(self):
        ctx = SimulationContext()
        ctx.record_damage(100.0)
        ctx.record_side_effect("poison", target_serial=1, value=1)
        ctx.record_absorption(20.0)
        initial_iteration = ctx.iteration

        ctx.reset_hit()

        assert ctx.total_damage_dealt == 0.0
        assert ctx.damage_absorbed == 0.0
        assert ctx.side_effects == []
        assert ctx.iteration == initial_iteration + 1

    def test_reset_preserves_config_cache(self):
        ctx = SimulationContext()
        ctx.cache_config("test.cfg", {"data": True})
        ctx.reset_hit()
        assert ctx.get_cached_config("test.cfg") == {"data": True}


class TestObjectRegistry:
    def test_register_and_find(self):
        ctx = SimulationContext()

        class FakeObj:
            serial = 42

        obj = FakeObj()
        ctx.register_object(obj)
        assert ctx.find_object(42) is obj

    def test_find_missing(self):
        ctx = SimulationContext()
        assert ctx.find_object(999) is None


class TestConfigCache:
    def test_cache_and_retrieve(self):
        ctx = SimulationContext()
        ctx.cache_config("settings.cfg", "parsed_data")
        assert ctx.get_cached_config("settings.cfg") == "parsed_data"

    def test_cache_miss(self):
        ctx = SimulationContext()
        assert ctx.get_cached_config("nonexistent.cfg") is None
