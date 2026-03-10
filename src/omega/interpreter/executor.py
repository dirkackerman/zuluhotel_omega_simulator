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
    ) -> None:
        self.scopes = ScopeStack()
        self.functions = FunctionRegistry()
        self._program: tuple[str, list[ParamDef], Any] | None = None
        self._interpreter = EscriptInterpreter(self.scopes, self.functions)
        self._em_modules_dir = em_modules_dir

        self._load(parse_results)

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
