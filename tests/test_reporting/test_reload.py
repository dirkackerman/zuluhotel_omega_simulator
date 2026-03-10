"""Tests for the hot-reload utility.

These tests mock ``importlib.reload`` to avoid actually reloading modules
mid-test-suite, which would corrupt singleton state (e.g., the runtime
registry) and break other tests.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

from omega.reporting.reload import _SKIP_RELOAD, reload_omega


@patch("omega.reporting.reload.importlib.reload")
class TestReloadOmega:
    def test_returns_list_of_reloaded_modules(self, mock_reload):
        result = reload_omega()
        assert isinstance(result, list)
        assert all(isinstance(name, str) for name in result)

    def test_reloads_omega_modules(self, mock_reload):
        result = reload_omega()
        assert any(name.startswith("omega") for name in result)

    def test_does_not_include_non_omega(self, mock_reload):
        result = reload_omega()
        assert all(
            name == "omega" or name.startswith("omega.")
            for name in result
        )

    def test_sorted_parent_first(self, mock_reload):
        result = reload_omega()
        for i in range(len(result) - 1):
            assert result[i] <= result[i + 1]

    def test_skips_registry(self, mock_reload):
        """The runtime registry holds singleton state and must not be reloaded."""
        result = reload_omega()
        assert "omega.runtime.registry" not in result

    def test_calls_importlib_reload(self, mock_reload):
        """Verify reload is actually called on each module."""
        result = reload_omega()
        assert mock_reload.call_count == len(result)
        reloaded_modules = [call.args[0] for call in mock_reload.call_args_list]
        for mod in reloaded_modules:
            assert mod.__name__.startswith("omega")

    def test_handles_reload_failure(self, mock_reload):
        """Modules that fail to reload are silently skipped."""
        mock_reload.side_effect = ImportError("boom")
        result = reload_omega()
        assert result == []
