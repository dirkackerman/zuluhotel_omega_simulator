"""Shared helpers for interpreter tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omega.interpreter.evaluator import EscriptInterpreter
from omega.interpreter.executor import Executor
from omega.interpreter.scope import ScopeStack
from omega.interpreter.types import UNINIT
from omega.parser.parser import ParseResult, parse_text


def eval_expr(expr_source: str) -> Any:
    """Parse and evaluate a single expression."""
    # Wrap in a var statement to parse as a statement
    source = f"var __result := {expr_source};"
    return run_snippet(source, "__result")


def run_snippet(source: str, var_name: str | None = None) -> Any:
    """Parse and execute a snippet of eScript code.

    If var_name is given, returns that variable's value.
    Otherwise returns None.
    """
    # Wrap in a program to ensure it parses as executable code
    program_source = f"program test_snippet()\n{source}\nendprogram"
    result = parse_text(program_source)
    assert result.success, f"Parse errors: {result.errors}"

    fake_path = Path("<test>")
    executor = Executor({fake_path: result})
    executor.run_program({})

    if var_name is not None:
        return executor.scopes.get(var_name)
    return None


def run_program_with_args(source: str, args: dict[str, Any]) -> Executor:
    """Parse and execute a program with arguments. Returns the executor."""
    result = parse_text(source)
    assert result.success, f"Parse errors: {result.errors}"

    fake_path = Path("<test>")
    executor = Executor({fake_path: result})
    executor.run_program(args)
    return executor


def run_function(includes_source: str, call_source: str, var_name: str) -> Any:
    """Parse source with function definitions, execute a snippet that calls them."""
    full_source = f"{includes_source}\nprogram test_func()\n{call_source}\nendprogram"
    result = parse_text(full_source)
    assert result.success, f"Parse errors: {result.errors}"

    fake_path = Path("<test>")
    executor = Executor({fake_path: result})
    executor.run_program({})
    return executor.scopes.get(var_name)
