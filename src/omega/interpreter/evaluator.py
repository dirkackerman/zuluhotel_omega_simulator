"""eScript tree-walking interpreter.

Visits the ANTLR4 parse tree and evaluates eScript code. Handles:
- Expression evaluation (arithmetic, comparison, logical, member access)
- Statement execution (var, const, if, while, for, foreach, case, etc.)
- Control flow via exceptions (ReturnSignal, BreakSignal, ContinueSignal, ExitSignal)
"""

from __future__ import annotations

from typing import Any

from omega.interpreter.scope import ByRef, ScopeStack
from omega.interpreter.types import (
    UNINIT,
    EArray,
    EDict,
    EError,
    EStruct,
    is_truthy,
)
from omega.logging import get_logger
from antlr4 import TerminalNode

from omega.parser.gen.EscriptParser import EscriptParser
from omega.parser.gen.EscriptParserVisitor import EscriptParserVisitor

# Pre-build type dispatch table for visitPrimary.
# Maps ANTLR4 context class → handler name (resolved at first call).
_PRIMARY_RULE_TYPES: tuple[type, ...] = (
    EscriptParser.LiteralContext,
    EscriptParser.ParExpressionContext,
    EscriptParser.FunctionCallContext,
    EscriptParser.ScopedFunctionCallContext,
    EscriptParser.FunctionReferenceContext,
    EscriptParser.ExplicitArrayInitializerContext,
    EscriptParser.BareArrayInitializerContext,
    EscriptParser.ExplicitStructInitializerContext,
    EscriptParser.ExplicitDictInitializerContext,
    EscriptParser.ExplicitErrorInitializerContext,
)

logger = get_logger("omega.interpreter")


# --- Control flow signals ---

class ReturnSignal(Exception):
    def __init__(self, value: Any = None) -> None:
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ExitSignal(Exception):
    pass


class EscriptInterpreter(EscriptParserVisitor):
    """Tree-walking interpreter for eScript parse trees."""

    def __init__(self, scopes: ScopeStack, function_registry: Any = None) -> None:
        self.scopes = scopes
        self.functions = function_registry  # Set by executor

    # ------------------------------------------------------------------
    # Compilation unit / top-level
    # ------------------------------------------------------------------

    def visitCompilationUnit(self, ctx: EscriptParser.CompilationUnitContext) -> Any:
        result = None
        for decl in ctx.topLevelDeclaration() or []:
            result = self.visit(decl)
        return result

    def visitTopLevelDeclaration(self, ctx: EscriptParser.TopLevelDeclarationContext) -> Any:
        # Dispatch to the specific declaration type
        child = ctx.getChild(0)
        if child is not None:
            return self.visit(child)
        return None

    # ------------------------------------------------------------------
    # Declarations (use, include, program, function handled at load time)
    # ------------------------------------------------------------------

    def visitUseDeclaration(self, ctx: EscriptParser.UseDeclarationContext) -> None:
        # USE declarations are processed during function loading, not execution
        pass

    def visitIncludeDeclaration(self, ctx: EscriptParser.IncludeDeclarationContext) -> None:
        # Include declarations are processed during parsing, not execution
        pass

    def visitFunctionDeclaration(self, ctx: EscriptParser.FunctionDeclarationContext) -> None:
        # Function declarations are collected during loading, not execution
        pass

    def visitProgramDeclaration(self, ctx: EscriptParser.ProgramDeclarationContext) -> Any:
        # Execute the program block
        return self.visitBlock(ctx.block())

    # ------------------------------------------------------------------
    # Block & statements
    # ------------------------------------------------------------------

    def visitBlock(self, ctx: EscriptParser.BlockContext) -> Any:
        # Direct call to visitStatement avoids visit() → accept() → hasattr() chain
        result = None
        for stmt in ctx.statement() or []:
            result = self.visitStatement(stmt)
        return result

    def visitStatement(self, ctx: EscriptParser.StatementContext) -> Any:
        # Expression statement — direct call avoids visit/accept overhead
        if ctx.statementExpression is not None:
            return self.visitExpression(ctx.statementExpression)
        # Empty statement (bare semicolon)
        if ctx.SEMI() is not None and ctx.getChildCount() == 1:
            return None
        # Delegate to specific statement type via accept (visitor dispatch)
        child = ctx.getChild(0)
        if child is not None:
            return child.accept(self)
        return None

    # ------------------------------------------------------------------
    # Variable & constant declarations
    # ------------------------------------------------------------------

    def visitVarStatement(self, ctx: EscriptParser.VarStatementContext) -> None:
        self.visit(ctx.variableDeclarationList())

    def visitVariableDeclarationList(self, ctx: EscriptParser.VariableDeclarationListContext) -> None:
        for decl in ctx.variableDeclaration():
            self.visit(decl)

    def visitVariableDeclaration(self, ctx: EscriptParser.VariableDeclarationContext) -> None:
        name = ctx.IDENTIFIER().getText()
        init = ctx.variableDeclarationInitializer()
        if init is not None:
            value = self.visit(init)
        else:
            value = UNINIT
        self.scopes.define(name, value)

    def visitVariableDeclarationInitializer(
        self, ctx: EscriptParser.VariableDeclarationInitializerContext
    ) -> Any:
        if ctx.ARRAY() is not None:
            return EArray()
        expr = ctx.expression()
        if expr is not None:
            return self.visit(expr)
        return UNINIT

    def visitConstStatement(self, ctx: EscriptParser.ConstStatementContext) -> None:
        decl = ctx.variableDeclaration()
        name = decl.IDENTIFIER().getText()
        init = decl.variableDeclarationInitializer()
        if init is not None:
            value = self.visit(init)
        else:
            value = UNINIT
        self.scopes.define(name, value, const=True)

    def visitEnumStatement(self, ctx: EscriptParser.EnumStatementContext) -> None:
        counter = 0
        for entry in ctx.enumList().enumListEntry():
            name = entry.IDENTIFIER().getText()
            expr = entry.expression()
            if expr is not None:
                counter = self.visit(expr)
                if not isinstance(counter, int):
                    counter = int(counter)
            self.scopes.define(name, counter, const=True)
            counter += 1

    # ------------------------------------------------------------------
    # Control flow: if/elseif/else
    # ------------------------------------------------------------------

    def visitIfStatement(self, ctx: EscriptParser.IfStatementContext) -> Any:
        par_exprs = ctx.parExpression()
        blocks = ctx.block()

        # First condition (if) — direct call avoids visit/accept
        if is_truthy(self.visitParExpression(par_exprs[0])):
            return self.visitBlock(blocks[0])

        # Elseif conditions
        elseif_count = len(par_exprs) - 1
        for i in range(elseif_count):
            if is_truthy(self.visitParExpression(par_exprs[i + 1])):
                return self.visitBlock(blocks[i + 1])

        # Else block
        if ctx.ELSE() is not None:
            return self.visitBlock(blocks[-1])

        return None

    # ------------------------------------------------------------------
    # Control flow: loops
    # ------------------------------------------------------------------

    def visitWhileStatement(self, ctx: EscriptParser.WhileStatementContext) -> Any:
        result = None
        par = ctx.parExpression()
        blk = ctx.block()
        while is_truthy(self.visitParExpression(par)):
            try:
                result = self.visitBlock(blk)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def visitDoStatement(self, ctx: EscriptParser.DoStatementContext) -> Any:
        result = None
        par = ctx.parExpression()
        blk = ctx.block()
        while True:
            try:
                result = self.visitBlock(blk)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            if not is_truthy(self.visitParExpression(par)):
                break
        return result

    def visitRepeatStatement(self, ctx: EscriptParser.RepeatStatementContext) -> Any:
        result = None
        expr = ctx.expression()
        blk = ctx.block()
        while True:
            try:
                result = self.visitBlock(blk)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            if is_truthy(self.visitExpression(expr)):
                break
        return result

    def visitForStatement(self, ctx: EscriptParser.ForStatementContext) -> Any:
        return self.visit(ctx.forGroup())

    def visitForGroup(self, ctx: EscriptParser.ForGroupContext) -> Any:
        child = ctx.cstyleForStatement()
        if child is not None:
            return self.visit(child)
        return self.visit(ctx.basicForStatement())

    def visitBasicForStatement(self, ctx: EscriptParser.BasicForStatementContext) -> Any:
        name = ctx.IDENTIFIER().getText()
        start = self.visitExpression(ctx.expression(0))
        end = self.visitExpression(ctx.expression(1))
        start = _to_int(start)
        end = _to_int(end)

        self.scopes.define(name, start)
        result = None
        i = start
        while i <= end:
            self.scopes.set(name, i)
            try:
                result = self.visitBlock(ctx.block())
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            i += 1
        return result

    def visitCstyleForStatement(self, ctx: EscriptParser.CstyleForStatementContext) -> Any:
        exprs = ctx.expression()
        blk = ctx.block()
        # init
        self.visitExpression(exprs[0])
        result = None
        while is_truthy(self.visitExpression(exprs[1])):
            try:
                result = self.visitBlock(blk)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            # step
            self.visitExpression(exprs[2])
        return result

    def visitForeachStatement(self, ctx: EscriptParser.ForeachStatementContext) -> Any:
        name = ctx.IDENTIFIER().getText()
        iterable = self.visitForeachIterableExpression(ctx.foreachIterableExpression())
        self.scopes.define(name, UNINIT)

        result = None
        items = _to_iterable(iterable)
        for item in items:
            self.scopes.set(name, item)
            try:
                result = self.visitBlock(ctx.block())
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def visitForeachIterableExpression(
        self, ctx: EscriptParser.ForeachIterableExpressionContext
    ) -> Any:
        # Can be functionCall, scopedFunctionCall, IDENTIFIER, parExpression,
        # bareArrayInitializer, or explicitArrayInitializer
        if ctx.IDENTIFIER() is not None and ctx.functionCall() is None and ctx.scopedFunctionCall() is None:
            return self.scopes.get(ctx.IDENTIFIER().getText())
        child = ctx.getChild(0)
        return self.visit(child)

    # ------------------------------------------------------------------
    # Control flow: case/endcase
    # ------------------------------------------------------------------

    def visitCaseStatement(self, ctx: EscriptParser.CaseStatementContext) -> Any:
        value = self.visitExpression(ctx.expression())

        for group in ctx.switchBlockStatementGroup():
            labels = group.switchLabel()
            matched = False
            for label in labels:
                if label.DEFAULT() is not None:
                    matched = True
                    break
                label_val = self._eval_switch_label(label)
                if value == label_val:
                    matched = True
                    break
            if matched:
                try:
                    return self.visitBlock(group.block())
                except BreakSignal:
                    return None
        return None

    def _eval_switch_label(self, ctx: EscriptParser.SwitchLabelContext) -> Any:
        int_lit = ctx.integerLiteral()
        if int_lit is not None:
            return self._parse_int_literal(int_lit)
        ident = ctx.IDENTIFIER()
        if ident is not None:
            return self.scopes.get(ident.getText())
        str_lit = ctx.STRING_LITERAL()
        if str_lit is not None:
            return _strip_quotes(str_lit.getText())
        return None

    # ------------------------------------------------------------------
    # Control flow: return, break, continue, exit
    # ------------------------------------------------------------------

    def visitReturnStatement(self, ctx: EscriptParser.ReturnStatementContext) -> None:
        expr = ctx.expression()
        value = self.visit(expr) if expr is not None else None
        raise ReturnSignal(value)

    def visitBreakStatement(self, ctx: EscriptParser.BreakStatementContext) -> None:
        raise BreakSignal()

    def visitContinueStatement(self, ctx: EscriptParser.ContinueStatementContext) -> None:
        raise ContinueSignal()

    def visitExitStatement(self, ctx: EscriptParser.ExitStatementContext) -> None:
        raise ExitSignal()

    def visitGotoStatement(self, ctx: EscriptParser.GotoStatementContext) -> None:
        logger.warning("goto statement not supported", label=ctx.IDENTIFIER().getText())

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def visitExpression(self, ctx: EscriptParser.ExpressionContext) -> Any:
        # Fast path: use pre-set token attributes to avoid getTypedRuleContext.
        children = ctx.children

        # Single child → must be a primary (most common case)
        if len(children) == 1:
            return self.visitPrimary(children[0])

        # Binary operator — very common (3 children: expr bop expr)
        bop = ctx.bop
        if bop is not None:
            op = bop.text.lower()
            return self._eval_binary(op, children[0], children[2] if len(children) > 2 else None, ctx)

        # Two children: prefix+expr or expr+postfix or expr+suffix
        if ctx.prefix is not None:
            op = ctx.prefix.text.lower()
            val = self.visitExpression(children[1])
            if op == "+":
                return _to_number(val)
            elif op == "-":
                return -_to_number(val)
            elif op == "++":
                name = self._get_lvalue_name(children[1])
                val = _to_number(val) + 1
                self.scopes.set(name, val)
                return val
            elif op == "--":
                name = self._get_lvalue_name(children[1])
                val = _to_number(val) - 1
                self.scopes.set(name, val)
                return val
            elif op in ("~",):
                return ~_to_int(val)
            elif op in ("!", "not"):
                return 0 if is_truthy(val) else 1

        if ctx.postfix is not None:
            op = ctx.postfix.text
            name = self._get_lvalue_name(children[0])
            val = self.visitExpression(children[0])
            val = _to_number(val)
            if op == "++":
                self.scopes.set(name, val + 1)
                return val
            else:
                self.scopes.set(name, val - 1)
                return val

        # Expression suffix (member access, indexing, method call)
        # Two children: expr + suffix
        if len(children) == 2 and isinstance(children[1], EscriptParser.ExpressionSuffixContext):
            obj = self.visitExpression(children[0])
            return self._eval_suffix(obj, children[1], children[0])

        # Fallback
        return self.visitExpression(children[0])

    def _eval_binary(
        self,
        op: str,
        left_ctx: EscriptParser.ExpressionContext,
        right_ctx: EscriptParser.ExpressionContext | None,
        parent_ctx: EscriptParser.ExpressionContext,
    ) -> Any:
        # Assignment operators — need lvalue handling
        if op in (":=", "+=", "-=", "*=", "/=", "%="):
            return self._eval_assignment(op, left_ctx, right_ctx)

        # Short-circuit logical operators
        if op in ("&&", "and"):
            left = self.visitExpression(left_ctx)
            if not is_truthy(left):
                return left
            return self.visitExpression(right_ctx)

        if op in ("||", "or"):
            left = self.visitExpression(left_ctx)
            if is_truthy(left):
                return left
            return self.visitExpression(right_ctx)

        # Eager evaluation for all other operators
        left = self.visitExpression(left_ctx)
        right = self.visitExpression(right_ctx) if right_ctx is not None else None

        # Arithmetic
        if op == "+":
            return _add(left, right)
        if op == "-":
            return _sub(left, right)
        if op == "*":
            return _mul(left, right)
        if op == "/":
            return _div(left, right)
        if op == "%":
            return _to_int(left) % _to_int(right) if _to_int(right) != 0 else 0

        # Bitwise
        if op == "&":
            return _to_int(left) & _to_int(right)
        if op == "|":
            return _to_int(left) | _to_int(right)
        if op == "^":
            return _to_int(left) ^ _to_int(right)
        if op == "<<":
            return _to_int(left) << _to_int(right)
        if op == ">>":
            return _to_int(left) >> _to_int(right)

        # Comparison
        if op == "==":
            return 1 if _eq(left, right) else 0
        if op in ("!=", "<>"):
            return 1 if not _eq(left, right) else 0
        if op == "<":
            return 1 if _compare(left, right) < 0 else 0
        if op == ">":
            return 1 if _compare(left, right) > 0 else 0
        if op == "<=":
            return 1 if _compare(left, right) <= 0 else 0
        if op == ">=":
            return 1 if _compare(left, right) >= 0 else 0
        if op == "=":
            # Deprecated = treated as ==
            return 1 if _eq(left, right) else 0

        # Elvis operator
        if op == "?:":
            return left if is_truthy(left) else right

        # In operator
        if op == "in":
            return 1 if _in_check(left, right) else 0

        # String interpolation ops (.+ .- .?)
        if op == ".+":
            return str(left if left is not None else "") + str(right if right is not None else "")
        if op == ".-":
            return str(left if left is not None else "") + str(right if right is not None else "")
        if op == ".?":
            return str(left if left is not None else "") + str(right if right is not None else "")

        logger.warning("Unknown binary operator", op=op)
        return None

    def _eval_assignment(
        self,
        op: str,
        left_ctx: EscriptParser.ExpressionContext,
        right_ctx: EscriptParser.ExpressionContext | None,
    ) -> Any:
        right = self.visitExpression(right_ctx) if right_ctx is not None else UNINIT

        # Simple variable assignment
        lvalue = self._resolve_lvalue(left_ctx)
        if lvalue is not None:
            kind, target = lvalue
            if kind == "var":
                if op == ":=":
                    value = right
                else:
                    old = self.scopes.get(target)
                    value = _compound_assign(op, old, right)
                self.scopes.set(target, value)
                return value
            elif kind == "index":
                obj, index = target
                if op == ":=":
                    value = right
                else:
                    old = _get_index(obj, index)
                    value = _compound_assign(op, old, right)
                _set_index(obj, index, value)
                return value
            elif kind == "member":
                obj, member_name = target
                if op == ":=":
                    value = right
                else:
                    old = _get_member(obj, member_name)
                    value = _compound_assign(op, old, right)
                _set_member(obj, member_name, value)
                return value

        # Fallback: try as simple variable name
        name = self._get_lvalue_name(left_ctx)
        if op == ":=":
            value = right
        else:
            old = self.scopes.get(name)
            value = _compound_assign(op, old, right)
        self.scopes.set(name, value)
        return value

    def _resolve_lvalue(self, ctx: EscriptParser.ExpressionContext) -> tuple[str, Any] | None:
        """Resolve an expression to an lvalue target.

        Returns:
            ("var", name) for simple variables
            ("index", (obj, index)) for indexed access
            ("member", (obj, member_name)) for member access
            None if cannot be resolved
        """
        # Check for suffix expressions (indexing or member access)
        suffix = ctx.expressionSuffix()
        if suffix is not None:
            exprs = ctx.expression()
            obj = self.visit(exprs[0])

            idx_suffix = suffix.indexingSuffix()
            if idx_suffix is not None:
                indices = [self.visit(e) for e in idx_suffix.expressionList().expression()]
                if len(indices) == 1:
                    return ("index", (obj, indices[0]))
                # Multi-dimensional: resolve down to penultimate
                current = obj
                for idx in indices[:-1]:
                    current = _get_index(current, idx)
                return ("index", (current, indices[-1]))

            nav = suffix.navigationSuffix()
            if nav is not None:
                member = nav.IDENTIFIER()
                if member is not None:
                    return ("member", (obj, member.getText()))
                str_lit = nav.STRING_LITERAL()
                if str_lit is not None:
                    return ("member", (obj, _strip_quotes(str_lit.getText())))

        # Simple identifier
        primary = ctx.primary()
        if primary is not None:
            ident = primary.IDENTIFIER()
            if ident is not None:
                return ("var", ident.getText())

        return None

    def _get_lvalue_name(self, ctx: EscriptParser.ExpressionContext) -> str:
        """Extract variable name from a simple identifier expression."""
        primary = ctx.primary()
        if primary is not None:
            ident = primary.IDENTIFIER()
            if ident is not None:
                return ident.getText()
        # For expression suffixes, this shouldn't be called
        return ctx.getText()

    # ------------------------------------------------------------------
    # Expression suffixes (member access, method calls, indexing)
    # ------------------------------------------------------------------

    def _eval_suffix(
        self,
        obj: Any,
        suffix: EscriptParser.ExpressionSuffixContext,
        obj_ctx: EscriptParser.ExpressionContext,
    ) -> Any:
        # Indexing: obj[expr] or obj[start, end] (string substring)
        idx = suffix.indexingSuffix()
        if idx is not None:
            indices = [self.visitExpression(e) for e in idx.expressionList().expression()]
            # eScript string slicing: str[start, end] → substring (1-based)
            if isinstance(obj, str) and len(indices) == 2:
                start = max(1, _to_int(indices[0]))
                end = _to_int(indices[1])
                return obj[start - 1 : end]
            result = obj
            for index in indices:
                result = _get_index(result, index)
            return result

        # Method call: obj.method(args)
        method = suffix.methodCallSuffix()
        if method is not None:
            name = method.IDENTIFIER().getText()
            expr_list = method.expressionList()
            args = [self.visitExpression(e) for e in expr_list.expression()] if expr_list else []
            return self._call_method(obj, name, args)

        # Navigation: obj.member
        nav = suffix.navigationSuffix()
        if nav is not None:
            ident = nav.IDENTIFIER()
            if ident is not None:
                return _get_member(obj, ident.getText())
            str_lit = nav.STRING_LITERAL()
            if str_lit is not None:
                return _get_member(obj, _strip_quotes(str_lit.getText()))

        return obj

    def _call_method(self, obj: Any, name: str, args: list[Any]) -> Any:
        """Dispatch a method call on an object."""
        lower_name = name.lower()

        # EArray methods
        if isinstance(obj, EArray):
            if lower_name == "append":
                for a in args:
                    obj.append(a)
                return None
            if lower_name == "shrink":
                if args:
                    obj.shrink(_to_int(args[0]))
                return None
            if lower_name == "size":
                return len(obj)

        # EDict methods
        if isinstance(obj, EDict):
            if lower_name == "exists":
                return obj.exists(args[0]) if args else 0
            if lower_name == "erase":
                if args:
                    obj.erase(args[0])
                return None
            if lower_name == "keys":
                return EArray(list(obj))
            if lower_name == "size":
                return len(obj)

        # EStruct methods
        if isinstance(obj, EStruct):
            if lower_name == "size":
                return len(obj.keys())

        # Game object methods
        if lower_name in ("isa", "is_a"):
            if args:
                if hasattr(obj, "isa"):
                    return 1 if obj.isa(args[0]) else 0
            return 0

        # setwarmode, backpack, etc. — no-ops or property access
        if lower_name == "setwarmode":
            return None

        # Generic: try calling as a POL built-in method
        # Some methods like IsEnemyGuild, IsAllyGuild are on stub objects
        method = getattr(obj, name, None) or getattr(obj, lower_name, None)
        if callable(method):
            return method(*args)

        logger.warning("Unknown method call", object_type=type(obj).__name__, method=name)
        return None

    # ------------------------------------------------------------------
    # Primary expressions
    # ------------------------------------------------------------------

    def visitPrimary(self, ctx: EscriptParser.PrimaryContext) -> Any:
        # Fast path: dispatch on the type of the first child node
        # instead of 11 sequential getTypedRuleContext calls.
        child = ctx.children[0]

        # Most common case: terminal node (IDENTIFIER)
        if isinstance(child, TerminalNode):
            return self.scopes.get(child.getText())

        # Rule context nodes — visit directly
        child_type = type(child)
        if child_type in _PRIMARY_RULE_TYPES:
            # Special case: functionReference returns name, not visited
            if child_type is EscriptParser.FunctionReferenceContext:
                return child.IDENTIFIER().getText()
            return self.visit(child)

        return UNINIT

    # ------------------------------------------------------------------
    # Literals
    # ------------------------------------------------------------------

    def visitLiteral(self, ctx: EscriptParser.LiteralContext) -> Any:
        # Fast dispatch on first child type instead of sequential getTypedRuleContext
        child = ctx.children[0]
        if isinstance(child, TerminalNode):
            # STRING_LITERAL or CHAR_LITERAL
            return _strip_quotes(child.getText())
        # integerLiteral or floatLiteral context
        child_type = type(child)
        if child_type is EscriptParser.IntegerLiteralContext:
            return self._parse_int_literal(child)
        if child_type is EscriptParser.FloatLiteralContext:
            return float(child.getText())
        return UNINIT

    def _parse_int_literal(self, ctx: EscriptParser.IntegerLiteralContext) -> int:
        if ctx.HEX_LITERAL() is not None:
            return int(ctx.getText(), 16)
        if ctx.OCT_LITERAL() is not None:
            return int(ctx.getText(), 8)
        if ctx.BINARY_LITERAL() is not None:
            return int(ctx.getText(), 2)
        return int(ctx.getText())

    def visitParExpression(self, ctx: EscriptParser.ParExpressionContext) -> Any:
        return self.visitExpression(ctx.expression())

    # ------------------------------------------------------------------
    # Initializers
    # ------------------------------------------------------------------

    def visitExplicitArrayInitializer(
        self, ctx: EscriptParser.ExplicitArrayInitializerContext
    ) -> EArray:
        arr_init = ctx.arrayInitializer()
        if arr_init is not None:
            return self.visit(arr_init)
        return EArray()

    def visitArrayInitializer(self, ctx: EscriptParser.ArrayInitializerContext) -> EArray:
        expr_list = ctx.expressionList()
        if expr_list is not None:
            items = [self.visit(e) for e in expr_list.expression()]
            return EArray(items)
        return EArray()

    def visitBareArrayInitializer(
        self, ctx: EscriptParser.BareArrayInitializerContext
    ) -> EArray:
        expr_list = ctx.expressionList()
        if expr_list is not None:
            items = [self.visit(e) for e in expr_list.expression()]
            return EArray(items)
        return EArray()

    def visitExplicitStructInitializer(
        self, ctx: EscriptParser.ExplicitStructInitializerContext
    ) -> EStruct:
        struct_init = ctx.structInitializer()
        if struct_init is not None:
            return self.visit(struct_init)
        return EStruct()

    def visitStructInitializer(self, ctx: EscriptParser.StructInitializerContext) -> EStruct:
        fields: dict[str, Any] = {}
        expr_list = ctx.structInitializerExpressionList()
        if expr_list is not None:
            for entry in expr_list.structInitializerExpression():
                ident = entry.IDENTIFIER()
                str_lit = entry.STRING_LITERAL()
                name = ident.getText() if ident else _strip_quotes(str_lit.getText())
                expr = entry.expression()
                value = self.visit(expr) if expr is not None else UNINIT
                fields[name] = value
        return EStruct(fields)

    def visitExplicitDictInitializer(
        self, ctx: EscriptParser.ExplicitDictInitializerContext
    ) -> EDict:
        d = EDict()
        dict_init = ctx.dictInitializer()
        if dict_init is not None:
            expr_list = dict_init.dictInitializerExpressionList()
            if expr_list is not None:
                for entry in expr_list.dictInitializerExpression():
                    exprs = entry.expression()
                    if len(exprs) == 2:
                        key = self.visit(exprs[0])
                        val = self.visit(exprs[1])
                        d.set(key, val)
                    elif len(exprs) == 1:
                        key = self.visit(exprs[0])
                        d.set(key, UNINIT)
        return d

    def visitExplicitErrorInitializer(
        self, ctx: EscriptParser.ExplicitErrorInitializerContext
    ) -> EError:
        fields: dict[str, Any] = {}
        struct_init = ctx.structInitializer()
        if struct_init is not None:
            expr_list = struct_init.structInitializerExpressionList()
            if expr_list is not None:
                for entry in expr_list.structInitializerExpression():
                    ident = entry.IDENTIFIER()
                    str_lit = entry.STRING_LITERAL()
                    name = ident.getText() if ident else _strip_quotes(str_lit.getText())
                    expr = entry.expression()
                    value = self.visit(expr) if expr is not None else UNINIT
                    fields[name] = value
        return EError(fields)

    # ------------------------------------------------------------------
    # Function calls
    # ------------------------------------------------------------------

    def visitFunctionCall(self, ctx: EscriptParser.FunctionCallContext) -> Any:
        name = ctx.IDENTIFIER().getText()
        expr_list = ctx.expressionList()
        args = [self.visitExpression(e) for e in expr_list.expression()] if expr_list else []

        return self._dispatch_call("", name, args, ctx)

    def visitScopedFunctionCall(self, ctx: EscriptParser.ScopedFunctionCallContext) -> Any:
        module = ctx.IDENTIFIER().getText()
        func_call = ctx.functionCall()
        name = func_call.IDENTIFIER().getText()
        expr_list = func_call.expressionList()
        args = [self.visitExpression(e) for e in expr_list.expression()] if expr_list else []

        return self._dispatch_call(module, name, args, ctx)

    def _dispatch_call(self, module: str, name: str, args: list[Any], ctx: Any) -> Any:
        """Dispatch a function call — user-defined first, then built-in.

        Python callable overrides (registered via FunctionRegistry.set_override)
        replace user-defined functions when present.  This is how the simulator
        injects metric-recording implementations for eScript no-op stubs.
        """
        # Check for Python callable overrides (e.g., __RecordSimulatorMetric)
        if not module and self.functions is not None:
            override = self.functions.get_override(name)
            if override is not None:
                return override(*args)

        # Try user-defined function (only for bare calls)
        if not module and self.functions is not None:
            func_def = self.functions.get(name)
            if func_def is not None:
                return self._call_user_function(func_def, args)

        # Dispatch to POL runtime stubs
        from omega.runtime.registry import call_builtin

        return call_builtin(module, name, args)

    def _call_user_function(self, func_def: Any, args: list[Any]) -> Any:
        """Call a user-defined eScript function."""
        scope = self.scopes.push()

        try:
            # Bind parameters
            params = func_def.params
            for i, param in enumerate(params):
                if param.byref and i < len(args) and isinstance(args[i], ByRef):
                    scope.define(param.name, args[i])
                elif param.byref and i < len(args):
                    # Create a ByRef if caller passed a variable name
                    # For now, just pass the value
                    scope.define(param.name, args[i] if i < len(args) else param.default)
                elif i < len(args):
                    scope.define(param.name, args[i])
                elif param.default_ctx is not None:
                    scope.define(param.name, self.visit(param.default_ctx))
                elif param.default is not UNINIT:
                    scope.define(param.name, param.default)
                else:
                    scope.define(param.name, UNINIT)

            # Execute function body
            self.visitBlock(func_def.body)
            return None  # implicit return
        except ReturnSignal as ret:
            return ret.value
        finally:
            self.scopes.pop()

    # ------------------------------------------------------------------
    # Expression list helper
    # ------------------------------------------------------------------

    def visitExpressionList(self, ctx: EscriptParser.ExpressionListContext) -> list[Any]:
        return [self.visit(e) for e in ctx.expression()]


# ======================================================================
# Helper functions — type coercion, arithmetic, comparison
# ======================================================================


def _strip_quotes(text: str) -> str:
    """Remove surrounding quotes from a string literal."""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        return text[1:-1]
    return text


def _to_number(val: Any) -> int | float:
    """Coerce a value to a number."""
    if val is None or val is UNINIT:
        return 0
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, str):
        try:
            if "." in val:
                return float(val)
            return int(val)
        except (ValueError, TypeError):
            return 0
    return 0


def _to_int(val: Any) -> int:
    """Coerce a value to int."""
    n = _to_number(val)
    return int(n)


def _add(left: Any, right: Any) -> Any:
    """eScript + operator: numeric add or string concat."""
    if isinstance(left, str) or isinstance(right, str):
        l_str = str(left) if left is not None and left is not UNINIT else ""
        r_str = str(right) if right is not None and right is not UNINIT else ""
        return l_str + r_str
    l_num = _to_number(left)
    r_num = _to_number(right)
    if isinstance(l_num, float) or isinstance(r_num, float):
        return float(l_num) + float(r_num)
    return l_num + r_num


def _sub(left: Any, right: Any) -> int | float:
    l_num = _to_number(left)
    r_num = _to_number(right)
    if isinstance(l_num, float) or isinstance(r_num, float):
        return float(l_num) - float(r_num)
    return l_num - r_num


def _mul(left: Any, right: Any) -> int | float:
    l_num = _to_number(left)
    r_num = _to_number(right)
    if isinstance(l_num, float) or isinstance(r_num, float):
        return float(l_num) * float(r_num)
    return l_num * r_num


def _div(left: Any, right: Any) -> int | float:
    l_num = _to_number(left)
    r_num = _to_number(right)
    if r_num == 0:
        return 0
    result = l_num / r_num
    # If both operands were int and result is whole, return int
    if isinstance(l_num, int) and isinstance(r_num, int) and result == int(result):
        return int(result)
    return result


def _compound_assign(op: str, old: Any, right: Any) -> Any:
    """Apply compound assignment operator."""
    if op == "+=":
        return _add(old, right)
    if op == "-=":
        return _sub(old, right)
    if op == "*=":
        return _mul(old, right)
    if op == "/=":
        return _div(old, right)
    if op == "%=":
        return _to_int(old) % _to_int(right) if _to_int(right) != 0 else 0
    return right


def _eq(left: Any, right: Any) -> bool:
    """eScript equality comparison."""
    if left is None or left is UNINIT:
        return right is None or right is UNINIT
    if right is None or right is UNINIT:
        return left is None or left is UNINIT
    # Numeric comparison if both can be numbers
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left) == float(right)
    # String comparison
    if isinstance(left, str) and isinstance(right, str):
        return left == right
    # Mixed: try numeric, fallback to string
    if isinstance(left, (int, float)) and isinstance(right, str):
        try:
            return float(left) == float(right)
        except ValueError:
            return str(left) == right
    if isinstance(left, str) and isinstance(right, (int, float)):
        try:
            return float(left) == float(right)
        except ValueError:
            return left == str(right)
    return left == right


def _compare(left: Any, right: Any) -> int:
    """Three-way comparison for eScript. Returns <0, 0, >0."""
    l_num = _to_number(left)
    r_num = _to_number(right)
    if l_num < r_num:
        return -1
    if l_num > r_num:
        return 1
    return 0


def _in_check(item: Any, container: Any) -> bool:
    """eScript 'in' operator."""
    if isinstance(container, (EArray, EDict, list, dict)):
        return item in container
    return False


def _get_index(obj: Any, index: Any) -> Any:
    """Get element by index from an array, dict, or game object."""
    if isinstance(obj, EArray):
        return obj.get(_to_int(index))
    if isinstance(obj, EDict):
        return obj.get(index)
    if isinstance(obj, dict):
        return obj.get(index, UNINIT)
    if isinstance(obj, list):
        idx = _to_int(index) - 1  # 1-based
        if 0 <= idx < len(obj):
            return obj[idx]
        return UNINIT
    # Fallback for objects supporting __getitem__ (e.g., RuntimeConfigFile)
    if hasattr(obj, '__getitem__'):
        try:
            result = obj[index]
            return result if result is not None else UNINIT
        except (KeyError, IndexError, TypeError):
            logger.debug(
                "_get_index __getitem__ failed",
                obj_type=type(obj).__name__,
                index=repr(index),
            )
            return UNINIT
    logger.warning(
        "_get_index unhandled type, returning UNINIT",
        obj_type=type(obj).__name__,
        index=repr(index),
    )
    return UNINIT


def _set_index(obj: Any, index: Any, value: Any) -> None:
    """Set element by index on an array, dict, or game object."""
    if isinstance(obj, EArray):
        obj.set(_to_int(index), value)
    elif isinstance(obj, EDict):
        obj.set(index, value)
    elif isinstance(obj, dict):
        obj[index] = value
    elif isinstance(obj, list):
        idx = _to_int(index) - 1
        while len(obj) <= idx:
            obj.append(UNINIT)
        obj[idx] = value


def _get_member(obj: Any, name: str) -> Any:
    """Get a member/property from an object.

    Handles the naming mismatch between eScript (no underscores, e.g.
    ``maxhp``, ``isnpc``) and the Python model (snake_case, e.g.
    ``max_hp``, ``is_npc``) by normalising both sides — stripping
    underscores — when a direct lookup misses.
    """
    if isinstance(obj, EStruct):
        return obj.get_member(name)
    if isinstance(obj, EError):
        return obj.get_member(name)
    if isinstance(obj, EDict):
        return obj.get(name)
    # Game objects — try attribute access
    if obj is None or obj is UNINIT:
        return UNINIT
    lower_name = name.lower()
    # 1. Direct attribute lookup — try original case first (important for
    #    objects like RuntimeConfigElement whose __getattr__ is case-sensitive
    #    and may return None for a wrong-case key), then lowered.
    try:
        val = getattr(obj, name, UNINIT)
        if val is not UNINIT:
            return val
        if lower_name != name:
            val = getattr(obj, lower_name, UNINIT)
            if val is not UNINIT:
                return val
    except Exception:
        pass
    # 2. Underscore-normalised fallback: strip underscores from both the
    #    requested name and every attribute on the object, then match.
    normalized = lower_name.replace("_", "")
    for attr in dir(obj):
        if attr.startswith("_"):
            continue
        if attr.lower().replace("_", "") == normalized:
            logger.debug(
                "Member resolved via underscore normalisation",
                requested=name,
                resolved=attr,
                obj_type=type(obj).__name__,
            )
            try:
                return getattr(obj, attr, UNINIT)
            except Exception:
                pass
    return UNINIT


def _set_member(obj: Any, name: str, value: Any) -> None:
    """Set a member/property on an object."""
    if isinstance(obj, EStruct):
        obj.set_member(name, value)
    elif isinstance(obj, EError):
        obj.set_member(name, value)
    elif isinstance(obj, EDict):
        obj.set(name, value)
    elif obj is not None:
        lower_name = name.lower()
        # 1. Direct set
        try:
            setattr(obj, lower_name, value)
            return
        except AttributeError:
            pass
        try:
            setattr(obj, name, value)
            return
        except AttributeError:
            pass
        # 2. Underscore-normalised fallback
        normalized = lower_name.replace("_", "")
        for attr in dir(obj):
            if attr.startswith("_"):
                continue
            if attr.lower().replace("_", "") == normalized:
                logger.debug(
                    "Member set via underscore normalisation",
                    requested=name,
                    resolved=attr,
                    obj_type=type(obj).__name__,
                )
                try:
                    setattr(obj, attr, value)
                    return
                except AttributeError:
                    pass


def _to_iterable(val: Any) -> list[Any]:
    """Convert a value to an iterable list for foreach."""
    if isinstance(val, EArray):
        return list(val)
    if isinstance(val, EDict):
        return list(val)
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return list(val.keys())
    if val is None or val is UNINIT:
        return []
    return [val]
