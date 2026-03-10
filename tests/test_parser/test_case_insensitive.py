"""Tests for case-insensitive eScript parsing."""

from omega.parser import parse_text


class TestCaseInsensitiveKeywords:
    """eScript keywords must be case-insensitive."""

    def test_if_variations(self):
        for kw in ["IF", "if", "If", "iF"]:
            r = parse_text(f"{kw} (x) var y := 1; endif")
            assert r.success, f"Failed for keyword: {kw}"

    def test_var_variations(self):
        for kw in ["VAR", "var", "Var", "vAr"]:
            r = parse_text(f"{kw} x := 5;")
            assert r.success, f"Failed for keyword: {kw}"

    def test_function_variations(self):
        for kw_f, kw_e in [
            ("FUNCTION", "ENDFUNCTION"),
            ("function", "endfunction"),
            ("Function", "EndFunction"),
        ]:
            r = parse_text(f"{kw_f} foo() return 1; {kw_e}")
            assert r.success, f"Failed for: {kw_f}/{kw_e}"

    def test_program_variations(self):
        for kw_p, kw_e in [
            ("PROGRAM", "ENDPROGRAM"),
            ("program", "endprogram"),
            ("Program", "EndProgram"),
        ]:
            r = parse_text(f"{kw_p} main() {kw_e}")
            assert r.success, f"Failed for: {kw_p}/{kw_e}"

    def test_while_variations(self):
        for kw_w, kw_e in [
            ("WHILE", "ENDWHILE"),
            ("while", "endwhile"),
            ("While", "EndWhile"),
        ]:
            r = parse_text(f"{kw_w} (1) break; {kw_e}")
            assert r.success, f"Failed for: {kw_w}/{kw_e}"

    def test_foreach_variations(self):
        r = parse_text("FOREACH x IN arr var y := x; ENDFOREACH")
        assert r.success
        r = parse_text("Foreach x In arr var y := x; EndForeach")
        assert r.success

    def test_use_include_variations(self):
        r = parse_text('USE uo; INCLUDE "test";')
        assert r.success
        r = parse_text('Use uo; Include "test";')
        assert r.success

    def test_logical_word_operators_case(self):
        r = parse_text("var x := a AND b OR NOT c;")
        assert r.success
        r = parse_text("var x := a And b Or Not c;")
        assert r.success


class TestCasePreservation:
    """Identifiers should preserve their original case."""

    def test_identifier_case_preserved(self):
        r = parse_text("var MyVariable := 5;")
        assert r.success
        # The parse tree should contain the identifier with original case
        # We verify this by checking the tree has the token
        tree = r.tree
        # Walk to find the var statement
        decl = tree.topLevelDeclaration(0)
        stmt = decl.statement()
        var_stmt = stmt.varStatement()
        var_decl = var_stmt.variableDeclarationList().variableDeclaration(0)
        ident = var_decl.IDENTIFIER()
        # Original text preserves case
        assert ident.symbol.text == "MyVariable"
