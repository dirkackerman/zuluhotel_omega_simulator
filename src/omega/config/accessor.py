"""Runtime-compatible config file accessor.

When eScript calls ``ReadConfigFile(":combat:settings")``, it gets back an
object that supports bracket indexing (``cfg["Weapons"]``) and the returned
elements support dot-style property access (``elem.WearChance``).

This module provides thin wrappers that match the POL API contract while
delegating to the underlying ``ConfigFile`` and ``ConfigElement`` objects.

Usage (from runtime stubs)::

    from omega.config.accessor import RuntimeConfigFile

    cfg = RuntimeConfigFile.from_path(path)
    elem = cfg["Weapons"]       # bracket index → RuntimeConfigElement
    val = elem.WearChance       # dot access → string value
"""

from __future__ import annotations

from pathlib import Path

from omega.config.cfg_parser import ConfigElement, ConfigFile, parse_config_file
from omega.logging import get_logger

logger = get_logger("omega.config")


class RuntimeConfigElement:
    """Wraps a ConfigElement for eScript runtime access.

    Supports dot-style property access matching POL's behavior:
    ``elem.PropertyName`` returns the property value as a string.
    """

    def __init__(self, elem: ConfigElement) -> None:
        self._elem = elem

    def __getattr__(self, name: str) -> str | int | None:
        if name.startswith("_"):
            raise AttributeError(name)
        # Try properties first
        val = self._elem.get(name)
        if val is not None:
            return val
        # Try cprops
        cprop = self._elem.get_cprop(name)
        if cprop is not None:
            return cprop
        return None

    def __getitem__(self, key: str) -> str | None:
        return self._elem.get(key)

    def __repr__(self) -> str:
        return f"RuntimeConfigElement({self._elem.block_type!r}, {self._elem.name!r})"


class RuntimeConfigFile:
    """Wraps a ConfigFile for eScript runtime access.

    Supports bracket indexing matching POL's ``ReadConfigFile`` return:
    ``cfg["ElementName"]`` or ``cfg[0x13BB]`` returns a ``RuntimeConfigElement``.
    """

    def __init__(self, cfg: ConfigFile) -> None:
        self._cfg = cfg

    @classmethod
    def from_path(cls, path: Path) -> RuntimeConfigFile:
        """Parse a config file and wrap it for runtime access."""
        cfg = parse_config_file(path)
        return cls(cfg)

    def __getitem__(self, key: str | int) -> RuntimeConfigElement | str | None:
        result = self._cfg[key]
        if isinstance(result, ConfigElement):
            return RuntimeConfigElement(result)
        return result  # flat property string or None

    def __contains__(self, key: str | int) -> bool:
        return key in self._cfg

    def __repr__(self) -> str:
        return f"RuntimeConfigFile({self._cfg.path!r})"
