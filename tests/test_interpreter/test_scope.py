"""Tests for scope management."""

import pytest

from omega.interpreter.scope import ByRef, Scope, ScopeStack
from omega.interpreter.types import UNINIT


class TestScope:
    def test_define_and_get(self):
        s = Scope()
        s.define("x", 42)
        assert s.get_local("x") == 42

    def test_case_insensitive(self):
        s = Scope()
        s.define("MyVar", 10)
        assert s.get_local("myvar") == 10
        assert s.get_local("MYVAR") == 10

    def test_set_existing(self):
        s = Scope()
        s.define("x", 1)
        s.set_local("x", 2)
        assert s.get_local("x") == 2

    def test_const_prevents_reassign(self):
        s = Scope()
        s.define("PI", 3.14, const=True)
        with pytest.raises(RuntimeError, match="constant"):
            s.set_local("PI", 99)

    def test_has_local(self):
        s = Scope()
        s.define("x", 1)
        assert s.has_local("x")
        assert not s.has_local("y")

    def test_uninit_default(self):
        s = Scope()
        assert s.get_local("missing") is UNINIT


class TestByRef:
    def test_get_set(self):
        s = Scope()
        s.define("val", 10)
        ref = ByRef(s, "val")
        assert ref.get() == 10
        ref.set(20)
        assert s.get_local("val") == 20

    def test_byref_in_scope(self):
        parent = Scope()
        parent.define("x", 100)
        child = Scope()
        child.define("x", ByRef(parent, "x"))
        # Getting through child should resolve byref
        assert child.get_local("x") == 100
        # Setting through child should propagate
        child.set_local("x", 200)
        assert parent.get_local("x") == 200


class TestScopeStack:
    def test_global_scope(self):
        ss = ScopeStack()
        ss.define_global("G", 99)
        assert ss.get("G") == 99

    def test_local_shadows_global(self):
        ss = ScopeStack()
        ss.define_global("x", 1)
        ss.push()
        ss.define("x", 2)
        assert ss.get("x") == 2
        ss.pop()
        assert ss.get("x") == 1

    def test_set_finds_correct_scope(self):
        ss = ScopeStack()
        ss.define_global("g", 10)
        ss.push()
        ss.define("l", 20)
        # Set local
        ss.set("l", 30)
        assert ss.get("l") == 30
        # Set global (not shadowed)
        ss.set("g", 50)
        ss.pop()
        assert ss.get("g") == 50

    def test_depth(self):
        ss = ScopeStack()
        assert ss.depth == 0
        ss.push()
        assert ss.depth == 1
        ss.push()
        assert ss.depth == 2
        ss.pop()
        assert ss.depth == 1

    def test_pop_empty_raises(self):
        ss = ScopeStack()
        with pytest.raises(RuntimeError):
            ss.pop()

    def test_define_in_current(self):
        ss = ScopeStack()
        ss.push()
        ss.define("local_var", 42)
        assert ss.get("local_var") == 42
        ss.pop()
        assert ss.get("local_var") is UNINIT
