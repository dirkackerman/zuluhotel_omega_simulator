"""SpellResult — structured output from a single spell execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from omega.runtime.context import SideEffect


@dataclass
class SpellResult:
    """Result of executing a single spell through the interpreter.

    Captures the spell damage pipeline values and any side effects recorded
    during execution.
    """

    # Spell identification
    spell_id: int = 0
    spell_name: str = ""
    circle: int = 0
    element: int = 0

    # Damage values
    base_damage: int = 0
    """CalcSpellDamage output (after efficiency, PvP/NPC scaling)."""

    final_damage: float = 0.0
    """Total damage actually applied via ApplyRawDamage."""

    absorbed: float = 0.0
    """Damage absorbed by elemental protection."""

    # Combat flags
    resisted: bool = False
    """Target resisted the spell (damage halved)."""

    fizzled: bool = False
    """CheckSkill failed — spell fizzled."""

    cast_success: bool = False
    """TryToCast returned SUCCESS (player mode only)."""

    immuned: bool = False
    """IsProtected blocked the spell entirely."""

    # Combatant info
    caster_name: str = ""
    target_name: str = ""
    target_hp_before: int = 0
    target_hp_after: int = 0

    # Side effects from script execution
    side_effects: list[SideEffect] = field(default_factory=list)

    # All metrics recorded by __RecordSimulatorMetric during this spell
    metrics: dict[str, Any] = field(default_factory=dict)

    # Timing
    casting_delay_ms: float = 0.0
    """Total casting time in milliseconds (from virtual time)."""

    # Execution status
    success: bool = True
    error: str | None = None
