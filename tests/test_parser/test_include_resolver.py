"""Tests for the include path resolver."""

from pathlib import Path

import pytest

from omega.parser.include_resolver import DictPackageMap, IncludeResolver
from tests.conftest import FIXTURE_SHARD_ROOT as SHARD_ROOT


def _make_resolver(pkg_map: dict[str, str] | None = None) -> IncludeResolver:
    mapping = {}
    if pkg_map:
        mapping = {k: SHARD_ROOT / v for k, v in pkg_map.items()}
    return IncludeResolver(SHARD_ROOT, DictPackageMap(mapping))


@pytest.fixture
def combat_resolver() -> IncludeResolver:
    return _make_resolver({"combat": "pkg/systems/combat"})


class TestRelativePaths:
    def test_resolve_include_with_inc_extension(self):
        resolver = _make_resolver()
        path = resolver.resolve("include/damages")
        assert path.name == "damages.inc"
        assert path.exists()

    def test_resolve_include_attributes(self):
        resolver = _make_resolver()
        path = resolver.resolve("include/attributes")
        assert path.name == "attributes.inc"
        assert path.exists()

    def test_resolve_include_classes(self):
        resolver = _make_resolver()
        path = resolver.resolve("include/classes")
        assert path.name == "classes.inc"
        assert path.exists()

    def test_nonexistent_raises(self):
        resolver = _make_resolver()
        with pytest.raises(FileNotFoundError):
            resolver.resolve("include/this_does_not_exist_xyz")


class TestPackagePaths:
    def test_resolve_combat_hitscriptinc(self, combat_resolver: IncludeResolver):
        path = combat_resolver.resolve(":combat:hitscriptinc")
        assert path.name == "hitscriptinc.inc"
        assert "combat" in str(path)
        assert path.exists()

    def test_unknown_package_raises(self):
        resolver = _make_resolver()
        with pytest.raises(FileNotFoundError, match="Unknown package"):
            resolver.resolve(":nonexistent_pkg:somefile")

    def test_invalid_format_raises(self):
        resolver = _make_resolver()
        with pytest.raises(ValueError, match="Invalid package include path"):
            resolver.resolve(":badformat")


class TestDeduplication:
    def test_mark_included_returns_true_first_time(self):
        resolver = _make_resolver()
        path = SHARD_ROOT / "scripts/include/damages.inc"
        assert resolver.mark_included(path) is True

    def test_mark_included_returns_false_second_time(self):
        resolver = _make_resolver()
        path = SHARD_ROOT / "scripts/include/damages.inc"
        resolver.mark_included(path)
        assert resolver.mark_included(path) is False

    def test_is_included(self):
        resolver = _make_resolver()
        path = SHARD_ROOT / "scripts/include/damages.inc"
        assert resolver.is_included(path) is False
        resolver.mark_included(path)
        assert resolver.is_included(path) is True
