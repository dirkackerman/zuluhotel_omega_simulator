"""Config file parsing for POL shard files."""

from omega.config.accessor import RuntimeConfigElement, RuntimeConfigFile
from omega.config.cfg_parser import ConfigElement, ConfigFile, parse_config_file
from omega.config.dice import DiceSpec, parse_dice, roll_dice
from omega.config.package_resolver import PackageResolver
from omega.config.spell_registry import (
    CASTABLE_SPELL_IDS,
    DAMAGE_SPELL_IDS,
    NON_DAMAGE_SPELL_IDS,
    CircleConfig,
    SpellEntry,
    SpellRegistry,
)

__all__ = [
    "CASTABLE_SPELL_IDS",
    "CircleConfig",
    "ConfigElement",
    "ConfigFile",
    "DAMAGE_SPELL_IDS",
    "DiceSpec",
    "NON_DAMAGE_SPELL_IDS",
    "PackageResolver",
    "RuntimeConfigElement",
    "RuntimeConfigFile",
    "SpellEntry",
    "SpellRegistry",
    "parse_config_file",
    "parse_dice",
    "roll_dice",
]
