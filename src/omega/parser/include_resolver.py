"""Include and use-declaration resolver for eScript files.

Resolves two forms of include paths:
- ``include "path/file";``      → relative to shard ``scripts/`` directory
- ``include ":pkgname:file";``  → resolved via package map to ``pkg/.../file.inc``
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from omega.logging import get_logger

logger = get_logger("omega.parser")


class PackageMap(Protocol):
    """Protocol for looking up package paths by name."""

    def resolve(self, package_name: str) -> Path | None:
        """Return the filesystem path for a package, or None if unknown."""
        ...

    def names(self) -> list[str]:
        """Return all known package names."""
        ...


class DictPackageMap:
    """Simple dict-backed package map, suitable for testing or hardcoding."""

    def __init__(self, mapping: dict[str, Path]) -> None:
        self._mapping = mapping

    def resolve(self, package_name: str) -> Path | None:
        return self._mapping.get(package_name)

    def names(self) -> list[str]:
        return list(self._mapping.keys())


class IncludeResolver:
    """Resolves eScript include paths to filesystem paths.

    Parameters
    ----------
    shard_root:
        Root directory of the shard (e.g., ``submodules/zuluhotel_omega_2.5/``).
    package_map:
        Maps package names to their filesystem directories.
    """

    def __init__(self, shard_root: Path, package_map: PackageMap) -> None:
        self.shard_root = shard_root
        self.package_map = package_map
        self._resolved: set[Path] = set()

    def resolve(self, include_path: str, from_file: Path | None = None) -> Path:
        """Resolve an include path to an absolute filesystem path.

        Parameters
        ----------
        include_path:
            The path string from an ``include`` declaration.
            May be a relative path (``"include/damages"``) or a
            package path (``":combat:hitscriptinc"``).
        from_file:
            The file containing the include declaration, used for context
            in error messages.

        Returns
        -------
        Path:
            Absolute path to the resolved ``.inc`` file.

        Raises
        ------
        FileNotFoundError:
            If the resolved path does not exist.
        CircularIncludeError:
            If the include would create a circular dependency.
        """
        # Strip quotes if present
        include_path = include_path.strip('"').strip("'")

        if include_path.startswith(":"):
            resolved = self._resolve_package_path(include_path)
        else:
            resolved = self._resolve_relative_path(include_path, from_file)

        resolved = resolved.resolve()

        if resolved in self._resolved:
            # Already included — not an error, just skip
            logger.debug("already included, skipping", path=str(resolved))
            return resolved

        if not resolved.exists():
            raise FileNotFoundError(
                f"Include file not found: {include_path!r} "
                f"(resolved to {resolved})"
                + (f", included from {from_file}" if from_file else "")
            )

        logger.debug("resolved include", raw=include_path, resolved=str(resolved))
        return resolved

    def mark_included(self, path: Path) -> bool:
        """Mark a file as included. Returns False if already included (skip it)."""
        resolved = path.resolve()
        if resolved in self._resolved:
            return False
        self._resolved.add(resolved)
        return True

    def is_included(self, path: Path) -> bool:
        """Check if a file has already been included."""
        return path.resolve() in self._resolved

    def _known_package_names(self) -> list[str]:
        """Return known package names for diagnostic messages."""
        try:
            return self.package_map.names()
        except AttributeError:
            return []

    def _resolve_package_path(self, include_path: str) -> Path:
        """Resolve ``:pkgname:filepath`` format."""
        # Strip leading colon, split on next colon
        parts = include_path.lstrip(":").split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid package include path: {include_path!r}. "
                f"Expected format ':pkgname:filepath'"
            )

        pkg_name, file_path = parts
        pkg_dir = self.package_map.resolve(pkg_name)
        if pkg_dir is None:
            # Check for case mismatch — common on Linux where fs is case-sensitive
            near = [
                n for n in self._known_package_names()
                if n.lower() == pkg_name.lower()
            ]
            hint = ""
            if near:
                hint = (
                    f". Did you mean {near[0]!r}? "
                    f"Package names are case-sensitive on Linux"
                )
            raise FileNotFoundError(
                f"Unknown package: {pkg_name!r} "
                f"(from include path {include_path!r}){hint}"
            )

        # Try with .inc extension first, then without
        candidate = pkg_dir / f"{file_path}.inc"
        if candidate.exists():
            return candidate

        candidate = pkg_dir / file_path
        if candidate.exists():
            return candidate

        # Also check include/ subdirectory
        candidate = pkg_dir / "include" / f"{file_path}.inc"
        if candidate.exists():
            return candidate

        candidate = pkg_dir / "include" / file_path
        if candidate.exists():
            return candidate

        # Return the most likely path for error message
        return pkg_dir / "include" / f"{file_path}.inc"

    def _resolve_relative_path(self, include_path: str, from_file: Path | None) -> Path:
        """Resolve relative include path.

        Tries in order:
        1. Relative to the shard's ``scripts/`` directory (with .inc)
        2. Relative to the shard's ``scripts/`` directory (without .inc)
        3. Relative to the shard root (with .inc)
        4. Relative to the shard root (without .inc)
        """
        scripts_dir = self.shard_root / "scripts"

        search_paths = [
            scripts_dir / f"{include_path}.inc",
            scripts_dir / include_path,
            self.shard_root / f"{include_path}.inc",
            self.shard_root / include_path,
        ]

        for candidate in search_paths:
            if candidate.exists():
                return candidate

        # Return first candidate for error message
        return search_paths[0]
