"""POL runtime stubs for the Omega combat simulator.

Importing this package registers all built-in function stubs.

Usage::

    import omega.runtime  # registers all stubs
    from omega.runtime.registry import call_builtin

    result = call_builtin("uo", "GetObjProperty", [mobile, "SlayType"])
"""

# Import stub modules to trigger @pol_function registration
from omega.runtime import basic_stubs as _basic  # noqa: F401
from omega.runtime import object_stubs as _object  # noqa: F401
from omega.runtime import structural_stubs as _structural  # noqa: F401
from omega.runtime.context import SimulationContext, get_context, set_context
from omega.runtime.registry import call_builtin, is_registered
from omega.runtime.rng import SimulationRNG, get_rng, set_rng_seed

__all__ = [
    "SimulationContext",
    "SimulationRNG",
    "call_builtin",
    "get_context",
    "get_rng",
    "is_registered",
    "set_context",
    "set_rng_seed",
]
