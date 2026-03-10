"""Tests for deterministic RNG."""

from omega.runtime.rng import SimulationRNG, set_rng_seed


class TestSimulationRNG:
    def test_deterministic_same_seed(self):
        rng1 = SimulationRNG(42)
        rng2 = SimulationRNG(42)
        results1 = [rng1.random(100) for _ in range(10)]
        results2 = [rng2.random(100) for _ in range(10)]
        assert results1 == results2

    def test_different_seeds_differ(self):
        rng1 = SimulationRNG(1)
        rng2 = SimulationRNG(2)
        results1 = [rng1.random(100) for _ in range(10)]
        results2 = [rng2.random(100) for _ in range(10)]
        assert results1 != results2

    def test_random_bounds(self):
        rng = SimulationRNG(0)
        for _ in range(100):
            val = rng.random(10)
            assert 1 <= val <= 10

    def test_random_int_bounds(self):
        rng = SimulationRNG(0)
        for _ in range(100):
            val = rng.random_int(10)
            assert 0 <= val <= 9

    def test_random_zero_max(self):
        rng = SimulationRNG(0)
        assert rng.random(0) == 0
        assert rng.random_int(0) == 0

    def test_seed_property(self):
        rng = SimulationRNG(42)
        assert rng.seed == 42


class TestRNGContext:
    def test_set_rng_seed(self):
        rng = set_rng_seed(99)
        assert rng.seed == 99
        val1 = rng.random(1000)

        rng2 = set_rng_seed(99)
        val2 = rng2.random(1000)
        assert val1 == val2
