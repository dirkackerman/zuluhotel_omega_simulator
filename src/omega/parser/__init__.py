"""eScript parser package — parse .src and .inc files into ANTLR4 parse trees."""

from omega.parser.parser import ParseError, ParseResult, parse_file, parse_text, parse_with_includes

__all__ = ["ParseError", "ParseResult", "parse_file", "parse_text", "parse_with_includes"]
