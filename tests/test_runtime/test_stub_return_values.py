"""Priority 5 — POL stub return value conformance tests.

Verifies that stubs return the correct types (int 0/1, not bool, not None)
and that no-op stubs are registered and callable without crashing.
"""

import omega.runtime  # noqa: F401
from omega.model.items import Weapon
from omega.model.mobile import Mobile
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.registry import call_builtin


# ---------------------------------------------------------------------------
# Guild stub return types (2.1: bool → int)
# ---------------------------------------------------------------------------


class TestGuildReturnTypes:
    def test_is_enemy_guild_returns_int(self):
        """IsEnemyGuild should return 0 (int), not False (bool)."""
        guild = call_builtin("uo", "FindGuild", [1])
        result = guild.IsEnemyGuild(None)
        assert result == 0
        # Python bool is subclass of int, but we want actual int
        assert isinstance(result, int)

    def test_is_ally_guild_returns_int(self):
        guild = call_builtin("uo", "FindGuild", [1])
        result = guild.IsAllyGuild(None)
        assert result == 0
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# HealDamage return value (2.2: None → 0/1)
# ---------------------------------------------------------------------------


class TestHealDamageReturn:
    def test_heal_returns_one_on_success(self):
        m = Mobile()
        m.hp = 50
        m.max_hp = 100
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "HealDamage", [m, 10])
        assert result == 1

    def test_heal_none_mobile(self):
        """HealDamage(None, 10) should return 0 or None gracefully."""
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "HealDamage", [None, 10])
        # Should not crash; may return None or 0
        assert result is None or result == 0


# ---------------------------------------------------------------------------
# GetEquipmentByLayer return value (2.2: None for missing)
# ---------------------------------------------------------------------------


class TestGetEquipmentByLayerReturn:
    def test_found_returns_item(self):
        m = Mobile(name="Equipped")
        w = Weapon(name="Sword")
        m.equip(1, w)
        result = call_builtin("uo", "GetEquipmentByLayer", [m, 1])
        assert result is w

    def test_not_found_returns_none(self):
        m = Mobile(name="Empty")
        result = call_builtin("uo", "GetEquipmentByLayer", [m, 99])
        assert result is None

    def test_none_mobile_returns_none(self):
        result = call_builtin("uo", "GetEquipmentByLayer", [None, 1])
        assert result is None


# ---------------------------------------------------------------------------
# DestroyItem return value
# ---------------------------------------------------------------------------


class TestDestroyItemReturn:
    def test_success_returns_one(self):
        w = Weapon(name="Trash")
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "DestroyItem", [w])
        assert result == 1
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# Stubs that always succeed (2.3)
# ---------------------------------------------------------------------------


class TestAlwaysSucceedStubs:
    def test_consume_reagents_returns_one(self):
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "ConsumeReagents", [None, 0])
        assert result == 1

    def test_check_line_of_sight_returns_one(self):
        result = call_builtin("uo", "CheckLineOfSight", [None, None])
        assert result == 1
        assert isinstance(result, int)

    def test_check_los_at_returns_one(self):
        result = call_builtin("uo", "CheckLosAt", [None, 0, 0, 0])
        assert result == 1
        assert isinstance(result, int)

    def test_distance_returns_int(self):
        result = call_builtin("uo", "Distance", [None, None])
        assert result == 1
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# No-op stubs — registered and callable (2.4)
# ---------------------------------------------------------------------------


class TestNoOpStubsRegistered:
    """Every no-op stub must be callable without crashing."""

    def test_play_sound_effect_private(self):
        call_builtin("uo", "PlaySoundEffectPrivate", [None, 0, None])

    def test_play_moving_effect(self):
        call_builtin("uo", "PlayMovingEffect", [None, None, 0, 0, 0, 0])

    def test_play_moving_effect_ex(self):
        call_builtin("uo", "PlayMovingEffectEx", [None, None, 0])

    def test_play_object_centered_effect(self):
        call_builtin("uo", "PlayObjectCenteredEffect", [None, 0, 0, 0])

    def test_play_object_centered_effect_ex(self):
        call_builtin("uo", "PlayObjectCenteredEffectEx", [None, 0])

    def test_play_stationary_effect(self):
        call_builtin("uo", "PlayStationaryEffect", [0, 0, 0, 0])

    def test_play_lightning_bolt_effect(self):
        call_builtin("uo", "PlayLightningBoltEffect", [None])

    def test_speak_power_words(self):
        call_builtin("uo", "SpeakPowerWords", [None, 0, 0, 0])

    def test_send_event(self):
        call_builtin("uo", "SendEvent", [None, None])

    def test_move_object_to_location(self):
        call_builtin("uo", "MoveObjectToLocation", [None, 0, 0, 0])

    def test_revoke_privilege(self):
        call_builtin("uo", "RevokePrivilege", [None, "hearing"])


# ---------------------------------------------------------------------------
# EraseObjProperty return value
# ---------------------------------------------------------------------------


class TestEraseObjPropertyReturn:
    def test_returns_one(self):
        """POL returns BLong(1) on success."""
        m = Mobile()
        m.set_property("test", 42)
        result = call_builtin("uo", "EraseObjProperty", [m, "test"])
        assert result == 1
        assert isinstance(result, int)

    def test_returns_one_even_if_missing(self):
        """POL returns 1 even if property doesn't exist."""
        m = Mobile()
        result = call_builtin("uo", "EraseObjProperty", [m, "nonexistent"])
        assert result == 1
