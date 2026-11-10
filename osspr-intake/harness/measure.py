"""Shared baseline measurement for osspr-intake harnesses.

Allocation counts are object-allocator calls (PYMEM_DOMAIN_OBJ malloc, calloc,
and realloc) while the counter is enabled. Peak bytes are the tracemalloc
high-water mark of memory allocated after tracing starts. The garbage collector
is disabled for the recorded trials so a collection cannot add extra blocks.
"""

from __future__ import annotations

import ctypes
import gc
import json
import subprocess
import sys
import tracemalloc
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

WARMUP = 3
TRIALS = 5

_COUNTER: ctypes.CDLL | None = None


def _counter() -> ctypes.CDLL:
    global _COUNTER
    if _COUNTER is not None:
        return _COUNTER
    source = Path(__file__).with_name("alloccount.c")
    binary = Path("/tmp/ossp-graphql-alloccount.so")
    if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
        subprocess.check_call(
            [
                "gcc",
                "-shared",
                "-fPIC",
                "-O2",
                "-o",
                str(binary),
                str(source),
                "-ldl",
            ]
        )
    lib = ctypes.CDLL(str(binary))
    lib.alloc_install.argtypes = []
    lib.alloc_install.restype = None
    lib.alloc_installed.argtypes = []
    lib.alloc_installed.restype = ctypes.c_int
    lib.alloc_reset.argtypes = []
    lib.alloc_reset.restype = None
    lib.alloc_stop.argtypes = []
    lib.alloc_stop.restype = ctypes.c_uint64
    lib.alloc_install()
    if not lib.alloc_installed():
        msg = "PyMem_GetAllocator was not found; allocation counter is not installed"
        raise RuntimeError(msg)
    _COUNTER = lib
    return lib


def count_allocations(fn: Callable[[], Any]) -> int:
    """Return object allocations performed by one call to ``fn``."""
    lib = _counter()
    lib.alloc_reset()
    fn()
    return int(lib.alloc_stop())


def peak_bytes(fn: Callable[[], Any]) -> int:
    """Return the tracemalloc peak of one call to ``fn``.

    Blocks allocated before tracing starts, including the workload inputs, are
    not included. ``tracemalloc.reset_peak`` runs immediately before ``fn``.
    """
    tracemalloc.stop()
    tracemalloc.start(1)
    tracemalloc.reset_peak()
    fn()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return int(peak)


def repeat(measure: Callable[[], int]) -> list[int]:
    """Warm up, then return ``TRIALS`` samples with the collector disabled.

    Samples are collected in a plain loop. A list comprehension's first
    iteration was enough to add one 56-byte block to the following peak.
    """
    gc.collect()
    gc.disable()
    try:
        for _ in range(WARMUP):
            measure()
        samples = []
        # The first call after the result list is created picks up one extra
        # 56-byte block under tracemalloc. Drop that call, then record.
        measure()
        for _ in range(TRIALS):
            samples.append(measure())
        return samples
    finally:
        gc.enable()


def summarize(metric_kind: str, samples: list[int]) -> dict[str, Any]:
    ordered = sorted(samples)
    median = ordered[len(ordered) // 2]
    spread = max(samples) - min(samples)
    noise = 0.0 if median == 0 else (spread / median) * 100.0
    return {
        "metric_kind": metric_kind,
        "samples": samples,
        "median": median,
        "noise_pct": noise,
    }


def emit(metric_kind: str, samples: list[int]) -> None:
    json.dump(summarize(metric_kind, samples), sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    def allocate_objects() -> None:
        sink = [object() for _ in range(4000)]
        if len(sink) != 4000:
            raise RuntimeError("allocation self-test built the wrong list")

    samples = repeat(lambda: count_allocations(allocate_objects))
    emit("allocations", samples)
