"""Write and recall cost at a given store size, measured separately (#522).

Opens the installed-facade path (``AgentMemory.open``) over the qualified SQLite
runtime, fills it to each requested fact count, then times a window of further
writes and a window of recalls. Selected persistence and recall components are
wrapped with timers so the integrity share of a write is visible on its own.

The script is revision-agnostic: components absent at a revision report
``null``. Timing depends on the host; record the host and whether it was shared.

    PYTHONPATH=reference python3 reference/run_write_recall_scaling.py \
        --sizes 100 1000 --output scaling.json
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import subprocess
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.runtime import runtime_composition, sqlite_runtime
from agentmem_ref.runtime.adapter import GovernedMemoryAdapter
from agentmem_ref.state.sqlite_substrate import SQLiteTemporalGraph

COMPONENTS = {
    "substrate.state_digest": (SQLiteTemporalGraph, "state_digest"),
    "substrate.incremental_state_digest": (SQLiteTemporalGraph, "incremental_state_digest"),
    "substrate.read_runtime_state": (SQLiteTemporalGraph, "read_runtime_state"),
    "substrate.read_runtime_journal": (SQLiteTemporalGraph, "read_runtime_journal"),
    "substrate.read_runtime_journal_tail": (SQLiteTemporalGraph, "read_runtime_journal_tail"),
    "substrate.write_runtime_state": (SQLiteTemporalGraph, "write_runtime_state"),
    "substrate.search": (SQLiteTemporalGraph, "search"),
    "runtime._validate_journal": (sqlite_runtime, "_validate_journal"),
    "runtime._validate_journal_tail": (sqlite_runtime, "_validate_journal_tail"),
    "runtime._governance_snapshot": (sqlite_runtime.SQLiteRestartSafeRuntime, "_governance_snapshot"),
    "runtime._persist_unlocked": (sqlite_runtime.SQLiteRestartSafeRuntime, "_persist_unlocked"),
    "adapter._recall_decision": (GovernedMemoryAdapter, "_recall_decision"),
    "composition.admit_preselected_candidates": (runtime_composition, "admit_preselected_candidates"),
}


class Timers:
    def __init__(self) -> None:
        self.totals: dict[str, float] = defaultdict(float)
        self.active = False
        self._originals = []

    def install(self) -> dict[str, bool]:
        present = {}
        for name, (owner, attribute) in COMPONENTS.items():
            original = getattr(owner, attribute, None)
            present[name] = original is not None
            if original is None:
                continue
            self._originals.append((owner, attribute, original))

            def wrapped(*args, __original=original, __name=name, **kwargs):
                if not self.active:
                    return __original(*args, **kwargs)
                start = time.perf_counter()
                try:
                    return __original(*args, **kwargs)
                finally:
                    self.totals[__name] += time.perf_counter() - start

            setattr(owner, attribute, wrapped)
        return present

    def uninstall(self) -> None:
        for owner, attribute, original in reversed(self._originals):
            setattr(owner, attribute, original)


def _text(rng: random.Random, words: list[str], count: int) -> str:
    return " ".join(rng.choices(words, k=count))


def _open(directory: str, scope: str) -> AgentMemory:
    return AgentMemory.open(directory, tenant="tenant:scale", actor_id="agent:scale", scope=scope, purpose="scaling")


def measure(size: int, *, window: int, recalls: int, seed: int, scopes: int = 1) -> dict:
    """``scopes > 1`` spreads the store round-robin over that many isolation scopes and
    measures from the first one, so most lexical matches belong to other scopes."""

    rng = random.Random(seed)
    words = [f"w{index}" for index in range(3000)]
    timers = Timers()
    present = timers.install()
    candidate_counts: list[int] = []
    admitted_counts: list[int] = []
    try:
        with tempfile.TemporaryDirectory() as directory:
            names = ["benchmark:scale"] if scopes == 1 else [f"benchmark:scale:{index}" for index in range(scopes)]
            for scope_index, scope in enumerate(names[1:], start=1):
                with _open(directory, scope) as other:
                    for index in range(scope_index, size, scopes):
                        other.remember(f"memory:{index}", _text(rng, words, 40))
            with _open(directory, names[0]) as memory:
                for index in range(0, size, scopes):
                    memory.remember(f"memory:{index}", _text(rng, words, 40))
                write_times = []
                timers.active = True
                timers.totals.clear()
                for index in range(size, size + window):
                    start = time.perf_counter()
                    result = memory.remember(f"memory:{index}", _text(rng, words, 40))
                    write_times.append(time.perf_counter() - start)
                    if not result["committed"]:
                        raise RuntimeError(f"write {index} did not commit")
                write_components = dict(timers.totals)
                timers.totals.clear()
                recall_times = []
                for _ in range(recalls):
                    start = time.perf_counter()
                    recalled = memory.recall(_text(rng, words, 8))
                    recall_times.append(time.perf_counter() - start)
                    candidate_counts.append(len(recalled["candidates"]))
                    admitted_counts.append(len(recalled["admitted"]))
                recall_components = dict(timers.totals)
                timers.active = False
    finally:
        timers.uninstall()

    def per_op(totals: dict[str, float], count: int) -> dict:
        return {name: (round(totals.get(name, 0.0) / count * 1000, 3) if present[name] else None) for name in COMPONENTS}

    return {
        "facts_before_window": size,
        "scopes": scopes,
        "write": {
            "ops": window,
            "median_ms": round(statistics.median(write_times) * 1000, 3),
            "mean_ms": round(statistics.fmean(write_times) * 1000, 3),
            "components_mean_ms": per_op(write_components, window),
        },
        "recall": {
            "ops": recalls,
            "median_ms": round(statistics.median(recall_times) * 1000, 3),
            "mean_ms": round(statistics.fmean(recall_times) * 1000, 3),
            "components_mean_ms": per_op(recall_components, recalls),
            "mean_candidates": round(statistics.fmean(candidate_counts), 2),
            "mean_admitted": round(statistics.fmean(admitted_counts), 2),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", type=int, nargs="+", default=[100, 1000])
    parser.add_argument("--window", type=int, default=40)
    parser.add_argument("--recalls", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--scopes", type=int, default=1, help="spread the store over N isolation scopes")
    parser.add_argument("--host-note", default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unknown"
    report = {
        "schema": "agent-memory-write-recall-scaling/1",
        "revision": revision,
        "host": {"python": platform.python_version(), "machine": platform.machine(), "note": args.host_note},
        "parameters": {"window": args.window, "recalls": args.recalls, "seed": args.seed, "scopes": args.scopes, "words_per_fact": 40, "words_per_query": 8},
        "results": [measure(size, window=args.window, recalls=args.recalls, seed=args.seed, scopes=args.scopes) for size in args.sizes],
        "authority_effect": "none",
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
