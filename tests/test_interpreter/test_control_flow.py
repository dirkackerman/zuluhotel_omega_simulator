"""Tests for control flow: break, continue, return, exit, nesting."""

from unittest.mock import patch

import omega.runtime  # noqa: F401

from .helpers import run_function, run_snippet


class TestBreak:
    def test_break_while(self):
        code = """
        var x := 0;
        while (1)
            x := x + 1;
            if (x >= 5)
                break;
            endif
        endwhile
        """
        assert run_snippet(code, "x") == 5

    def test_break_for(self):
        code = """
        var x := 0;
        for i := 1 to 100
            x := i;
            if (i >= 3)
                break;
            endif
        endfor
        """
        assert run_snippet(code, "x") == 3

    def test_break_foreach(self):
        code = """
        var x := 0;
        foreach item in {10, 20, 30, 40}
            x := item;
            if (item == 20)
                break;
            endif
        endforeach
        """
        assert run_snippet(code, "x") == 20


class TestContinue:
    def test_continue_while(self):
        code = """
        var total := 0;
        var i := 0;
        while (i < 5)
            i := i + 1;
            if (i == 3)
                continue;
            endif
            total := total + i;
        endwhile
        """
        # total = 1+2+4+5 = 12 (skips 3)
        assert run_snippet(code, "total") == 12

    def test_continue_foreach(self):
        code = """
        var total := 0;
        foreach item in {1, 2, 3, 4, 5}
            if (item == 3)
                continue;
            endif
            total := total + item;
        endforeach
        """
        assert run_snippet(code, "total") == 12


class TestReturn:
    def test_return_value(self):
        funcs = """
        function get_val()
            return 42;
        endfunction
        """
        result = run_function(funcs, "var x := get_val();", "x")
        assert result == 42

    def test_early_return(self):
        funcs = """
        function check(n)
            if (n > 0)
                return "positive";
            endif
            return "not positive";
        endfunction
        """
        result = run_function(funcs, 'var x := check(5);', "x")
        assert result == "positive"

    def test_return_no_value(self):
        funcs = """
        function noop()
            return;
        endfunction
        """
        result = run_function(funcs, "var x := noop();", "x")
        assert result is None


class TestNestedControlFlow:
    def test_nested_loops_with_break(self):
        code = """
        var count := 0;
        for i := 1 to 3
            for j := 1 to 3
                if (j == 2)
                    break;
                endif
                count := count + 1;
            endfor
        endfor
        """
        # Inner loop breaks at j==2, so only j==1 executes per outer iteration
        # count = 3 (one per outer iteration)
        assert run_snippet(code, "count") == 3

    def test_loop_with_function_call(self):
        funcs = """
        function square(n)
            return n * n;
        endfunction
        """
        call = """
        var total := 0;
        for i := 1 to 3
            total := total + square(i);
        endfor
        """
        result = run_function(funcs, call, "total")
        assert result == 14  # 1+4+9


class TestMemberAccess:
    def test_array_index(self):
        code = """
        var arr := {10, 20, 30};
        var x := arr[2];
        """
        assert run_snippet(code, "x") == 20

    def test_array_index_set(self):
        code = """
        var arr := {10, 20, 30};
        arr[2] := 99;
        var x := arr[2];
        """
        assert run_snippet(code, "x") == 99

    def test_struct_member(self):
        code = """
        var s := struct{ name := "test", value := 42 };
        var x := s.name;
        """
        assert run_snippet(code, "x") == "test"

    def test_dict_index(self):
        code = """
        var d := dictionary;
        d["key"] := 99;
        var x := d["key"];
        """
        assert run_snippet(code, "x") == 99

    def test_dict_exists(self):
        code = """
        var d := dictionary;
        d["a"] := 1;
        var x := d.exists("a");
        var y := d.exists("b");
        """
        assert run_snippet(code, "x") == 1

    def test_array_append(self):
        code = """
        var arr := array;
        arr.append(10);
        arr.append(20);
        var x := Len(arr);
        """
        assert run_snippet(code, "x") == 2

    def test_nested_array_access(self):
        """Multi-dimensional array access like hitlist[current][1]."""
        code = """
        var arr := { {1, 2}, {3, 4}, {5, 6} };
        var x := arr[2][1];
        """
        assert run_snippet(code, "x") == 3

    def test_parms_unpacking(self):
        """The parms[1], parms[2] pattern from hitscripts."""
        code = """
        var parms := {100, 200, 300};
        var a := parms[1];
        var b := parms[2];
        var c := parms[3];
        var total := a + b + c;
        """
        assert run_snippet(code, "total") == 600


class TestLoopIterationGuard:
    """Tests for the _MAX_LOOP_ITERATIONS guard on while/do/repeat/cstyle-for."""

    def test_while_loop_guard_breaks_infinite(self):
        """Infinite while(1) should break at _MAX_LOOP_ITERATIONS."""
        code = """
        var x := 0;
        while (1)
            x := x + 1;
        endwhile
        """
        with patch("omega.interpreter.evaluator._MAX_LOOP_ITERATIONS", 50):
            assert run_snippet(code, "x") == 50

    def test_do_loop_guard_breaks_infinite(self):
        """Infinite do...while(1) should break at _MAX_LOOP_ITERATIONS."""
        code = """
        var x := 0;
        do
            x := x + 1;
        dowhile (1);
        """
        with patch("omega.interpreter.evaluator._MAX_LOOP_ITERATIONS", 50):
            assert run_snippet(code, "x") == 50

    def test_repeat_loop_guard_breaks_infinite(self):
        """Infinite repeat...until(0) should break at _MAX_LOOP_ITERATIONS."""
        code = """
        var x := 0;
        repeat
            x := x + 1;
        until (0);
        """
        with patch("omega.interpreter.evaluator._MAX_LOOP_ITERATIONS", 50):
            assert run_snippet(code, "x") == 50

    def test_cstyle_for_loop_guard_breaks_infinite(self):
        """Infinite for(;;) should break at _MAX_LOOP_ITERATIONS."""
        code = """
        var x := 0;
        for (x := 0; 1; x := x)
            x := x + 1;
        endfor
        """
        with patch("omega.interpreter.evaluator._MAX_LOOP_ITERATIONS", 50):
            assert run_snippet(code, "x") == 50

    def test_normal_while_loop_not_affected(self):
        """A while loop with 100 iterations should complete normally."""
        code = """
        var x := 0;
        while (x < 100)
            x := x + 1;
        endwhile
        """
        assert run_snippet(code, "x") == 100

    def test_normal_cstyle_for_not_affected(self):
        """A C-style for loop with 100 iterations should complete normally."""
        code = """
        var x := 0;
        for (x := 0; x < 100; x := x + 1)
        endfor
        """
        assert run_snippet(code, "x") == 100

    def test_break_works_in_guarded_loop(self):
        """Break should exit before the guard triggers."""
        code = """
        var x := 0;
        while (1)
            x := x + 1;
            if (x >= 10)
                break;
            endif
        endwhile
        """
        with patch("omega.interpreter.evaluator._MAX_LOOP_ITERATIONS", 50):
            assert run_snippet(code, "x") == 10
