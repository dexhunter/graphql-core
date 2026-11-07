"""Time natural_comparison_key on the GitHub schema's type and field names.

Each sample builds a sort key for every type name and field name 40 times.
Schema sorting and suggestion ordering both use this key.
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
from graphql.pyutils.natural_compare import natural_comparison_key

REPEATS = 25
WARMUP = 4
PASSES = 40


def main() -> None:
    schema = build_schema(
        (ROOT / "tests/fixtures/github_schema.graphql").read_text(encoding="utf-8"),
        assume_valid=True,
    )
    names: list[str] = []
    for type_ in schema.type_map.values():
        names.append(type_.name)
        fields = getattr(type_, "fields", None)
        if isinstance(fields, dict):
            names.extend(fields)
    names_tuple = tuple(names)

    def block() -> int:
        total = 0
        key = natural_comparison_key
        for _ in range(PASSES):
            for name in names_tuple:
                total += len(key(name))
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
