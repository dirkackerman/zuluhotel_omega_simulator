"""Combat integration — execute eScript hit scripts and collect results."""

from omega.combat.hit import execute_hit, execute_hit_from_shard
from omega.combat.result import HitResult

__all__ = ["HitResult", "execute_hit", "execute_hit_from_shard"]
