#!/usr/bin/env bash
# Regenerate the ANTLR4 Python lexer/parser from the grammar files.
# Requires: uv, antlr4-tools (uv pip install antlr4-tools), Java 11+
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GRAMMAR_DIR="$PROJECT_ROOT/src/omega/parser/grammar"
GEN_DIR="$PROJECT_ROOT/src/omega/parser/gen"

export ANTLR4_TOOLS_ANTLR_VERSION=4.13.2

echo "Generating lexer..."
cd "$GRAMMAR_DIR"
uv run antlr4 -Dlanguage=Python3 -o "$GEN_DIR" -visitor EscriptLexer.g4

echo "Generating parser..."
uv run antlr4 -Dlanguage=Python3 -o "$GEN_DIR" -lib "$GEN_DIR" -visitor EscriptParser.g4

echo "Done. Generated files in $GEN_DIR"
