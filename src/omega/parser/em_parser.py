"""Parser for POL .em module files (constant declarations).

.em files define constants used by `use` declarations in eScript:
  ``const POLCLASS_NPC := 4;``
  ``const CRMULTI_IGNORE_ALL := 0x0007;``

This is a simple regex-based parser — .em files only contain
constant declarations and function signatures (which we ignore).
"""

from __future__ import annotations

import re
from pathlib import Path

from omega.logging import get_logger

logger = get_logger("omega.parser")

# Matches: const NAME := VALUE;
_CONST_RE = re.compile(
    r"^\s*const\s+(\w+)\s*:=\s*(.+?)\s*;\s*$",
    re.IGNORECASE,
)


def parse_em_constants(path: Path) -> dict[str, int | float | str]:
    """Parse constant declarations from a .em module file.

    Returns a dict of constant_name → value.
    Only handles integer (decimal and hex), float, and string literals.
    """
    constants: dict[str, int | float | str] = {}

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        logger.warning("Cannot read .em file", path=str(path))
        return constants

    for line in text.splitlines():
        m = _CONST_RE.match(line)
        if m is None:
            continue

        name = m.group(1)
        raw_value = m.group(2).strip()

        value = _parse_value(raw_value)
        if value is not None:
            constants[name] = value

    return constants


def _parse_value(raw: str) -> int | float | str | None:
    """Parse a constant value literal."""
    # String literal
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]

    # Hex integer
    if raw.startswith("0x") or raw.startswith("0X"):
        try:
            return int(raw, 16)
        except ValueError:
            return None

    # Try integer
    try:
        return int(raw)
    except ValueError:
        pass

    # Try float
    try:
        return float(raw)
    except ValueError:
        pass

    return None


def load_em_modules(
    modules_dir: Path, module_names: list[str]
) -> dict[str, int | float | str]:
    """Load constants from multiple .em module files.

    Parameters
    ----------
    modules_dir:
        Directory containing .em files (e.g., ``scripts/modules/``).
    module_names:
        Module names from ``use`` declarations (e.g., ["uo", "os", "util"]).

    Returns
    -------
    dict:
        Combined constants from all requested modules.
    """
    all_constants: dict[str, int | float | str] = {}

    for name in module_names:
        em_path = modules_dir / f"{name}.em"
        if em_path.exists():
            constants = parse_em_constants(em_path)
            all_constants.update(constants)
            logger.debug("Loaded .em module", module=name, constants=len(constants))
        else:
            logger.debug("No .em file found", module=name)

    return all_constants
