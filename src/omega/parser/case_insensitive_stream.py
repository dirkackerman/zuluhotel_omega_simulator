"""Case-insensitive input stream for eScript parsing.

eScript keywords are case-insensitive (IF, if, If all valid).
The ANTLR4 lexer grammar defines keywords in lowercase, so we lowercase
the input stream before the lexer sees it. Identifiers preserve their
original case via the parse tree's token text.
"""

from __future__ import annotations

from antlr4 import InputStream


class CaseInsensitiveInputStream(InputStream):
    """InputStream that presents lowercased characters to the lexer.

    The original text is preserved — only ``LA()`` (lookahead) returns
    lowered codepoints so the lexer matches case-insensitively.
    """

    def __init__(self, data: str) -> None:
        super().__init__(data)
        self._lowered = data.lower()

    def LA(self, offset: int) -> int:  # noqa: N802 — matches ANTLR4 API
        if offset == 0:
            return 0
        if offset < 0:
            offset += 1
        pos = self.index + offset - 1
        if pos < 0 or pos >= self.size:
            return -1  # EOF
        return ord(self._lowered[pos])
