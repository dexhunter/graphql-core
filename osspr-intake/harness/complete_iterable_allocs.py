"""Allocation baseline for Executor.complete_iterable_value.

Executes ``{ nums }`` where ``nums`` is a list of ints. Only allocations inside
``complete_iterable_value`` and the callees it runs are counted. The response
list must equal the input list.
"""

from __future__ import annotations

from measure import _counter, emit, repeat
from graphql import build_schema, graphql_sync
from graphql.execution.executor import Executor

ITEM_COUNT = 6000


def main() -> None:
    counter = _counter()
    schema = build_schema("type Query { nums: [Int] }")
    items = list(range(ITEM_COUNT))
    root = {"nums": items}
    query = "{ nums }"
    recorded: list[int] = []
    original = Executor.complete_iterable_value

    def wrapped(self, *args, **kwargs):
        counter.alloc_reset()
        try:
            return original(self, *args, **kwargs)
        finally:
            recorded.append(int(counter.alloc_stop()))

    Executor.complete_iterable_value = wrapped

    def execute() -> None:
        recorded.clear()
        result = graphql_sync(schema, query, root_value=root)
        if result.errors:
            raise RuntimeError(result.errors)
        if result.data != {"nums": items}:
            raise RuntimeError("completed list does not match the input")
        if len(recorded) != 1:
            raise RuntimeError(f"expected one list completion, saw {len(recorded)}")

    def one_count() -> int:
        execute()
        return recorded[0]

    try:
        emit("allocations", repeat(one_count))
    finally:
        Executor.complete_iterable_value = original


if __name__ == "__main__":
    main()
