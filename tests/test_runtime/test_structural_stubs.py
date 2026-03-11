"""Tests for Batch 3 — structural POL built-in stubs."""

import omega.runtime  # noqa: F401
from omega.model.mobile import Mobile
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.registry import call_builtin


class TestApplyRawDamage:
    def test_reduces_hp(self):
        m = Mobile()
        m.hp = 100
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)

        call_builtin("uo", "ApplyRawDamage", [m, 30])
        assert m.hp == 70

    def test_records_damage(self):
        m = Mobile()
        m.hp = 100
        ctx = SimulationContext()
        set_context(ctx)

        call_builtin("uo", "ApplyRawDamage", [m, 50])
        assert ctx.total_damage_dealt == 50.0

    def test_records_side_effect(self):
        m = Mobile()
        m.hp = 100
        ctx = SimulationContext()
        set_context(ctx)

        call_builtin("uo", "ApplyRawDamage", [m, 25])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "damage"
        assert ctx.side_effects[0].value == 25

    def test_lethal_damage(self):
        m = Mobile()
        m.hp = 10
        ctx = SimulationContext()
        set_context(ctx)

        call_builtin("uo", "ApplyRawDamage", [m, 100])
        assert m.hp == 0
        assert m.dead is True

    def test_zero_damage_ignored(self):
        m = Mobile()
        m.hp = 100
        ctx = SimulationContext()
        set_context(ctx)

        call_builtin("uo", "ApplyRawDamage", [m, 0])
        assert m.hp == 100
        assert ctx.total_damage_dealt == 0.0


class TestGuildStubs:
    def test_find_guild(self):
        guild = call_builtin("uo", "FindGuild", [1])
        assert guild is not None

    def test_guild_not_enemy(self):
        guild = call_builtin("uo", "FindGuild", [1])
        assert guild.IsEnemyGuild(None) is False

    def test_guild_not_ally(self):
        guild = call_builtin("uo", "FindGuild", [1])
        assert guild.IsAllyGuild(None) is False


class TestScriptControl:
    def test_start_script_returns_none(self):
        result = call_builtin("os", "start_script", [":combat:crithit", None])
        assert result is None

    def test_start_script_case_variant(self):
        result = call_builtin("os", "Start_Script", [":combat:test"])
        assert result is None


class TestSideEffectRecording:
    def test_set_poisoned(self):
        m = Mobile(name="Victim")
        ctx = SimulationContext()
        set_context(ctx)

        call_builtin("uo", "SetPoisoned", [m, 3])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "poison"
        assert ctx.side_effects[0].value == 3

    def test_destroy_item(self):
        from omega.model.items import Weapon

        w = Weapon(name="BrokenSword")
        ctx = SimulationContext()
        set_context(ctx)

        call_builtin("uo", "DestroyItem", [w])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "item_destroyed"

    def test_set_paralyzed(self):
        m = Mobile()
        ctx = SimulationContext()
        set_context(ctx)

        call_builtin("uo", "SetParalyzed", [m, True])
        assert len(ctx.side_effects) == 1
        assert ctx.side_effects[0].kind == "paralyze"


class TestObjectLookup:
    def test_find_registered_object(self):
        m = Mobile(name="Warrior")
        ctx = SimulationContext()
        ctx.register_object(m)
        set_context(ctx)

        result = call_builtin("uo", "SystemFindObjectBySerial", [m.serial])
        assert result is m

    def test_find_missing_serial(self):
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "SystemFindObjectBySerial", [99999])
        assert result is None


class TestMiscStubs:
    def test_get_global_property_default(self):
        result = call_builtin("os", "GetGlobalProperty", ["powerHour"])
        assert result == 0

    def test_get_global_property_unknown(self):
        result = call_builtin("os", "GetGlobalProperty", ["unknown_prop"])
        assert result is None

    def test_enumerate_online_characters(self):
        result = call_builtin("uo", "EnumerateOnlineCharacters", [])
        assert result == []

    def test_no_op_equip_item(self):
        call_builtin("uo", "EquipItem", [None, None])

    def test_no_op_move_item(self):
        call_builtin("uo", "MoveItemToContainer", [None, None])


class TestApplyRawDamageExtended:
    """Extended ApplyRawDamage tests: negative damage, side effect target serial."""

    def test_negative_damage_ignored(self):
        m = Mobile()
        m.hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "ApplyRawDamage", [m, -10])
        assert m.hp == 100
        assert ctx.total_damage_dealt == 0.0

    def test_null_mobile_ignored(self):
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "ApplyRawDamage", [None, 50])
        assert ctx.total_damage_dealt == 0.0

    def test_side_effect_target_serial(self):
        m = Mobile(name="Target")
        m.hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        call_builtin("uo", "ApplyRawDamage", [m, 30])
        assert ctx.side_effects[0].target_serial == m.serial


class TestMoveObjectToLocation:
    """MoveObjectToLocation: no-op stub."""

    def test_no_op(self):
        m = Mobile(name="Mover")
        m.x = 100
        m.y = 200
        call_builtin("uo", "MoveObjectToLocation", [m, 500, 600, 0, "britannia", 0])
        # No-op — coordinates should NOT change
        assert m.x == 100
        assert m.y == 200
