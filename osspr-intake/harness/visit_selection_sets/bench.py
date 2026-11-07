"""Time visit_selection_sets on a wide selection set.

Each sample collects a 4000-field query selection 28 times. That is the
per-request field walk used before resolvers run.
"""

from __future__ import annotations

import gc
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from graphql import (
    GraphQLField,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
    parse,
)
from graphql.execution.collect_fields import CollectFieldsContext, visit_selection_sets
from graphql.execution.values import VariableValues

REPEATS = 25
WARMUP = 4
FIELD_COUNT = 4000
PASSES = 28


def main() -> None:
    source = "{\n" + "\n".join(f"f{i}" for i in range(FIELD_COUNT)) + "\n}\n"
    document = parse(source)
    operation = document.definitions[0]
    selection_set = operation.selection_set
    query_type = GraphQLObjectType(
        "Query",
        {f"f{i}": GraphQLField(GraphQLString) for i in range(FIELD_COUNT)},
    )
    schema = GraphQLSchema(query_type)
    context = CollectFieldsContext(
        schema,
        {},
        VariableValues({}, {}),
        operation,
        query_type,
        {},
        False,
        [],
        False,
        None,
    )

    def block() -> int:
        total = 0
        for _ in range(PASSES):
            grouped: dict = defaultdict(list)
            visit_selection_sets(context, selection_set, grouped, [])
            total += len(grouped)
        return total

    for _ in range(WARMUP):
        block()
    gc.collect()
    gc.freeze()
    gc.disable()
    samples: list[float] = []
    try:
        for _ in range(REPEATS):
            start = time.perf_counter()
            block()
            samples.append((time.perf_counter() - start) * 1000.0)
    finally:
        gc.enable()
        gc.unfreeze()
    print(f"{statistics.median(samples):.4f}")


if __name__ == "__main__":
    main()
