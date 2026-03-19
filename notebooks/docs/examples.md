# Examples

Copy-paste recipes for common balancing questions. Each recipe is self-contained with all necessary imports.

## Preamble

Every recipe starts with this setup. Adjust the shard path if needed.

```python
from pathlib import Path
from omega.model.constants import *
from omega.shard import ShardData
from omega.simulation import (
    ArmorSpec, CombatantSpec, ParameterSweep, Scenario,
    Variable, WeaponSpec, run_scenario, run_sweep,
)
from omega.reporting.plots import (
    damage_histogram, damage_vs_parameter,
    damage_breakdown, comparison_breakdown, comparison_overlay,
    dps_vs_parameter, dps_comparison,
)
from omega.reporting.tables import summary_table, comparison_table, format_table_html
from IPython.display import HTML, display

shard = ShardData.from_path(Path("../submodules/zuluhotel_omega_2.5"))
```

---

## Recipe 1: Basic damage check

**Question**: "How much damage does a GM Warrior with a broadsword deal to a plate-armored target?"

```python
scenario = Scenario(
    attacker=CombatantSpec(
        name="GM Warrior",
        skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
        str_=100, dex_=100, int_=25,
        class_levels={CLASSEID_WARRIOR: 5},
        weapon=WeaponSpec(name="Broadsword", damage="3d6+2"),
    ),
    defender=CombatantSpec(
        name="Plate Target",
        is_npc=True,
        str_=50, dex_=50, int_=50,
        hp=500,
        armor=ArmorSpec(name="Plate", ar=30),
    ),
    iterations=1000,
    base_seed=42,
)

result = run_scenario(scenario, shard=shard)

# Summary
ds = result.damage_stats
print(f"Mean:   {ds.mean:.1f}")
print(f"Median: {ds.median:.1f}")
print(f"Range:  {ds.min:.0f} – {ds.max:.0f}")
print(f"p5-p95: {ds.p5:.0f} – {ds.p95:.0f}")

# Plots
damage_histogram(result, title="GM Warrior vs Plate (AR 30)")
damage_breakdown(result)
```

---

## Recipe 2: Skill sweep — damage vs Tactics

**Question**: "How does Tactics skill affect damage output?"

```python
warrior = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_ANATOMY: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=WeaponSpec(name="Broadsword", damage="3d6+2"),
)

target = CombatantSpec(
    name="Target",
    is_npc=True,
    str_=50, dex_=50, int_=50,
    hp=500,
    armor=ArmorSpec(ar=30),
)

sweep = ParameterSweep(
    scenario=Scenario(attacker=warrior, defender=target, iterations=500, base_seed=42),
    variables=(
        Variable.from_range("attacker", f"skills.{SKILLID_TACTICS}", start=50, stop=130, step=10),
    ),
)

result = run_sweep(sweep, shard=shard)

# Damage curve
damage_vs_parameter(result, f"attacker.skills.{SKILLID_TACTICS}",
                    title="Damage vs Tactics (Warrior, AR 30)")

# Table
display(HTML(format_table_html(summary_table(result))))
```

---

## Recipe 3: Armor Rating sweep — finding the breakpoint

**Question**: "At what AR does armor start making a real difference?"

```python
sweep = ParameterSweep(
    scenario=Scenario(
        attacker=CombatantSpec(
            name="Warrior",
            skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
            str_=100, dex_=100, int_=25,
            class_levels={CLASSEID_WARRIOR: 5},
            weapon=WeaponSpec(damage="3d6+2"),
        ),
        defender=CombatantSpec(
            name="Target", is_npc=True,
            str_=50, dex_=50, int_=50, hp=500,
            armor=ArmorSpec(ar=0),
        ),
        iterations=500,
        base_seed=42,
    ),
    variables=(
        Variable.from_range("defender", "armor.ar", start=0, stop=60, step=5),
    ),
)

result = run_sweep(sweep, shard=shard)

damage_vs_parameter(result, "defender.armor.ar",
                    title="Damage vs Armor Rating")

# Table with absorption stats
rows = summary_table(result, stats=["mean", "absorbed_mean", "base_mean", "hit_rate"])
display(HTML(format_table_html(rows)))
```

---

## Recipe 4: Comparing two weapons

**Question**: "Is a 4d5+3 mace better than a 3d6+2 sword for a Warrior?"

```python
base_warrior = CombatantSpec(
    name="Warrior",
    skills={SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
)

target = CombatantSpec(
    name="Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    armor=ArmorSpec(ar=30),
)

# Scenario A: Sword
sword_warrior = CombatantSpec(
    **{**{f.name: getattr(base_warrior, f.name)
          for f in base_warrior.__dataclass_fields__.values()},
       "skills": {**base_warrior.skills, SKILLID_SWORDSMANSHIP: 100},
       "weapon": WeaponSpec(name="Broadsword", damage="3d6+2",
                           attribute=SKILLID_SWORDSMANSHIP)},
)

# Scenario B: Mace
mace_warrior = CombatantSpec(
    **{**{f.name: getattr(base_warrior, f.name)
          for f in base_warrior.__dataclass_fields__.values()},
       "skills": {**base_warrior.skills, SKILLID_MACEFIGHTING: 100},
       "weapon": WeaponSpec(name="War Hammer", damage="4d5+3",
                           attribute=SKILLID_MACEFIGHTING)},
)

results = {}
for name, attacker in [("Broadsword 3d6+2", sword_warrior), ("War Hammer 4d5+3", mace_warrior)]:
    results[name] = run_scenario(
        Scenario(attacker=attacker, defender=target, iterations=1000, base_seed=42),
        shard=shard,
    )

# Compare
comparison_overlay(results, title="Sword vs Mace")
comparison_breakdown(results)
display(HTML(format_table_html(comparison_table(results))))
```

---

## Recipe 5: Class vs class comparison

**Question**: "How does damage differ across character classes?"

```python
CLASS_CONFIGS = {
    "Warrior": {
        "class_levels": {CLASSEID_WARRIOR: 5},
        "skills": {SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
        "str_": 100, "dex_": 100, "int_": 25,
    },
    "Ranger": {
        "class_levels": {CLASSEID_RANGER: 5},
        "skills": {SKILLID_ARCHERY: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 80},
        "str_": 90, "dex_": 100, "int_": 35,
    },
    "Paladin": {
        "class_levels": {CLASSEID_PALADIN: 5},
        "skills": {SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 80},
        "str_": 100, "dex_": 80, "int_": 50,
    },
    "Bladesinger": {
        "class_levels": {CLASSEID_BLADESINGER: 5},
        "skills": {SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_MAGERY: 80},
        "str_": 80, "dex_": 100, "int_": 50,
    },
}

target = CombatantSpec(
    name="Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    armor=ArmorSpec(ar=30),
)

results = {}
for class_name, cfg in CLASS_CONFIGS.items():
    weapon_skill = next(
        s for s in cfg["skills"]
        if s in (SKILLID_SWORDSMANSHIP, SKILLID_ARCHERY, SKILLID_MACEFIGHTING)
    )
    attacker = CombatantSpec(
        name=class_name,
        skills=cfg["skills"],
        str_=cfg["str_"], dex_=cfg["dex_"], int_=cfg["int_"],
        class_levels=cfg["class_levels"],
        weapon=WeaponSpec(name="Broadsword", damage="3d6+2", attribute=weapon_skill),
    )
    results[class_name] = run_scenario(
        Scenario(attacker=attacker, defender=target, iterations=500, base_seed=42),
        shard=shard,
    )

comparison_overlay(results, title="Class Comparison (AR 30)")
comparison_breakdown(results)
display(HTML(format_table_html(comparison_table(results))))
```

---

## Recipe 6: Slayer weapon effectiveness

**Question**: "How much extra damage does a slayer weapon deal against a matching creature type?"

```python
attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
)

# Defender with a creature type
undead_target = CombatantSpec(
    name="Undead Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    armor=ArmorSpec(ar=30),
)

# Normal weapon
normal_scenario = Scenario(
    attacker=CombatantSpec(
        **{f.name: getattr(attacker, f.name)
           for f in attacker.__dataclass_fields__.values()},
        weapon=WeaponSpec(name="Normal Sword", damage="3d6+2"),
    ),
    defender=undead_target,
    iterations=500,
    base_seed=42,
)

# Slayer weapon
slayer_scenario = Scenario(
    attacker=CombatantSpec(
        **{f.name: getattr(attacker, f.name)
           for f in attacker.__dataclass_fields__.values()},
        weapon=WeaponSpec(
            name="Undead Slayer",
            damage="3d6+2",
            properties={"SlayType": "Undead"},
        ),
    ),
    defender=undead_target,
    iterations=500,
    base_seed=42,
)

results = {
    "Normal": run_scenario(normal_scenario, shard=shard),
    "Slayer": run_scenario(slayer_scenario, shard=shard),
}

comparison_overlay(results, title="Normal vs Slayer Weapon (Undead target)")
display(HTML(format_table_html(comparison_table(results))))
```

---

## Recipe 7: PvP vs PvE damage scaling

**Question**: "How much does PvP scaling reduce damage?"

```python
attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=WeaponSpec(damage="3d6+2"),
)

# PvE — defender is NPC
pve = Scenario(
    attacker=attacker,
    defender=CombatantSpec(
        name="NPC Target", is_npc=True,
        str_=50, dex_=50, int_=50, hp=500,
        armor=ArmorSpec(ar=30),
    ),
    iterations=500,
    base_seed=42,
)

# PvP — defender is player
pvp = Scenario(
    attacker=attacker,
    defender=CombatantSpec(
        name="Player Target", is_npc=False,
        str_=50, dex_=50, int_=50, hp=200,
        armor=ArmorSpec(ar=30),
    ),
    iterations=500,
    base_seed=42,
)

results = {
    "PvE (vs NPC)": run_scenario(pve, shard=shard),
    "PvP (vs Player)": run_scenario(pvp, shard=shard),
}

comparison_overlay(results, title="PvE vs PvP Damage")
display(HTML(format_table_html(comparison_table(results))))

# The PvP scaling factor is 0.4 * 0.6 = 0.24 net
pvp_ratio = results["PvP (vs Player)"].damage_stats.mean / results["PvE (vs NPC)"].damage_stats.mean
print(f"PvP/PvE ratio: {pvp_ratio:.2f} (expected ~0.24)")
```

---

## Recipe 8: Strength scaling

**Question**: "How does STR affect damage output?"

```python
sweep = ParameterSweep(
    scenario=Scenario(
        attacker=CombatantSpec(
            name="Warrior",
            skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
            str_=50, dex_=100, int_=25,
            class_levels={CLASSEID_WARRIOR: 5},
            weapon=WeaponSpec(damage="3d6+2"),
        ),
        defender=CombatantSpec(
            name="Target", is_npc=True,
            str_=50, dex_=50, int_=50, hp=500,
            armor=ArmorSpec(ar=30),
        ),
        iterations=500,
        base_seed=42,
    ),
    variables=(
        Variable.from_range("attacker", "str_", start=50, stop=130, step=10),
    ),
)

result = run_sweep(sweep, shard=shard)

damage_vs_parameter(result, "attacker.str_", title="Damage vs Strength")
display(HTML(format_table_html(summary_table(result))))
```

---

## Recipe 9: Multi-variable grid — skill x AR

**Question**: "How does weapon skill interact with armor rating?"

```python
sweep = ParameterSweep(
    scenario=Scenario(
        attacker=CombatantSpec(
            name="Warrior",
            skills={SKILLID_SWORDSMANSHIP: 50, SKILLID_TACTICS: 100},
            str_=100, dex_=100, int_=25,
            class_levels={CLASSEID_WARRIOR: 5},
            weapon=WeaponSpec(damage="3d6+2"),
        ),
        defender=CombatantSpec(
            name="Target", is_npc=True,
            str_=50, dex_=50, int_=50, hp=500,
            armor=ArmorSpec(ar=0),
        ),
        iterations=200,
        base_seed=42,
    ),
    variables=(
        Variable.from_range("attacker", f"skills.{SKILLID_SWORDSMANSHIP}", 50, 130, 20),
        Variable.from_range("defender", "armor.ar", 0, 50, 10),
    ),
)

result = run_sweep(sweep, shard=shard)

# Full grid table
rows = summary_table(result, stats=["mean", "std_dev", "hit_rate"])
display(HTML(format_table_html(rows)))
```

---

## Recipe 10: Debug a single hit

**Question**: "What's happening step-by-step inside the script for one specific hit?"

```python
import logging

# Enable verbose logging
logging.getLogger("omega.runtime.messaging").setLevel(logging.INFO)
logging.getLogger("omega.runtime").setLevel(logging.DEBUG)

scenario = Scenario(
    attacker=CombatantSpec(
        name="Warrior",
        skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
        str_=100, dex_=100, int_=25,
        class_levels={CLASSEID_WARRIOR: 5},
        weapon=WeaponSpec(damage="3d6+2"),
    ),
    defender=CombatantSpec(
        name="Target", is_npc=True,
        str_=50, dex_=50, int_=50, hp=500,
        armor=ArmorSpec(ar=30),
    ),
    iterations=1,        # Just one hit
    base_seed=42,
    debug_mode=True,     # Enable script debug messages
)

result = run_scenario(scenario, shard=shard)

hit = result.raw_results[0]
print(f"Base damage:  {hit.base_damage}")
print(f"Final damage: {hit.final_damage:.1f}")
print(f"Absorbed:     {hit.absorbed:.1f}")
print(f"HP: {hit.defender_hp_before} → {hit.defender_hp_after}")
print(f"Side effects: {len(hit.side_effects)}")
for se in hit.side_effects:
    print(f"  {se.kind}: value={se.value}")

# Reset logging when done
logging.getLogger("omega.runtime.messaging").setLevel(logging.WARNING)
logging.getLogger("omega.runtime").setLevel(logging.WARNING)
```

---

## Recipe 11: Elemental weapon comparison (V1.5)

**Question**: "How does a fire weapon perform against targets with different fire resistance?"

```python
from omega.config.enchantments import Enchantment
from omega.reporting.plots import elemental_breakdown_chart, elemental_vs_parameter

attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=WeaponSpec(
        name="Fire Sword", damage="3d6+2",
        properties={"ElementalDamage": 0x01},  # FIRE
    ),
)

sweep = ParameterSweep(
    scenario=Scenario(
        attacker=attacker,
        defender=CombatantSpec(
            name="Target", is_npc=True,
            str_=50, dex_=50, int_=50, hp=500,
            armor=ArmorSpec(ar=30),
        ),
        iterations=500,
        base_seed=42,
    ),
    variables=(
        Variable.from_range("defender", "properties.FireProtection", start=0, stop=5, step=1),
    ),
)

result = run_sweep(sweep, shard=shard)

# Elemental breakdown for one cell
elemental_breakdown_chart(result.cells[0], title="Fire Sword Damage Breakdown")

# How fire resistance reduces damage
elemental_vs_parameter(result, "defender.properties.FireProtection",
                       title="Fire Weapon vs Fire Resistance")
```

---

## Recipe 12: Enchantment effectiveness (V1.5)

**Question**: "How does a spell-strike enchantment compare to a slayer enchantment?"

```python
from omega.config.enchantments import Enchantment

target = CombatantSpec(
    name="Undead Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    armor=ArmorSpec(ar=30),
    properties={"Type": "Undead"},
)

base_attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
)

# Plain weapon
plain = WeaponSpec(name="Plain Sword", damage="3d6+2")

# Spell strike (Fireball)
fire_sword = WeaponSpec(name="Fire Sword", damage="3d6+2").enchant_with(
    Enchantment.OF_DAEMONS_BREATH
)

# Slayer (Undead)
slayer_sword = WeaponSpec(name="Silver Sword", damage="3d6+2").enchant_with(
    Enchantment.SILVER
)

import dataclasses

results = {}
for label, wpn in [("Plain", plain), ("Spell Strike", fire_sword), ("Slayer", slayer_sword)]:
    spec = dataclasses.replace(base_attacker, weapon=wpn)
    results[label] = run_scenario(
        Scenario(attacker=spec, defender=target, iterations=500, base_seed=42),
        shard=shard,
    )

comparison_overlay(results, title="Enchantment Comparison vs Undead")
display(HTML(format_table_html(comparison_table(results))))
```

---

## Recipe 13: Reactive armor test (V1.5)

**Question**: "How much damage does reactive armor reflect back to the attacker?"

```python
attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=WeaponSpec(name="Sword", damage="3d6+2"),
)

# Defender with reactive armor active
reactive_defender = CombatantSpec(
    name="Reactive Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    armor=ArmorSpec(ar=30),
    properties={"ReactiveArmor": 1},
)

# Defender without reactive armor
normal_defender = CombatantSpec(
    name="Normal Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    armor=ArmorSpec(ar=30),
)

results = {
    "No Reactive": run_scenario(
        Scenario(attacker=attacker, defender=normal_defender, iterations=500, base_seed=42),
        shard=shard,
    ),
    "Reactive Armor": run_scenario(
        Scenario(attacker=attacker, defender=reactive_defender, iterations=500, base_seed=42),
        shard=shard,
    ),
}

comparison_overlay(results, title="Effect of Reactive Armor")
display(HTML(format_table_html(comparison_table(results))))

# Check reflected damage on attacker
reactive_result = results["Reactive Armor"]
reactive_hits = [h for h in reactive_result.raw_results
                 if any(se.kind == "reactive" for se in h.side_effects)]
print(f"Reactive triggered: {len(reactive_hits)}/{len(reactive_result.raw_results)} hits")
```

---

## Recipe 14: DPS comparison across weapons (V2)

**Question**: "Which weapon delivers the best sustained DPS when accounting for attack speed?"

```python
from omega.reporting.plots import dps_comparison

target = CombatantSpec(
    name="Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    armor=ArmorSpec(ar=30),
)

weapons = {
    "War Axe (Speed 15)": WeaponSpec(name="War Axe", damage="5d8+5", speed=15),
    "Longsword (Speed 50)": WeaponSpec(name="Longsword", damage="3d6+2", speed=50),
    "Short Bow (Speed 98)": WeaponSpec(name="Short Bow", damage="2d4+1", speed=98,
                                        attribute=SKILLID_ARCHERY),
}

results = {}
for label, wpn in weapons.items():
    skill = wpn.attribute or SKILLID_SWORDSMANSHIP
    attacker = CombatantSpec(
        name="Fighter",
        skills={skill: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
        str_=100, dex_=100, int_=25,
        class_levels={CLASSEID_WARRIOR: 5},
        weapon=wpn,
    )
    results[label] = run_scenario(
        Scenario(attacker=attacker, defender=target, iterations=500, base_seed=42),
        shard=shard,
    )

# DPS comparison bar chart with delay annotations
dps_comparison(results, title="DPS by Weapon Speed")

# Table with DPS columns
display(HTML(format_table_html(comparison_table(results,
    stats=["mean", "swing_delay_ms", "effective_dps"]))))
```

---

## Recipe 15: DPS vs Dexterity curve (V2)

**Question**: "How does Dexterity affect attack speed and DPS?"

```python
from omega.reporting.plots import dps_vs_parameter

sweep = ParameterSweep(
    scenario=Scenario(
        attacker=CombatantSpec(
            name="Warrior",
            skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
            str_=100, dex_=50, int_=25,
            class_levels={CLASSEID_WARRIOR: 5},
            weapon=WeaponSpec(damage="3d6+2", speed=50),
        ),
        defender=CombatantSpec(
            name="Target", is_npc=True,
            str_=50, dex_=50, int_=50, hp=500,
            armor=ArmorSpec(ar=30),
        ),
        iterations=500,
        base_seed=42,
    ),
    variables=(
        Variable.from_range("attacker", "dex_", start=10, stop=130, step=10),
    ),
)

result = run_sweep(sweep, shard=shard)

# Dual-axis plot: DPS (left) + swing delay (right)
dps_vs_parameter(result, "attacker.dex_", title="DPS vs Dexterity")

# Table with timing stats
rows = summary_table(result, stats=["mean", "swing_delay_ms", "swings_per_sec", "effective_dps"])
display(HTML(format_table_html(rows)))
```

---

## Recipe 16: Astral damage analysis (V2)

**Question**: "How does an astral weapon compare to a physical weapon?"

```python
target = CombatantSpec(
    name="Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    skills={SKILLID_MEDITATION: 80},
    armor=ArmorSpec(ar=30),
)

# Physical warrior
physical_result = run_scenario(
    Scenario(
        attacker=CombatantSpec(
            name="Physical Warrior",
            skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100, SKILLID_ANATOMY: 100},
            str_=100, dex_=100, int_=25,
            class_levels={CLASSEID_WARRIOR: 5},
            weapon=WeaponSpec(name="Sword", damage="3d6+2"),
        ),
        defender=target,
        iterations=500,
        base_seed=42,
    ),
    shard=shard,
)

# Astral mage
astral_result = run_scenario(
    Scenario(
        attacker=CombatantSpec(
            name="Astral Mage",
            skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 80,
                    SKILLID_SPIRITSPEAK: 100, SKILLID_EVALINT: 100},
            str_=50, dex_=100, int_=100,
            class_levels={CLASSEID_MAGE: 5},
            weapon=WeaponSpec(name="Astral Blade", damage="3d6+2",
                            properties={"Astral": 1}),
        ),
        defender=target,
        iterations=500,
        base_seed=42,
    ),
    shard=shard,
)

results = {"Physical": physical_result, "Astral": astral_result}
comparison_overlay(results, title="Physical vs Astral Damage")
display(HTML(format_table_html(comparison_table(results))))

# Astral-specific metrics
for hit in astral_result.raw_results[:3]:
    if "astral_basedamage" in hit.metrics:
        print(f"  base={hit.metrics['astral_basedamage']}, "
              f"raw={hit.metrics['astral_rawdamage']}, "
              f"meditation={hit.metrics['astral_meditation_triggered']}")
```

---

## Recipe 17: Spell resistance by class (V2)

**Question**: "How does defender class affect spell resistance?"

```python
from omega.config.enchantments import Enchantment

# Spell strike weapon (Fireball, circle 3)
weapon = WeaponSpec(name="Enchanted Sword", damage="3d6+2").enchant_with(
    Enchantment.OF_DAEMONS_BREATH
)

attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=weapon,
)

# Different defender classes, all with Magic Resistance 80
defender_classes = {
    "No Class": {},
    "Warrior L5": {CLASSEID_WARRIOR: 5},
    "Mage L5": {CLASSEID_MAGE: 5},
    "Paladin L5": {CLASSEID_PALADIN: 5},
}

results = {}
for label, cls in defender_classes.items():
    defender = CombatantSpec(
        name=label, is_npc=True,
        skills={SKILLID_MAGICRESISTANCE: 80},
        str_=50, dex_=50, int_=50, hp=500,
        class_levels=cls,
        armor=ArmorSpec(ar=30),
    )
    results[label] = run_scenario(
        Scenario(attacker=attacker, defender=defender, iterations=500, base_seed=42),
        shard=shard,
    )

comparison_overlay(results, title="Spell Damage by Defender Class")
display(HTML(format_table_html(comparison_table(results,
    stats=["mean", "spell_strike_rate", "effect_rate"]))))
```

---

## Recipe 17.1: Enchanted armor — define and run (V3.1)

**Question**: "How does a fire-enchanted armor affect incoming damage?"

```python
from omega.config.armor_enchantments import ArmorEnchantment

attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=WeaponSpec(name="Sword", damage="3d6+2"),
)

# Defender with enchanted armor
fire_defender = CombatantSpec(
    name="Fire Plate Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
    armor=ArmorSpec(name="Fire Plate", ar=35).enchant_with(
        ArmorEnchantment.OF_DAEMONS_BREATH
    ),
)

result = run_scenario(
    Scenario(attacker=attacker, defender=fire_defender, iterations=1000, base_seed=42),
    shard=shard,
)

print(f"Mean damage: {result.damage_stats.mean:.1f}")
print(f"Onhit trigger rate: {result.ratios.onhit_trigger_rate:.1%}")
damage_histogram(result, title="vs Fire Plate Armor")
```

---

## Recipe 17.2: Compare armor enchantments (V3.1)

**Question**: "Which armor enchantment provides the best defensive value?"

```python
from omega.config.armor_enchantments import ArmorEnchantment
from omega.reporting.plots import armor_enchantment_comparison
import dataclasses

attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=WeaponSpec(name="Sword", damage="3d6+2"),
)

base_defender = CombatantSpec(
    name="Target", is_npc=True,
    str_=50, dex_=50, int_=50, hp=500,
)

enchantments = {
    "Plain (AR 35)": ArmorSpec(ar=35),
    "Fire Plate": ArmorSpec(ar=35).enchant_with(ArmorEnchantment.OF_DAEMONS_BREATH),
    "Piercing Plate": ArmorSpec(ar=35).enchant_with(ArmorEnchantment.OF_PIERCING),
    "Planar Plate": ArmorSpec(ar=35).enchant_with(ArmorEnchantment.OF_PLANAR_FURY),
}

results = {}
for label, armor in enchantments.items():
    defender = dataclasses.replace(base_defender, armor=armor)
    results[label] = run_scenario(
        Scenario(attacker=attacker, defender=defender, iterations=500, base_seed=42),
        shard=shard,
    )

armor_enchantment_comparison(results, title="Armor Enchantment Comparison")
display(HTML(format_table_html(comparison_table(results,
    stats=["mean", "onhit_trigger_rate", "effect_rate"]))))
```

---

## Recipe 17.3: Sweep ChanceOfEffect on armor (V3.1)

**Question**: "How does the ChanceOfEffect property affect armor onhit trigger rate?"

```python
from omega.config.armor_enchantments import ArmorEnchantment

attacker = CombatantSpec(
    name="Warrior",
    skills={SKILLID_SWORDSMANSHIP: 100, SKILLID_TACTICS: 100},
    str_=100, dex_=100, int_=25,
    class_levels={CLASSEID_WARRIOR: 5},
    weapon=WeaponSpec(name="Sword", damage="3d6+2"),
)

sweep = ParameterSweep(
    scenario=Scenario(
        attacker=attacker,
        defender=CombatantSpec(
            name="Target", is_npc=True,
            str_=50, dex_=50, int_=50, hp=500,
            armor=ArmorSpec(ar=35).enchant_with(ArmorEnchantment.OF_DAEMONS_BREATH),
        ),
        iterations=500,
        base_seed=42,
    ),
    variables=(
        Variable.from_range("defender", "armor.properties.ChanceOfEffect",
                            start=1, stop=15, step=2),
    ),
)

result = run_sweep(sweep, shard=shard)

damage_vs_parameter(result, "defender.armor.properties.ChanceOfEffect",
                    title="Damage vs Armor ChanceOfEffect")
rows = summary_table(result, stats=["mean", "onhit_trigger_rate", "hit_rate"])
display(HTML(format_table_html(rows)))
```

---

## Recipe 18: Basic spell damage (V3)

**Question**: "How much damage does a Mage's Fireball deal?"

```python
from omega.config.spells import Spell
from omega.simulation import SpellScenario, run_spell_scenario

scenario = SpellScenario(
    caster=CombatantSpec(
        name="Mage",
        skills={SKILLID_MAGERY: 100, SKILLID_EVALINT: 100},
        str_=50, dex_=50, int_=120,
        class_levels={"IsMage": 5},
    ),
    target=CombatantSpec(name="Target", is_npc=True, hp=500, armor=ArmorSpec(ar=30)),
    spell_id=Spell.FIREBALL,
    iterations=1000,
    base_seed=42,
    npc_mode=False,
)

result = run_spell_scenario(scenario, shard=shard)

print(f"Mean damage: {result.damage_stats.mean:.1f}")
print(f"Fizzle rate: {result.ratios.fizzle_rate:.1%}")
print(f"Resist rate: {result.ratios.resist_rate:.1%}")
print(f"On-cast mean: {result.damage_stats_on_cast.mean:.1f}")

damage_histogram(result, title="Fireball — 1000 casts")
```

---

## Recipe 19: Spell fizzle sweep (V3)

**Question**: "How does Magery skill affect Fireball fizzle rate?"

```python
from omega.config.spells import Spell
from omega.simulation import SpellParameterSweep, SpellScenario, run_spell_sweep
from omega.reporting.plots import fizzle_rate_vs_parameter

sweep = SpellParameterSweep(
    scenario=SpellScenario(
        caster=CombatantSpec(
            name="Mage",
            skills={SKILLID_MAGERY: 100, SKILLID_EVALINT: 100},
            str_=50, dex_=50, int_=120,
            class_levels={"IsMage": 5},
        ),
        target=CombatantSpec(name="Target", is_npc=True, hp=500),
        spell_id=Spell.FIREBALL,
        iterations=200,
        npc_mode=False,
    ),
    variables=(
        Variable.from_range("caster", f"skills.{SKILLID_MAGERY}", 30, 130, 10),
    ),
)

result = run_spell_sweep(sweep, shard=shard)
fizzle_rate_vs_parameter(result, f"caster.skills.{SKILLID_MAGERY}",
                         title="Fizzle Rate vs Magery")
display(HTML(format_table_html(summary_table(result,
    stats=["mean", "fizzle_rate", "resist_rate", "effective_dps"]))))
```

---

## Recipe 20: Spell school comparison (V3)

**Question**: "How do spells from different schools compare at similar circles?"

```python
from omega.config.spells import Spell
from omega.simulation import SpellScenario, run_spell_scenario
from omega.reporting.plots import spell_comparison

caster = CombatantSpec(
    name="Mage",
    skills={SKILLID_MAGERY: 100, SKILLID_EVALINT: 100},
    str_=50, dex_=50, int_=120,
    class_levels={"IsMage": 5},
)
target = CombatantSpec(name="Target", is_npc=True, hp=500, armor=ArmorSpec(ar=30))

spells = {
    "Fireball (Standard)": Spell.FIREBALL,
    "Abyssal Flame (Necro)": Spell.ABYSSAL_FLAME,
    "Ice Strike (Earth)": Spell.ICE_STRIKE,
    "Divine Fury (Holy)": Spell.DIVINE_FURY,
}

results = {}
for label, spell_id in spells.items():
    results[label] = run_spell_scenario(
        SpellScenario(caster=caster, target=target, spell_id=spell_id,
                      iterations=500, npc_mode=False),
        shard=shard,
    )

spell_comparison(results, title="School Comparison")
display(HTML(format_table_html(comparison_table(results,
    stats=["mean", "mean_on_cast", "fizzle_rate", "effective_dps"]))))
```
