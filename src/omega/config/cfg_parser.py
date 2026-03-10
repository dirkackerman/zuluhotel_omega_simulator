"""POL config file parser.

Handles two formats found in POL shards:

1. **Flat key=value** (e.g., ``combat.cfg``): ``Key=Value`` lines with ``#`` comments.
2. **Block-based** (e.g., ``npcdesc.cfg``): ``BlockType Name { Key Value }`` with
   ``//`` comments, tab/space-separated values, and CProp entries.

Usage::

    cfg = parse_config_file(Path("config/npcdesc.cfg"))
    npc = cfg["nazgul"]
    strength = npc["STR"]  # "200"
    npc_type = npc.get_cprop("Type")  # "Human"
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

from omega.logging import get_logger

logger = get_logger("omega.config")


class ConfigElement:
    """A single element/block from a config file.

    Supports property access by name. Keys with multiple values
    (e.g., multiple ``spell`` or ``Coverage`` entries) store all values;
    single access returns the first.
    """

    def __init__(self, block_type: str, name: str) -> None:
        self.block_type = block_type
        self.name = name
        self._properties: dict[str, list[str]] = {}
        self._cprops: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        """Add a property value. Multiple calls with the same key append."""
        self._properties.setdefault(key, []).append(value)

    def set_cprop(self, name: str, raw_value: str) -> None:
        """Store a CProp with its raw type-prefixed value."""
        self._cprops[name] = raw_value

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get the first value for a key, or default if not present."""
        values = self._properties.get(key)
        if values:
            return values[0]
        return default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get a property as an integer."""
        val = self.get(key)
        if val is None:
            return default
        try:
            return int(val)
        except ValueError:
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a property as a float."""
        val = self.get(key)
        if val is None:
            return default
        try:
            return float(val)
        except ValueError:
            return default

    def get_all(self, key: str) -> list[str]:
        """Get all values for a multi-value key (e.g., spell, Coverage)."""
        return list(self._properties.get(key, []))

    def get_cprop(self, name: str) -> Any:
        """Get a CProp value, parsing the type prefix (i=int, s=string)."""
        raw = self._cprops.get(name)
        if raw is None:
            return None
        return _parse_cprop_value(raw)

    def get_cprop_raw(self, name: str) -> str | None:
        """Get the raw CProp value string including type prefix."""
        return self._cprops.get(name)

    @property
    def properties(self) -> dict[str, list[str]]:
        """All properties as key → list of values."""
        return dict(self._properties)

    @property
    def cprops(self) -> dict[str, str]:
        """All CProps as name → raw value."""
        return dict(self._cprops)

    def __getitem__(self, key: str) -> str | None:
        return self.get(key)

    def __getattr__(self, name: str) -> str | None:
        # Only called for attributes not found normally
        if name.startswith("_"):
            raise AttributeError(name)
        val = self.get(name)
        if val is not None:
            return val
        # Check cprops
        cprop = self.get_cprop(name)
        if cprop is not None:
            return cprop
        return None

    def __contains__(self, key: str) -> bool:
        return key in self._properties or key in self._cprops

    def __repr__(self) -> str:
        return f"ConfigElement({self.block_type!r}, {self.name!r}, props={len(self._properties)}, cprops={len(self._cprops)})"


class ConfigFile:
    """A parsed POL config file containing elements/blocks.

    Supports lookup by element name or integer key (for objtype-based configs).
    """

    def __init__(self, path: str = "<unknown>") -> None:
        self.path = path
        self._elements_by_name: dict[str, ConfigElement] = {}
        self._elements_by_int: dict[int, ConfigElement] = {}
        self._elements_ordered: list[ConfigElement] = []
        self._flat_properties: dict[str, str] = {}

    def add_element(self, elem: ConfigElement) -> None:
        """Add a parsed element to the config file."""
        self._elements_ordered.append(elem)
        self._elements_by_name[elem.name] = elem
        # Try to parse name as int (for objtype-keyed configs like itemdesc)
        try:
            int_key = int(elem.name, 0)  # base 0 handles 0x hex
            self._elements_by_int[int_key] = elem
        except (ValueError, TypeError):
            pass

    def set_flat(self, key: str, value: str) -> None:
        """Set a flat key=value property (for non-block configs like combat.cfg)."""
        self._flat_properties[key] = value

    def __getitem__(self, key: str | int) -> ConfigElement | str | None:
        if isinstance(key, int):
            elem = self._elements_by_int.get(key)
            if elem is not None:
                return elem
            # Try hex string lookup
            hex_key = f"0x{key:04X}"
            return self._elements_by_name.get(hex_key)
        # String key — try element lookup first, then flat properties
        elem = self._elements_by_name.get(key)
        if elem is not None:
            return elem
        # Case-insensitive fallback for element lookup
        key_lower = key.lower()
        for name, e in self._elements_by_name.items():
            if name.lower() == key_lower:
                return e
        return self._flat_properties.get(key)

    def __contains__(self, key: str | int) -> bool:
        return self[key] is not None

    def __iter__(self) -> Iterator[ConfigElement]:
        return iter(self._elements_ordered)

    def __len__(self) -> int:
        return len(self._elements_ordered)

    @property
    def flat_properties(self) -> dict[str, str]:
        """Flat key=value properties (for non-block configs)."""
        return dict(self._flat_properties)

    def __repr__(self) -> str:
        return f"ConfigFile({self.path!r}, elements={len(self._elements_ordered)}, flat={len(self._flat_properties)})"


def parse_config_file(path: Path) -> ConfigFile:
    """Parse a POL config file.

    Auto-detects format (flat key=value vs block-based) from content.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    cfg = ConfigFile(str(path))

    lines = text.splitlines()

    # Detect format: if we find a '{' that's not in a comment, it's block format
    is_block = False
    for line in lines:
        stripped = _strip_comments(line)
        if "{" in stripped:
            is_block = True
            break

    if is_block:
        _parse_block_format(lines, cfg)
    else:
        _parse_flat_format(lines, cfg)

    logger.debug(
        "parsed config file",
        path=str(path),
        elements=len(cfg._elements_ordered),
        flat=len(cfg._flat_properties),
    )
    return cfg


def _strip_comments(line: str) -> str:
    """Strip comments from a line, handling both # and // formats."""
    # Handle // comments (but not inside strings — simple approach: first //)
    idx = line.find("//")
    if idx >= 0:
        line = line[:idx]
    return line


def _parse_flat_format(lines: list[str], cfg: ConfigFile) -> None:
    """Parse flat Key=Value format (e.g., combat.cfg)."""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if "=" in line:
            # Strip # comments from value
            comment_idx = line.find("#")
            if comment_idx > 0:
                line = line[:comment_idx].strip()
            key, _, value = line.partition("=")
            cfg.set_flat(key.strip(), value.strip())


def _parse_block_format(lines: list[str], cfg: ConfigFile) -> None:
    """Parse block-based format (NpcTemplate/Equipment/Weapon/Armor/Elem/etc.)."""
    i = 0
    while i < len(lines):
        line = _strip_comments(lines[i]).strip()
        i += 1

        if not line or line.startswith("#"):
            continue

        # Look for block opener: "BlockType Name" or "BlockType Name {"
        # The brace may be on the same line or the next line
        if "{" in line and not line.startswith("{"):
            # "BlockType Name {" on one line
            before_brace = line.split("{")[0].strip()
            parts = before_brace.split(None, 1)
            if len(parts) >= 2:
                block_type, name = parts[0], parts[1]
            elif len(parts) == 1:
                block_type, name = parts[0], parts[0]
            else:
                continue
            elem = ConfigElement(block_type, name)
            i = _parse_block_body(lines, i, elem)
            cfg.add_element(elem)
        elif "{" not in line and "}" not in line and "=" not in line:
            # Could be "BlockType Name" with { on next line
            parts = line.split(None, 1)
            if len(parts) >= 1:
                # Peek at next non-empty, non-comment line for {
                j = i
                while j < len(lines):
                    next_line = _strip_comments(lines[j]).strip()
                    if next_line:
                        break
                    j += 1
                if j < len(lines) and _strip_comments(lines[j]).strip().startswith("{"):
                    block_type = parts[0]
                    name = parts[1] if len(parts) >= 2 else parts[0]
                    elem = ConfigElement(block_type, name)
                    i = _parse_block_body(lines, j + 1, elem)
                    cfg.add_element(elem)


def _parse_block_body(lines: list[str], start: int, elem: ConfigElement) -> int:
    """Parse the body of a block until closing }. Returns next line index."""
    i = start
    while i < len(lines):
        line = _strip_comments(lines[i]).strip()
        i += 1

        if not line:
            continue
        if line.startswith("}"):
            return i
        if line.startswith("{"):
            # Opening brace on its own line (already inside block), skip
            continue

        # Parse key-value pair
        # Split on first run of whitespace (tabs/spaces)
        parts = line.split(None, 1)
        if not parts:
            continue

        key = parts[0]
        value = parts[1].strip() if len(parts) > 1 else ""

        # Handle CProp entries: "CProp Name TypeValue"
        if key.lower() == "cprop":
            cprop_parts = value.split(None, 1)
            if len(cprop_parts) >= 2:
                elem.set_cprop(cprop_parts[0], cprop_parts[1])
            elif len(cprop_parts) == 1:
                elem.set_cprop(cprop_parts[0], "")
        else:
            elem.set(key, value)

    return i


def _parse_cprop_value(raw: str) -> Any:
    """Parse a CProp type-prefixed value: i=int, s=string."""
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("i"):
        try:
            return int(raw[1:])
        except ValueError:
            return raw
    if raw.startswith("s"):
        return raw[1:]
    # No recognized prefix — return as-is
    return raw
