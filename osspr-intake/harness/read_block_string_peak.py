"""Peak-memory baseline for Lexer.read_block_string.

The source is a block string whose lines share a two-space indent. The token
value is checked against one untimed call, which is the dedented block value.
"""

from __future__ import annotations

from measure import emit, peak_bytes, repeat
from graphql.language.lexer import Lexer
from graphql.language.source import Source
from graphql.language.token_kind import TokenKind

LINE_COUNT = 2500
LINE = "  " + ("abc " * 8)


def build():
    body = '"""\n' + ((LINE + "\n") * LINE_COUNT) + '"""'
    source = Source(body)
    expected = Lexer(source).read_block_string(0)
    if expected.kind is not TokenKind.BLOCK_STRING or not expected.value:
        raise RuntimeError("block string did not lex")
    if any(line.startswith("  ") for line in expected.value.split("\n") if line):
        raise RuntimeError("block string kept its common indent")
    return source, expected.value


def main() -> None:
    source, expected = build()
    lexer = Lexer(source)

    def read() -> None:
        token = lexer.read_block_string(0)
        if token.value != expected:
            raise RuntimeError("block string value changed")

    emit("peak_memory_bytes", repeat(lambda: peak_bytes(read)))


if __name__ == "__main__":
    main()
