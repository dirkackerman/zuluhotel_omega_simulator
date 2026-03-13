"""Simulation context — per-hit state and side effect tracking.

The context holds references to the current combatants and records
side effects (damage dealt, poison applied, equipment damaged, etc.)
during each hit iteration. Reset between iterations.

Stored in a ``contextvars.ContextVar`` so stubs can access it without
passing context through every function call.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from typing import Any

from omega.logging import get_logger

logger = get_logger("omega.runtime")

_ctx_var: contextvars.ContextVar[SimulationContext] = contextvars.ContextVar("omega_sim_ctx")


@dataclass
class SideEffect:
    """A single recorded side effect from a combat hit."""

    kind: str
    target_serial: int
    value: Any = None
    detail: str = ""


@dataclass
class SimulationContext:
    """Per-hit simulation state.

    Attributes
    ----------
    attacker:
        The attacking mobile (or None if not yet set).
    defenders:
        List of defending mobiles for AoE support. Use the ``defender``
        property to access the primary target.
    main_target_index:
        Index into ``defenders`` for the primary target (default 0).
    weapon:
        The weapon used (or None).
    iteration:
        Current iteration number.
    debug_mode:
        When True, SendSysMessage and similar stubs log their output.
    game_clock:
        Simulated game clock value (increments per iteration).
    """

    attacker: Any = None
    defenders: list[Any] = field(default_factory=list)
    main_target_index: int = 0
    weapon: Any = None
    iteration: int = 0
    debug_mode: bool = False
    game_clock: int = 1000

    # Virtual time accumulated within an iteration (milliseconds).
    # Sleepms/Sleep advance this; ReadGameClock uses it.
    _virtual_time_ms: int = 0

    @property
    def defender(self) -> Any:
        """Primary target — backward compatible with single-defender code."""
        if not self.defenders:
            return None
        return self.defenders[self.main_target_index]

    @defender.setter
    def defender(self, value: Any) -> None:
        """Set single defender — backward compatible."""
        if not self.defenders:
            self.defenders = [value]
        else:
            self.defenders[self.main_target_index] = value

    # Side effects recorded during this hit
    side_effects: list[SideEffect] = field(default_factory=list)

    # Damage tracking
    total_damage_dealt: float = 0.0
    damage_absorbed: float = 0.0

    # Object registry for SystemFindObjectBySerial
    _object_registry: dict[int, Any] = field(default_factory=dict)

    # Config file cache for ReadConfigFile
    _config_cache: dict[str, Any] = field(default_factory=dict)

    # Config path resolver: maps ":pkg:name" → filesystem Path
    # Set by combat runner when a shard is loaded
    _config_resolver: Any = None

    # Metrics recorded by __RecordSimulatorMetric from eScript
    metrics: dict[str, Any] = field(default_factory=dict)

    # Global properties (GetGlobalProperty/SetGlobalProperty)
    global_properties: dict[str, Any] = field(default_factory=dict)

    # Executor reference for start_script() sub-program dispatch
    executor: Any = None

    def record_side_effect(
        self, kind: str, target_serial: int, value: Any = None, detail: str = ""
    ) -> None:
        """Record a side effect from combat."""
        self.side_effects.append(
            SideEffect(kind=kind, target_serial=target_serial, value=value, detail=detail)
        )

    def record_damage(self, amount: float) -> None:
        """Record damage dealt."""
        self.total_damage_dealt += amount

    def record_absorption(self, amount: float) -> None:
        """Record damage absorbed by armor."""
        self.damage_absorbed += amount

    def register_object(self, obj: Any) -> None:
        """Register a game object for serial-based lookup."""
        self._object_registry[obj.serial] = obj

    def find_object(self, serial: int) -> Any:
        """Find a registered object by serial."""
        return self._object_registry.get(serial)

    def get_cached_config(self, path: str) -> Any:
        """Get a cached config file, or None."""
        return self._config_cache.get(path)

    def cache_config(self, path: str, cfg: Any) -> None:
        """Cache a parsed config file."""
        self._config_cache[path] = cfg

    def reset_hit(self) -> None:
        """Reset per-hit state for the next iteration.

        Preserves config cache, object registry, and defenders list;
        clears side effects, damage tracking, and virtual time.
        """
        self.side_effects.clear()
        self.total_damage_dealt = 0.0
        self.damage_absorbed = 0.0
        self.metrics.clear()
        self.iteration += 1
        self.game_clock += 1
        self._virtual_time_ms = 0


def get_context() -> SimulationContext:
    """Get the current simulation context."""
    try:
        return _ctx_var.get()
    except LookupError:
        ctx = SimulationContext()
        _ctx_var.set(ctx)
        return ctx


def set_context(ctx: SimulationContext) -> None:
    """Set the simulation context."""
    _ctx_var.set(ctx)
