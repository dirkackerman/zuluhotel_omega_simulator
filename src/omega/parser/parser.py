"""eScript parser — public API for parsing .src and .inc files.

Usage::

    from omega.parser import parse_file, parse_with_includes

    # Parse a single file (no include resolution)
    tree = parse_file("var x := 5;")

    # Parse an entry file with all includes resolved
    trees = parse_with_includes(Path("mainhit.src"), shard_root, package_map)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from antlr4 import CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener

from omega.logging import get_logger
from omega.parser.case_insensitive_stream import CaseInsensitiveInputStream
from omega.parser.gen.EscriptLexer import EscriptLexer
from omega.parser.gen.EscriptParser import EscriptParser
from omega.parser.include_resolver import (
    DictPackageMap,
    IncludeResolver,
    PackageMap,
)

logger = get_logger("omega.parser")


class ParseError:
    """A single parse error with location info."""

    def __init__(self, line: int, column: int, msg: str, file: str = "<string>") -> None:
        self.line = line
        self.column = column
        self.msg = msg
        self.file = file

    def __repr__(self) -> str:
        return f"ParseError({self.file}:{self.line}:{self.column}: {self.msg})"


class _CollectingErrorListener(ErrorListener):
    """Collects parse errors instead of printing to stderr."""

    def __init__(self, file: str = "<string>") -> None:
        self.errors: list[ParseError] = []
        self._file = file

    def syntaxError(
        self,
        recognizer: Any,
        offendingSymbol: Any,
        line: int,
        column: int,
        msg: str,
        e: Any,
    ) -> None:
        error = ParseError(line, column, msg, self._file)
        self.errors.append(error)
        logger.warning("parse error", file=self._file, line=line, column=column, detail=msg)


class ParseResult:
    """Result of parsing a single file."""

    def __init__(
        self,
        tree: EscriptParser.CompilationUnitContext,
        errors: list[ParseError],
        file: str = "<string>",
    ) -> None:
        self.tree = tree
        self.errors = errors
        self.file = file

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


def parse_text(source: str, file: str = "<string>") -> ParseResult:
    """Parse eScript source text into a parse tree.

    Parameters
    ----------
    source:
        eScript source code as a string.
    file:
        Filename for error messages.

    Returns
    -------
    ParseResult:
        Contains the parse tree and any errors encountered.
    """
    input_stream = CaseInsensitiveInputStream(source)
    lexer = EscriptLexer(input_stream)

    # Remove default error listener, add our collector
    lexer.removeErrorListeners()
    lexer_errors = _CollectingErrorListener(file)
    lexer.addErrorListener(lexer_errors)

    token_stream = CommonTokenStream(lexer)

    parser = EscriptParser(token_stream)
    parser.removeErrorListeners()
    parser_errors = _CollectingErrorListener(file)
    parser.addErrorListener(parser_errors)

    tree = parser.compilationUnit()

    all_errors = lexer_errors.errors + parser_errors.errors
    if all_errors:
        logger.warning("parse completed with errors", file=file, error_count=len(all_errors))
    else:
        logger.debug("parse completed successfully", file=file)

    return ParseResult(tree, all_errors, file)


def parse_file(path: Path) -> ParseResult:
    """Parse a single eScript file.

    Parameters
    ----------
    path:
        Path to a ``.src`` or ``.inc`` file.

    Returns
    -------
    ParseResult:
        Contains the parse tree and any errors encountered.
    """
    source = path.read_text(encoding="utf-8", errors="replace")
    return parse_text(source, file=str(path))


def parse_with_includes(
    entry_path: Path,
    shard_root: Path,
    package_map: PackageMap | dict[str, Path] | None = None,
) -> dict[Path, ParseResult]:
    """Parse an eScript file and all its includes recursively.

    Parameters
    ----------
    entry_path:
        Path to the entry ``.src`` file.
    shard_root:
        Root directory of the shard.
    package_map:
        Package name → directory mapping. If a dict is passed, it is
        wrapped in a ``DictPackageMap``. If None, an empty map is used.

    Returns
    -------
    dict[Path, ParseResult]:
        Map of resolved file path → parse result for the entry file
        and all included files.
    """
    if package_map is None:
        pkg_map: PackageMap = DictPackageMap({})
    elif isinstance(package_map, dict):
        pkg_map = DictPackageMap(package_map)
    else:
        pkg_map = package_map

    resolver = IncludeResolver(shard_root, pkg_map)
    results: dict[Path, ParseResult] = {}

    _parse_recursive(entry_path.resolve(), resolver, results)

    total_errors = sum(len(r.errors) for r in results.values())
    if total_errors:
        logger.warning(
            "parse_with_includes completed",
            files=len(results),
            total_errors=total_errors,
        )
    else:
        logger.info(
            "parse_with_includes completed",
            files=len(results),
            total_errors=0,
        )

    return results


def _parse_recursive(
    file_path: Path,
    resolver: IncludeResolver,
    results: dict[Path, ParseResult],
) -> None:
    """Parse a file and recursively parse its includes."""
    resolved = file_path.resolve()

    if not resolver.mark_included(resolved):
        return  # Already included

    result = parse_file(resolved)
    results[resolved] = result

    if not result.success:
        return  # Don't follow includes from files with errors

    # Walk the parse tree to find include declarations
    includes = _extract_includes(result.tree)
    for include_path in includes:
        try:
            included_file = resolver.resolve(include_path, from_file=resolved)
            _parse_recursive(included_file, resolver, results)
        except (FileNotFoundError, ValueError) as exc:
            logger.warning(
                "include resolution failed "
                "(hint: package names are case-sensitive on Linux — "
                "check pkg.cfg Name field matches the include path exactly)",
                from_file=resolved.name,
                include_path=include_path,
                error=str(exc),
            )
            result.errors.append(
                ParseError(0, 0, f"Include resolution failed: {exc}", str(resolved))
            )


def _extract_includes(tree: EscriptParser.CompilationUnitContext) -> list[str]:
    """Extract include paths from a parsed compilation unit."""
    includes: list[str] = []

    for decl in tree.topLevelDeclaration() or []:
        inc = decl.includeDeclaration()
        if inc is not None:
            string_id = inc.stringIdentifier()
            if string_id is not None:
                text = string_id.getText()
                # Strip quotes if it's a string literal
                if text.startswith('"') and text.endswith('"'):
                    text = text[1:-1]
                elif text.startswith("'") and text.endswith("'"):
                    text = text[1:-1]
                includes.append(text)

    return includes
