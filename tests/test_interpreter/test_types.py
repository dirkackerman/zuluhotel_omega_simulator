"""Tests for eScript data types."""

from omega.interpreter.types import (
    UNINIT,
    EArray,
    EDict,
    EError,
    EStruct,
    is_truthy,
    pol_typeof,
)


class TestUninit:
    def test_singleton(self):
        from omega.interpreter.types import _UninitType

        assert _UninitType() is _UninitType()

    def test_falsy(self):
        assert not UNINIT
        assert is_truthy(UNINIT) is False

    def test_eq_none(self):
        assert UNINIT == None  # noqa: E711
        assert UNINIT == UNINIT

    def test_repr(self):
        assert repr(UNINIT) == "UNINIT"


class TestEArray:
    def test_empty(self):
        arr = EArray()
        assert len(arr) == 0
        assert not arr

    def test_from_items(self):
        arr = EArray([10, 20, 30])
        assert len(arr) == 3
        assert arr

    def test_one_based_get(self):
        arr = EArray([10, 20, 30])
        assert arr.get(1) == 10
        assert arr.get(2) == 20
        assert arr.get(3) == 30

    def test_out_of_bounds(self):
        arr = EArray([10])
        assert arr.get(0) is UNINIT
        assert arr.get(5) is UNINIT

    def test_one_based_set(self):
        arr = EArray([0, 0])
        arr.set(1, 99)
        assert arr.get(1) == 99

    def test_set_extends(self):
        arr = EArray()
        arr.set(3, 42)
        assert len(arr) == 3
        assert arr.get(3) == 42
        assert arr.get(1) is UNINIT

    def test_append(self):
        arr = EArray()
        arr.append(1)
        arr.append(2)
        assert len(arr) == 2
        assert arr.get(1) == 1
        assert arr.get(2) == 2

    def test_iterate(self):
        arr = EArray([10, 20, 30])
        assert list(arr) == [10, 20, 30]

    def test_contains(self):
        arr = EArray([1, 2, 3])
        assert 2 in arr
        assert 5 not in arr

    def test_shrink(self):
        arr = EArray([1, 2, 3, 4, 5])
        arr.shrink(3)
        assert len(arr) == 3
        assert arr.get(3) == 3


class TestEStruct:
    def test_create_with_fields(self):
        s = EStruct({"x": 10, "y": 20})
        assert s.get_member("x") == 10
        assert s.get_member("y") == 20

    def test_case_insensitive(self):
        s = EStruct({"Name": "test"})
        assert s.get_member("name") == "test"
        assert s.get_member("NAME") == "test"

    def test_set_member(self):
        s = EStruct()
        s.set_member("value", 42)
        assert s.get_member("value") == 42

    def test_has_member(self):
        s = EStruct({"x": 1})
        assert s.has_member("x")
        assert not s.has_member("y")

    def test_truthy(self):
        assert is_truthy(EStruct())


class TestEDict:
    def test_empty(self):
        d = EDict()
        assert len(d) == 0

    def test_set_get(self):
        d = EDict()
        d.set("key", "value")
        assert d.get("key") == "value"

    def test_exists(self):
        d = EDict()
        d.set("a", 1)
        assert d.exists("a") == 1
        assert d.exists("b") == 0

    def test_erase(self):
        d = EDict()
        d.set("k", 1)
        d.erase("k")
        assert d.exists("k") == 0

    def test_iterate_keys(self):
        d = EDict()
        d.set("a", 1)
        d.set("b", 2)
        assert sorted(d) == ["a", "b"]

    def test_contains(self):
        d = EDict()
        d.set(42, "val")
        assert 42 in d
        assert 99 not in d

    def test_truthy(self):
        assert is_truthy(EDict())


class TestEError:
    def test_errortext(self):
        e = EError({"errortext": "something failed"})
        assert e.errortext == "something failed"

    def test_falsy(self):
        assert not EError()
        assert is_truthy(EError()) is False

    def test_get_set_member(self):
        e = EError()
        e.set_member("errortext", "bad")
        assert e.get_member("errortext") == "bad"


class TestTruthiness:
    def test_numbers(self):
        assert is_truthy(0) is False
        assert is_truthy(0.0) is False
        assert is_truthy(1) is True
        assert is_truthy(-1) is True
        assert is_truthy(0.5) is True

    def test_strings(self):
        assert is_truthy("") is False
        assert is_truthy("hello") is True

    def test_none(self):
        assert is_truthy(None) is False

    def test_collections(self):
        assert is_truthy(EArray()) is False
        assert is_truthy(EArray([1])) is True


class TestPolTypeof:
    def test_basic_types(self):
        assert pol_typeof(42) == "Integer"
        assert pol_typeof(3.14) == "Double"
        assert pol_typeof("hi") == "String"
        assert pol_typeof(None) == "Uninit"
        assert pol_typeof(UNINIT) == "Uninit"

    def test_collection_types(self):
        assert pol_typeof(EArray()) == "Array"
        assert pol_typeof(EDict()) == "Dictionary"
        assert pol_typeof(EStruct()) == "Struct"
        assert pol_typeof(EError()) == "Error"
        assert pol_typeof([1, 2]) == "Array"
        assert pol_typeof({"a": 1}) == "Dictionary"

    def test_game_objects(self):
        from omega.model.mobile import Mobile
        from omega.model.items import Weapon, Armor

        assert pol_typeof(Mobile()) == "MobileRef"
        assert pol_typeof(Weapon(name="S")) == "ItemRef"
        assert pol_typeof(Armor(name="A", ar=5)) == "ItemRef"
