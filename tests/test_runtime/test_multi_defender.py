"""Tests for multi-defender context support."""

from omega.runtime.context import SimulationContext, set_context


class _FakeMobile:
    def __init__(self, serial, name="mob", x=0, y=0, z=0):
        self.serial = serial
        self.name = name
        self.x = x
        self.y = y
        self.z = z


class TestMultiDefenderContext:
    def test_defender_property_none_when_empty(self):
        ctx = SimulationContext()
        assert ctx.defender is None
        assert ctx.defenders == []

    def test_defender_setter_creates_list(self):
        ctx = SimulationContext()
        mob = _FakeMobile(1, "target")
        ctx.defender = mob
        assert ctx.defenders == [mob]
        assert ctx.defender is mob

    def test_defenders_list_direct(self):
        mob1 = _FakeMobile(1, "t1")
        mob2 = _FakeMobile(2, "t2")
        mob3 = _FakeMobile(3, "t3")
        ctx = SimulationContext(defenders=[mob1, mob2, mob3])
        assert ctx.defender is mob1  # default index 0
        assert len(ctx.defenders) == 3

    def test_main_target_index(self):
        mob1 = _FakeMobile(1, "t1")
        mob2 = _FakeMobile(2, "t2")
        ctx = SimulationContext(defenders=[mob1, mob2], main_target_index=1)
        assert ctx.defender is mob2

    def test_defender_setter_replaces_at_index(self):
        mob1 = _FakeMobile(1, "t1")
        mob2 = _FakeMobile(2, "t2")
        mob3 = _FakeMobile(3, "t3")
        ctx = SimulationContext(defenders=[mob1, mob2])
        ctx.defender = mob3  # replaces at index 0
        assert ctx.defenders[0] is mob3
        assert ctx.defenders[1] is mob2

    def test_backward_compat_hit_pattern(self):
        """Existing execute_hit pattern: set defender after construction."""
        mob = _FakeMobile(1, "defender")
        ctx = SimulationContext(attacker=_FakeMobile(2, "attacker"))
        ctx.defender = mob
        assert ctx.defender is mob
        assert ctx.defenders == [mob]

    def test_reset_preserves_defenders(self):
        mob = _FakeMobile(1, "target")
        ctx = SimulationContext(defenders=[mob])
        ctx.record_damage(50.0)
        ctx.reset_hit()
        assert ctx.defenders == [mob]
        assert ctx.total_damage_dealt == 0.0


class TestMultiDefenderStubs:
    def test_target_returns_main_defender(self):
        mob1 = _FakeMobile(1, "t1")
        mob2 = _FakeMobile(2, "t2")
        ctx = SimulationContext(defenders=[mob1, mob2], main_target_index=1)
        set_context(ctx)

        from omega.runtime.structural_stubs import target_stub
        result = target_stub(character=_FakeMobile(3, "caster"))
        assert result is mob2

    def test_list_mobiles_near_location_ex_returns_all(self):
        mob1 = _FakeMobile(1, "t1")
        mob2 = _FakeMobile(2, "t2")
        mob3 = _FakeMobile(3, "t3")
        ctx = SimulationContext(defenders=[mob1, mob2, mob3])
        set_context(ctx)

        from omega.runtime.structural_stubs import list_mobiles_near_location_ex
        result = list_mobiles_near_location_ex(0, 0, 0, 10, 1)
        assert len(result) == 3
        assert mob1 in result

    def test_list_mobiles_near_location_returns_all(self):
        mob1 = _FakeMobile(1, "t1")
        mob2 = _FakeMobile(2, "t2")
        ctx = SimulationContext(defenders=[mob1, mob2])
        set_context(ctx)

        from omega.runtime.structural_stubs import list_mobiles_near_location
        result = list_mobiles_near_location(0, 0, 0, 10)
        assert len(result) == 2

    def test_list_hostiles_returns_empty(self):
        ctx = SimulationContext(defenders=[_FakeMobile(1)])
        set_context(ctx)

        from omega.runtime.structural_stubs import list_hostiles
        result = list_hostiles(_FakeMobile(2), 4, 0)
        assert result == []

    def test_target_coordinates_returns_struct(self):
        mob = _FakeMobile(1, "t1", x=100, y=200, z=5)
        ctx = SimulationContext(defenders=[mob])
        set_context(ctx)

        from omega.runtime.structural_stubs import target_coordinates
        result = target_coordinates(_FakeMobile(2, "caster"))
        assert result.get_member("x") == 100
        assert result.get_member("y") == 200
        assert result.get_member("z") == 5
