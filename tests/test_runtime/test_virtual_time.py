"""Tests for virtual time — Sleepms/Sleep advance game clock."""

from omega.runtime.context import SimulationContext, set_context


def _setup_ctx(**kwargs):
    ctx = SimulationContext(**kwargs)
    set_context(ctx)
    return ctx


class TestSleepmsVirtualTime:
    def test_sleepms_advances_virtual_time(self):
        ctx = _setup_ctx(game_clock=1000)
        from omega.runtime.basic_stubs import sleepms, read_game_clock

        sleepms(500)
        sleepms(500)
        sleepms(500)
        sleepms(500)
        assert read_game_clock() == 1002

    def test_sleep_advances_virtual_time(self):
        ctx = _setup_ctx(game_clock=1000)
        from omega.runtime.basic_stubs import sleep_func, read_game_clock

        sleep_func(3)
        assert read_game_clock() == 1003

    def test_sub_second_accumulation(self):
        ctx = _setup_ctx(game_clock=1000)
        from omega.runtime.basic_stubs import sleepms, read_game_clock

        sleepms(300)
        sleepms(300)
        sleepms(300)
        # 900ms — not yet 1 second
        assert read_game_clock() == 1000
        sleepms(300)
        # 1200ms — 1 full second
        assert read_game_clock() == 1001

    def test_virtual_time_resets_between_hits(self):
        ctx = _setup_ctx(game_clock=1000)
        from omega.runtime.basic_stubs import sleepms, read_game_clock

        sleepms(2000)
        assert read_game_clock() == 1002

        ctx.reset_hit()
        # After reset: game_clock incremented by 1 (to 1001), virtual time cleared
        assert read_game_clock() == 1001

    def test_readgameclock_with_base_clock(self):
        ctx = _setup_ctx(game_clock=5000)
        from omega.runtime.basic_stubs import sleepms, read_game_clock

        sleepms(2500)
        assert read_game_clock() == 5002

    def test_trytocast_delay_loop_pattern(self):
        """Simulate the TryToCast delay loop: spelldelay=3000 → 6 iterations of Sleepms(500)."""
        ctx = _setup_ctx(game_clock=1000)
        from omega.runtime.basic_stubs import sleepms, read_game_clock

        spelldelay = 3000
        while spelldelay >= 500:
            sleepms(500)
            spelldelay -= 500

        # 6 × 500ms = 3000ms = 3 seconds
        assert read_game_clock() == 1003
        assert ctx._virtual_time_ms == 3000


class TestReadGameClockIntegration:
    def test_returns_integer(self):
        ctx = _setup_ctx(game_clock=1000)
        from omega.runtime.basic_stubs import read_game_clock

        result = read_game_clock()
        assert isinstance(result, int)

    def test_advances_with_mixed_sleep(self):
        ctx = _setup_ctx(game_clock=100)
        from omega.runtime.basic_stubs import sleepms, sleep_func, read_game_clock

        sleepms(500)
        sleep_func(2)
        sleepms(700)
        # 500 + 2000 + 700 = 3200ms = 3 seconds
        assert read_game_clock() == 103


class TestVirtualTimeEdgeCases:
    def test_zero_ms(self):
        ctx = _setup_ctx(game_clock=1000)
        from omega.runtime.basic_stubs import sleepms, read_game_clock

        sleepms(0)
        assert read_game_clock() == 1000
        assert ctx._virtual_time_ms == 0

    def test_none_ms(self):
        ctx = _setup_ctx(game_clock=1000)
        from omega.runtime.basic_stubs import sleepms, read_game_clock

        sleepms(None)
        assert read_game_clock() == 1000
