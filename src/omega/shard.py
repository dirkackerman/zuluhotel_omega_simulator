"""Shard loader — discovers packages, config files, and combat scripts.

Usage::

    shard = ShardData.from_path(Path("submodules/zuluhotel_omega_2.5"))
    trees = shard.parse_combat_scripts()
"""

from __future__ import annotations

from pathlib import Path

from omega.config.cfg_parser import ConfigFile, parse_config_file
from omega.logging import get_logger
from omega.parser.include_resolver import DictPackageMap, PackageMap

logger = get_logger("omega.shard")


class ShardData:
    """Loaded shard data: package map, config files, script paths.

    Parameters
    ----------
    shard_root:
        Root directory of the shard (contains ``pkg/``, ``config/``, ``scripts/``).
    """

    def __init__(self, shard_root: Path) -> None:
        self.root: Path = shard_root.resolve()
        self._package_map: dict[str, Path] = {}
        self._config_cache: dict[str, ConfigFile] = {}

    @classmethod
    def from_path(cls, shard_root: Path) -> ShardData:
        """Load a shard from a filesystem path.

        Scans ``pkg/`` for packages (reads pkg.cfg for Name), builds
        the package map used by include resolution.
        """
        shard = cls(shard_root)
        shard._scan_packages()
        return shard

    @property
    def package_map(self) -> PackageMap:
        """Package map for include resolution."""
        return DictPackageMap(self._package_map)

    @property
    def scripts_dir(self) -> Path:
        """Path to the shard's scripts/ directory."""
        return self.root / "scripts"

    @property
    def config_dir(self) -> Path:
        """Path to the shard's config/ directory."""
        return self.root / "config"

    @property
    def combat_pkg_dir(self) -> Path | None:
        """Path to the combat package directory, or None."""
        return self._package_map.get("combat")

    @property
    def mainhit_path(self) -> Path | None:
        """Path to mainhit.src, or None if not found."""
        combat = self.combat_pkg_dir
        if combat is None:
            return None
        path = combat / "mainhit.src"
        return path if path.exists() else None

    def get_config(self, name: str) -> ConfigFile | None:
        """Load and cache a config file by name.

        Searches in:
        1. ``config/<name>.cfg``
        2. Package config dirs (e.g., ``pkg/systems/combat/config/<name>.cfg``)
        """
        if name in self._config_cache:
            return self._config_cache[name]

        # Try shard config/ directory
        path = self.config_dir / f"{name}.cfg"
        if path.exists():
            return self._load_config(name, path)

        # Try package config directories
        for pkg_dir in self._package_map.values():
            path = pkg_dir / "config" / f"{name}.cfg"
            if path.exists():
                return self._load_config(name, path)

        logger.warning("Config file not found", name=name)
        return None

    def resolve_config_path(self, pkg_path: str) -> Path | None:
        """Resolve a POL package config path like ``:combat:settings``.

        Returns the filesystem path, or None if not resolvable.
        """
        parts = pkg_path.strip(":").split(":", 1)
        if len(parts) != 2:
            return None

        pkg_name, cfg_name = parts
        pkg_dir = self._package_map.get(pkg_name)
        if pkg_dir is None:
            return None

        path = pkg_dir / "config" / f"{cfg_name}.cfg"
        return path if path.exists() else None

    def parse_combat_scripts(self) -> dict[Path, object]:
        """Parse mainhit.src and all its includes.

        Returns a dict of Path → ParseResult suitable for Executor.
        """
        from omega.parser.parser import parse_with_includes

        mainhit = self.mainhit_path
        if mainhit is None:
            raise FileNotFoundError("mainhit.src not found in combat package")

        return parse_with_includes(mainhit, self.root, self.package_map)

    def _scan_packages(self) -> None:
        """Scan pkg/ directory tree for packages (identified by pkg.cfg)."""
        pkg_root = self.root / "pkg"
        if not pkg_root.exists():
            logger.warning("No pkg/ directory found", shard=str(self.root))
            return

        for pkg_cfg in pkg_root.rglob("pkg.cfg"):
            pkg_dir = pkg_cfg.parent
            name = self._read_pkg_name(pkg_cfg)
            if name:
                self._package_map[name] = pkg_dir
                logger.debug("Found package", name=name, path=str(pkg_dir))

        logger.info("Package scan complete", count=len(self._package_map))

    def _read_pkg_name(self, pkg_cfg: Path) -> str | None:
        """Read the Name field from a pkg.cfg file."""
        try:
            for line in pkg_cfg.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line.lower().startswith("name"):
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        return parts[1].strip()
        except OSError:
            pass
        return None

    def _load_config(self, name: str, path: Path) -> ConfigFile:
        """Parse and cache a config file."""
        cfg = parse_config_file(path)
        self._config_cache[name] = cfg
        return cfg
