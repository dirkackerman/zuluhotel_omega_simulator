"""Tests for statement execution in the interpreter."""

import omega.runtime  # noqa: F401

from omega.interpreter.types import UNINIT, EArray

from .helpers import run_snippet


class TestVarDeclaration:
    def test_var_with_init(self):
        assert run_snippet("var x := 42;", "x") == 42

    def test_var_without_init(self):
        assert run_snippet("var x;", "x") is UNINIT

    def test_var_array_keyword(self):
        result = run_snippet("var x := array;", "x")
        assert isinstance(result, EArray)
        assert len(result) == 0

    def test_multiple_vars(self):
        code = "var a := 1, b := 2;"
        assert run_snippet(code + " var c := a + b;", "c") == 3

    def test_var_no_init(self):
        code = "var a, b;"
        run_snippet(code, "a")  # should not error


class TestConstDeclaration:
    def test_const_value(self):
        assert run_snippet("const PI := 3; var x := PI;", "x") == 3


class TestIfStatement:
    def test_true_branch(self):
        code = """
        var x := 0;
        if (1)
            x := 10;
        endif
        """
        assert run_snippet(code, "x") == 10

    def test_false_branch(self):
        code = """
        var x := 0;
        if (0)
            x := 10;
        else
            x := 20;
        endif
        """
        assert run_snippet(code, "x") == 20

    def test_elseif(self):
        code = """
        var x := 0;
        var n := 2;
        if (n == 1)
            x := 10;
        elseif (n == 2)
            x := 20;
        elseif (n == 3)
            x := 30;
        else
            x := 40;
        endif
        """
        assert run_snippet(code, "x") == 20

    def test_nested_if(self):
        code = """
        var x := 0;
        if (1)
            if (1)
                x := 99;
            endif
        endif
        """
        assert run_snippet(code, "x") == 99


class TestWhileLoop:
    def test_basic_while(self):
        code = """
        var x := 0;
        while (x < 5)
            x := x + 1;
        endwhile
        """
        assert run_snippet(code, "x") == 5

    def test_while_false_initial(self):
        code = """
        var x := 10;
        while (0)
            x := 0;
        endwhile
        """
        assert run_snippet(code, "x") == 10


class TestDoWhile:
    def test_executes_once(self):
        code = """
        var x := 0;
        do
            x := x + 1;
        dowhile (0);
        """
        assert run_snippet(code, "x") == 1

    def test_loops(self):
        code = """
        var x := 0;
        do
            x := x + 1;
        dowhile (x < 3);
        """
        assert run_snippet(code, "x") == 3


class TestForLoop:
    def test_basic_for(self):
        code = """
        var total := 0;
        for i := 1 to 5
            total := total + i;
        endfor
        """
        assert run_snippet(code, "total") == 15

    def test_cstyle_for(self):
        code = """
        var total := 0;
        var i;
        for (i := 0; i < 5; i := i + 1)
            total := total + 1;
        endfor
        """
        assert run_snippet(code, "total") == 5


class TestForeach:
    def test_foreach_array(self):
        code = """
        var total := 0;
        var items := {10, 20, 30};
        foreach item in items
            total := total + item;
        endforeach
        """
        assert run_snippet(code, "total") == 60

    def test_foreach_inline_array(self):
        code = """
        var total := 0;
        foreach item in {1, 2, 3}
            total := total + item;
        endforeach
        """
        assert run_snippet(code, "total") == 6


class TestCaseStatement:
    def test_integer_match(self):
        code = """
        var x := 0;
        var n := 2;
        case (n)
            1: x := 10;
            2: x := 20;
            3: x := 30;
        endcase
        """
        assert run_snippet(code, "x") == 20

    def test_string_match(self):
        code = """
        var x := 0;
        var s := "b";
        case (s)
            "a": x := 1;
            "b": x := 2;
            "c": x := 3;
        endcase
        """
        assert run_snippet(code, "x") == 2

    def test_default(self):
        code = """
        var x := 0;
        var n := 99;
        case (n)
            1: x := 10;
            default: x := -1;
        endcase
        """
        assert run_snippet(code, "x") == -1

    def test_no_match(self):
        code = """
        var x := 0;
        var n := 99;
        case (n)
            1: x := 10;
            2: x := 20;
        endcase
        """
        assert run_snippet(code, "x") == 0


class TestRepeatUntil:
    def test_basic(self):
        code = """
        var x := 0;
        repeat
            x := x + 1;
        until (x >= 3);
        """
        assert run_snippet(code, "x") == 3
