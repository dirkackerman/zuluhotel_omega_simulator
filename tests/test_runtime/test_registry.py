"""Tests for the POL built-in function registry."""

import omega.runtime  # noqa: F401 — triggers registration
from omega.runtime.registry import call_builtin, is_registered, list_registered


class TestRegistration:
    def test_cint_is_registered(self):
        assert is_registered("", "CInt")

    def test_cint_via_module(self):
        assert is_registered("util", "CInt")

    def test_get_obj_property_registered(self):
        assert is_registered("uo", "GetObjProperty")

    def test_apply_raw_damage_registered(self):
        assert is_registered("uo", "ApplyRawDamage")

    def test_case_insensitive(self):
        assert is_registered("", "cint")
        assert is_registered("UO", "GETOBJPROPERTY")

    def test_many_stubs_registered(self):
        registered = list_registered()
        # We expect at least 50 unique registrations
        assert len(registered) >= 50


class TestDispatch:
    def test_call_cint(self):
        result = call_builtin("", "CInt", ["42"])
        assert result == 42

    def test_call_cint_via_module(self):
        result = call_builtin("util", "CInt", ["42"])
        assert result == 42

    def test_call_case_insensitive(self):
        result = call_builtin("", "cint", ["10"])
        assert result == 10

    def test_unknown_returns_none(self):
        result = call_builtin("uo", "TotallyFakeFunction", [])
        assert result is None

    def test_bare_fallback(self):
        """Calling with module should fall back to bare registration."""
        result = call_builtin("somemodule", "CInt", ["5"])
        assert result == 5
