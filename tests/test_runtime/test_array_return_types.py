"""Priority 2 — Array return type conformance tests.

Verifies that all array-returning stubs return EArray (not Python list),
so eScript code can call .size(), .append(), and iterate correctly.
Also verifies 1-based indexing on returned arrays.
"""

import omega.runtime  # noqa: F401
from omega.interpreter.types import EArray
from omega.model.items import Weapon
from omega.model.mobile import Mobile
from omega.runtime.context import SimulationContext, set_context
from omega.runtime.registry import call_builtin


class TestSplitWordsReturnType:
    def test_returns_earray(self):
        result = call_builtin("", "SplitWords", ["hello world"])
        assert isinstance(result, EArray), f"Expected EArray, got {type(result).__name__}"

    def test_indexing_one_based(self):
        result = call_builtin("", "SplitWords", ["a b c"])
        assert result.get(1) == "a"
        assert result.get(2) == "b"
        assert result.get(3) == "c"

    def test_size_method(self):
        result = call_builtin("", "SplitWords", ["a b c"])
        assert len(result) == 3

    def test_iteration(self):
        result = call_builtin("", "SplitWords", ["x y z"])
        assert list(result) == ["x", "y", "z"]

    def test_with_delimiter(self):
        result = call_builtin("", "SplitWords", ["a,b,c", ","])
        assert isinstance(result, EArray)
        assert result.get(1) == "a"
        assert len(result) == 3


class TestListEquippedItemsReturnType:
    def test_returns_earray(self):
        m = Mobile(name="Test")
        w = Weapon(name="Sword")
        m.equip(1, w)
        result = call_builtin("uo", "ListEquippedItems", [m])
        assert isinstance(result, EArray), f"Expected EArray, got {type(result).__name__}"

    def test_empty_returns_earray(self):
        m = Mobile(name="Naked")
        result = call_builtin("uo", "ListEquippedItems", [m])
        assert isinstance(result, EArray)
        assert len(result) == 0


class TestGetConfigStringArrayReturnType:
    def test_returns_earray(self):
        result = call_builtin("", "GetConfigStringArray", [None, "key"])
        assert isinstance(result, EArray), f"Expected EArray, got {type(result).__name__}"


class TestGetConfigStringKeysReturnType:
    def test_returns_earray_on_none(self):
        result = call_builtin("", "GetConfigStringKeys", [None])
        assert isinstance(result, EArray), f"Expected EArray, got {type(result).__name__}"


class TestListHostilesReturnType:
    def test_returns_earray(self):
        m = Mobile(name="Test")
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "ListHostiles", [m, 10, 0])
        assert isinstance(result, EArray), f"Expected EArray, got {type(result).__name__}"


class TestListMobilesNearLocationReturnType:
    def test_returns_earray(self):
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "ListMobilesNearLocationEx", [100, 100, 0, 10, 0])
        assert isinstance(result, EArray), f"Expected EArray, got {type(result).__name__}"

    def test_with_defenders_returns_earray(self):
        m = Mobile(name="Target")
        ctx = SimulationContext()
        ctx.defenders = [m]
        set_context(ctx)
        result = call_builtin("uo", "ListMobilesNearLocationEx", [100, 100, 0, 10, 0])
        assert isinstance(result, EArray)
        assert result.get(1) is m

    def test_list_mobiles_near_location_returns_earray(self):
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "ListMobilesNearLocation", [100, 100, 0, 10])
        assert isinstance(result, EArray), f"Expected EArray, got {type(result).__name__}"


class TestListItemsReturnType:
    """These already return EArray — verify they stay correct."""

    def test_list_items_near_location(self):
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "ListItemsNearLocation", [100, 100, 0, 10])
        assert isinstance(result, EArray)

    def test_list_items_near_location_of_type(self):
        ctx = SimulationContext()
        set_context(ctx)
        result = call_builtin("uo", "ListItemsNearLocationOfType", [100, 100, 0, 10, 0x1234])
        assert isinstance(result, EArray)
