"""Tests for ShardData loader."""

from pathlib import Path

import pytest

from omega.shard import ShardData

SHARD_ROOT = Path(__file__).resolve().parents[2] / "submodules" / "zuluhotel_omega_2.5"

# Skip if submodule missing; mark as shard-dependent
pytestmark = [
    pytest.mark.skipif(not SHARD_ROOT.exists(), reason="Shard submodule not available"),
    pytest.mark.shard,
]


class TestShardLoading:
    def test_from_path(self):
        shard = ShardData.from_path(SHARD_ROOT)
        assert shard.root == SHARD_ROOT.resolve()

    def test_package_map_has_combat(self):
        shard = ShardData.from_path(SHARD_ROOT)
        assert shard.combat_pkg_dir is not None
        assert (shard.combat_pkg_dir / "mainhit.src").exists()

    def test_mainhit_path(self):
        shard = ShardData.from_path(SHARD_ROOT)
        assert shard.mainhit_path is not None
        assert shard.mainhit_path.name == "mainhit.src"

    def test_resolve_config_path(self):
        shard = ShardData.from_path(SHARD_ROOT)
        path = shard.resolve_config_path(":combat:settings")
        assert path is not None
        assert path.exists()
        assert path.name == "settings.cfg"

    def test_resolve_config_path_unknown(self):
        shard = ShardData.from_path(SHARD_ROOT)
        path = shard.resolve_config_path(":nonexistent:foo")
        assert path is None

    def test_get_config_npcdesc(self):
        shard = ShardData.from_path(SHARD_ROOT)
        cfg = shard.get_config("npcdesc")
        assert cfg is not None

    def test_scripts_dir(self):
        shard = ShardData.from_path(SHARD_ROOT)
        assert shard.scripts_dir.name == "scripts"


class TestCombatScriptParsing:
    def test_parse_combat_scripts(self):
        shard = ShardData.from_path(SHARD_ROOT)
        trees = shard.parse_combat_scripts()
        assert len(trees) > 0
        # Should include mainhit.src and at least hitscriptinc.inc
        filenames = {p.name for p in trees.keys()}
        assert "mainhit.src" in filenames
        assert "hitscriptinc.inc" in filenames

    def test_parse_includes_transitive(self):
        shard = ShardData.from_path(SHARD_ROOT)
        trees = shard.parse_combat_scripts()
        filenames = {p.name for p in trees.keys()}
        # hitscriptinc includes classes.inc and damages.inc
        assert "classes.inc" in filenames
        assert "damages.inc" in filenames
