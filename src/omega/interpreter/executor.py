"""High-level API for executing eScript programs.

Usage::

    from omega.parser import parse_with_includes
    from omega.interpreter.executor import Executor

    trees = parse_with_includes(Path("mainhit.src"), shard_root, pkg_map)
    executor = Executor(trees)
    result = executor.run_program({"attacker": mob_a, "defender": mob_b, ...})
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omega.interpreter.evaluator import (
    EscriptInterpreter,
    ExitSignal,
    ReturnSignal,
)
from omega.interpreter.functions import (
    FunctionDef,
    FunctionRegistry,
    ParamDef,
    extract_constants,
    extract_functions,
    extract_program,
    extract_use_declarations,
)
from omega.interpreter.scope import ScopeStack
from omega.interpreter.types import UNINIT
from omega.logging import get_logger
from omega.parser.parser import ParseResult

logger = get_logger("omega.interpreter")


class Executor:
    """Loads parsed eScript files and executes the program entry point.

    Initialization:
    1. Walk all ParseResult trees
    2. Extract function declarations → function registry
    3. Extract constants → global scope
    4. Extract USE declarations
    5. Locate the program block

    Running:
    1. Bind program parameters
    2. Execute program body
    3. Return result
    """

    def __init__(
        self,
        parse_results: dict[Path, ParseResult],
        *,
        em_modules_dir: Path | None = None,
        shard_root: Path | None = None,
        package_map: Any | None = None,
    ) -> None:
        self.scopes = ScopeStack()
        self.functions = FunctionRegistry()
        self._program: tuple[str, list[ParamDef], Any] | None = None
        self._interpreter = EscriptInterpreter(self.scopes, self.functions)
        self._em_modules_dir = em_modules_dir
        self._shard_root = shard_root
        self._package_map = package_map

        # Sub-script program cache: script path key → (name, params, body)
        self._sub_programs: dict[str, tuple[str, list[ParamDef], Any]] = {}

        self._load(parse_results)
        # Snapshot the global scope after loading so we can cheaply
        # restore it before each run_program() call.
        self._global_snapshot = self.scopes.snapshot_globals()

    def reset(self) -> None:
        """Reset interpreter state for a new run.

        Restores the global scope to the post-load state (constants +
        functions preserved, runtime variables cleared) and empties the
        local scope stack.  Much cheaper than re-creating the Executor.
        """
        self.scopes.restore_globals(self._global_snapshot)

    def _load(self, parse_results: dict[Path, ParseResult]) -> None:
        """Load all parsed files: extract functions, constants, program."""
        for path, result in parse_results.items():
            if result.tree is None:
                logger.warning("Skipping file with no parse tree", file=str(path))
                continue

            # Process files even with include-resolution errors —
            # the tree itself is valid and contains useful functions/constants
            if not result.success:
                logger.debug(
                    "File has warnings, processing anyway",
                    file=str(path),
                    error_count=len(result.errors),
                )

            tree = result.tree

            # Extract USE declarations
            for module in extract_use_declarations(tree):
                self.functions.add_module(module)

            # Extract function definitions
            for func_def in extract_functions(tree, source_file=str(path)):
                self.functions.register(func_def)

            # Extract constants (evaluated in global scope)
            constants = extract_constants(tree)
            enum_counter = 0
            for name, expr_ctx, is_enum in constants:
                if expr_ctx is not None:
                    value = self._interpreter.visit(expr_ctx)
                    if is_enum:
                        enum_counter = int(value) if isinstance(value, (int, float)) else 0
                elif is_enum:
                    value = enum_counter
                else:
                    value = UNINIT
                self.scopes.define_global(name, value, const=True)
                if is_enum:
                    enum_counter = (int(value) if isinstance(value, (int, float)) else 0) + 1

            # Extract program declaration
            prog = extract_program(tree)
            if prog is not None:
                if self._program is not None:
                    logger.warning(
                        "Multiple program declarations found",
                        existing=self._program[0],
                        new=prog[0],
                    )
                self._program = prog

        # Load .em module constants if modules dir is provided
        if self._em_modules_dir is not None:
            self._load_em_constants()

    def _load_em_constants(self) -> None:
        """Load constants from .em module files for all USE declarations."""
        from omega.parser.em_parser import load_em_modules

        module_names = list(self.functions.module_names)
        if not module_names:
            return

        constants = load_em_modules(self._em_modules_dir, module_names)
        for name, value in constants.items():
            # Don't overwrite constants already defined by scripts
            existing = self.scopes.get(name)
            if existing is UNINIT:
                self.scopes.define_global(name, value, const=True)

        logger.debug(
            "Loaded .em module constants",
            modules=len(module_names),
            constants=len(constants),
        )

    def run_program(self, program_args: dict[str, Any] | list[Any] | None = None) -> Any:
        """Execute the program entry point with given arguments.

        Parameters
        ----------
        program_args:
            If dict: maps parameter names to values.
            If list: positional arguments matched to program parameters.
            If None: no arguments.

        Returns
        -------
        Any:
            The return value of the program (if any).
        """
        if self._program is None:
            raise RuntimeError("No program declaration found in parsed files")

        prog_name, params, body = self._program

        # Bind program parameters
        if isinstance(program_args, dict):
            for param in params:
                if param.unused:
                    self.scopes.define(param.name, UNINIT)
                    continue
                key = param.name.lower()
                # Try exact match, then case-insensitive
                value = program_args.get(param.name, UNINIT)
                if value is UNINIT:
                    value = program_args.get(key, UNINIT)
                    if value is UNINIT:
                        # Try case-insensitive search
                        for k, v in program_args.items():
                            if k.lower() == key:
                                value = v
                                break
                if value is UNINIT and param.default_ctx is not None:
                    value = self._interpreter.visit(param.default_ctx)
                self.scopes.define(param.name, value)
        elif isinstance(program_args, list):
            for i, param in enumerate(params):
                if param.unused:
                    self.scopes.define(param.name, UNINIT)
                elif i < len(program_args):
                    self.scopes.define(param.name, program_args[i])
                elif param.default_ctx is not None:
                    self.scopes.define(param.name, self._interpreter.visit(param.default_ctx))
                else:
                    self.scopes.define(param.name, UNINIT)
        else:
            for param in params:
                if param.default_ctx is not None:
                    self.scopes.define(param.name, self._interpreter.visit(param.default_ctx))
                else:
                    self.scopes.define(param.name, UNINIT)

        logger.info("Executing program", name=prog_name, param_count=len(params))

        try:
            self._interpreter.visitBlock(body)
        except ExitSignal:
            pass
        except ReturnSignal as ret:
            return ret.value

        return None

    def run_sub_program(self, script_path: str, args: list[Any]) -> Any:
        """Execute a sub-script program (e.g., from ``start_script``).

        Resolves the script path, parses the ``.src`` file on first use,
        and runs its program block with scope isolation.  The args list
        is passed as positional arguments — POL convention passes the
        array as the first (and only) positional argument.

        Parameters
        ----------
        script_path:
            Script path in ``:package:name`` format
            (e.g., ``":combat:reactivearmoronhit"``).
        args:
            List of arguments.  Passed as positional args to the program.

        Returns
        -------
        Any:
            The return value of the sub-script program (if any).
        """
        # Normalize key for cache lookup
        key = script_path.strip().lower()

        if key not in self._sub_programs:
            self._load_sub_script(script_path, key)

        prog_name, params, body = self._sub_programs[key]

        # Scope isolation: save depth, push new scope, run, pop back
        saved_depth = self.scopes.depth

        # Bind program parameters — POL passes the array as positional args
        self.scopes.push()
        try:
            for i, param in enumerate(params):
                if param.unused:
                    self.scopes.define(param.name, UNINIT)
                elif i < len(args):
                    self.scopes.define(param.name, args[i])
                elif param.default_ctx is not None:
                    self.scopes.define(param.name, self._interpreter.visit(param.default_ctx))
                else:
                    self.scopes.define(param.name, UNINIT)

            logger.info("Executing sub-program", name=prog_name, script=script_path)

            try:
                self._interpreter.visitBlock(body)
            except ExitSignal:
                pass
            except ReturnSignal as ret:
                return ret.value
        finally:
            # Pop back to saved depth (handles any scopes pushed by
            # function calls within the sub-script that didn't clean up)
            while self.scopes.depth > saved_depth:
                self.scopes.pop()

        return None

    def _load_sub_script(self, script_path: str, cache_key: str) -> None:
        """Parse a sub-script .src file and cache its program block."""
        resolved = self._resolve_script_path(script_path)

        from omega.parser.parser import parse_file

        result = parse_file(resolved)
        if result.tree is None:
            raise RuntimeError(
                f"Failed to parse sub-script: {script_path} "
                f"(resolved to {resolved})"
            )

        # Extract USE declarations (usually already registered)
        for module in extract_use_declarations(result.tree):
            self.functions.add_module(module)

        # Extract any functions defined in the sub-script
        for func_def in extract_functions(result.tree, source_file=str(resolved)):
            if not self.functions.has(func_def.name):
                self.functions.register(func_def)

        # Extract the program block
        prog = extract_program(result.tree)
        if prog is None:
            raise RuntimeError(
                f"No program declaration in sub-script: {script_path} "
                f"(resolved to {resolved})"
            )

        self._sub_programs[cache_key] = prog
        logger.info(
            "Loaded sub-script",
            script=script_path,
            program=prog[0],
            param_count=len(prog[1]),
        )

    def _resolve_script_path(self, script_path: str) -> Path:
        """Resolve a script path like ``:combat:reactivearmoronhit`` to a .src file."""
        if self._shard_root is None or self._package_map is None:
            raise RuntimeError(
                f"Cannot resolve sub-script path {script_path!r}: "
                "Executor was created without shard_root/package_map"
            )

        path = script_path.strip().strip('"').strip("'")

        if path.startswith(":"):
            # Package path: ":combat:reactivearmoronhit" → pkg/.../reactivearmoronhit.src
            parts = path.lstrip(":").split(":", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid script path: {script_path!r}")

            pkg_name, file_name = parts
            pkg_dir = self._package_map.resolve(pkg_name)
            if pkg_dir is None:
                raise FileNotFoundError(f"Unknown package: {pkg_name!r}")

            # Try .src extension first, then without
            for candidate in [
                pkg_dir / f"{file_name}.src",
                pkg_dir / file_name,
            ]:
                if candidate.exists():
                    return candidate.resolve()

            raise FileNotFoundError(
                f"Sub-script not found: {script_path!r} "
                f"(tried {pkg_dir / f'{file_name}.src'})"
            )
        else:
            # Relative path
            scripts_dir = self._shard_root / "scripts"
            for candidate in [
                scripts_dir / f"{path}.src",
                scripts_dir / path,
                self._shard_root / f"{path}.src",
                self._shard_root / path,
            ]:
                if candidate.exists():
                    return candidate.resolve()

            raise FileNotFoundError(f"Sub-script not found: {script_path!r}")

    def call_function(self, name: str, args: list[Any] | None = None) -> Any:
        """Call a named function directly (for testing/integration).

        Parameters
        ----------
        name:
            Function name (case-insensitive).
        args:
            Positional arguments.
        """
        func_def = self.functions.get(name)
        if func_def is None:
            raise RuntimeError(f"Function '{name}' not found")
        return self._interpreter._call_user_function(func_def, args or [])

    @property
    def interpreter(self) -> EscriptInterpreter:
        """Access the underlying interpreter (for advanced use)."""
        return self._interpreter

    @property
    def program_name(self) -> str | None:
        """Name of the loaded program, or None."""
        return self._program[0] if self._program else None

    @property
    def function_count(self) -> int:
        """Number of registered user-defined functions."""
        return len(self.functions.function_names)
