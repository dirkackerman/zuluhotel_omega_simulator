"""HitResult — structured output from a single combat hit execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from omega.runtime.context import SideEffect


@dataclass
class HitResult:
    """Result of executing a single combat hit through the interpreter.

    Captures the damage pipeline values and any side effects recorded
    during execution.
    """

    # Damage values
    base_damage: int = 0
    """Weapon roll before any modifiers (from dice roll)."""

    raw_damage: int = 0
    """Damage after multipliers, before absorption (passed to mainhit)."""

    final_damage: float = 0.0
    """Total damage actually applied via ApplyRawDamage."""

    absorbed: float = 0.0
    """Total damage absorbed by armor."""

    # Combat flags
    attacker_name: str = ""
    defender_name: str = ""
    defender_hp_before: int = 0
    defender_hp_after: int = 0

    # Side effects from the script execution
    side_effects: list[SideEffect] = field(default_factory=list)

    # Debug: execution log messages
    hit_log: list[str] = field(default_factory=list)

    # All metrics recorded by __RecordSimulatorMetric during this hit
    metrics: dict[str, Any] = field(default_factory=dict)

    # Whether the script executed successfully
    success: bool = True
    error: str | None = None
