"""Combat integration — execute eScript hit/spell scripts and collect results."""

from omega.combat.hit import execute_hit, execute_hit_from_shard
from omega.combat.result import HitResult
from omega.combat.spell import execute_spell, execute_spell_from_shard
from omega.combat.spell_result import SpellResult

__all__ = [
    "HitResult",
    "SpellResult",
    "execute_hit",
    "execute_hit_from_shard",
    "execute_spell",
    "execute_spell_from_shard",
]
