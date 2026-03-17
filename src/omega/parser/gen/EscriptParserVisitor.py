# Generated from EscriptParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .EscriptParser import EscriptParser
else:
    from EscriptParser import EscriptParser



# This class defines a complete generic visitor for a parse tree produced by EscriptParser.

class EscriptParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by EscriptParser#compilationUnit.
    def visitCompilationUnit(self, ctx:EscriptParser.CompilationUnitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#moduleUnit.
    def visitModuleUnit(self, ctx:EscriptParser.ModuleUnitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#moduleDeclarationStatement.
    def visitModuleDeclarationStatement(self, ctx:EscriptParser.ModuleDeclarationStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#moduleFunctionDeclaration.
    def visitModuleFunctionDeclaration(self, ctx:EscriptParser.ModuleFunctionDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#moduleFunctionParameterList.
    def visitModuleFunctionParameterList(self, ctx:EscriptParser.ModuleFunctionParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#moduleFunctionParameter.
    def visitModuleFunctionParameter(self, ctx:EscriptParser.ModuleFunctionParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#topLevelDeclaration.
    def visitTopLevelDeclaration(self, ctx:EscriptParser.TopLevelDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#functionDeclaration.
    def visitFunctionDeclaration(self, ctx:EscriptParser.FunctionDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#stringIdentifier.
    def visitStringIdentifier(self, ctx:EscriptParser.StringIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#useDeclaration.
    def visitUseDeclaration(self, ctx:EscriptParser.UseDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#includeDeclaration.
    def visitIncludeDeclaration(self, ctx:EscriptParser.IncludeDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#programDeclaration.
    def visitProgramDeclaration(self, ctx:EscriptParser.ProgramDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#statement.
    def visitStatement(self, ctx:EscriptParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#statementLabel.
    def visitStatementLabel(self, ctx:EscriptParser.StatementLabelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#ifStatement.
    def visitIfStatement(self, ctx:EscriptParser.IfStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#gotoStatement.
    def visitGotoStatement(self, ctx:EscriptParser.GotoStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#returnStatement.
    def visitReturnStatement(self, ctx:EscriptParser.ReturnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#constStatement.
    def visitConstStatement(self, ctx:EscriptParser.ConstStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#varStatement.
    def visitVarStatement(self, ctx:EscriptParser.VarStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#doStatement.
    def visitDoStatement(self, ctx:EscriptParser.DoStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#whileStatement.
    def visitWhileStatement(self, ctx:EscriptParser.WhileStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#exitStatement.
    def visitExitStatement(self, ctx:EscriptParser.ExitStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#breakStatement.
    def visitBreakStatement(self, ctx:EscriptParser.BreakStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#continueStatement.
    def visitContinueStatement(self, ctx:EscriptParser.ContinueStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#forStatement.
    def visitForStatement(self, ctx:EscriptParser.ForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#foreachIterableExpression.
    def visitForeachIterableExpression(self, ctx:EscriptParser.ForeachIterableExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#foreachStatement.
    def visitForeachStatement(self, ctx:EscriptParser.ForeachStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#repeatStatement.
    def visitRepeatStatement(self, ctx:EscriptParser.RepeatStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#caseStatement.
    def visitCaseStatement(self, ctx:EscriptParser.CaseStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#enumStatement.
    def visitEnumStatement(self, ctx:EscriptParser.EnumStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#block.
    def visitBlock(self, ctx:EscriptParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#variableDeclarationInitializer.
    def visitVariableDeclarationInitializer(self, ctx:EscriptParser.VariableDeclarationInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#enumList.
    def visitEnumList(self, ctx:EscriptParser.EnumListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#enumListEntry.
    def visitEnumListEntry(self, ctx:EscriptParser.EnumListEntryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#switchBlockStatementGroup.
    def visitSwitchBlockStatementGroup(self, ctx:EscriptParser.SwitchBlockStatementGroupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#switchLabel.
    def visitSwitchLabel(self, ctx:EscriptParser.SwitchLabelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#forGroup.
    def visitForGroup(self, ctx:EscriptParser.ForGroupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#basicForStatement.
    def visitBasicForStatement(self, ctx:EscriptParser.BasicForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#cstyleForStatement.
    def visitCstyleForStatement(self, ctx:EscriptParser.CstyleForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#identifierList.
    def visitIdentifierList(self, ctx:EscriptParser.IdentifierListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#variableDeclarationList.
    def visitVariableDeclarationList(self, ctx:EscriptParser.VariableDeclarationListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#variableDeclaration.
    def visitVariableDeclaration(self, ctx:EscriptParser.VariableDeclarationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#programParameters.
    def visitProgramParameters(self, ctx:EscriptParser.ProgramParametersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#programParameterList.
    def visitProgramParameterList(self, ctx:EscriptParser.ProgramParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#programParameter.
    def visitProgramParameter(self, ctx:EscriptParser.ProgramParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#functionParameters.
    def visitFunctionParameters(self, ctx:EscriptParser.FunctionParametersContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#functionParameterList.
    def visitFunctionParameterList(self, ctx:EscriptParser.FunctionParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#functionParameter.
    def visitFunctionParameter(self, ctx:EscriptParser.FunctionParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#scopedFunctionCall.
    def visitScopedFunctionCall(self, ctx:EscriptParser.ScopedFunctionCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#functionReference.
    def visitFunctionReference(self, ctx:EscriptParser.FunctionReferenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#expression.
    def visitExpression(self, ctx:EscriptParser.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#primary.
    def visitPrimary(self, ctx:EscriptParser.PrimaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#explicitArrayInitializer.
    def visitExplicitArrayInitializer(self, ctx:EscriptParser.ExplicitArrayInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#explicitStructInitializer.
    def visitExplicitStructInitializer(self, ctx:EscriptParser.ExplicitStructInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#explicitDictInitializer.
    def visitExplicitDictInitializer(self, ctx:EscriptParser.ExplicitDictInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#explicitErrorInitializer.
    def visitExplicitErrorInitializer(self, ctx:EscriptParser.ExplicitErrorInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#bareArrayInitializer.
    def visitBareArrayInitializer(self, ctx:EscriptParser.BareArrayInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#parExpression.
    def visitParExpression(self, ctx:EscriptParser.ParExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#expressionList.
    def visitExpressionList(self, ctx:EscriptParser.ExpressionListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#expressionSuffix.
    def visitExpressionSuffix(self, ctx:EscriptParser.ExpressionSuffixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#indexingSuffix.
    def visitIndexingSuffix(self, ctx:EscriptParser.IndexingSuffixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#navigationSuffix.
    def visitNavigationSuffix(self, ctx:EscriptParser.NavigationSuffixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#methodCallSuffix.
    def visitMethodCallSuffix(self, ctx:EscriptParser.MethodCallSuffixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#functionCall.
    def visitFunctionCall(self, ctx:EscriptParser.FunctionCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#structInitializerExpression.
    def visitStructInitializerExpression(self, ctx:EscriptParser.StructInitializerExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#structInitializerExpressionList.
    def visitStructInitializerExpressionList(self, ctx:EscriptParser.StructInitializerExpressionListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#structInitializer.
    def visitStructInitializer(self, ctx:EscriptParser.StructInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#dictInitializerExpression.
    def visitDictInitializerExpression(self, ctx:EscriptParser.DictInitializerExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#dictInitializerExpressionList.
    def visitDictInitializerExpressionList(self, ctx:EscriptParser.DictInitializerExpressionListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#dictInitializer.
    def visitDictInitializer(self, ctx:EscriptParser.DictInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#arrayInitializer.
    def visitArrayInitializer(self, ctx:EscriptParser.ArrayInitializerContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#literal.
    def visitLiteral(self, ctx:EscriptParser.LiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#integerLiteral.
    def visitIntegerLiteral(self, ctx:EscriptParser.IntegerLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by EscriptParser#floatLiteral.
    def visitFloatLiteral(self, ctx:EscriptParser.FloatLiteralContext):
        return self.visitChildren(ctx)



del EscriptParser