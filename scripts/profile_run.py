"""Profile a 200-iteration simulation run to find remaining bottlenecks."""

import cProfile
import pstats
import io
from pathlib import Path

from omega.model.constants import SKILLID_ANATOMY, SKILLID_SWORDSMANSHIP, SKILLID_TACTICS
from omega.shard import ShardData
from omega.simulation import ArmorSpec, CombatantSpec, Scenario, WeaponSpec, run_scenario

shard = ShardData.from_path(Path("submodules/zuluhotel_omega_2.5"))
pr = shard.parse_combat_scripts()

scenario = Scenario(
    attacker=CombatantSpec(
        name="Warrior", str_=100, dex_=100, int_=25,
        skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
        class_levels={"IsWarrior": 5},
        weapon=WeaponSpec(damage="3d5+2"),
    ),
    defender=CombatantSpec(
        name="Target", is_npc=True,
        str_=50, dex_=50, int_=50, hp=500,
        armor=ArmorSpec(ar=30),
    ),
    iterations=200,
    base_seed=42,
)

prof = cProfile.Profile()
prof.enable()
result = run_scenario(
    scenario,
    parse_results=pr,
    config_resolver=shard.resolve_config_path,
    em_modules_dir=shard.root / "scripts" / "modules",
)
prof.disable()

s = io.StringIO()
ps = pstats.Stats(prof, stream=s).sort_stats("tottime")
ps.print_stats(30)
print(s.getvalue())
