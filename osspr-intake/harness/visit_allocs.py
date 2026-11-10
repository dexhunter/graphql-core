"""Allocation baseline for graphql.language.visitor.visit.

The workload is one read-only walk of a wide operation. The visitor defines no
enter or leave methods, and the walk returns the original document.
"""

from __future__ import annotations

from measure import count_allocations, emit, repeat
from graphql.language.parser import parse
from graphql.language.visitor import Visitor, visit

FIELD_COUNT = 12000


def build():
    source = "{ " + " ".join(f"f{i}" for i in range(FIELD_COUNT)) + " }"
    document = parse(source)
    visitor = Visitor()
    # Fill the per-kind enter/leave cache before the recorded trials.
    if visit(document, visitor) is not document:
        raise RuntimeError("read-only visit did not return the original document")
    return document, visitor


def main() -> None:
    document, visitor = build()

    def walk() -> None:
        result = visit(document, visitor)
        if result is not document:
            raise RuntimeError("read-only visit did not return the original document")

    emit("allocations", repeat(lambda: count_allocations(walk)))


if __name__ == "__main__":
    main()
