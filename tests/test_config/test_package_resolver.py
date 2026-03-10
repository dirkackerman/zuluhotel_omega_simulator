"""Tests for the package path resolver."""

from pathlib import Path

import pytest

from omega.config.package_resolver import PackageResolver
from tests.conftest import FIXTURE_SHARD_ROOT as SHARD_ROOT


@pytest.fixture(scope="module")
def resolver() -> PackageResolver:
    return PackageResolver(SHARD_ROOT)


class TestPackageDiscovery:
    def test_finds_many_packages(self, resolver: PackageResolver):
        assert len(resolver) > 100

    def test_combat_package_exists(self, resolver: PackageResolver):
        assert "combat" in resolver

    def test_karmafame_package_exists(self, resolver: PackageResolver):
        assert "karmafame" in resolver

    def test_spells_package_exists(self, resolver: PackageResolver):
        assert "spells" in resolver


class TestPackageResolve:
    def test_resolve_combat(self, resolver: PackageResolver):
        path = resolver.resolve("combat")
        assert path is not None
        assert path.exists()
        assert "combat" in str(path)

    def test_resolve_case_insensitive(self, resolver: PackageResolver):
        path1 = resolver.resolve("combat")
        path2 = resolver.resolve("Combat")
        assert path1 == path2

    def test_resolve_unknown_returns_none(self, resolver: PackageResolver):
        assert resolver.resolve("nonexistent_xyz") is None


class TestConfigPathResolve:
    def test_resolve_combat_settings(self, resolver: PackageResolver):
        path = resolver.resolve_config_path(":combat:settings")
        assert path is not None
        assert path.exists()
        assert path.name == "settings.cfg"

    def test_resolve_combat_hitscriptdesc(self, resolver: PackageResolver):
        path = resolver.resolve_config_path(":combat:hitscriptdesc")
        assert path is not None
        assert path.exists()

    def test_wildcard_itemdesc(self, resolver: PackageResolver):
        path = resolver.resolve_config_path(":*:itemdesc")
        assert path is not None
        assert path.exists()
        assert "itemdesc" in path.name

    def test_unknown_package_config(self, resolver: PackageResolver):
        path = resolver.resolve_config_path(":nonexistent_xyz:settings")
        assert path is None


class TestPackageMapProtocol:
    """PackageResolver implements the PackageMap protocol from M2."""

    def test_resolve_method_exists(self, resolver: PackageResolver):
        # The protocol requires a resolve(package_name) -> Path | None method
        result = resolver.resolve("combat")
        assert isinstance(result, Path)
