"""eScript data types for the interpreter.

Maps eScript's dynamic type system to Python:
- Scalars: int, float, str used directly
- UNINIT: sentinel for uninitialized variables
- EArray: 1-based indexed array with .append()
- EStruct: named-field container with attribute access
- EDict: dictionary with .Exists() method
- EError: error object with .errortext
- Game objects (Mobile, Weapon, Armor) pass through as-is
"""

from __future__ import annotations

from typing import Any


class _UninitType:
    """Sentinel for uninitialized eScript variables."""

    _instance = None

    def __new__(cls) -> _UninitType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "UNINIT"

    def __eq__(self, other: object) -> bool:
        if other is None or isinstance(other, _UninitType):
            return True
        return NotImplemented

    def __hash__(self) -> int:
        return hash(None)


UNINIT = _UninitType()


class EArray:
    """eScript array — 1-based indexing wrapping a Python list.

    In eScript, arrays are 1-indexed:
      var arr := {10, 20, 30};
      arr[1]  // => 10
      arr[3]  // => 30
    """

    def __init__(self, items: list[Any] | None = None) -> None:
        self._items: list[Any] = list(items) if items else []

    def get(self, index: int) -> Any:
        """Get element at 1-based index."""
        if index < 1 or index > len(self._items):
            return UNINIT
        return self._items[index - 1]

    def set(self, index: int, value: Any) -> None:
        """Set element at 1-based index, extending if needed."""
        if index < 1:
            return
        while len(self._items) < index:
            self._items.append(UNINIT)
        self._items[index - 1] = value

    def append(self, value: Any) -> None:
        """Append element to end of array."""
        self._items.append(value)

    def shrink(self, new_size: int) -> None:
        """Shrink array to new_size elements."""
        if new_size < len(self._items):
            self._items = self._items[:new_size]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __bool__(self) -> bool:
        return len(self._items) > 0

    def __repr__(self) -> str:
        return f"EArray({self._items!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EArray):
            return self._items == other._items
        if isinstance(other, list):
            return self._items == other
        return NotImplemented

    def __contains__(self, item: Any) -> bool:
        return item in self._items

    @property
    def raw(self) -> list[Any]:
        """Access the underlying Python list."""
        return self._items


class EStruct:
    """eScript struct — named-field container with attribute-style access.

    In eScript:
      var s := struct{ x := 10, y := 20 };
      s.x  // => 10
    """

    def __init__(self, fields: dict[str, Any] | None = None) -> None:
        self._fields: dict[str, Any] = {}
        if fields:
            for k, v in fields.items():
                self._fields[k.lower()] = v
        # Store original-case names for display
        self._original_names: dict[str, str] = {}
        if fields:
            for k in fields:
                self._original_names[k.lower()] = k

    def get_member(self, name: str) -> Any:
        """Get field by name (case-insensitive)."""
        return self._fields.get(name.lower(), UNINIT)

    def set_member(self, name: str, value: Any) -> None:
        """Set field by name (case-insensitive)."""
        key = name.lower()
        self._fields[key] = value
        if key not in self._original_names:
            self._original_names[key] = name

    def has_member(self, name: str) -> bool:
        """Check if field exists (case-insensitive)."""
        return name.lower() in self._fields

    def keys(self) -> list[str]:
        """Return field names in original case."""
        return [self._original_names.get(k, k) for k in self._fields]

    def __repr__(self) -> str:
        display = {self._original_names.get(k, k): v for k, v in self._fields.items()}
        return f"EStruct({display!r})"

    def __bool__(self) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EStruct):
            return self._fields == other._fields
        return NotImplemented


class EDict:
    """eScript dictionary with .Exists() and [] access.

    In eScript:
      var d := dictionary;
      d[key] := value;
      d.Exists(key)  // => 0 or 1
    """

    def __init__(self) -> None:
        self._data: dict[Any, Any] = {}

    def get(self, key: Any) -> Any:
        """Get value by key."""
        return self._data.get(key, UNINIT)

    def set(self, key: Any, value: Any) -> None:
        """Set value by key."""
        self._data[key] = value

    def exists(self, key: Any) -> int:
        """Check if key exists. Returns 1/0 (POL convention)."""
        return 1 if key in self._data else 0

    def erase(self, key: Any) -> None:
        """Remove key if present."""
        self._data.pop(key, None)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data.keys())

    def __contains__(self, key: Any) -> bool:
        return key in self._data

    def __bool__(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"EDict({self._data!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EDict):
            return self._data == other._data
        return NotImplemented

    @property
    def raw(self) -> dict[Any, Any]:
        """Access the underlying Python dict."""
        return self._data


class EError:
    """eScript error object.

    In eScript:
      var e := error{ errortext := "something went wrong" };
      e.errortext  // => "something went wrong"
    """

    def __init__(self, fields: dict[str, Any] | None = None) -> None:
        self._fields: dict[str, Any] = {}
        if fields:
            for k, v in fields.items():
                self._fields[k.lower()] = v

    @property
    def errortext(self) -> str:
        return str(self._fields.get("errortext", ""))

    def get_member(self, name: str) -> Any:
        """Get field by name (case-insensitive)."""
        return self._fields.get(name.lower(), UNINIT)

    def set_member(self, name: str, value: Any) -> None:
        """Set field by name (case-insensitive)."""
        self._fields[name.lower()] = value

    def __bool__(self) -> bool:
        return False  # errors are falsy in POL

    def __repr__(self) -> str:
        return f"EError({self._fields!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EError):
            return self._fields == other._fields
        return NotImplemented


def is_truthy(value: Any) -> bool:
    """Evaluate eScript truthiness.

    Falsy: 0, 0.0, "", None, UNINIT, empty EArray, EError
    Truthy: everything else (including empty EDict, EStruct)
    """
    if value is None or value is UNINIT:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    if isinstance(value, EArray):
        return len(value) > 0
    if isinstance(value, EError):
        return False
    # EStruct, EDict, game objects — truthy
    return True


def pol_typeof(value: Any) -> str:
    """Return the POL TypeOf() string for a value."""
    if value is None or value is UNINIT:
        return "Uninit"
    if isinstance(value, bool):
        return "Integer"
    if isinstance(value, int):
        return "Integer"
    if isinstance(value, float):
        return "Double"
    if isinstance(value, str):
        return "String"
    if isinstance(value, (EArray, list)):
        return "Array"
    if isinstance(value, (EDict, dict)):
        return "Dictionary"
    if isinstance(value, EStruct):
        return "Struct"
    if isinstance(value, EError):
        return "Error"
    # Game objects
    from omega.model.mobile import Mobile
    from omega.model.items import Weapon, Armor

    if isinstance(value, Mobile):
        return "MobileRef"
    if isinstance(value, (Weapon, Armor)):
        return "ItemRef"
    return "Unknown"
