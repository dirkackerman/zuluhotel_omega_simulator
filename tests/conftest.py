"""Shared test fixtures — shard data from local fixture copy."""

from pathlib import Path

import pytest

from omega.shard import ShardData

FIXTURE_SHARD_ROOT = Path(__file__).parent / "fixtures" / "shard"


@pytest.fixture(scope="session")
def fixture_shard() -> ShardData:
    """ShardData loaded from local fixture copy (no submodule needed)."""
    return ShardData.from_path(FIXTURE_SHARD_ROOT)


@pytest.fixture(scope="session")
def fixture_parse_results(fixture_shard: ShardData) -> dict:
    """Parsed combat scripts from fixture shard."""
    return fixture_shard.parse_combat_scripts()
