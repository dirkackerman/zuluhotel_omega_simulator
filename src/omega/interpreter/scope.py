"""Variable scope management for the eScript interpreter.

Provides lexical scoping with:
- Global scope (program-level variables and constants)
- Function-local scope (pushed/popped on function entry/exit)
- ByRef parameter binding (alias to caller's variable)
- Case-insensitive variable name lookup
"""

from __future__ import annotations

from typing import Any

from omega.interpreter.types import UNINIT


class ByRef:
    """Reference to a variable in another scope.

    When a function parameter is declared ``byref``, assignments to it
    propagate back to the caller's variable.
    """

    def __init__(self, scope: Scope, name: str) -> None:
        self.scope = scope
        self.name = name.lower()

    def get(self) -> Any:
        return self.scope.get_local(self.name)

    def set(self, value: Any) -> None:
        self.scope.set_local(self.name, value)

    def __repr__(self) -> str:
        return f"ByRef({self.name!r})"


class Scope:
    """A single variable scope (global or function-local).

    Variable names are stored and looked up case-insensitively.
    """

    def __init__(self, parent: Scope | None = None) -> None:
        self.parent = parent
        self._vars: dict[str, Any] = {}
        self._consts: set[str] = set()

    def define(self, name: str, value: Any = UNINIT, *, const: bool = False) -> None:
        """Declare a new variable in this scope."""
        key = name.lower()
        self._vars[key] = value
        if const:
            self._consts.add(key)

    def get_local(self, name: str) -> Any:
        """Get a variable from this scope only (no parent chain)."""
        key = name.lower()
        val = self._vars.get(key, UNINIT)
        if isinstance(val, ByRef):
            return val.get()
        return val

    def set_local(self, name: str, value: Any) -> None:
        """Set a variable in this scope only."""
        key = name.lower()
        if key in self._consts:
            raise RuntimeError(f"Cannot assign to constant '{name}'")
        existing = self._vars.get(key)
        if isinstance(existing, ByRef):
            existing.set(value)
        else:
            self._vars[key] = value

    def has_local(self, name: str) -> bool:
        """Check if variable exists in this scope (not parents)."""
        return name.lower() in self._vars

    def is_const(self, name: str) -> bool:
        """Check if a variable is declared as const."""
        return name.lower() in self._consts

    def __repr__(self) -> str:
        return f"Scope(vars={list(self._vars.keys())})"


class ScopeStack:
    """Manages the scope chain for the interpreter.

    - One global scope (always at the bottom)
    - Function-local scopes pushed/popped on call/return
    """

    def __init__(self) -> None:
        self._global = Scope()
        self._stack: list[Scope] = []

    @property
    def global_scope(self) -> Scope:
        return self._global

    @property
    def current(self) -> Scope:
        """The current (innermost) scope."""
        return self._stack[-1] if self._stack else self._global

    def push(self) -> Scope:
        """Push a new local scope for a function call."""
        scope = Scope(parent=self.current)
        self._stack.append(scope)
        return scope

    def pop(self) -> Scope:
        """Pop the current local scope after function return."""
        if not self._stack:
            raise RuntimeError("Cannot pop global scope")
        return self._stack.pop()

    @property
    def depth(self) -> int:
        """Number of local scopes on the stack."""
        return len(self._stack)

    def get(self, name: str) -> Any:
        """Look up a variable by walking the scope chain.

        Checks current scope first, then walks up to global.
        """
        key = name.lower()

        # Check current local scope — inline dict lookup to avoid
        # has_local + get_local double-lowering and double-lookup.
        if self._stack:
            val = self._stack[-1]._vars.get(key, UNINIT)
            if val is not UNINIT:
                if isinstance(val, ByRef):
                    return val.get()
                return val

        # Check global scope
        val = self._global._vars.get(key, UNINIT)
        if val is not UNINIT:
            if isinstance(val, ByRef):
                return val.get()
            return val

        return UNINIT

    def set(self, name: str, value: Any) -> None:
        """Set a variable in the appropriate scope.

        If the variable exists in the current local scope, set it there.
        If it exists in global scope, set it there.
        Otherwise, set in current scope (local if in a function, global otherwise).
        """
        key = name.lower()

        # Check current local scope first — inline to avoid double-lookup
        if self._stack:
            scope = self._stack[-1]
            if key in scope._vars:
                if key in scope._consts:
                    raise RuntimeError(f"Cannot assign to constant '{name}'")
                existing = scope._vars[key]
                if isinstance(existing, ByRef):
                    existing.set(value)
                else:
                    scope._vars[key] = value
                return

        # Check global scope
        if key in self._global._vars:
            if key in self._global._consts:
                raise RuntimeError(f"Cannot assign to constant '{name}'")
            existing = self._global._vars[key]
            if isinstance(existing, ByRef):
                existing.set(value)
            else:
                self._global._vars[key] = value
            return

        # Not found — set in current scope
        self.current._vars[key] = value

    def define(self, name: str, value: Any = UNINIT, *, const: bool = False) -> None:
        """Define a new variable in the current scope."""
        self.current.define(name, value, const=const)

    def define_global(self, name: str, value: Any = UNINIT, *, const: bool = False) -> None:
        """Define a variable in the global scope."""
        self._global.define(name, value, const=const)

    def snapshot_globals(self) -> tuple[dict[str, Any], set[str]]:
        """Capture a snapshot of the global scope (vars + const set)."""
        return dict(self._global._vars), set(self._global._consts)

    def restore_globals(self, snapshot: tuple[dict[str, Any], set[str]]) -> None:
        """Reset scope stack and restore global scope from snapshot."""
        self._stack.clear()
        saved_vars, saved_consts = snapshot
        self._global._vars = dict(saved_vars)
        self._global._consts = set(saved_consts)
