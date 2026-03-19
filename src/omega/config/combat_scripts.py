"""Combat script path enum — canonical package paths for hitscripts and onhitscripts.

Eliminates magic strings like ``":combat:spellstrikescript"`` throughout the
codebase.  Uses a ``str`` enum so values pass straight through to
``executor.run_sub_program()``, ``start_script()``, and property assignment
without conversion::

    from omega.config.combat_scripts import CombatScript

    weapon.hitscript = CombatScript.SPELLSTRIKESCRIPT
    armor.set_property("OnHitScript", CombatScript.SPELLONHIT)
"""

from __future__ import annotations

from enum import Enum


class CombatScript(str, Enum):
    """Combat script package paths from hitscriptdesc.cfg and onhitscriptdesc.cfg.

    Each value is the exact ``:combat:name`` string used by POL's
    ``start_script()`` and weapon/armor hitscript properties.
    """

    # -- Main combat entry point --
    MAINHIT = ":combat:mainhit"

    # -- Weapon hitscripts (from hitscriptdesc.cfg) --
    SPELLSTRIKESCRIPT = ":combat:spellstrikescript"
    SLAYERSCRIPT = ":combat:slayerscript"
    PIERCINGSCRIPT = ":combat:piercingscript"
    BANISHSCRIPT = ":combat:banishscript"
    POISONHIT = ":combat:poisonhit"
    LIFEDRAINSCRIPT = ":combat:lifedrainscript"
    MANADRAINSCRIPT = ":combat:manadrainscript"
    STAMINADRAINSCRIPT = ":combat:staminadrainscript"
    BLINDINGSCRIPT = ":combat:blindingscript"
    DUALPLANARSCRIPT = ":combat:dualplanarscript"
    VOIDSCRIPT = ":combat:voidscript"
    TRIELEMENTALSCRIPT = ":combat:trielementalscript"

    # -- Armor onhitscripts (from onhitscriptdesc.cfg) --
    SPELLONHIT = ":combat:spellonhit"
    RACERESISTONHIT = ":combat:raceresistonhit"
    PIERCINGONHIT = ":combat:piercingonhit"
    BANISHONHIT = ":combat:banishonhit"
    POISONONHIT = ":combat:poisononhit"
    BOUNCINGONHIT = ":combat:bouncingonhit"
    MANADRAINONHIT = ":combat:manadrainonhit"
    STAMINADRAINONHIT = ":combat:staminadrainonhit"
    BLINDINGONHIT = ":combat:blindingonhit"
    TRIELEMENTALONHIT = ":combat:trielementalonhit"
    DEFLECTIONONHIT = ":combat:deflectiononhit"
    AVENGINGONHIT = ":combat:avengingonhit"
    INVISIBLEONHIT = ":combat:invisibleonhit"
    DUALPLANARONHIT = ":combat:dualplanaronhit"

    # -- Reactive armor (hardcoded in hitscriptinc.inc) --
    REACTIVEARMORONHIT = ":combat:reactivearmoronhit"
