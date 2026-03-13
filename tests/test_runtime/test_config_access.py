"""Priority 6 — Config access tests.

Tests RuntimeConfigElement/RuntimeConfigFile behavior: property access,
type coercion, case sensitivity, iteration, and CProp edge cases.
"""

import tempfile
import os
from pathlib import Path

import omega.runtime  # noqa: F401
from omega.config.accessor import RuntimeConfigElement, RuntimeConfigFile
from omega.config.cfg_parser import parse_config_file
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.registry import call_builtin


def _make_config(content: str) -> Path:
    """Write content to a temp .cfg file and return its Path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False)
    f.write(content)
    f.flush()
    f.close()
    return Path(f.name)


class TestRuntimeConfigElementAccess:
    def test_property_returns_string(self):
        """elem.AR for 'AR 50' returns '50' (string), not 50 (int)."""
        path = _make_config("Weapon 0x1234\n{\n    AR 50\n}\n")
        try:
            cfg = parse_config_file(path)
            elem = cfg["0x1234"]
            assert elem is not None
            rce = RuntimeConfigElement(elem)
            val = rce.AR
            assert val == "50"
            assert isinstance(val, str)
        finally:
            os.unlink(path)

    def test_missing_property_returns_none(self):
        """elem.MissingProp returns None."""
        path = _make_config("Weapon 0x1234\n{\n    AR 50\n}\n")
        try:
            cfg = parse_config_file(path)
            elem = cfg["0x1234"]
            rce = RuntimeConfigElement(elem)
            val = rce.MissingProp
            assert val is None
        finally:
            os.unlink(path)

    def test_bracket_access(self):
        """elem['AR'] returns property value."""
        path = _make_config("Weapon 0x1234\n{\n    AR 50\n}\n")
        try:
            cfg = parse_config_file(path)
            elem = cfg["0x1234"]
            rce = RuntimeConfigElement(elem)
            assert rce["AR"] == "50"
        finally:
            os.unlink(path)

    def test_repr(self):
        path = _make_config("Weapon 0x1234\n{\n    AR 50\n}\n")
        try:
            cfg = parse_config_file(path)
            elem = cfg["0x1234"]
            rce = RuntimeConfigElement(elem)
            r = repr(rce)
            assert "RuntimeConfigElement" in r
            assert "Weapon" in r
        finally:
            os.unlink(path)


class TestRuntimeConfigFileLookup:
    def test_bracket_lookup_returns_element(self):
        path = _make_config("Weapon 0x1234\n{\n    AR 50\n}\n")
        try:
            rcf = RuntimeConfigFile.from_path(path)
            elem = rcf["0x1234"]
            assert isinstance(elem, RuntimeConfigElement)
        finally:
            os.unlink(path)

    def test_contains(self):
        path = _make_config("Weapon 0x1234\n{\n    AR 50\n}\n")
        try:
            rcf = RuntimeConfigFile.from_path(path)
            assert "0x1234" in rcf
        finally:
            os.unlink(path)

    def test_repr(self):
        path = _make_config("Weapon 0x1234\n{\n    AR 50\n}\n")
        try:
            rcf = RuntimeConfigFile.from_path(path)
            assert "RuntimeConfigFile" in repr(rcf)
        finally:
            os.unlink(path)


class TestConfigCPropAccess:
    def test_cprop_with_int_prefix(self):
        """CProp TestProp i42 → returns 42 (integer)."""
        path = _make_config("NpcTemplate test\n{\n    CProp TestProp i42\n}\n")
        try:
            cfg = parse_config_file(path)
            elem = cfg["test"]
            assert elem is not None
            rce = RuntimeConfigElement(elem)
            val = rce.TestProp
            assert val == 42
        finally:
            os.unlink(path)

    def test_cprop_with_string_prefix(self):
        """CProp TestProp shello → returns 'hello' (string)."""
        path = _make_config("NpcTemplate test\n{\n    CProp TestProp shello\n}\n")
        try:
            cfg = parse_config_file(path)
            elem = cfg["test"]
            assert elem is not None
            rce = RuntimeConfigElement(elem)
            val = rce.TestProp
            assert val == "hello"
        finally:
            os.unlink(path)


class TestReadConfigFileStub:
    def test_none_returns_none(self):
        result = call_builtin("", "ReadConfigFile", [None])
        assert result is None

    def test_missing_path_returns_none(self):
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("", "ReadConfigFile", ["/nonexistent/path.cfg"])
        assert result is None

    def test_valid_path_returns_runtime_config_file(self):
        path = _make_config("Weapon 0x1234\n{\n    AR 50\n}\n")
        try:
            ctx = SimulationContext()
            set_context(ctx)
            result = call_builtin("", "ReadConfigFile", [path])
            assert isinstance(result, RuntimeConfigFile)
        finally:
            os.unlink(path)


class TestGetConfigIntStub:
    def test_none_elem_returns_zero(self):
        assert call_builtin("", "GetConfigInt", [None, "key"]) == 0

    def test_none_key_returns_zero(self):
        assert call_builtin("", "GetConfigInt", [{"key": 42}, None]) == 0


class TestGetConfigStringStub:
    def test_none_elem_returns_empty(self):
        assert call_builtin("", "GetConfigString", [None, "key"]) == ""

    def test_none_key_returns_empty(self):
        assert call_builtin("", "GetConfigString", [{"key": "val"}, None]) == ""
