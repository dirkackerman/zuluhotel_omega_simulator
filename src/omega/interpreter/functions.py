"""Function registry for user-defined eScript functions.

Collects function declarations from parsed files and provides lookup
for the interpreter's call dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from omega.interpreter.types import UNINIT
from omega.parser.gen.EscriptParser import EscriptParser


@dataclass
class ParamDef:
    """Definition of a function parameter."""

    name: str
    byref: bool = False
    unused: bool = False
    default: Any = UNINIT
    default_ctx: EscriptParser.ExpressionContext | None = None


@dataclass
class FunctionDef:
    """A user-defined eScript function."""

    name: str
    params: list[ParamDef] = field(default_factory=list)
    body: EscriptParser.BlockContext | None = None
    source_file: str = ""
    exported: bool = False


class FunctionRegistry:
    """Stores user-defined functions by name (case-insensitive).

    Functions are extracted from parsed files during the loading phase
    and looked up during execution.
    """

    def __init__(self) -> None:
        self._functions: dict[str, FunctionDef] = {}
        self._modules: set[str] = set()  # USE declarations

    def register(self, func_def: FunctionDef) -> None:
        """Register a function definition."""
        self._functions[func_def.name.lower()] = func_def

    def get(self, name: str) -> FunctionDef | None:
        """Look up a function by name (case-insensitive)."""
        return self._functions.get(name.lower())

    def has(self, name: str) -> bool:
        """Check if a function is registered."""
        return name.lower() in self._functions

    def add_module(self, module_name: str) -> None:
        """Record a USE declaration."""
        self._modules.add(module_name.lower())

    def has_module(self, module_name: str) -> bool:
        """Check if a module was USE'd."""
        return module_name.lower() in self._modules

    @property
    def function_names(self) -> list[str]:
        """Return all registered function names."""
        return list(self._functions.keys())

    @property
    def module_names(self) -> list[str]:
        """Return all USE'd module names."""
        return sorted(self._modules)

    def clear(self) -> None:
        """Clear all functions and modules."""
        self._functions.clear()
        self._modules.clear()


def extract_functions(
    tree: EscriptParser.CompilationUnitContext,
    source_file: str = "",
) -> list[FunctionDef]:
    """Extract function definitions from a parsed compilation unit.

    Returns a list of FunctionDef objects ready for registration.
    """
    functions: list[FunctionDef] = []

    for decl in tree.topLevelDeclaration() or []:
        func_decl = decl.functionDeclaration()
        if func_decl is None:
            continue

        name = func_decl.IDENTIFIER().getText()
        exported = func_decl.EXPORTED() is not None
        body = func_decl.block()
        params = _extract_params(func_decl.functionParameters())

        functions.append(
            FunctionDef(
                name=name,
                params=params,
                body=body,
                source_file=source_file,
                exported=exported,
            )
        )

    return functions


def extract_use_declarations(tree: EscriptParser.CompilationUnitContext) -> list[str]:
    """Extract USE module names from a parsed compilation unit."""
    modules: list[str] = []
    for decl in tree.topLevelDeclaration() or []:
        use = decl.useDeclaration()
        if use is not None:
            string_id = use.stringIdentifier()
            text = string_id.getText()
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            elif text.startswith("'") and text.endswith("'"):
                text = text[1:-1]
            modules.append(text)
    return modules


def extract_constants(
    tree: EscriptParser.CompilationUnitContext,
) -> list[tuple[str, EscriptParser.ExpressionContext | None, bool]]:
    """Extract top-level const and enum declarations.

    Returns list of (name, expression_ctx_or_None, is_enum_entry).
    For enums, the expression may be None (auto-increment).
    """
    constants: list[tuple[str, EscriptParser.ExpressionContext | None, bool]] = []

    for decl in tree.topLevelDeclaration() or []:
        stmt = decl.statement()
        if stmt is None:
            continue

        # const declarations
        const = stmt.constStatement()
        if const is not None:
            var_decl = const.variableDeclaration()
            name = var_decl.IDENTIFIER().getText()
            init = var_decl.variableDeclarationInitializer()
            expr = init.expression() if init is not None and init.expression() is not None else None
            constants.append((name, expr, False))

        # enum declarations
        enum = stmt.enumStatement()
        if enum is not None:
            for entry in enum.enumList().enumListEntry():
                name = entry.IDENTIFIER().getText()
                expr = entry.expression()
                constants.append((name, expr, True))

    return constants


def _extract_params(
    params_ctx: EscriptParser.FunctionParametersContext,
) -> list[ParamDef]:
    """Extract parameter definitions from a function's parameter list."""
    params: list[ParamDef] = []
    param_list = params_ctx.functionParameterList()
    if param_list is None:
        return params

    for param in param_list.functionParameter():
        name = param.IDENTIFIER().getText()
        byref = param.BYREF() is not None
        unused = param.UNUSED() is not None
        expr = param.expression()
        default_ctx = expr if expr is not None else None

        params.append(
            ParamDef(
                name=name,
                byref=byref,
                unused=unused,
                default=UNINIT,
                default_ctx=default_ctx,
            )
        )

    return params


def extract_program(
    tree: EscriptParser.CompilationUnitContext,
) -> tuple[str, list[ParamDef], EscriptParser.BlockContext] | None:
    """Extract the program declaration from a compilation unit.

    Returns (name, params, body) or None if no program found.
    """
    for decl in tree.topLevelDeclaration() or []:
        prog = decl.programDeclaration()
        if prog is None:
            continue

        name = prog.IDENTIFIER().getText()
        body = prog.block()
        params = _extract_program_params(prog.programParameters())
        return (name, params, body)

    return None


def _extract_program_params(
    params_ctx: EscriptParser.ProgramParametersContext,
) -> list[ParamDef]:
    """Extract parameter definitions from a program's parameter list."""
    params: list[ParamDef] = []
    param_list = params_ctx.programParameterList()
    if param_list is None:
        return params

    for param in param_list.programParameter():
        ident = param.IDENTIFIER()
        if ident is None:
            continue
        name = ident.getText()
        unused = param.UNUSED() is not None
        expr = param.expression()
        default_ctx = expr if expr is not None else None

        params.append(
            ParamDef(
                name=name,
                byref=False,
                unused=unused,
                default=UNINIT,
                default_ctx=default_ctx,
            )
        )

    return params
