"""Result aggregation and statistical computation for simulations.

Computes per-cell statistics (mean, median, percentiles, ratios) from
lists of :class:`~omega.combat.result.HitResult` objects.  Uses the
Python ``statistics`` standard library — no numpy required.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from omega.combat.result import HitResult


def _safe_float(val: Any) -> float:
    """Convert a value to float, returning 0.0 for non-numeric types (e.g. UNINIT)."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Statistical summary dataclasses
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DamageStats:
    """Statistical summary over a sequence of damage values."""

    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    min: float = 0.0
    max: float = 0.0
    std_dev: float = 0.0
    p5: float = 0.0
    p25: float = 0.0
    p75: float = 0.0
    p95: float = 0.0


@dataclass(slots=True)
class RatioStats:
    """Event frequency ratios (0.0–1.0).

    "Overall" rates (``hit_rate``, ``spell_strike_rate``, etc.) are computed
    over **all swings**, including misses.  "On-hit" rates
    (``spell_strike_rate_on_hit``, etc.) are computed over **hits only**,
    showing the conditional probability given that the swing connected.
    """

    hit_rate: float = 0.0
    poison_rate: float = 0.0
    equipment_break_rate: float = 0.0
    reactive_rate: float = 0.0
    spell_strike_rate: float = 0.0
    effect_rate: float = 0.0

    # Conditional rates — given the swing hit, how often did X happen?
    reactive_rate_on_hit: float = 0.0
    spell_strike_rate_on_hit: float = 0.0
    effect_rate_on_hit: float = 0.0


# Bitflag → field name mapping for element types
_DMGID_TO_ELEMENT: dict[int, str] = {
    0x0001: "fire",
    0x0002: "air",
    0x0004: "earth",
    0x0008: "water",
    0x0010: "necro",
    0x0020: "holy",
    0x0040: "poison",
    0x0080: "acid",
    0x0100: "physical",
    0x0200: "magic",
    0x0400: "astral",
}


@dataclass(slots=True)
class ElementDamage:
    """Aggregated damage stats for a single element type.

    All values are means across iterations.
    """

    gross: float = 0.0
    """Mean damage before protection reduction."""

    net: float = 0.0
    """Mean damage after protection reduction."""

    prot: float = 0.0
    """Mean protection percentage applied (0–100+)."""

    healed: float = 0.0
    """Mean amount healed via over-protection (>100%)."""

    @property
    def absorbed(self) -> float:
        """Mean damage absorbed by protection (gross - net)."""
        return self.gross - self.net


# All known element names in canonical order
_ELEMENT_NAMES = (
    "fire", "air", "earth", "water", "necro", "holy",
    "poison", "acid", "physical", "magic", "astral",
)


@dataclass
class ElementalBreakdown:
    """Per-element damage breakdown from the elemental damage pipeline.

    Contains an :class:`ElementDamage` per element that was active.
    Only populated for weapons with ``ElementalDamage`` property.
    """

    elements: dict[str, ElementDamage] = field(default_factory=dict)
    """Mapping of element name → :class:`ElementDamage`."""

    @property
    def total_net(self) -> float:
        """Sum of net damage across all elements."""
        return sum(ed.net for ed in self.elements.values())

    @property
    def total_gross(self) -> float:
        """Sum of gross damage across all elements."""
        return sum(ed.gross for ed in self.elements.values())

    def net_dict(self, *, include_zero: bool = False) -> dict[str, float]:
        """Return ``{element_name: net_damage}`` mapping.

        By default only includes non-zero elements.
        """
        if include_zero:
            return {name: self.elements.get(name, ElementDamage()).net for name in _ELEMENT_NAMES}
        return {name: ed.net for name, ed in self.elements.items() if ed.net != 0.0}

    def gross_dict(self, *, include_zero: bool = False) -> dict[str, float]:
        """Return ``{element_name: gross_damage}`` mapping."""
        if include_zero:
            return {name: self.elements.get(name, ElementDamage()).gross for name in _ELEMENT_NAMES}
        return {name: ed.gross for name, ed in self.elements.items() if ed.gross != 0.0}

    def prot_dict(self, *, include_zero: bool = False) -> dict[str, float]:
        """Return ``{element_name: protection_%}`` mapping."""
        if include_zero:
            return {name: self.elements.get(name, ElementDamage()).prot for name in _ELEMENT_NAMES}
        return {name: ed.prot for name, ed in self.elements.items() if ed.prot != 0.0}


@dataclass
class CellResult:
    """Results for a single scenario (one cell in a sweep grid)."""

    variable_values: dict[str, Any] = field(default_factory=dict)
    damage_stats: DamageStats = field(default_factory=DamageStats)
    base_damage_stats: DamageStats = field(default_factory=DamageStats)
    absorbed_stats: DamageStats = field(default_factory=DamageStats)
    ratios: RatioStats = field(default_factory=RatioStats)
    elemental_breakdown: ElementalBreakdown = field(default_factory=ElementalBreakdown)
    drain_stats: DamageStats = field(default_factory=DamageStats)
    """Stats for effect drain amount (mana/hp/stamina drained per hit)."""

    # On-hit variants — stats computed only over swings that connected
    damage_stats_on_hit: DamageStats = field(default_factory=DamageStats)
    """Damage stats for hits only (excludes misses with 0 damage)."""
    drain_stats_on_hit: DamageStats = field(default_factory=DamageStats)
    """Drain stats for hits only (excludes misses)."""

    raw_results: list[HitResult] = field(default_factory=list)
    iteration_count: int = 0
    success_count: int = 0
    error_count: int = 0


@dataclass
class SimulationResult:
    """Full results of a parameter sweep."""

    cells: list[CellResult] = field(default_factory=list)
    total_time: float = 0.0

    def get_cell(self, **variable_values: Any) -> CellResult | None:
        """Look up a cell by its variable values."""
        for cell in self.cells:
            if all(cell.variable_values.get(k) == v for k, v in variable_values.items()):
                return cell
        return None

    def damage_curve(self, variable_name: str) -> list[tuple[Any, DamageStats]]:
        """Extract ``(value, damage_stats)`` pairs for a single variable.

        Useful for plotting damage vs. a swept parameter.
        """
        return [
            (cell.variable_values.get(variable_name), cell.damage_stats)
            for cell in self.cells
            if variable_name in cell.variable_values
        ]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _compute_damage_stats(values: list[float]) -> DamageStats:
    """Compute statistical summary from a list of numeric values."""
    if not values:
        return DamageStats()

    n = len(values)
    sorted_vals = sorted(values)

    mean = statistics.mean(sorted_vals)
    median = statistics.median(sorted_vals)
    std_dev = statistics.stdev(sorted_vals) if n >= 2 else 0.0

    if n >= 4:
        quartiles = statistics.quantiles(sorted_vals, n=20)
        p5 = quartiles[0]    # 5th percentile  (index 0 of 20-quantiles)
        p25 = quartiles[4]   # 25th percentile (index 4)
        p75 = quartiles[14]  # 75th percentile (index 14)
        p95 = quartiles[18]  # 95th percentile (index 18)
    else:
        p5 = sorted_vals[0]
        p25 = sorted_vals[0]
        p75 = sorted_vals[-1]
        p95 = sorted_vals[-1]

    return DamageStats(
        count=n,
        mean=mean,
        median=median,
        min=sorted_vals[0],
        max=sorted_vals[-1],
        std_dev=std_dev,
        p5=p5,
        p25=p25,
        p75=p75,
        p95=p95,
    )


def aggregate_cell(results: list[HitResult]) -> CellResult:
    """Compute all statistics from a list of HitResult objects."""
    cell = CellResult(
        raw_results=results,
        iteration_count=len(results),
    )

    if not results:
        return cell

    # Separate successes/errors
    successes = [r for r in results if r.success]
    cell.success_count = len(successes)
    cell.error_count = len(results) - len(successes)

    if not successes:
        return cell

    # Damage stats — overall (all swings including misses)
    final_damages = [r.final_damage for r in successes]
    base_damages = [float(r.base_damage) for r in successes]
    absorbed_vals = [r.absorbed for r in successes]

    cell.damage_stats = _compute_damage_stats(final_damages)
    cell.base_damage_stats = _compute_damage_stats(base_damages)
    cell.absorbed_stats = _compute_damage_stats(absorbed_vals)

    # Separate hits (damage > 0) from misses
    hits_only = [r for r in successes if r.final_damage > 0]
    n = len(successes)
    n_hits = len(hits_only)

    # On-hit damage stats (only swings that connected)
    if hits_only:
        hit_damages = [r.final_damage for r in hits_only]
        cell.damage_stats_on_hit = _compute_damage_stats(hit_damages)

    # Event counts
    poisons = sum(
        1 for r in successes
        if any(se.kind == "poison_applied" for se in r.side_effects)
    )
    equip_breaks = sum(
        1 for r in successes
        if any(se.kind == "equipment_damaged" for se in r.side_effects)
    )

    reactives = sum(
        1 for r in successes
        if r.metrics.get("reactive_triggered")
    )
    spell_strikes = sum(
        1 for r in successes
        if r.metrics.get("spell_strike_triggered")
    )
    effects = sum(
        1 for r in successes
        if r.metrics.get("effect_triggered")
    )

    cell.ratios = RatioStats(
        hit_rate=n_hits / n,
        poison_rate=poisons / n,
        equipment_break_rate=equip_breaks / n,
        reactive_rate=reactives / n,
        spell_strike_rate=spell_strikes / n,
        effect_rate=effects / n,
        # On-hit conditional rates
        reactive_rate_on_hit=reactives / n_hits if n_hits else 0.0,
        spell_strike_rate_on_hit=spell_strikes / n_hits if n_hits else 0.0,
        effect_rate_on_hit=effects / n_hits if n_hits else 0.0,
    )

    # Elemental breakdown — aggregate from per-hit metrics
    # Both elemental_applied (inline elemental) and planar_applied (enchantment
    # planar damage) share the same format: attack_type, dmg_gross, dmg_net, prot, healed.
    elem_gross: dict[str, float] = {}
    elem_net: dict[str, float] = {}
    elem_prot: dict[str, float] = {}
    elem_healed: dict[str, float] = {}
    elem_count = 0
    for r in successes:
        has_elem = False
        for metric_key in ("elemental_applied", "planar_applied"):
            applied = r.metrics.get(metric_key)
            if not applied:
                continue
            has_elem = True
            for entry in applied:
                attack_type = entry.get("attack_type", 0)
                try:
                    elem_name = _DMGID_TO_ELEMENT.get(int(attack_type))
                except (TypeError, ValueError):
                    continue
                if elem_name is None:
                    continue
                elem_gross[elem_name] = elem_gross.get(elem_name, 0.0) + _safe_float(entry.get("dmg_gross", 0))
                elem_net[elem_name] = elem_net.get(elem_name, 0.0) + _safe_float(entry.get("dmg_net", 0))
                elem_prot[elem_name] = elem_prot.get(elem_name, 0.0) + _safe_float(entry.get("prot", 0))
                elem_healed[elem_name] = elem_healed.get(elem_name, 0.0) + _safe_float(entry.get("healed", 0))
        if has_elem:
            elem_count += 1

    if elem_count > 0:
        elements = {}
        for name in set(elem_gross) | set(elem_net) | set(elem_healed):
            elements[name] = ElementDamage(
                gross=elem_gross.get(name, 0.0) / elem_count,
                net=elem_net.get(name, 0.0) / elem_count,
                prot=elem_prot.get(name, 0.0) / elem_count,
                healed=elem_healed.get(name, 0.0) / elem_count,
            )
        cell.elemental_breakdown = ElementalBreakdown(elements=elements)

    # Drain stats — aggregate effect_drain_amount from per-hit metrics
    # On-hit: only iterations where drain actually occurred
    drain_amounts_on_hit = [
        _safe_float(r.metrics.get("effect_drain_amount", 0))
        for r in successes
        if r.metrics.get("effect_drain_amount") is not None
    ]
    if drain_amounts_on_hit:
        cell.drain_stats_on_hit = _compute_damage_stats(drain_amounts_on_hit)

    # Overall: drain per swing (0 for misses and non-drain hits)
    drain_amounts_all = [
        _safe_float(r.metrics.get("effect_drain_amount", 0))
        for r in successes
    ]
    if any(d > 0 for d in drain_amounts_all):
        cell.drain_stats = _compute_damage_stats(drain_amounts_all)

    return cell
