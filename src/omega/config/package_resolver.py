"""Package path resolver for POL shard directory structure.

Scans ``pkg.cfg`` files to build a mapping of package names to filesystem
paths, then resolves ``:pkgname:filepath`` references used in eScript
``include`` statements and ``ReadConfigFile()`` calls.

Implements the ``PackageMap`` protocol from ``omega.parser.include_resolver``.
"""

from __future__ import annotations

import re
from pathlib import Path

from omega.logging import get_logger

logger = get_logger("omega.config")


class PackageResolver:
    """Resolves package names to filesystem paths by scanning pkg.cfg files.

    Parameters
    ----------
    shard_root:
        Root directory of the shard (e.g., ``submodules/zuluhotel_omega_2.5/``).
    """

    def __init__(self, shard_root: Path) -> None:
        self.shard_root = shard_root
        self._map: dict[str, Path] = {}
        self._scan()

    def _scan(self) -> None:
        """Scan all pkg.cfg files under the shard root."""
        for pkg_cfg in self.shard_root.rglob("pkg.cfg"):
            text = pkg_cfg.read_text(errors="replace")
            m = re.search(r"Name\s+(\S+)", text, re.IGNORECASE)
            if m:
                name = m.group(1).lower()
                self._map[name] = pkg_cfg.parent
        logger.info("scanned packages", count=len(self._map))

    def resolve(self, package_name: str) -> Path | None:
        """Resolve a package name to its directory path.

        Parameters
        ----------
        package_name:
            The package name (case-insensitive).

        Returns
        -------
        Path or None:
            The directory containing the package, or None if unknown.
        """
        return self._map.get(package_name.lower())

    def resolve_config_path(self, config_ref: str) -> Path | None:
        """Resolve a config file reference like ``:combat:settings`` or ``:*:itemdesc``.

        Parameters
        ----------
        config_ref:
            A config reference string. Format: ``:pkgname:filename`` or
            ``:*:filename`` (wildcard — search all packages).

        Returns
        -------
        Path or None:
            Path to the resolved config file, or None if not found.
        """
        ref = config_ref.strip().strip('"').strip("'")
        if not ref.startswith(":"):
            # Not a package reference — treat as relative path
            return self.shard_root / ref

        parts = ref.lstrip(":").split(":", 1)
        if len(parts) != 2:
            logger.warning("invalid config ref format", ref=config_ref)
            return None

        pkg_name, file_name = parts

        if pkg_name == "*":
            return self._resolve_wildcard(file_name)

        pkg_dir = self.resolve(pkg_name)
        if pkg_dir is None:
            logger.warning("unknown package in config ref", package=pkg_name, ref=config_ref)
            return None

        # Search for the file in the package's config/ directory, then root
        for candidate in [
            pkg_dir / "config" / f"{file_name}.cfg",
            pkg_dir / f"{file_name}.cfg",
            pkg_dir / "config" / file_name,
            pkg_dir / file_name,
        ]:
            if candidate.exists():
                return candidate

        logger.warning("config file not found in package", package=pkg_name, file=file_name)
        return None

    def _resolve_wildcard(self, file_name: str) -> Path | None:
        """Resolve ``:*:filename`` by searching all packages."""
        for pkg_dir in self._map.values():
            for candidate in [
                pkg_dir / "config" / f"{file_name}.cfg",
                pkg_dir / f"{file_name}.cfg",
            ]:
                if candidate.exists():
                    return candidate
        logger.warning("wildcard config file not found", file=file_name)
        return None

    @property
    def packages(self) -> dict[str, Path]:
        """All discovered packages as name → directory mapping."""
        return dict(self._map)

    def __len__(self) -> int:
        return len(self._map)

    def __contains__(self, package_name: str) -> bool:
        return package_name.lower() in self._map
