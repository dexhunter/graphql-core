"""Time is_printable_as_block_string on GitHub schema descriptions.

Each sample scans every type and field description of at least 80 characters,
25 times. Schema printing calls this once per description.
"""

from __future__ import annotations

import gc
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from graphql import build_schema
from graphql.language.block_string import is_printable_as_block_string

REPEATS = 25
WARMUP = 4
PASSES = 25


def main() -> None:
    schema = build_schema(
        (ROOT / "tests/fixtures/github_schema.graphql").read_text(encoding="utf-8"),
        assume_valid=True,
    )
    descriptions: list[str] = []
    for type_ in schema.type_map.values():
        candidates = [getattr(type_, "description", None)]
        fields = getattr(type_, "fields", None)
        if isinstance(fields, dict):
            for field in fields.values():
                candidates.append(getattr(field, "description", None))
        for description in candidates:
            if isinstance(description, str) and len(description) >= 80:
                descriptions.append(description)

    def block() -> int:
        printable = 0
        predicate = is_printable_as_block_string
        for _ in range(PASSES):
            for description in descriptions:
                if predicate(description):
                    printable += 1
        return printable

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
