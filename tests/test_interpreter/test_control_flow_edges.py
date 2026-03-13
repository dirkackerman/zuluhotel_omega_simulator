"""Priority 4 — Control flow edge case tests.

Tests exit, case statement details, for loop edge cases, foreach
modification safety, loop variable scope leakage, return from nested
loops, and continue in post-test loops.
"""

import omega.runtime  # noqa: F401

from .helpers import run_function, run_snippet


# ---------------------------------------------------------------------------
# Exit statement
# ---------------------------------------------------------------------------


class TestExitStatement:
    """Exit statement terminates the program. The executor catches ExitSignal
    so from the caller's perspective it's a normal termination — code after
    exit simply doesn't execute."""

    def test_exit_from_main(self):
        """exit stops execution; code after exit is not reached."""
        code = """
        var x := 1;
        exit;
        x := 999;
        """
        assert run_snippet(code, "x") == 1

    def test_exit_from_function(self):
        """exit inside a function stops the entire program."""
        funcs = """
        function bail()
            exit;
        endfunction
        """
        code = """
        var x := 1;
        bail();
        x := 999;
        """
        result = run_function(funcs, code, "x")
        assert result == 1

    def test_exit_from_loop(self):
        """exit inside a loop terminates program, not just loop."""
        code = """
        var x := 0;
        while (1)
            x := x + 1;
            exit;
        endwhile
        x := 999;
        """
        assert run_snippet(code, "x") == 1

    def test_exit_from_nested_loop(self):
        """exit inside nested loops terminates program."""
        code = """
        var x := 0;
        for i := 1 to 10
            for j := 1 to 10
                x := i * 10 + j;
                exit;
            endfor
        endfor
        """
        assert run_snippet(code, "x") == 11


# ---------------------------------------------------------------------------
# Case statement
# ---------------------------------------------------------------------------


class TestCaseStatement:
    def test_case_basic_match(self):
        code = """
        var x := 0;
        case (2)
            1: x := 10;
            2: x := 20;
            3: x := 30;
        endcase
        """
        assert run_snippet(code, "x") == 20

    def test_case_default(self):
        code = """
        var x := 0;
        case (99)
            1: x := 10;
            default: x := -1;
        endcase
        """
        assert run_snippet(code, "x") == -1

    def test_case_no_match_no_default(self):
        """No matching case and no default — x stays unchanged."""
        code = """
        var x := 0;
        case (99)
            1: x := 10;
            2: x := 20;
        endcase
        """
        assert run_snippet(code, "x") == 0

    def test_case_with_break(self):
        """Break in case block exits the case statement."""
        code = """
        var x := 0;
        case (1)
            1:
                x := 10;
                break;
        endcase
        """
        assert run_snippet(code, "x") == 10

    def test_case_string_match(self):
        code = """
        var x := 0;
        case ("hello")
            "hi": x := 1;
            "hello": x := 2;
            default: x := 3;
        endcase
        """
        assert run_snippet(code, "x") == 2

    def test_case_with_identifier(self):
        """Case label can be a variable/constant identifier."""
        code = """
        var OPTION_A := 1;
        var OPTION_B := 2;
        var choice := 2;
        var x := 0;
        case (choice)
            OPTION_A: x := 10;
            OPTION_B: x := 20;
        endcase
        """
        assert run_snippet(code, "x") == 20


# ---------------------------------------------------------------------------
# For loop edge cases
# ---------------------------------------------------------------------------


class TestForLoopEdges:
    def test_for_descending_zero_iterations(self):
        """for i := 5 to 1 → 0 iterations (condition i <= end false immediately)."""
        code = """
        var count := 0;
        for i := 5 to 1
            count := count + 1;
        endfor
        """
        assert run_snippet(code, "count") == 0

    def test_for_single_iteration(self):
        """for i := 3 to 3 → exactly 1 iteration."""
        code = """
        var count := 0;
        for i := 3 to 3
            count := count + 1;
        endfor
        """
        assert run_snippet(code, "count") == 1


# ---------------------------------------------------------------------------
# Loop variable scope leakage
# ---------------------------------------------------------------------------


class TestLoopVariableScope:
    def test_for_variable_leaks_after_loop(self):
        """For loop variable is accessible after the loop (eScript has no block scope)."""
        code = """
        var total := 0;
        for i := 1 to 5
            total := total + i;
        endfor
        """
        # i should be 5 (last value set in scope during iteration)
        assert run_snippet(code, "i") == 5

    def test_foreach_variable_leaks(self):
        """Foreach loop variable holds last value after loop."""
        code = """
        var last := 0;
        foreach item in {10, 20, 30}
            last := item;
        endforeach
        """
        assert run_snippet(code, "last") == 30
        # The iteration variable 'item' should also be accessible
        assert run_snippet(code, "item") == 30


# ---------------------------------------------------------------------------
# Foreach modification safety
# ---------------------------------------------------------------------------


class TestForeachModification:
    def test_foreach_sees_original_values(self):
        """Modifying array during foreach doesn't affect iteration."""
        code = """
        var arr := {1, 2, 3};
        var total := 0;
        foreach val in arr
            total := total + val;
            arr.append(99);
        endforeach
        """
        # Should iterate exactly 3 times with original values
        assert run_snippet(code, "total") == 6


# ---------------------------------------------------------------------------
# Return from nested loop
# ---------------------------------------------------------------------------


class TestReturnFromNestedLoop:
    def test_return_from_for_loop_in_function(self):
        """Return inside a for loop exits the function correctly."""
        funcs = """
        function find_first_gt(arr, threshold)
            foreach val in arr
                if (val > threshold)
                    return val;
                endif
            endforeach
            return -1;
        endfunction
        """
        result = run_function(funcs, "var x := find_first_gt({5, 10, 15, 20}, 12);", "x")
        assert result == 15

    def test_return_from_nested_for_loops(self):
        """Return from doubly-nested for loop exits the function."""
        funcs = """
        function find_pair()
            for i := 1 to 5
                for j := 1 to 5
                    if (i * j == 6)
                        return i * 10 + j;
                    endif
                endfor
            endfor
            return 0;
        endfunction
        """
        result = run_function(funcs, "var x := find_pair();", "x")
        assert result == 23  # i=2, j=3


# ---------------------------------------------------------------------------
# Continue in do-while and repeat-until
# ---------------------------------------------------------------------------


class TestContinueInPostTestLoops:
    def test_continue_in_do_while(self):
        """Continue in do-while skips to condition check."""
        code = """
        var total := 0;
        var i := 0;
        do
            i := i + 1;
            if (i == 3)
                continue;
            endif
            total := total + i;
        dowhile (i < 5);
        """
        # total = 1+2+4+5 = 12 (skips 3)
        assert run_snippet(code, "total") == 12

    def test_continue_in_repeat_until(self):
        """Continue in repeat-until skips to condition check."""
        code = """
        var total := 0;
        var i := 0;
        repeat
            i := i + 1;
            if (i == 3)
                continue;
            endif
            total := total + i;
        until (i >= 5);
        """
        # total = 1+2+4+5 = 12 (skips 3)
        assert run_snippet(code, "total") == 12
