"""Time LexicalDistance.measure on realistic unknown-field suggestions.

Each sample is one pass of the suggestion scan used when validation reports
unknown fields: several typos against every field name of each GitHub schema
type that has at least 15 fields.
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
from graphql.pyutils.suggestion_list import LexicalDistance

REPEATS = 31
WARMUP = 5
TYPOS = (
    "namee",
    "idd",
    "repositry",
    "creatdAt",
    "updatdAt",
    "descripton",
    "urlh",
    "titlee",
)


def main() -> None:
    schema = build_schema(
        (ROOT / "tests/fixtures/github_schema.graphql").read_text(encoding="utf-8"),
        assume_valid=True,
    )
    field_sets: list[tuple[str, ...]] = []
    for type_ in schema.type_map.values():
        fields = getattr(type_, "fields", None)
        if isinstance(fields, dict) and len(fields) >= 15:
            field_sets.append(tuple(fields))

    def block() -> int:
        hits = 0
        for fields in field_sets:
            for typo in TYPOS:
                distance = LexicalDistance(typo)
                threshold = int(len(typo) * 0.4) + 1
                measure = distance.measure
                for name in fields:
                    if measure(name, threshold) is not None:
                        hits += 1
        return hits

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
