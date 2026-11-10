"""Peak-memory baseline for input_is_nested_too_deeply.

The value is a wide list of ints under ``[Int]``. The depth check returns
False. The input list is built before tracing starts.
"""

from __future__ import annotations

from measure import emit, peak_bytes, repeat
from graphql import GraphQLInt, GraphQLList
from graphql.execution.values import input_is_nested_too_deeply

WIDTH = 50000


def main() -> None:
    value = list(range(WIDTH))
    list_type = GraphQLList(GraphQLInt)
    if input_is_nested_too_deeply(value, list_type):
        raise RuntimeError("flat list was reported as nested too deeply")

    def check() -> None:
        if input_is_nested_too_deeply(value, list_type):
            raise RuntimeError("flat list was reported as nested too deeply")

    emit("peak_memory_bytes", repeat(lambda: peak_bytes(check)))


if __name__ == "__main__":
    main()
