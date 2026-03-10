"""Tests for sub-script execution (M15 — Sub-Script Executor).

Covers:
- Sub-script runs and receives arguments correctly
- Scope isolation: sub-script variables don't leak to main program
- Sub-script can call shared user-defined functions
- start_script stub dispatches to executor
- Script path resolution for :package:name format
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from omega.interpreter.executor import Executor
from omega.interpreter.types import UNINIT
from omega.parser.include_resolver import DictPackageMap
from omega.parser.parser import ParseResult, parse_text


def _make_executor(
    sources: dict[str, str],
    *,
    shard_root: Path | None = None,
    package_map: DictPackageMap | None = None,
) -> Executor:
    """Create an executor from multiple named source strings.

    The first source with a program declaration becomes the main program.
    """
    parse_results: dict[Path, ParseResult] = {}
    for name, source in sources.items():
        result = parse_text(source, file=name)
        assert result.success, f"Parse errors in {name}: {result.errors}"
        parse_results[Path(name)] = result

    return Executor(
        parse_results,
        shard_root=shard_root,
        package_map=package_map,
    )


class TestRunSubProgram:
    """Test Executor.run_sub_program()."""

    def test_sub_program_runs_and_returns(self, tmp_path: Path):
        """A sub-script program can execute and return a value."""
        # Main program
        main_src = textwrap.dedent("""\
            program main()
                var x := 42;
            endprogram
        """)

        # Sub-script that returns a computed value
        sub_src = textwrap.dedent("""\
            program sub_script(parms)
                var a := parms[1];
                var b := parms[2];
                return a + b;
            endprogram
        """)

        # Write sub-script to filesystem for path resolution
        pkg_dir = tmp_path / "pkg" / "systems" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "sub_script.src").write_text(sub_src)

        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})

        # POL convention: array passed as single first arg
        result = executor.run_sub_program(":combat:sub_script", [[10, 20]])
        assert result == 30

    def test_sub_program_single_array_arg(self, tmp_path: Path):
        """POL convention: args array passed as single first argument."""
        sub_src = textwrap.dedent("""\
            program reactive(parms)
                var attacker := parms[1];
                var power := parms[2];
                return attacker + power;
            endprogram
        """)

        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "reactive.src").write_text(sub_src)

        main_src = "program main()\nendprogram"
        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})

        # POL passes the array as the first arg
        args_array = [100, 50]
        result = executor.run_sub_program(":combat:reactive", [args_array])
        assert result == 150

    def test_sub_program_named_params_with_unpack(self, tmp_path: Path):
        """Sub-script with named params and TypeOf array unpack pattern."""
        sub_src = textwrap.dedent("""\
            program piercing(attacker, defender, weapon)
                if (TypeOf(attacker) == "Array")
                    defender := attacker[2];
                    weapon := attacker[3];
                    attacker := attacker[1];
                endif
                return attacker + defender + weapon;
            endprogram
        """)

        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "piercing.src").write_text(sub_src)

        main_src = "program main()\nendprogram"
        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})

        # POL passes {a, b, c} array as first positional arg
        result = executor.run_sub_program(":combat:piercing", [[10, 20, 30]])
        assert result == 60


class TestScopeIsolation:
    """Sub-script scope must not leak variables to the main program."""

    def test_sub_script_vars_dont_leak(self, tmp_path: Path):
        """Variables defined in a sub-script are not visible after it returns."""
        main_src = textwrap.dedent("""\
            program main()
                var before := 1;
            endprogram
        """)

        sub_src = textwrap.dedent("""\
            program sub(parms)
                var leaked_var := 999;
                var another := "should not leak";
            endprogram
        """)

        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "sub.src").write_text(sub_src)

        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})
        executor.run_sub_program(":combat:sub", [[]])

        assert executor.scopes.get("leaked_var") is UNINIT
        assert executor.scopes.get("another") is UNINIT

    def test_main_globals_visible_in_sub_script(self, tmp_path: Path):
        """Global constants from the main script are accessible in sub-scripts."""
        main_src = textwrap.dedent("""\
            const MY_CONST := 42;
            program main()
            endprogram
        """)

        # Sub-script references the global constant
        sub_src = textwrap.dedent("""\
            program sub(parms)
                return MY_CONST + 1;
            endprogram
        """)

        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "sub.src").write_text(sub_src)

        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})

        result = executor.run_sub_program(":combat:sub", [[]])
        assert result == 43

    def test_scope_depth_restored_after_sub_script(self, tmp_path: Path):
        """Scope stack depth is restored even if sub-script exits abnormally."""
        main_src = "program main()\nendprogram"

        sub_src = textwrap.dedent("""\
            program sub(parms)
                var x := 1;
                return x;
            endprogram
        """)

        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "sub.src").write_text(sub_src)

        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})

        depth_before = executor.scopes.depth
        executor.run_sub_program(":combat:sub", [[]])
        assert executor.scopes.depth == depth_before


class TestSharedFunctions:
    """Sub-scripts can call user-defined functions from the main include chain."""

    def test_sub_script_calls_shared_function(self, tmp_path: Path):
        """A sub-script can call a function defined in the main script's includes."""
        main_src = textwrap.dedent("""\
            function MultiplyByTwo(x)
                return x * 2;
            endfunction

            program main()
            endprogram
        """)

        sub_src = textwrap.dedent("""\
            program sub(parms)
                var val := parms[1];
                return MultiplyByTwo(val);
            endprogram
        """)

        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "sub.src").write_text(sub_src)

        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})

        result = executor.run_sub_program(":combat:sub", [[7]])
        assert result == 14


class TestScriptPathResolution:
    """Test _resolve_script_path edge cases."""

    def test_missing_shard_root_raises(self):
        """Executor without shard_root cannot resolve sub-script paths."""
        main_src = "program main()\nendprogram"
        executor = _make_executor({"main.src": main_src})

        with pytest.raises(RuntimeError, match="shard_root"):
            executor.run_sub_program(":combat:missing", [[]])

    def test_unknown_package_raises(self, tmp_path: Path):
        """Unknown package name raises FileNotFoundError."""
        main_src = "program main()\nendprogram"
        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({}),
        )

        with pytest.raises(FileNotFoundError, match="Unknown package"):
            executor.run_sub_program(":unknown:script", [[]])

    def test_missing_script_file_raises(self, tmp_path: Path):
        """Missing .src file raises FileNotFoundError."""
        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)

        main_src = "program main()\nendprogram"
        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )

        with pytest.raises(FileNotFoundError, match="not found"):
            executor.run_sub_program(":combat:nonexistent", [[]])

    def test_sub_program_cached_on_second_call(self, tmp_path: Path):
        """Second call to same sub-script uses cached program block."""
        sub_src = textwrap.dedent("""\
            program sub(parms)
                return parms[1] * 3;
            endprogram
        """)

        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "sub.src").write_text(sub_src)

        main_src = "program main()\nendprogram"
        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})

        result1 = executor.run_sub_program(":combat:sub", [[5]])
        result2 = executor.run_sub_program(":combat:sub", [[10]])
        assert result1 == 15
        assert result2 == 30
        # Only one entry in cache
        assert len(executor._sub_programs) == 1


class TestStartScriptStub:
    """Test that the start_script POL stub dispatches to executor."""

    def test_start_script_dispatches(self, tmp_path: Path):
        """start_script() in eScript dispatches to run_sub_program."""
        import omega.runtime  # noqa: F401 — register stubs

        from omega.runtime.context import SimulationContext, set_context

        main_src = "program main()\nendprogram"

        sub_src = textwrap.dedent("""\
            program on_hit(parms)
                var val := parms[1];
                return val * 10;
            endprogram
        """)

        pkg_dir = tmp_path / "pkg" / "combat"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "on_hit.src").write_text(sub_src)

        executor = _make_executor(
            {"main.src": main_src},
            shard_root=tmp_path,
            package_map=DictPackageMap({"combat": pkg_dir}),
        )
        executor.run_program({})

        # Set up context with executor
        ctx = SimulationContext()
        ctx.executor = executor
        set_context(ctx)

        from omega.runtime.structural_stubs import start_script

        result = start_script(":combat:on_hit", [42])
        assert result == 420

    def test_start_script_no_executor_returns_none(self):
        """start_script() with no executor returns None gracefully."""
        import omega.runtime  # noqa: F401

        from omega.runtime.context import SimulationContext, set_context

        ctx = SimulationContext()
        ctx.executor = None
        set_context(ctx)

        from omega.runtime.structural_stubs import start_script

        result = start_script(":combat:something", [1, 2, 3])
        assert result is None
