"""POL built-in function registry.

Stubs register themselves with the ``@pol_function`` decorator and are
dispatched by the interpreter via ``call_builtin(module, name, args)``.

Usage in stub files::

    from omega.runtime.registry import pol_function

    @pol_function("uo", "GetObjProperty")
    def get_obj_property(obj, name):
        return obj.get_property(name)

Usage from interpreter::

    from omega.runtime.registry import call_builtin

    result = call_builtin("uo", "GetObjProperty", [mobile, "SlayType"])
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from omega.logging import get_logger

logger = get_logger("omega.runtime")

# Registry: (module_lower, function_lower) → callable
_registry: dict[tuple[str, str], Callable[..., Any]] = {}

# Track original names for logging
_registry_names: dict[tuple[str, str], tuple[str, str]] = {}


def pol_function(module: str, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a POL built-in function stub.

    Parameters
    ----------
    module:
        The POL module name (e.g., "uo", "vitals", "math").
        Use "" for global/unscoped functions.
    name:
        The function name as it appears in eScript.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        key = (module.lower(), name.lower())
        _registry[key] = func
        _registry_names[key] = (module, name)
        return func

    return decorator


def call_builtin(module: str, name: str, args: list[Any]) -> Any:
    """Dispatch a POL built-in function call.

    Looks up the stub by (module, name) case-insensitively.
    If not found, logs a WARNING and returns None.

    Parameters
    ----------
    module:
        The module prefix (e.g., "uo"). Empty string for bare calls.
    name:
        The function name.
    args:
        Positional arguments to pass.

    Returns
    -------
    Any:
        The stub's return value, or None if not found.
    """
    key = (module.lower(), name.lower())
    func = _registry.get(key)

    if func is not None:
        return func(*args)

    # Try bare lookup (no module prefix) as fallback
    if module:
        bare_key = ("", name.lower())
        func = _registry.get(bare_key)
        if func is not None:
            return func(*args)

    qualified = f"{module}::{name}" if module else name
    logger.warning(
        f"Unimplemented built-in: {qualified}(… {len(args)} args)",
        module=module or "(global)",
        function=name,
        arg_count=len(args),
    )
    return None


def is_registered(module: str, name: str) -> bool:
    """Check if a built-in function is registered."""
    key = (module.lower(), name.lower())
    if key in _registry:
        return True
    if module:
        return ("", name.lower()) in _registry
    return False


def list_registered() -> list[tuple[str, str]]:
    """Return all registered (module, name) pairs with original casing."""
    return list(_registry_names.values())


def clear_registry() -> None:
    """Clear all registered stubs. Used for testing."""
    _registry.clear()
    _registry_names.clear()
