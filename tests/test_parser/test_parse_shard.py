"""Integration tests: parse actual shard combat scripts."""

import re
from pathlib import Path

import pytest

from omega.parser import parse_file, parse_with_includes
from tests.conftest import FIXTURE_SHARD_ROOT as SHARD_ROOT


def _build_package_map() -> dict[str, Path]:
    """Scan shard for pkg.cfg files and build name -> path mapping."""
    pkg_map: dict[str, Path] = {}
    for pkg_cfg in SHARD_ROOT.rglob("pkg.cfg"):
        text = pkg_cfg.read_text(errors="replace")
        m = re.search(r"Name\s+(\S+)", text, re.IGNORECASE)
        if m:
            pkg_map[m.group(1)] = pkg_cfg.parent
    return pkg_map


@pytest.fixture(scope="module")
def package_map() -> dict[str, Path]:
    return _build_package_map()


class TestSingleFileParse:
    """Parse individual shard files without include resolution."""

    def test_mainhit_src(self):
        path = SHARD_ROOT / "pkg/systems/combat/mainhit.src"
        result = parse_file(path)
        assert result.success, f"Errors: {result.errors}"

    def test_hitscriptinc(self):
        path = SHARD_ROOT / "pkg/systems/combat/include/hitscriptinc.inc"
        result = parse_file(path)
        assert result.success, f"Errors: {result.errors}"

    def test_damages_inc(self):
        path = SHARD_ROOT / "scripts/include/damages.inc"
        result = parse_file(path)
        assert result.success, f"Errors: {result.errors}"

    def test_classes_inc(self):
        path = SHARD_ROOT / "scripts/include/classes.inc"
        result = parse_file(path)
        assert result.success, f"Errors: {result.errors}"

    def test_attributes_inc(self):
        path = SHARD_ROOT / "scripts/include/attributes.inc"
        result = parse_file(path)
        assert result.success, f"Errors: {result.errors}"

    def test_client_inc(self):
        path = SHARD_ROOT / "scripts/include/client.inc"
        result = parse_file(path)
        assert result.success, f"Errors: {result.errors}"


class TestParseWithIncludes:
    """Parse entry file with full include resolution."""

    def test_mainhit_full_chain(self, package_map: dict[str, Path]):
        entry = SHARD_ROOT / "pkg/systems/combat/mainhit.src"
        results = parse_with_includes(entry, SHARD_ROOT, package_map)

        # Should parse many files (mainhit + all includes)
        assert len(results) > 10, f"Only parsed {len(results)} files"

        # All should parse successfully
        for path, result in results.items():
            assert result.success, (
                f"Parse errors in {path.relative_to(SHARD_ROOT)}: {result.errors}"
            )

    def test_includes_damages(self, package_map: dict[str, Path]):
        """damages.inc should be in the include chain."""
        entry = SHARD_ROOT / "pkg/systems/combat/mainhit.src"
        results = parse_with_includes(entry, SHARD_ROOT, package_map)

        damages_path = (SHARD_ROOT / "scripts/include/damages.inc").resolve()
        assert damages_path in results, "damages.inc not found in include chain"

    def test_includes_classes(self, package_map: dict[str, Path]):
        """classes.inc should be in the include chain."""
        entry = SHARD_ROOT / "pkg/systems/combat/mainhit.src"
        results = parse_with_includes(entry, SHARD_ROOT, package_map)

        classes_path = (SHARD_ROOT / "scripts/include/classes.inc").resolve()
        assert classes_path in results, "classes.inc not found in include chain"

    def test_includes_hitscriptinc(self, package_map: dict[str, Path]):
        """hitscriptinc.inc should be in the include chain via package resolution."""
        entry = SHARD_ROOT / "pkg/systems/combat/mainhit.src"
        results = parse_with_includes(entry, SHARD_ROOT, package_map)

        hitscript_path = (
            SHARD_ROOT / "pkg/systems/combat/include/hitscriptinc.inc"
        ).resolve()
        assert hitscript_path in results, "hitscriptinc.inc not found in include chain"
