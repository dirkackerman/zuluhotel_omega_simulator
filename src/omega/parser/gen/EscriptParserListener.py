# Generated from EscriptParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .EscriptParser import EscriptParser
else:
    from EscriptParser import EscriptParser



# This class defines a complete listener for a parse tree produced by EscriptParser.
class EscriptParserListener(ParseTreeListener):

    # Enter a parse tree produced by EscriptParser#compilationUnit.
    def enterCompilationUnit(self, ctx:EscriptParser.CompilationUnitContext):
        pass

    # Exit a parse tree produced by EscriptParser#compilationUnit.
    def exitCompilationUnit(self, ctx:EscriptParser.CompilationUnitContext):
        pass


    # Enter a parse tree produced by EscriptParser#moduleUnit.
    def enterModuleUnit(self, ctx:EscriptParser.ModuleUnitContext):
        pass

    # Exit a parse tree produced by EscriptParser#moduleUnit.
    def exitModuleUnit(self, ctx:EscriptParser.ModuleUnitContext):
        pass


    # Enter a parse tree produced by EscriptParser#moduleDeclarationStatement.
    def enterModuleDeclarationStatement(self, ctx:EscriptParser.ModuleDeclarationStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#moduleDeclarationStatement.
    def exitModuleDeclarationStatement(self, ctx:EscriptParser.ModuleDeclarationStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#moduleFunctionDeclaration.
    def enterModuleFunctionDeclaration(self, ctx:EscriptParser.ModuleFunctionDeclarationContext):
        pass

    # Exit a parse tree produced by EscriptParser#moduleFunctionDeclaration.
    def exitModuleFunctionDeclaration(self, ctx:EscriptParser.ModuleFunctionDeclarationContext):
        pass


    # Enter a parse tree produced by EscriptParser#moduleFunctionParameterList.
    def enterModuleFunctionParameterList(self, ctx:EscriptParser.ModuleFunctionParameterListContext):
        pass

    # Exit a parse tree produced by EscriptParser#moduleFunctionParameterList.
    def exitModuleFunctionParameterList(self, ctx:EscriptParser.ModuleFunctionParameterListContext):
        pass


    # Enter a parse tree produced by EscriptParser#moduleFunctionParameter.
    def enterModuleFunctionParameter(self, ctx:EscriptParser.ModuleFunctionParameterContext):
        pass

    # Exit a parse tree produced by EscriptParser#moduleFunctionParameter.
    def exitModuleFunctionParameter(self, ctx:EscriptParser.ModuleFunctionParameterContext):
        pass


    # Enter a parse tree produced by EscriptParser#topLevelDeclaration.
    def enterTopLevelDeclaration(self, ctx:EscriptParser.TopLevelDeclarationContext):
        pass

    # Exit a parse tree produced by EscriptParser#topLevelDeclaration.
    def exitTopLevelDeclaration(self, ctx:EscriptParser.TopLevelDeclarationContext):
        pass


    # Enter a parse tree produced by EscriptParser#functionDeclaration.
    def enterFunctionDeclaration(self, ctx:EscriptParser.FunctionDeclarationContext):
        pass

    # Exit a parse tree produced by EscriptParser#functionDeclaration.
    def exitFunctionDeclaration(self, ctx:EscriptParser.FunctionDeclarationContext):
        pass


    # Enter a parse tree produced by EscriptParser#stringIdentifier.
    def enterStringIdentifier(self, ctx:EscriptParser.StringIdentifierContext):
        pass

    # Exit a parse tree produced by EscriptParser#stringIdentifier.
    def exitStringIdentifier(self, ctx:EscriptParser.StringIdentifierContext):
        pass


    # Enter a parse tree produced by EscriptParser#useDeclaration.
    def enterUseDeclaration(self, ctx:EscriptParser.UseDeclarationContext):
        pass

    # Exit a parse tree produced by EscriptParser#useDeclaration.
    def exitUseDeclaration(self, ctx:EscriptParser.UseDeclarationContext):
        pass


    # Enter a parse tree produced by EscriptParser#includeDeclaration.
    def enterIncludeDeclaration(self, ctx:EscriptParser.IncludeDeclarationContext):
        pass

    # Exit a parse tree produced by EscriptParser#includeDeclaration.
    def exitIncludeDeclaration(self, ctx:EscriptParser.IncludeDeclarationContext):
        pass


    # Enter a parse tree produced by EscriptParser#programDeclaration.
    def enterProgramDeclaration(self, ctx:EscriptParser.ProgramDeclarationContext):
        pass

    # Exit a parse tree produced by EscriptParser#programDeclaration.
    def exitProgramDeclaration(self, ctx:EscriptParser.ProgramDeclarationContext):
        pass


    # Enter a parse tree produced by EscriptParser#statement.
    def enterStatement(self, ctx:EscriptParser.StatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#statement.
    def exitStatement(self, ctx:EscriptParser.StatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#statementLabel.
    def enterStatementLabel(self, ctx:EscriptParser.StatementLabelContext):
        pass

    # Exit a parse tree produced by EscriptParser#statementLabel.
    def exitStatementLabel(self, ctx:EscriptParser.StatementLabelContext):
        pass


    # Enter a parse tree produced by EscriptParser#ifStatement.
    def enterIfStatement(self, ctx:EscriptParser.IfStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#ifStatement.
    def exitIfStatement(self, ctx:EscriptParser.IfStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#gotoStatement.
    def enterGotoStatement(self, ctx:EscriptParser.GotoStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#gotoStatement.
    def exitGotoStatement(self, ctx:EscriptParser.GotoStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#returnStatement.
    def enterReturnStatement(self, ctx:EscriptParser.ReturnStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#returnStatement.
    def exitReturnStatement(self, ctx:EscriptParser.ReturnStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#constStatement.
    def enterConstStatement(self, ctx:EscriptParser.ConstStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#constStatement.
    def exitConstStatement(self, ctx:EscriptParser.ConstStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#varStatement.
    def enterVarStatement(self, ctx:EscriptParser.VarStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#varStatement.
    def exitVarStatement(self, ctx:EscriptParser.VarStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#doStatement.
    def enterDoStatement(self, ctx:EscriptParser.DoStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#doStatement.
    def exitDoStatement(self, ctx:EscriptParser.DoStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#whileStatement.
    def enterWhileStatement(self, ctx:EscriptParser.WhileStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#whileStatement.
    def exitWhileStatement(self, ctx:EscriptParser.WhileStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#exitStatement.
    def enterExitStatement(self, ctx:EscriptParser.ExitStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#exitStatement.
    def exitExitStatement(self, ctx:EscriptParser.ExitStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#breakStatement.
    def enterBreakStatement(self, ctx:EscriptParser.BreakStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#breakStatement.
    def exitBreakStatement(self, ctx:EscriptParser.BreakStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#continueStatement.
    def enterContinueStatement(self, ctx:EscriptParser.ContinueStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#continueStatement.
    def exitContinueStatement(self, ctx:EscriptParser.ContinueStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#forStatement.
    def enterForStatement(self, ctx:EscriptParser.ForStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#forStatement.
    def exitForStatement(self, ctx:EscriptParser.ForStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#foreachIterableExpression.
    def enterForeachIterableExpression(self, ctx:EscriptParser.ForeachIterableExpressionContext):
        pass

    # Exit a parse tree produced by EscriptParser#foreachIterableExpression.
    def exitForeachIterableExpression(self, ctx:EscriptParser.ForeachIterableExpressionContext):
        pass


    # Enter a parse tree produced by EscriptParser#foreachStatement.
    def enterForeachStatement(self, ctx:EscriptParser.ForeachStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#foreachStatement.
    def exitForeachStatement(self, ctx:EscriptParser.ForeachStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#repeatStatement.
    def enterRepeatStatement(self, ctx:EscriptParser.RepeatStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#repeatStatement.
    def exitRepeatStatement(self, ctx:EscriptParser.RepeatStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#caseStatement.
    def enterCaseStatement(self, ctx:EscriptParser.CaseStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#caseStatement.
    def exitCaseStatement(self, ctx:EscriptParser.CaseStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#enumStatement.
    def enterEnumStatement(self, ctx:EscriptParser.EnumStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#enumStatement.
    def exitEnumStatement(self, ctx:EscriptParser.EnumStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#block.
    def enterBlock(self, ctx:EscriptParser.BlockContext):
        pass

    # Exit a parse tree produced by EscriptParser#block.
    def exitBlock(self, ctx:EscriptParser.BlockContext):
        pass


    # Enter a parse tree produced by EscriptParser#variableDeclarationInitializer.
    def enterVariableDeclarationInitializer(self, ctx:EscriptParser.VariableDeclarationInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#variableDeclarationInitializer.
    def exitVariableDeclarationInitializer(self, ctx:EscriptParser.VariableDeclarationInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#enumList.
    def enterEnumList(self, ctx:EscriptParser.EnumListContext):
        pass

    # Exit a parse tree produced by EscriptParser#enumList.
    def exitEnumList(self, ctx:EscriptParser.EnumListContext):
        pass


    # Enter a parse tree produced by EscriptParser#enumListEntry.
    def enterEnumListEntry(self, ctx:EscriptParser.EnumListEntryContext):
        pass

    # Exit a parse tree produced by EscriptParser#enumListEntry.
    def exitEnumListEntry(self, ctx:EscriptParser.EnumListEntryContext):
        pass


    # Enter a parse tree produced by EscriptParser#switchBlockStatementGroup.
    def enterSwitchBlockStatementGroup(self, ctx:EscriptParser.SwitchBlockStatementGroupContext):
        pass

    # Exit a parse tree produced by EscriptParser#switchBlockStatementGroup.
    def exitSwitchBlockStatementGroup(self, ctx:EscriptParser.SwitchBlockStatementGroupContext):
        pass


    # Enter a parse tree produced by EscriptParser#switchLabel.
    def enterSwitchLabel(self, ctx:EscriptParser.SwitchLabelContext):
        pass

    # Exit a parse tree produced by EscriptParser#switchLabel.
    def exitSwitchLabel(self, ctx:EscriptParser.SwitchLabelContext):
        pass


    # Enter a parse tree produced by EscriptParser#forGroup.
    def enterForGroup(self, ctx:EscriptParser.ForGroupContext):
        pass

    # Exit a parse tree produced by EscriptParser#forGroup.
    def exitForGroup(self, ctx:EscriptParser.ForGroupContext):
        pass


    # Enter a parse tree produced by EscriptParser#basicForStatement.
    def enterBasicForStatement(self, ctx:EscriptParser.BasicForStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#basicForStatement.
    def exitBasicForStatement(self, ctx:EscriptParser.BasicForStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#cstyleForStatement.
    def enterCstyleForStatement(self, ctx:EscriptParser.CstyleForStatementContext):
        pass

    # Exit a parse tree produced by EscriptParser#cstyleForStatement.
    def exitCstyleForStatement(self, ctx:EscriptParser.CstyleForStatementContext):
        pass


    # Enter a parse tree produced by EscriptParser#identifierList.
    def enterIdentifierList(self, ctx:EscriptParser.IdentifierListContext):
        pass

    # Exit a parse tree produced by EscriptParser#identifierList.
    def exitIdentifierList(self, ctx:EscriptParser.IdentifierListContext):
        pass


    # Enter a parse tree produced by EscriptParser#variableDeclarationList.
    def enterVariableDeclarationList(self, ctx:EscriptParser.VariableDeclarationListContext):
        pass

    # Exit a parse tree produced by EscriptParser#variableDeclarationList.
    def exitVariableDeclarationList(self, ctx:EscriptParser.VariableDeclarationListContext):
        pass


    # Enter a parse tree produced by EscriptParser#variableDeclaration.
    def enterVariableDeclaration(self, ctx:EscriptParser.VariableDeclarationContext):
        pass

    # Exit a parse tree produced by EscriptParser#variableDeclaration.
    def exitVariableDeclaration(self, ctx:EscriptParser.VariableDeclarationContext):
        pass


    # Enter a parse tree produced by EscriptParser#programParameters.
    def enterProgramParameters(self, ctx:EscriptParser.ProgramParametersContext):
        pass

    # Exit a parse tree produced by EscriptParser#programParameters.
    def exitProgramParameters(self, ctx:EscriptParser.ProgramParametersContext):
        pass


    # Enter a parse tree produced by EscriptParser#programParameterList.
    def enterProgramParameterList(self, ctx:EscriptParser.ProgramParameterListContext):
        pass

    # Exit a parse tree produced by EscriptParser#programParameterList.
    def exitProgramParameterList(self, ctx:EscriptParser.ProgramParameterListContext):
        pass


    # Enter a parse tree produced by EscriptParser#programParameter.
    def enterProgramParameter(self, ctx:EscriptParser.ProgramParameterContext):
        pass

    # Exit a parse tree produced by EscriptParser#programParameter.
    def exitProgramParameter(self, ctx:EscriptParser.ProgramParameterContext):
        pass


    # Enter a parse tree produced by EscriptParser#functionParameters.
    def enterFunctionParameters(self, ctx:EscriptParser.FunctionParametersContext):
        pass

    # Exit a parse tree produced by EscriptParser#functionParameters.
    def exitFunctionParameters(self, ctx:EscriptParser.FunctionParametersContext):
        pass


    # Enter a parse tree produced by EscriptParser#functionParameterList.
    def enterFunctionParameterList(self, ctx:EscriptParser.FunctionParameterListContext):
        pass

    # Exit a parse tree produced by EscriptParser#functionParameterList.
    def exitFunctionParameterList(self, ctx:EscriptParser.FunctionParameterListContext):
        pass


    # Enter a parse tree produced by EscriptParser#functionParameter.
    def enterFunctionParameter(self, ctx:EscriptParser.FunctionParameterContext):
        pass

    # Exit a parse tree produced by EscriptParser#functionParameter.
    def exitFunctionParameter(self, ctx:EscriptParser.FunctionParameterContext):
        pass


    # Enter a parse tree produced by EscriptParser#scopedFunctionCall.
    def enterScopedFunctionCall(self, ctx:EscriptParser.ScopedFunctionCallContext):
        pass

    # Exit a parse tree produced by EscriptParser#scopedFunctionCall.
    def exitScopedFunctionCall(self, ctx:EscriptParser.ScopedFunctionCallContext):
        pass


    # Enter a parse tree produced by EscriptParser#functionReference.
    def enterFunctionReference(self, ctx:EscriptParser.FunctionReferenceContext):
        pass

    # Exit a parse tree produced by EscriptParser#functionReference.
    def exitFunctionReference(self, ctx:EscriptParser.FunctionReferenceContext):
        pass


    # Enter a parse tree produced by EscriptParser#expression.
    def enterExpression(self, ctx:EscriptParser.ExpressionContext):
        pass

    # Exit a parse tree produced by EscriptParser#expression.
    def exitExpression(self, ctx:EscriptParser.ExpressionContext):
        pass


    # Enter a parse tree produced by EscriptParser#primary.
    def enterPrimary(self, ctx:EscriptParser.PrimaryContext):
        pass

    # Exit a parse tree produced by EscriptParser#primary.
    def exitPrimary(self, ctx:EscriptParser.PrimaryContext):
        pass


    # Enter a parse tree produced by EscriptParser#explicitArrayInitializer.
    def enterExplicitArrayInitializer(self, ctx:EscriptParser.ExplicitArrayInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#explicitArrayInitializer.
    def exitExplicitArrayInitializer(self, ctx:EscriptParser.ExplicitArrayInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#explicitStructInitializer.
    def enterExplicitStructInitializer(self, ctx:EscriptParser.ExplicitStructInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#explicitStructInitializer.
    def exitExplicitStructInitializer(self, ctx:EscriptParser.ExplicitStructInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#explicitDictInitializer.
    def enterExplicitDictInitializer(self, ctx:EscriptParser.ExplicitDictInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#explicitDictInitializer.
    def exitExplicitDictInitializer(self, ctx:EscriptParser.ExplicitDictInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#explicitErrorInitializer.
    def enterExplicitErrorInitializer(self, ctx:EscriptParser.ExplicitErrorInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#explicitErrorInitializer.
    def exitExplicitErrorInitializer(self, ctx:EscriptParser.ExplicitErrorInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#bareArrayInitializer.
    def enterBareArrayInitializer(self, ctx:EscriptParser.BareArrayInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#bareArrayInitializer.
    def exitBareArrayInitializer(self, ctx:EscriptParser.BareArrayInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#parExpression.
    def enterParExpression(self, ctx:EscriptParser.ParExpressionContext):
        pass

    # Exit a parse tree produced by EscriptParser#parExpression.
    def exitParExpression(self, ctx:EscriptParser.ParExpressionContext):
        pass


    # Enter a parse tree produced by EscriptParser#expressionList.
    def enterExpressionList(self, ctx:EscriptParser.ExpressionListContext):
        pass

    # Exit a parse tree produced by EscriptParser#expressionList.
    def exitExpressionList(self, ctx:EscriptParser.ExpressionListContext):
        pass


    # Enter a parse tree produced by EscriptParser#expressionSuffix.
    def enterExpressionSuffix(self, ctx:EscriptParser.ExpressionSuffixContext):
        pass

    # Exit a parse tree produced by EscriptParser#expressionSuffix.
    def exitExpressionSuffix(self, ctx:EscriptParser.ExpressionSuffixContext):
        pass


    # Enter a parse tree produced by EscriptParser#indexingSuffix.
    def enterIndexingSuffix(self, ctx:EscriptParser.IndexingSuffixContext):
        pass

    # Exit a parse tree produced by EscriptParser#indexingSuffix.
    def exitIndexingSuffix(self, ctx:EscriptParser.IndexingSuffixContext):
        pass


    # Enter a parse tree produced by EscriptParser#navigationSuffix.
    def enterNavigationSuffix(self, ctx:EscriptParser.NavigationSuffixContext):
        pass

    # Exit a parse tree produced by EscriptParser#navigationSuffix.
    def exitNavigationSuffix(self, ctx:EscriptParser.NavigationSuffixContext):
        pass


    # Enter a parse tree produced by EscriptParser#methodCallSuffix.
    def enterMethodCallSuffix(self, ctx:EscriptParser.MethodCallSuffixContext):
        pass

    # Exit a parse tree produced by EscriptParser#methodCallSuffix.
    def exitMethodCallSuffix(self, ctx:EscriptParser.MethodCallSuffixContext):
        pass


    # Enter a parse tree produced by EscriptParser#functionCall.
    def enterFunctionCall(self, ctx:EscriptParser.FunctionCallContext):
        pass

    # Exit a parse tree produced by EscriptParser#functionCall.
    def exitFunctionCall(self, ctx:EscriptParser.FunctionCallContext):
        pass


    # Enter a parse tree produced by EscriptParser#structInitializerExpression.
    def enterStructInitializerExpression(self, ctx:EscriptParser.StructInitializerExpressionContext):
        pass

    # Exit a parse tree produced by EscriptParser#structInitializerExpression.
    def exitStructInitializerExpression(self, ctx:EscriptParser.StructInitializerExpressionContext):
        pass


    # Enter a parse tree produced by EscriptParser#structInitializerExpressionList.
    def enterStructInitializerExpressionList(self, ctx:EscriptParser.StructInitializerExpressionListContext):
        pass

    # Exit a parse tree produced by EscriptParser#structInitializerExpressionList.
    def exitStructInitializerExpressionList(self, ctx:EscriptParser.StructInitializerExpressionListContext):
        pass


    # Enter a parse tree produced by EscriptParser#structInitializer.
    def enterStructInitializer(self, ctx:EscriptParser.StructInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#structInitializer.
    def exitStructInitializer(self, ctx:EscriptParser.StructInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#dictInitializerExpression.
    def enterDictInitializerExpression(self, ctx:EscriptParser.DictInitializerExpressionContext):
        pass

    # Exit a parse tree produced by EscriptParser#dictInitializerExpression.
    def exitDictInitializerExpression(self, ctx:EscriptParser.DictInitializerExpressionContext):
        pass


    # Enter a parse tree produced by EscriptParser#dictInitializerExpressionList.
    def enterDictInitializerExpressionList(self, ctx:EscriptParser.DictInitializerExpressionListContext):
        pass

    # Exit a parse tree produced by EscriptParser#dictInitializerExpressionList.
    def exitDictInitializerExpressionList(self, ctx:EscriptParser.DictInitializerExpressionListContext):
        pass


    # Enter a parse tree produced by EscriptParser#dictInitializer.
    def enterDictInitializer(self, ctx:EscriptParser.DictInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#dictInitializer.
    def exitDictInitializer(self, ctx:EscriptParser.DictInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#arrayInitializer.
    def enterArrayInitializer(self, ctx:EscriptParser.ArrayInitializerContext):
        pass

    # Exit a parse tree produced by EscriptParser#arrayInitializer.
    def exitArrayInitializer(self, ctx:EscriptParser.ArrayInitializerContext):
        pass


    # Enter a parse tree produced by EscriptParser#literal.
    def enterLiteral(self, ctx:EscriptParser.LiteralContext):
        pass

    # Exit a parse tree produced by EscriptParser#literal.
    def exitLiteral(self, ctx:EscriptParser.LiteralContext):
        pass


    # Enter a parse tree produced by EscriptParser#integerLiteral.
    def enterIntegerLiteral(self, ctx:EscriptParser.IntegerLiteralContext):
        pass

    # Exit a parse tree produced by EscriptParser#integerLiteral.
    def exitIntegerLiteral(self, ctx:EscriptParser.IntegerLiteralContext):
        pass


    # Enter a parse tree produced by EscriptParser#floatLiteral.
    def enterFloatLiteral(self, ctx:EscriptParser.FloatLiteralContext):
        pass

    # Exit a parse tree produced by EscriptParser#floatLiteral.
    def exitFloatLiteral(self, ctx:EscriptParser.FloatLiteralContext):
        pass



del EscriptParser