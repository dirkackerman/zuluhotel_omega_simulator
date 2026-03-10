"""Deterministic RNG for reproducible simulations.

Each simulation iteration gets its own seeded ``Random`` instance.
The RNG is stored in a ``contextvars.ContextVar`` so stubs can access
it without threading state through every function call.

Usage::

    from omega.runtime.rng import get_rng, set_rng_seed

    set_rng_seed(42)
    rng = get_rng()
    rng.random_int(100)   # 0..99, deterministic
    rng.random(100)       # 1..100, deterministic
"""

from __future__ import annotations

import contextvars
from random import Random

_rng_var: contextvars.ContextVar[SimulationRNG] = contextvars.ContextVar("omega_rng")


class SimulationRNG:
    """Seeded RNG wrapper matching POL's Random/RandomInt semantics."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = Random(seed)
        self._seed = seed

    @property
    def seed(self) -> int:
        return self._seed

    def random_int(self, max_val: int) -> int:
        """Return random integer in [0, max_val-1]. Matches POL's RandomInt()."""
        if max_val <= 0:
            return 0
        return self._rng.randint(0, max_val - 1)

    def random(self, max_val: int) -> int:
        """Return random integer in [1, max_val]. Matches POL's Random()."""
        if max_val <= 0:
            return 0
        return self._rng.randint(1, max_val)

    def random_float(self) -> float:
        """Return random float in [0.0, 1.0)."""
        return self._rng.random()


def get_rng() -> SimulationRNG:
    """Get the current simulation RNG from context."""
    try:
        return _rng_var.get()
    except LookupError:
        # Default unseeded RNG if none set
        rng = SimulationRNG(0)
        _rng_var.set(rng)
        return rng


def set_rng_seed(seed: int) -> SimulationRNG:
    """Create a new RNG with the given seed and set it in context."""
    rng = SimulationRNG(seed)
    _rng_var.set(rng)
    return rng
