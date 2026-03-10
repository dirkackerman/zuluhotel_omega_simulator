"""Hot-reload utility for interactive / Jupyter workflows.

Call ``reload_omega()`` after editing source files to pick up changes
without restarting the kernel.
"""

from __future__ import annotations

import importlib
import sys


# Modules that hold singleton state (registries, caches) and must NOT be
# reloaded — doing so replaces module-level dicts/sets, orphaning any
# references other modules already hold to the old objects.
_SKIP_RELOAD = frozenset({
    "omega.runtime.registry",
})


def reload_omega() -> list[str]:
    """Reload all loaded ``omega.*`` modules.

    Returns the list of module names that were reloaded.  Modules are
    reloaded in sorted order (parents before children) so that
    cross-module references stay consistent.

    Modules in ``_SKIP_RELOAD`` are excluded because they hold singleton
    state (e.g., the POL built-in function registry) that would be lost
    on reload.

    Usage (in a notebook cell)::

        from omega.reporting.reload import reload_omega
        reload_omega()
    """
    omega_modules = sorted(
        name for name in sys.modules
        if name == "omega" or name.startswith("omega.")
    )

    reloaded: list[str] = []
    for name in omega_modules:
        if name in _SKIP_RELOAD:
            continue
        mod = sys.modules.get(name)
        if mod is None:
            continue
        try:
            importlib.reload(mod)
            reloaded.append(name)
        except Exception:
            # Skip modules that fail to reload (e.g. namespace packages)
            pass

    return reloaded
