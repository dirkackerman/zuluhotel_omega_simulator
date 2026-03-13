"""Zuluhotel Omega Combat Simulator — Streamlit UI.

Launch:  streamlit run notebooks/web/app.py
"""

from __future__ import annotations

import dataclasses
import logging
import time
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import streamlit as st
import yaml

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------

from omega.config.enchantments import Enchantment
from omega.logging import setup_logging
from omega.model.constants import (
    ALL_CLASS_IDS,
    SKILLID_ANATOMY,
    SKILLID_ARCHERY,
    SKILLID_EVALINT,
    SKILLID_FENCING,
    SKILLID_MACEFIGHTING,
    SKILLID_MAGERY,
    SKILLID_MAGICRESISTANCE,
    SKILLID_MEDITATION,
    SKILLID_PARRY,
    SKILLID_SPIRITSPEAK,
    SKILLID_SWORDSMANSHIP,
    SKILLID_TACTICS,
    SKILLID_WRESTLING,
)
from omega.shard import ShardData
from omega.simulation import (
    ArmorSpec,
    CellResult,
    CombatantSpec,
    ParameterSweep,
    Scenario,
    SimulationResult,
    Variable,
    WeaponSpec,
    run_scenario,
    run_sweep,
)
from omega.simulation.stats import TimingStats

setup_logging(level=logging.ERROR)

# ═══════════════════════════════════════════════════════════════════════════
# THEME — all visual constants in one place
# ═══════════════════════════════════════════════════════════════════════════

# Backgrounds
BG_DEEP      = "#0B0E17"      # deepest background (page)
BG_PANEL     = "#111827"      # chart / card panels
BG_SURFACE   = "#1A2236"      # elevated surfaces
BG_HIGHLIGHT = "#232D45"      # hover / active states

# Borders / grid
BORDER       = "rgba(100, 160, 255, 0.12)"
GRID         = "rgba(100, 160, 255, 0.08)"
GRID_ZERO    = "rgba(100, 160, 255, 0.18)"

# Accent colours — vivid against navy
CYAN         = "#67E8F9"       # primary accent (like your reference charts)
CYAN_DIM     = "rgba(103, 232, 249, 0.25)"
ORANGE       = "#FDBA74"       # secondary accent
ORANGE_DIM   = "rgba(253, 186, 116, 0.25)"
RED          = "#F87171"
RED_DIM      = "rgba(248, 113, 113, 0.18)"
GREEN        = "#6EE7B7"
GREEN_DIM    = "rgba(110, 231, 183, 0.18)"
YELLOW       = "#FDE68A"
PURPLE       = "#C4B5FD"
PINK         = "#F9A8D4"

# Text
TEXT_PRIMARY   = "#E2E8F0"
TEXT_SECONDARY = "#94A3B8"
TEXT_MUTED     = "#64748B"

# Chart series palette (ordered)
SERIES_COLORS = [CYAN, ORANGE, GREEN, YELLOW, PURPLE, PINK, RED,
                 "#93C5FD", "#A5B4FC", "#86EFAC"]

# Element colours — tuned for dark bg visibility
ELEM_COLORS: dict[str, str] = {
    "fire":     "#EF4444",
    "air":      "#67E8F9",
    "earth":    "#A78BFA",
    "water":    "#3B82F6",
    "necro":    "#C084FC",
    "holy":     "#FDE68A",
    "poison":   "#34D399",
    "acid":     "#BEF264",
    "physical": "#94A3B8",
    "magic":    "#F0ABFC",
    "astral":   "#7DD3FC",
}


# ═══════════════════════════════════════════════════════════════════════════
# PLOTLY LAYOUT TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════

_OMEGA_LAYOUT = go.Layout(
    font=dict(family="Inter, Segoe UI, system-ui, sans-serif",
              color=TEXT_PRIMARY, size=13),
    paper_bgcolor=BG_PANEL,
    plot_bgcolor=BG_PANEL,
    margin=dict(l=56, r=24, t=72, b=56),
    title=dict(font=dict(size=16, color=TEXT_PRIMARY),
               x=0.5, xanchor="center", y=0.97),
    xaxis=dict(
        gridcolor=GRID, gridwidth=1,
        zerolinecolor=GRID_ZERO, zerolinewidth=1,
        linecolor=BORDER, linewidth=1,
        tickfont=dict(size=11, color=TEXT_SECONDARY),
        title_font=dict(size=12, color=TEXT_SECONDARY),
    ),
    yaxis=dict(
        gridcolor=GRID, gridwidth=1,
        zerolinecolor=GRID_ZERO, zerolinewidth=1,
        linecolor=BORDER, linewidth=1,
        tickfont=dict(size=11, color=TEXT_SECONDARY),
        title_font=dict(size=12, color=TEXT_SECONDARY),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
        font=dict(size=11, color=TEXT_SECONDARY),
    ),
    hoverlabel=dict(
        bgcolor=BG_SURFACE, bordercolor=BORDER,
        font=dict(size=12, color=TEXT_PRIMARY),
    ),
    colorway=SERIES_COLORS,
    bargap=0.15,
)


def _base_fig(**overrides) -> go.Figure:
    """Return a Figure pre-configured with the Omega theme."""
    layout = _OMEGA_LAYOUT.to_plotly_json()
    layout.update(overrides)
    return go.Figure(layout=layout)


# ═══════════════════════════════════════════════════════════════════════════
# DOMAIN CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

COMBAT_SKILLS: dict[str, int] = {
    "Swordsmanship": SKILLID_SWORDSMANSHIP,
    "Mace Fighting": SKILLID_MACEFIGHTING,
    "Fencing": SKILLID_FENCING,
    "Wrestling": SKILLID_WRESTLING,
    "Archery": SKILLID_ARCHERY,
    "Parry": SKILLID_PARRY,
    "Anatomy": SKILLID_ANATOMY,
    "Tactics": SKILLID_TACTICS,
    "Magery": SKILLID_MAGERY,
    "Magic Resistance": SKILLID_MAGICRESISTANCE,
    "Eval Intelligence": SKILLID_EVALINT,
    "Spirit Speak": SKILLID_SPIRITSPEAK,
    "Meditation": SKILLID_MEDITATION,
}
SKILL_ID_TO_NAME: dict[int, str] = {v: k for k, v in COMBAT_SKILLS.items()}

CLASS_DISPLAY: dict[str, str] = {
    "IsWarrior": "Warrior", "IsMage": "Mage", "IsThief": "Thief",
    "IsRanger": "Ranger", "IsBard": "Bard", "IsPaladin": "Paladin",
    "IsMysticArcher": "Mystic Archer", "IsBladesinger": "Bladesinger",
    "IsCrafter": "Crafter", "IsPowerplayer": "Powerplayer",
}

ENCHANTMENT_CATEGORIES: dict[str, list[tuple[str, Enchantment]]] = {
    "None": [],
    "Spell Strike": [
        ("Bungling (Clumsy)", Enchantment.OF_BUNGLING),
        ("Senility (Feeblemind)", Enchantment.OF_SENILITY),
        ("Burning (Magic Arrow)", Enchantment.OF_BURNING),
        ("Weakening (Weaken)", Enchantment.OF_WEAKENING),
        ("Wounding (Harm)", Enchantment.OF_WOUNDING),
        ("Daemon's Breath (Fireball)", Enchantment.OF_DAEMONS_BREATH),
        ("Evil (Curse)", Enchantment.OF_EVIL),
        ("Thunder (Lightning)", Enchantment.OF_THUNDER),
        ("Mage's Bane (Mana Drain)", Enchantment.OF_MAGES_BANE),
        ("Mental Strike (Mind Blast)", Enchantment.OF_MENTAL_STRIKE),
        ("Entrapment (Paralyze)", Enchantment.OF_ENTRAPMENT),
        ("Disruption (Energy Bolt)", Enchantment.OF_DISRUPTION),
        ("Conflagration (Explosion)", Enchantment.OF_CONFLAGRATION),
        ("Corruption (Mass Curse)", Enchantment.OF_CORRUPTION),
        ("Heaven's Wrath (Chain Lightning)", Enchantment.OF_HEAVENS_WRATH),
        ("Hellfire (Flame Strike)", Enchantment.OF_HELLFIRE),
        ("Celestial Fury (Meteor Swarm)", Enchantment.OF_CELESTIAL_FURY),
        ("Gaia's Wrath (Earthquake)", Enchantment.OF_GAIAS_WRATH),
    ],
    "Slayer": [
        ("Silver (Undead)", Enchantment.SILVER),
        ("Holy (Daemon)", Enchantment.HOLY),
        ("Dragon Slayer", Enchantment.DRAGON_SLAYER),
        ("Elemental Slayer", Enchantment.ELEMENTAL_SLAYER),
        ("Animal Slayer", Enchantment.ANIMAL_SLAYER),
        ("Orc Slayer", Enchantment.ORC_SLAYER),
        ("Troll Slayer", Enchantment.TROLL_SLAYER),
        ("Giant Slayer", Enchantment.GIANT_SLAYER),
        ("Terathan Slayer", Enchantment.TERATHAN_SLAYER),
        ("Ophidian Slayer", Enchantment.OPHIDIAN_SLAYER),
        ("Gargoyle Slayer", Enchantment.GARGOYLE_SLAYER),
        ("Beholder Slayer", Enchantment.BEHOLDER_SLAYER),
        ("Bewitched Slayer (Animated)", Enchantment.BEWITCHED_SLAYER),
        ("Ratkin Slayer", Enchantment.RATKIN_SLAYER),
        ("Slime Slayer", Enchantment.SLIME_SLAYER),
        ("Plant Slayer", Enchantment.PLANT_SLAYER),
        ("Assassin's (Human)", Enchantment.ASSASSINS),
    ],
    "Effect": [
        ("Piercing", Enchantment.OF_PIERCING),
        ("Banishing", Enchantment.BANISHING),
        ("Poisoned", Enchantment.POISONED),
        ("Bloody (Life Drain)", Enchantment.BLOODY),
        ("Vampiric (Mana Drain)", Enchantment.VAMPIRIC),
        ("Leech (Stamina Drain)", Enchantment.LEECH),
        ("Blinding", Enchantment.BLINDING),
    ],
    "Greater": [
        ("Planar Fury (Holy + Necro)", Enchantment.OF_PLANAR_FURY),
        ("The Void", Enchantment.OF_THE_VOID),
        ("Elemental Fury (Fire + Air + Earth)", Enchantment.OF_ELEMENTAL_FURY),
    ],
}

SWEEP_PARAMS: dict[str, str] = {
    "str_": "Strength", "int_": "Intelligence", "dex_": "Dexterity",
    "hp": "Hit Points", "mana": "Mana", "stamina": "Stamina",
    "skills.40": "Swordsmanship", "skills.41": "Mace Fighting",
    "skills.42": "Fencing", "skills.43": "Wrestling",
    "skills.31": "Archery", "skills.5": "Parry",
    "skills.1": "Anatomy", "skills.27": "Tactics",
    "skills.25": "Magery", "skills.26": "Magic Resistance",
    "skills.16": "Eval Intelligence", "skills.32": "Spirit Speak",
    "skills.46": "Meditation", "armor.ar": "Armor Rating",
    "weapon.speed": "Weapon Speed", "weapon.quality": "Weapon Quality",
    "properties.ReactiveArmor": "Reactive Armor Power",
    "properties.FireProtection": "Fire Protection %",
    "properties.AirProtection": "Air Protection %",
    "properties.EarthProtection": "Earth Protection %",
    "properties.WaterProtection": "Water Protection %",
    "properties.NecroProtection": "Necro Protection %",
    "properties.HolyProtection": "Holy Protection %",
    "properties.PoisonProtection": "Poison Protection %",
}
SWEEP_PARAM_REVERSE: dict[str, str] = {v: k for k, v in SWEEP_PARAMS.items()}


# ═══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG + CSS
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Omega Combat Simulator",
    page_icon="\u2694\uFE0F",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
<style>
/* ── Global ────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {{
    --bg-deep:    {BG_DEEP};
    --bg-panel:   {BG_PANEL};
    --bg-surface: {BG_SURFACE};
    --border:     {BORDER};
    --cyan:       {CYAN};
    --orange:     {ORANGE};
    --text-1:     {TEXT_PRIMARY};
    --text-2:     {TEXT_SECONDARY};
    --text-3:     {TEXT_MUTED};
}}

.stApp {{
    background: var(--bg-deep) !important;
}}

/* ── Sidebar ───────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #0F1629 0%, #0B0E17 100%) !important;
    border-right: 1px solid rgba(100, 160, 255, 0.08);
}}
section[data-testid="stSidebar"] .block-container {{
    padding-top: 1rem;
}}

/* ── Section headers ───────────────────────────────────────────────── */
.omega-section {{
    background: linear-gradient(90deg, rgba(103,232,249,0.08), transparent);
    border-left: 3px solid {CYAN};
    padding: 6px 14px;
    border-radius: 0 6px 6px 0;
    margin: 12px 0 8px 0;
    font-weight: 600;
    font-size: 0.92rem;
    letter-spacing: 0.03em;
    color: {CYAN};
    text-transform: uppercase;
}}
.omega-section-warm {{
    background: linear-gradient(90deg, rgba(253,186,116,0.08), transparent);
    border-left-color: {ORANGE};
    color: {ORANGE};
}}

/* ── Metric cards ──────────────────────────────────────────────────── */
div[data-testid="stMetric"] {{
    background: linear-gradient(135deg, {BG_SURFACE}, {BG_PANEL});
    border: 1px solid rgba(103, 232, 249, 0.12);
    border-radius: 10px;
    padding: 16px 18px 12px 18px;
    box-shadow: 0 0 20px rgba(103, 232, 249, 0.04);
}}
div[data-testid="stMetric"] label {{
    color: {TEXT_SECONDARY} !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: {CYAN} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    font-size: 1.5rem !important;
}}

/* ── Tabs ──────────────────────────────────────────────────────────── */
button[data-baseweb="tab"] {{
    color: {TEXT_MUTED} !important;
    font-weight: 500;
    border-bottom: 2px solid transparent !important;
    transition: all 0.2s;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {CYAN} !important;
    border-bottom-color: {CYAN} !important;
}}

/* ── Tables ─────────────────────────────────────────────────────────── */
.stDataFrame {{
    border: 1px solid rgba(103, 232, 249, 0.1) !important;
    border-radius: 8px !important;
    overflow: hidden;
}}

/* ── Run button glow ───────────────────────────────────────────────── */
div.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    border: 1px solid rgba(103, 232, 249, 0.3) !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 0 24px rgba(37, 99, 235, 0.35);
    transition: all 0.25s;
}}
div.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 0 32px rgba(103, 232, 249, 0.4);
    border-color: {CYAN} !important;
}}

/* ── Success banner ────────────────────────────────────────────────── */
div[data-testid="stAlert"] {{
    border-radius: 8px;
    border: 1px solid rgba(110, 231, 183, 0.2);
}}

/* ── Title ─────────────────────────────────────────────────────────── */
.omega-title {{
    text-align: center;
    padding: 1.2rem 0 0.6rem 0;
}}
.omega-title h1 {{
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 1.7rem;
    letter-spacing: -0.01em;
    background: linear-gradient(135deg, {CYAN}, {ORANGE});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}}
.omega-title p {{
    color: {TEXT_MUTED};
    font-size: 0.88rem;
    margin-top: 0;
}}

/* ── Landing page ──────────────────────────────────────────────────── */
.omega-landing {{
    max-width: 720px;
    margin: 2rem auto;
    color: {TEXT_SECONDARY};
    line-height: 1.7;
}}
.omega-landing h3 {{
    color: {CYAN};
    font-size: 1.15rem;
    margin-bottom: 0.4rem;
}}
.omega-landing li {{
    margin-bottom: 0.3rem;
}}

/* ── Stat row ──────────────────────────────────────────────────────── */
.omega-stat-row {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin: 8px 0;
}}
.omega-stat-badge {{
    background: {BG_SURFACE};
    border: 1px solid rgba(103,232,249,0.1);
    border-radius: 6px;
    padding: 6px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: {TEXT_SECONDARY};
}}
.omega-stat-badge strong {{
    color: {CYAN};
    font-weight: 600;
}}
.omega-stat-badge.warn strong {{
    color: {ORANGE};
}}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SHARD LOADING (cached)
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_resource
def load_shard() -> ShardData:
    for p in [Path("/shard"),  # Docker volume mount
              Path("submodules/zuluhotel_omega_2.5"),
              Path("../submodules/zuluhotel_omega_2.5"),
              Path("../../submodules/zuluhotel_omega_2.5")]:
        if p.exists():
            return ShardData.from_path(p)
    st.error("Could not find shard data. Mount shard to /shard or run "
             "from project root with submodules/zuluhotel_omega_2.5.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════
# YAML SERIALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def _spec_to_dict(spec: CombatantSpec) -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": spec.name, "is_npc": spec.is_npc,
        "str": spec.str_, "int": spec.int_, "dex": spec.dex_,
    }
    if spec.hp is not None:
        d["hp"] = spec.hp
    if spec.mana is not None:
        d["mana"] = spec.mana
    if spec.stamina is not None:
        d["stamina"] = spec.stamina
    if spec.skills:
        d["skills"] = {SKILL_ID_TO_NAME.get(k, str(k)): v for k, v in spec.skills.items()}
    if spec.class_levels:
        d["class_levels"] = {CLASS_DISPLAY.get(k, k): v for k, v in spec.class_levels.items()}
    if spec.weapon:
        wd: dict[str, Any] = {
            "name": spec.weapon.name, "damage": spec.weapon.damage,
            "speed": spec.weapon.speed,
            "attribute": SKILL_ID_TO_NAME.get(spec.weapon.attribute, str(spec.weapon.attribute)),
            "quality": spec.weapon.quality,
        }
        if spec.weapon.two_handed:
            wd["two_handed"] = True
        if spec.weapon.properties:
            wd["properties"] = spec.weapon.properties
        if spec.weapon.hitscript:
            wd["hitscript"] = spec.weapon.hitscript
        d["weapon"] = wd
    if spec.armor:
        d["armor"] = {"name": spec.armor.name, "ar": spec.armor.ar}
    if spec.properties:
        d["properties"] = spec.properties
    return d


def _scenario_to_yaml(attacker: dict, defender: dict,
                       iterations: int, seed: int,
                       sweep: dict | None = None) -> str:
    data: dict[str, Any] = {
        "scenario": {"attacker": attacker, "defender": defender,
                     "iterations": iterations, "seed": seed}
    }
    if sweep:
        data["sweep"] = sweep
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


# ═══════════════════════════════════════════════════════════════════════════
# COMBATANT BUILDER WIDGET
# ═══════════════════════════════════════════════════════════════════════════

def build_combatant_ui(label: str, key_prefix: str,
                       default_is_attacker: bool) -> CombatantSpec:
    css_class = "omega-section" if default_is_attacker else "omega-section omega-section-warm"
    icon = "\u2694\uFE0F" if default_is_attacker else "\U0001F6E1\uFE0F"
    st.markdown(f'<div class="{css_class}">{icon} {label}</div>',
                unsafe_allow_html=True)

    col_name, col_npc = st.columns([3, 1])
    with col_name:
        name = st.text_input("Name", value=label, key=f"{key_prefix}_name")
    with col_npc:
        is_npc = st.checkbox("NPC", value=not default_is_attacker,
                             key=f"{key_prefix}_npc")

    # -- Stats --
    st.caption("BASE STATS")
    c1, c2, c3 = st.columns(3)
    with c1:
        str_ = st.number_input("STR", 1, 200, 100, key=f"{key_prefix}_str")
    with c2:
        int_ = st.number_input("INT", 1, 200, 25, key=f"{key_prefix}_int")
    with c3:
        dex_ = st.number_input("DEX", 1, 200, 100, key=f"{key_prefix}_dex")

    with st.expander("Vitals (auto-calculated if empty)"):
        vc1, vc2, vc3 = st.columns(3)
        with vc1:
            hp = st.number_input("HP", 0, 10000, 0, key=f"{key_prefix}_hp",
                                 help=f"Default: STR x 2 = {str_ * 2}")
        with vc2:
            mana = st.number_input("Mana", 0, 10000, 0, key=f"{key_prefix}_mana",
                                   help=f"Default: INT = {int_}")
        with vc3:
            stamina = st.number_input("Stamina", 0, 10000, 0,
                                      key=f"{key_prefix}_stam",
                                      help=f"Default: DEX = {dex_}")

    # -- Class --
    st.caption("CLASS")
    class_levels: dict[str, int] = {}
    cc1, cc2 = st.columns(2)
    with cc1:
        selected_class = st.selectbox(
            "Class", ["None"] + list(CLASS_DISPLAY.values()),
            key=f"{key_prefix}_class")
    with cc2:
        class_level = st.slider("Level", 1, 6, 4,
                                key=f"{key_prefix}_class_level")
    if selected_class != "None":
        class_id = next(k for k, v in CLASS_DISPLAY.items()
                        if v == selected_class)
        class_levels[class_id] = class_level

    # -- Skills --
    st.caption("COMBAT SKILLS")
    skills: dict[int, int] = {}
    preset = st.selectbox(
        "Skill Preset",
        ["Custom", "Melee Fighter", "Archer", "Mage", "Tank", "Unarmed"],
        key=f"{key_prefix}_preset")

    presets: dict[str, dict[str, int]] = {
        "Melee Fighter": {"Swordsmanship": 100, "Tactics": 100,
                          "Anatomy": 100, "Parry": 80},
        "Archer": {"Archery": 100, "Tactics": 100, "Anatomy": 80},
        "Mage": {"Magery": 100, "Eval Intelligence": 100,
                 "Magic Resistance": 100, "Meditation": 100,
                 "Spirit Speak": 80},
        "Tank": {"Swordsmanship": 80, "Tactics": 80, "Anatomy": 80,
                 "Parry": 100, "Magic Resistance": 80},
        "Unarmed": {"Wrestling": 100, "Tactics": 80, "Anatomy": 80},
    }
    preset_skills = presets.get(preset, {})

    with st.expander("Individual Skills",
                     expanded=bool(preset_skills) or preset == "Custom"):
        skill_cols = st.columns(2)
        for i, (sname, sid) in enumerate(COMBAT_SKILLS.items()):
            default = preset_skills.get(sname, 0)
            with skill_cols[i % 2]:
                val = st.slider(sname, 0, 200, default,
                                key=f"{key_prefix}_skill_{sid}")
                if val > 0:
                    skills[sid] = val

    # -- Weapon (attacker) --
    weapon_spec: WeaponSpec | None = None
    if default_is_attacker:
        st.caption("WEAPON")
        wc1, wc2 = st.columns(2)
        with wc1:
            w_name = st.text_input("Name", "Broadsword",
                                   key=f"{key_prefix}_wname")
            w_damage = st.text_input("Damage (dice)", "3d6+2",
                                     key=f"{key_prefix}_wdmg",
                                     help="XdY+Z  (e.g. 3d6+2, 1d20+35)")
        with wc2:
            w_attr_name = st.selectbox(
                "Weapon Skill", list(COMBAT_SKILLS.keys())[:5],
                key=f"{key_prefix}_wattr")
            w_speed = st.slider("Speed", 20, 100, 50,
                                key=f"{key_prefix}_wspeed",
                                help="Lower = faster. 30-70 typical")

        w_quality = st.slider("Quality", 0.5, 3.0, 1.0, step=0.1,
                              key=f"{key_prefix}_wqual")
        w_two_handed = st.checkbox("Two-Handed", key=f"{key_prefix}_w2h")

        # Enchantment
        st.caption("ENCHANTMENT")
        ench_category = st.selectbox(
            "Category", list(ENCHANTMENT_CATEGORIES.keys()),
            key=f"{key_prefix}_ench_cat")

        selected_enchantment: Enchantment | None = None
        chance, circle = 75, 8  # defaults
        if ench_category != "None":
            ench_options = ENCHANTMENT_CATEGORIES[ench_category]
            ench_names = [n for n, _ in ench_options]
            ench_choice = st.selectbox("Enchantment", ench_names,
                                       key=f"{key_prefix}_ench")
            selected_enchantment = dict(ench_options)[ench_choice]
            if ench_category == "Spell Strike":
                ec1, ec2 = st.columns(2)
                with ec1:
                    chance = st.slider("Chance %", 1, 100, 75,
                                       key=f"{key_prefix}_ench_chance")
                with ec2:
                    circle = st.slider("Circle", 1, 10, 8,
                                       key=f"{key_prefix}_ench_circle")

        with st.expander("Elemental Damage Split"):
            elem_parts: list[str] = []
            elem_types = ["Fire", "Air", "Earth", "Water",
                          "Necro", "Holy", "Poison", "Acid"]
            ecols = st.columns(4)
            for i, et in enumerate(elem_types):
                with ecols[i % 4]:
                    pct = st.number_input(f"{et} %", 0, 100, 0,
                                          key=f"{key_prefix}_elem_{et.lower()}")
                    if pct > 0:
                        elem_parts.append(f"{et.upper()}:{pct}")
            astral = st.checkbox("Astral Weapon", key=f"{key_prefix}_astral")

        w_props: dict[str, Any] = {}
        if elem_parts:
            total_elem = sum(int(p.split(":")[1]) for p in elem_parts)
            if total_elem < 100:
                elem_parts.append(f"PHYSICAL:{100 - total_elem}")
            w_props["ElementalDamage"] = " ".join(elem_parts)
        if astral:
            w_props["Astral"] = 1
        if ench_category == "Spell Strike" and selected_enchantment:
            w_props["ChanceOfEffect"] = chance
            w_props["EffectCircle"] = circle

        weapon_spec = WeaponSpec(
            name=w_name, damage=w_damage, speed=w_speed,
            attribute=COMBAT_SKILLS[w_attr_name],
            quality=w_quality, two_handed=w_two_handed,
            properties=w_props)
        if selected_enchantment:
            weapon_spec = weapon_spec.enchant_with(selected_enchantment)

    # -- Armor (defender) --
    armor_spec: ArmorSpec | None = None
    props: dict[str, Any] = {}
    if not default_is_attacker:
        st.caption("ARMOR")
        ac1, ac2 = st.columns(2)
        with ac1:
            a_name = st.text_input("Name", "Plate",
                                   key=f"{key_prefix}_aname")
        with ac2:
            a_ar = st.slider("AR", 0, 100, 30, key=f"{key_prefix}_ar")
        armor_spec = ArmorSpec(name=a_name, ar=a_ar)

        with st.expander("Resistances & Properties"):
            react = st.slider("Reactive Armor", 0, 100, 0,
                               key=f"{key_prefix}_reactive",
                               help="Reflects basedamage * power/100")
            if react > 0:
                props["ReactiveArmor"] = react
            rcols = st.columns(2)
            resist_types = [
                ("Fire", "FireProtection"), ("Air", "AirProtection"),
                ("Earth", "EarthProtection"), ("Water", "WaterProtection"),
                ("Necro", "NecroProtection"), ("Holy", "HolyProtection"),
                ("Poison", "PoisonProtection"),
            ]
            for i, (disp, pname) in enumerate(resist_types):
                with rcols[i % 2]:
                    v = st.slider(f"{disp} Prot %", 0, 100, 0,
                                  key=f"{key_prefix}_resist_{pname}")
                    if v > 0:
                        props[pname] = v

    return CombatantSpec(
        name=name, is_npc=is_npc, str_=str_, int_=int_, dex_=dex_,
        hp=hp if hp > 0 else None,
        mana=mana if mana > 0 else None,
        stamina=stamina if stamina > 0 else None,
        skills=skills, class_levels=class_levels,
        weapon=weapon_spec, armor=armor_spec,
        properties=props)


# ═══════════════════════════════════════════════════════════════════════════
# CHART FACTORIES
# ═══════════════════════════════════════════════════════════════════════════

def _empty_fig(msg: str = "No data", height: int = 380) -> go.Figure:
    fig = _base_fig(height=height)
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(size=15, color=TEXT_MUTED))
    return fig


def chart_histogram(cell: CellResult) -> go.Figure:
    """Damage distribution with glowing mean/median markers."""
    damages = [r.final_damage for r in cell.raw_results
               if r.success and r.final_damage > 0]
    if not damages:
        return _empty_fig("No hits recorded")

    ds = cell.damage_stats_on_hit
    fig = _base_fig(height=420)

    # Histogram bars
    fig.add_trace(go.Histogram(
        x=damages, nbinsx=40,
        marker=dict(
            color=CYAN_DIM,
            line=dict(color=CYAN, width=1),
        ),
        name="Damage",
        hovertemplate="Damage: %{x:.0f}<br>Count: %{y}<extra></extra>",
    ))

    # p5-p95 shaded band
    fig.add_vrect(x0=ds.p5, x1=ds.p95,
                  fillcolor="rgba(103,232,249,0.04)",
                  line_width=0)

    # Mean line
    fig.add_vline(x=ds.mean, line=dict(color=CYAN, width=2, dash="dash"))
    fig.add_annotation(
        x=ds.mean, y=1, yref="paper", yshift=8,
        text=f"<b>Mean {ds.mean:.1f}</b>",
        font=dict(size=12, color=CYAN),
        showarrow=False, bgcolor=BG_SURFACE,
        bordercolor=CYAN, borderwidth=1, borderpad=4)

    # Median line
    fig.add_vline(x=ds.median, line=dict(color=ORANGE, width=2, dash="dot"))
    fig.add_annotation(
        x=ds.median, y=0.92, yref="paper",
        text=f"<b>Median {ds.median:.1f}</b>",
        font=dict(size=11, color=ORANGE),
        showarrow=False, bgcolor=BG_SURFACE,
        bordercolor=ORANGE, borderwidth=1, borderpad=3)

    # p5 / p95 annotations
    fig.add_annotation(
        x=ds.p5, y=0, yref="paper", yshift=-4,
        text=f"p5: {ds.p5:.0f}", font=dict(size=10, color=TEXT_MUTED),
        showarrow=False)
    fig.add_annotation(
        x=ds.p95, y=0, yref="paper", yshift=-4,
        text=f"p95: {ds.p95:.0f}", font=dict(size=10, color=TEXT_MUTED),
        showarrow=False)

    hr = cell.ratios.hit_rate
    fig.update_layout(
        title=dict(text=(f"Damage Distribution<br>"
                         f"<span style='font-size:12px;color:{TEXT_MUTED}'>"
                         f"Hit rate: {hr:.1%}  |  "
                         f"Range: {ds.min:.0f}\u2013{ds.max:.0f}  |  "
                         f"\u03C3 = {ds.std_dev:.1f}</span>")),
        xaxis_title="Final Damage per Hit",
        yaxis_title="Frequency",
        showlegend=False,
        bargap=0.03,
    )
    return fig


def chart_breakdown(cell: CellResult) -> go.Figure:
    """Horizontal breakdown bars — base, absorbed, final, elemental."""
    base = cell.base_damage_stats.mean
    absorbed = cell.absorbed_stats.mean
    final = cell.damage_stats.mean
    elem_total = cell.elemental_breakdown.total_net

    labels = ["Final Damage", "Absorbed (AR)", "Base Damage"]
    values = [final, absorbed, base]
    colors = [GREEN, ORANGE, CYAN]

    if elem_total > 0:
        labels.insert(0, "Elemental")
        values.insert(0, elem_total)
        colors.insert(0, RED)

    fig = _base_fig(height=max(220, 60 * len(labels)))

    def _to_rgba(hex_color: str, alpha: float = 0.35) -> str:
        """Convert #RRGGBB to rgba(r,g,b,alpha)."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig.add_trace(go.Bar(
        y=labels, x=values,
        orientation="h",
        marker=dict(
            color=[_to_rgba(c, 0.35) for c in colors],
            line=dict(color=colors, width=1.5),
        ),
        text=[f"  {v:.1f}" for v in values],
        textposition="outside",
        textfont=dict(size=13, color=colors, family="JetBrains Mono"),
        hovertemplate="%{y}: <b>%{x:.2f}</b><extra></extra>",
    ))

    fig.update_layout(
        title="Damage Pipeline Breakdown",
        xaxis_title="Mean Damage",
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    return fig


def chart_elemental_donut(cell: CellResult) -> go.Figure:
    """Donut chart of per-element damage."""
    data = cell.elemental_breakdown.net_dict()
    if not data:
        return _empty_fig("No elemental damage", 340)

    names = list(data.keys())
    vals = list(data.values())
    colors = [ELEM_COLORS.get(n, TEXT_MUTED) for n in names]
    total = sum(vals)

    fig = _base_fig(height=380)
    fig.add_trace(go.Pie(
        labels=[n.title() for n in names],
        values=vals, hole=0.52,
        marker=dict(colors=colors, line=dict(color=BG_PANEL, width=2)),
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>%{value:.1f}",
        textfont=dict(size=11),
        hovertemplate="%{label}: <b>%{value:.2f}</b> (%{percent})<extra></extra>",
        sort=False,
    ))
    fig.update_layout(
        title=f"Elemental Breakdown (net: {total:.1f})",
        annotations=[dict(text=f"<b>{total:.1f}</b>", x=0.5, y=0.5,
                          font=dict(size=22, color=CYAN),
                          showarrow=False)],
        margin=dict(l=20, r=20, t=72, b=20),
        showlegend=False,
    )
    return fig


def chart_sweep_curve(result: SimulationResult,
                      variable_name: str) -> go.Figure:
    """Damage vs parameter — line + confidence band with data labels."""
    x_vals, means, medians, p5s, p95s, p25s, p75s = [], [], [], [], [], [], []
    for cell in result.cells:
        if variable_name not in cell.variable_values:
            continue
        ds = cell.damage_stats
        x_vals.append(cell.variable_values[variable_name])
        means.append(ds.mean)
        medians.append(ds.median)
        p5s.append(ds.p5)
        p95s.append(ds.p95)
        p25s.append(ds.p25)
        p75s.append(ds.p75)

    if not x_vals:
        return _empty_fig()

    label = SWEEP_PARAMS.get(variable_name, variable_name)
    fig = _base_fig(height=460)

    # p5-p95 outer band
    fig.add_trace(go.Scatter(
        x=x_vals + x_vals[::-1], y=p95s + p5s[::-1],
        fill="toself", fillcolor="rgba(103,232,249,0.06)",
        line=dict(color="rgba(0,0,0,0)"),
        name="p5\u2013p95", hoverinfo="skip", showlegend=True))

    # p25-p75 inner band
    fig.add_trace(go.Scatter(
        x=x_vals + x_vals[::-1], y=p75s + p25s[::-1],
        fill="toself", fillcolor="rgba(103,232,249,0.12)",
        line=dict(color="rgba(0,0,0,0)"),
        name="p25\u2013p75", hoverinfo="skip", showlegend=True))

    # Mean line with data labels
    fig.add_trace(go.Scatter(
        x=x_vals, y=means,
        mode="lines+markers+text",
        name="Mean",
        line=dict(color=CYAN, width=3),
        marker=dict(size=9, color=BG_PANEL, line=dict(color=CYAN, width=2.5)),
        text=[f"{v:.1f}" for v in means],
        textposition="top center",
        textfont=dict(size=10, color=CYAN,
                      family="JetBrains Mono"),
        hovertemplate=(f"{label}: %{{x}}<br>"
                       "Mean: <b>%{y:.2f}</b><extra></extra>")))

    # Median dashed
    fig.add_trace(go.Scatter(
        x=x_vals, y=medians,
        mode="lines+markers",
        name="Median",
        line=dict(color=ORANGE, width=2, dash="dash"),
        marker=dict(size=6, symbol="square",
                    color=BG_PANEL, line=dict(color=ORANGE, width=2)),
        hovertemplate=(f"{label}: %{{x}}<br>"
                       "Median: <b>%{y:.2f}</b><extra></extra>")))

    fig.update_layout(
        title=(f"Damage vs. {label}<br>"
               f"<span style='font-size:11px;color:{TEXT_MUTED}'>"
               f"Bands: p25\u2013p75 (dark) and p5\u2013p95 (light)</span>"),
        xaxis_title=label,
        yaxis_title="Damage",
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
    )
    return fig


def chart_dps_sweep(result: SimulationResult,
                    variable_name: str) -> go.Figure:
    """Effective DPS + hit rate overlay."""
    x_vals, dps_vals, hr_vals = [], [], []
    for cell in result.cells:
        if variable_name not in cell.variable_values:
            continue
        ts = cell.timing or TimingStats()
        x_vals.append(cell.variable_values[variable_name])
        dps_vals.append(ts.effective_dps)
        hr_vals.append(cell.ratios.hit_rate * 100)

    if not x_vals:
        return _empty_fig()

    label = SWEEP_PARAMS.get(variable_name, variable_name)
    fig = _base_fig(height=420)

    # Hit rate area (secondary y)
    fig.add_trace(go.Scatter(
        x=x_vals, y=hr_vals,
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(110,231,183,0.08)",
        line=dict(color="rgba(110,231,183,0.35)", width=1),
        name="Hit Rate %", yaxis="y2",
        hovertemplate=f"{label}: %{{x}}<br>Hit Rate: <b>%{{y:.1f}}%</b><extra></extra>"))

    # DPS line with data labels
    fig.add_trace(go.Scatter(
        x=x_vals, y=dps_vals,
        mode="lines+markers+text",
        name="Effective DPS",
        line=dict(color=RED, width=3),
        marker=dict(size=9, color=BG_PANEL, line=dict(color=RED, width=2.5)),
        text=[f"{v:.2f}" for v in dps_vals],
        textposition="top center",
        textfont=dict(size=10, color=RED, family="JetBrains Mono"),
        hovertemplate=f"{label}: %{{x}}<br>DPS: <b>%{{y:.3f}}</b><extra></extra>"))

    fig.update_layout(
        title=f"DPS vs. {label}",
        xaxis_title=label,
        yaxis_title="Effective DPS",
        yaxis2=dict(
            title="Hit Rate %", overlaying="y", side="right",
            range=[0, 110],
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(size=11, color=GREEN),
            title_font=dict(size=12, color=GREEN)),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
    )
    return fig


def chart_hit_gauge(hit_rate: float) -> go.Figure:
    """Compact radial gauge for hit rate."""
    fig = _base_fig(height=180, margin=dict(l=20, r=20, t=20, b=0))
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=hit_rate * 100,
        number=dict(suffix="%", font=dict(size=26, color=CYAN,
                                          family="JetBrains Mono")),
        gauge=dict(
            axis=dict(range=[0, 100], ticksuffix="%",
                      tickfont=dict(size=10, color=TEXT_MUTED)),
            bar=dict(color=CYAN),
            bgcolor=BG_SURFACE,
            bordercolor=BORDER,
            borderwidth=1,
            steps=[
                dict(range=[0, 33], color="rgba(248,113,113,0.12)"),
                dict(range=[33, 66], color="rgba(253,186,116,0.12)"),
                dict(range=[66, 100], color="rgba(110,231,183,0.12)"),
            ]),
    ))
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# STYLED HTML TABLE
# ═══════════════════════════════════════════════════════════════════════════

def _html_table(headers: list[str], rows: list[list[str]], *,
                highlight_col: int | None = None) -> str:
    """Render a professional dark-themed HTML table."""
    ths = "".join(
        f'<th style="padding:8px 14px;text-align:{"left" if i==0 else "right"};'
        f'font-size:0.78rem;text-transform:uppercase;letter-spacing:0.05em;'
        f'color:{TEXT_MUTED};border-bottom:2px solid rgba(103,232,249,0.15);'
        f'background:{BG_SURFACE}">{h}</th>'
        for i, h in enumerate(headers))

    trs = []
    for row in rows:
        tds = []
        for j, val in enumerate(row):
            color = CYAN if j == highlight_col else TEXT_PRIMARY
            align = "left" if j == 0 else "right"
            font = "JetBrains Mono, monospace" if j > 0 else "inherit"
            tds.append(
                f'<td style="padding:6px 14px;text-align:{align};'
                f'color:{color};font-family:{font};font-size:0.88rem;'
                f'border-bottom:1px solid rgba(100,160,255,0.06)">{val}</td>')
        trs.append(f'<tr style="transition:background 0.15s"'
                   f' onmouseover="this.style.background=\'{BG_HIGHLIGHT}\'"'
                   f' onmouseout="this.style.background=\'transparent\'">'
                   + "".join(tds) + '</tr>')

    return (f'<div style="overflow-x:auto;border:1px solid {BORDER};'
            f'border-radius:8px;background:{BG_PANEL}">'
            f'<table style="width:100%;border-collapse:collapse">'
            f'<thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


# ═══════════════════════════════════════════════════════════════════════════
# RESULTS DISPLAY
# ═══════════════════════════════════════════════════════════════════════════

def display_single_result(cell: CellResult):
    ds = cell.damage_stats
    ds_hit = cell.damage_stats_on_hit
    rs = cell.ratios
    ts = cell.timing

    # ── Key metrics ──
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Mean Damage", f"{ds.mean:.1f}")
    m2.metric("On-Hit Mean", f"{ds_hit.mean:.1f}")
    m3.metric("Hit Rate", f"{rs.hit_rate:.1%}")
    if ts and ts.effective_dps > 0:
        m4.metric("Eff. DPS", f"{ts.effective_dps:.2f}")
        m5.metric("Swing", f"{ts.swing_delay_ms:.0f}ms")
    else:
        m4.metric("Std Dev", f"{ds.std_dev:.1f}")
        m5.metric("Range", f"{ds.min:.0f}\u2013{ds.max:.0f}")

    # ── Charts ──
    tab_hist, tab_break, tab_elem, tab_detail = st.tabs([
        "\U0001F4CA Distribution",
        "\U0001F4C9 Breakdown",
        "\U0001F525 Elemental",
        "\U0001F4CB Detailed Stats",
    ])

    with tab_hist:
        st.plotly_chart(chart_histogram(cell))

    with tab_break:
        st.plotly_chart(chart_breakdown(cell))

    with tab_elem:
        if cell.elemental_breakdown.total_net > 0:
            st.plotly_chart(chart_elemental_donut(cell),
                            )
        else:
            st.markdown(f"""
            <div style="text-align:center;padding:3rem;color:{TEXT_MUTED}">
            <div style="font-size:2rem;margin-bottom:0.5rem">\u2694\uFE0F</div>
            Pure physical damage — no elemental split active.<br>
            <span style="font-size:0.85rem">
            Enable elemental damage on the weapon to see per-element breakdown.
            </span></div>
            """, unsafe_allow_html=True)

    with tab_detail:
        # ── Damage stats table ──
        st.markdown(f'<div class="omega-section" style="margin-top:0">'
                    f'DAMAGE STATISTICS</div>', unsafe_allow_html=True)
        headers = ["Metric", "All Swings", "On Hit Only"]
        rows_data = [
            ("Mean",    f"{ds.mean:.2f}",    f"{ds_hit.mean:.2f}"),
            ("Median",  f"{ds.median:.2f}",  f"{ds_hit.median:.2f}"),
            ("Min",     f"{ds.min:.0f}",     f"{ds_hit.min:.0f}"),
            ("Max",     f"{ds.max:.0f}",     f"{ds_hit.max:.0f}"),
            ("Std Dev", f"{ds.std_dev:.2f}", f"{ds_hit.std_dev:.2f}"),
            ("P5",      f"{ds.p5:.1f}",      f"{ds_hit.p5:.1f}"),
            ("P25",     f"{ds.p25:.1f}",     f"{ds_hit.p25:.1f}"),
            ("P75",     f"{ds.p75:.1f}",     f"{ds_hit.p75:.1f}"),
            ("P95",     f"{ds.p95:.1f}",     f"{ds_hit.p95:.1f}"),
            ("Count",   str(ds.count),       str(ds_hit.count)),
        ]
        st.markdown(_html_table(headers,
                                [[a, b, c] for a, b, c in rows_data]),
                    unsafe_allow_html=True)

        # ── Event rates table ──
        st.markdown(f'<div class="omega-section omega-section-warm" '
                    f'style="margin-top:16px">EVENT RATES</div>',
                    unsafe_allow_html=True)
        rate_rows = [
            ["Hit Rate",       f"{rs.hit_rate:.1%}",        "\u2014"],
            ["Spell Strike",   f"{rs.spell_strike_rate:.1%}",
             f"{rs.spell_strike_rate_on_hit:.1%}"],
            ["Reactive",       f"{rs.reactive_rate:.1%}",
             f"{rs.reactive_rate_on_hit:.1%}"],
            ["Effect",         f"{rs.effect_rate:.1%}",
             f"{rs.effect_rate_on_hit:.1%}"],
            ["Poison",         f"{rs.poison_rate:.1%}",     "\u2014"],
            ["Equip Break",    f"{rs.equipment_break_rate:.1%}", "\u2014"],
        ]
        st.markdown(_html_table(["Event", "Per Swing", "Per Hit"],
                                rate_rows), unsafe_allow_html=True)

        # ── DPS ──
        if ts and ts.swing_delay_ms > 0:
            st.markdown(f'<div class="omega-section" '
                        f'style="margin-top:16px">TIMING & DPS</div>',
                        unsafe_allow_html=True)
            dps_rows = [
                ["Swing Delay",   f"{ts.swing_delay_ms:.0f}ms"],
                ["Swings/sec",    f"{ts.swings_per_second:.3f}"],
                ["DPS (mean)",    f"{ts.dps_mean:.3f}"],
                ["DPS (on hit)",  f"{ts.dps_on_hit:.3f}"],
                ["Effective DPS", f"{ts.effective_dps:.3f}"],
            ]
            st.markdown(_html_table(["Metric", "Value"], dps_rows,
                                    highlight_col=1),
                        unsafe_allow_html=True)

        # ── Drain ──
        if cell.drain_stats.mean > 0:
            st.markdown(f'<div class="omega-section omega-section-warm" '
                        f'style="margin-top:16px">DRAIN STATS</div>',
                        unsafe_allow_html=True)
            dr = cell.drain_stats
            drh = cell.drain_stats_on_hit
            drain_rows = [
                ["Mean Drain",        f"{dr.mean:.2f}"],
                ["Mean Drain (hit)",  f"{drh.mean:.2f}"],
                ["Max Drain",         f"{dr.max:.0f}"],
                ["Drain Count",       str(dr.count)],
            ]
            st.markdown(_html_table(["Metric", "Value"], drain_rows),
                        unsafe_allow_html=True)


def display_sweep_result(result: SimulationResult,
                         variables: list[Variable]):
    if not result.cells:
        st.warning("No results to display.")
        return

    var = variables[0]
    var_name = f"{var.target}.{var.parameter}"
    label = SWEEP_PARAMS.get(var.parameter, var.parameter)

    tab_curve, tab_dps, tab_table, tab_cells = st.tabs([
        "\U0001F4C8 Damage Curve",
        "\u26A1 DPS Analysis",
        "\U0001F4CB Data Table",
        "\U0001F50D Cell Detail",
    ])

    with tab_curve:
        st.plotly_chart(chart_sweep_curve(result, var_name),
                        )

    with tab_dps:
        st.plotly_chart(chart_dps_sweep(result, var_name),
                        )

    with tab_table:
        headers = [label, "Mean", "Median", "Min", "Max",
                   "P5", "P95", "Hit Rate"]
        has_dps = any(c.timing and c.timing.swing_delay_ms > 0
                      for c in result.cells)
        if has_dps:
            headers += ["DPS", "Swing"]

        rows = []
        for cell in result.cells:
            ts = cell.timing
            row = [
                str(cell.variable_values.get(var_name, "")),
                f"{cell.damage_stats.mean:.2f}",
                f"{cell.damage_stats.median:.2f}",
                f"{cell.damage_stats.min:.0f}",
                f"{cell.damage_stats.max:.0f}",
                f"{cell.damage_stats.p5:.1f}",
                f"{cell.damage_stats.p95:.1f}",
                f"{cell.ratios.hit_rate:.1%}",
            ]
            if has_dps:
                if ts and ts.swing_delay_ms > 0:
                    row += [f"{ts.effective_dps:.3f}",
                            f"{ts.swing_delay_ms:.0f}ms"]
                else:
                    row += ["\u2014", "\u2014"]
            rows.append(row)

        st.markdown(_html_table(headers, rows, highlight_col=1),
                    unsafe_allow_html=True)

    with tab_cells:
        cell_idx = st.selectbox(
            "Select cell", range(len(result.cells)),
            format_func=lambda i: (
                f"{label} = "
                f"{result.cells[i].variable_values.get(var_name, '?')}"))
        display_single_result(result.cells[cell_idx])


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════

def main():
    # Title
    st.markdown("""
    <div class="omega-title">
        <h1>\u2694\uFE0F  Omega Combat Simulator</h1>
        <p>Configure combatants \u00b7 Run simulations \u00b7 Analyze results</p>
    </div>
    """, unsafe_allow_html=True)

    shard = load_shard()

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(f'<div class="omega-section">SIMULATION</div>',
                    unsafe_allow_html=True)
        sim_mode = st.radio("Mode",
                            ["Single Scenario", "Parameter Sweep"],
                            horizontal=True)
        ci, cs = st.columns(2)
        with ci:
            iterations = st.number_input("Iterations", 10, 50000, 1000,
                                         step=100)
        with cs:
            seed = st.number_input("RNG Seed", 0, 999999, 42)

        st.divider()
        attacker_spec = build_combatant_ui("Attacker", "atk",
                                           default_is_attacker=True)
        st.divider()
        defender_spec = build_combatant_ui("Defender", "def",
                                           default_is_attacker=False)

        # Sweep config
        sweep_variables: list[Variable] = []
        if sim_mode == "Parameter Sweep":
            st.divider()
            st.markdown(f'<div class="omega-section">'
                        f'PARAMETER SWEEP</div>', unsafe_allow_html=True)
            sweep_target = st.selectbox("Target",
                                        ["attacker", "defender"])
            sweep_param_label = st.selectbox("Parameter",
                                             list(SWEEP_PARAMS.values()))
            sweep_param = SWEEP_PARAM_REVERSE[sweep_param_label]
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                sweep_start = st.number_input("Start", 0, 1000, 50)
            with sc2:
                sweep_stop = st.number_input("Stop", 0, 1000, 130)
            with sc3:
                sweep_step = st.number_input("Step", 1, 100, 10)
            sweep_variables.append(
                Variable.from_range(sweep_target, sweep_param,
                                    start=sweep_start, stop=sweep_stop,
                                    step=sweep_step))

        # Save/load
        st.divider()
        st.caption("SCENARIO FILES")
        dl_col, up_col = st.columns(2)
        with dl_col:
            yaml_str = _scenario_to_yaml(
                _spec_to_dict(attacker_spec),
                _spec_to_dict(defender_spec),
                iterations, seed)
            st.download_button("\u2B07 Export YAML", data=yaml_str,
                               file_name="scenario.yaml",
                               mime="text/yaml",
                               )
        with up_col:
            uploaded = st.file_uploader("Load", type=["yaml", "yml"],
                                        label_visibility="collapsed")
            if uploaded:
                st.info("YAML import: set widget values manually for now.")

        # Run
        st.divider()
        run_pressed = st.button("\u25B6  Run Simulation",
                                type="primary",
                                )

    # ── Main panel ──
    if run_pressed:
        scenario = Scenario(attacker=attacker_spec,
                            defender=defender_spec,
                            iterations=iterations, base_seed=seed)

        if sim_mode == "Single Scenario":
            with st.spinner("Simulating..."):
                t0 = time.time()
                cell = run_scenario(scenario, shard=shard)
                elapsed = time.time() - t0

            hits_sec = cell.iteration_count / elapsed if elapsed > 0 else 0
            st.markdown(
                f'<div class="omega-stat-row">'
                f'<span class="omega-stat-badge">'
                f'<strong>{cell.iteration_count}</strong> iterations</span>'
                f'<span class="omega-stat-badge">'
                f'<strong>{elapsed:.2f}s</strong> elapsed</span>'
                f'<span class="omega-stat-badge">'
                f'<strong>{hits_sec:.0f}</strong> hits/sec</span>'
                f'<span class="omega-stat-badge">'
                f'<strong>{cell.success_count}</strong> successes</span>'
                f'<span class="omega-stat-badge warn">'
                f'<strong>{cell.error_count}</strong> errors</span>'
                f'</div>', unsafe_allow_html=True)

            display_single_result(cell)

        else:
            sweep = ParameterSweep(scenario=scenario,
                                   variables=tuple(sweep_variables))
            n_cells = 1
            for v in sweep_variables:
                n_cells *= len(v.values)

            with st.spinner(
                    f"Sweeping {n_cells} cells \u00d7 "
                    f"{iterations} iterations..."):
                t0 = time.time()
                result = run_sweep(sweep, shard=shard)
                elapsed = time.time() - t0

            total_hits = sum(c.iteration_count for c in result.cells)
            hits_sec = total_hits / elapsed if elapsed > 0 else 0
            st.markdown(
                f'<div class="omega-stat-row">'
                f'<span class="omega-stat-badge">'
                f'<strong>{n_cells}</strong> cells</span>'
                f'<span class="omega-stat-badge">'
                f'<strong>{total_hits:,}</strong> iterations</span>'
                f'<span class="omega-stat-badge">'
                f'<strong>{elapsed:.2f}s</strong> elapsed</span>'
                f'<span class="omega-stat-badge">'
                f'<strong>{hits_sec:.0f}</strong> hits/sec</span>'
                f'</div>', unsafe_allow_html=True)

            display_sweep_result(result, sweep_variables)

    else:
        # ── Landing ──
        st.markdown(f"""
        <div class="omega-landing">
        <h3>Getting Started</h3>
        <ol>
            <li><strong>Configure combatants</strong> in the sidebar
                \u2014 stats, skills, class, equipment</li>
            <li><strong>Choose a mode</strong> \u2014 single scenario
                or parameter sweep</li>
            <li><strong>Run Simulation</strong> to see interactive results</li>
        </ol>

        <h3>Capabilities</h3>
        <ul>
            <li><strong>10 character classes</strong> with level 1\u20135
                bonus scaling</li>
            <li><strong>45 weapon enchantments</strong> \u2014 spell strike,
                slayers, effects, greaters</li>
            <li><strong>8 elemental damage types</strong> with per-element
                resistance</li>
            <li><strong>Astral weapons</strong> \u2014 mana/stamina drain
                pipeline</li>
            <li><strong>Parameter sweeps</strong> \u2014 vary any stat, skill,
                or property and see damage/DPS curves</li>
            <li><strong>YAML export</strong> \u2014 save and share scenario
                configurations</li>
        </ul>

        <h3>Simulation Modes</h3>
        <table style="width:100%;border-collapse:collapse;margin-top:8px">
            <tr style="border-bottom:1px solid rgba(100,160,255,0.1)">
                <td style="padding:8px 12px;color:{CYAN};
                    font-weight:600">Single Scenario</td>
                <td style="padding:8px 12px">Run N iterations of a fixed
                    matchup. See distribution, breakdown, DPS.</td>
            </tr>
            <tr>
                <td style="padding:8px 12px;color:{ORANGE};
                    font-weight:600">Parameter Sweep</td>
                <td style="padding:8px 12px">Vary one parameter across a
                    range. See damage curves and per-cell drill-down.</td>
            </tr>
        </table>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
