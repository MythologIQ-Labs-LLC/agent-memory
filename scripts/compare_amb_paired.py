#!/usr/bin/env python3
"""Paired before/after comparison of two AMB PrecisionMemBench result files (#819).

Reads AMB's own per-case outcomes (``correct``, ``meta.retrieval_precision``,
``meta.retrieval_recall``, ``meta.category``) for the same cases under two systems and reports:
strict case success, mean precision and recall (AMB's definitions: over cases where defined),
per-category pass counts, the fixed/broken case lists, an exact two-sided McNemar test on
strict success, and paired bootstrap 95% intervals (case resampling, fixed seed) for the
differences. Nothing here rescores a case; every number is derived from AMB's output.

    python scripts/compare_amb_paired.py BEFORE.json AFTER.json --json out.json --markdown out.md
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

SEED = 819
RESAMPLES = 10000


def load(path: Path) -> dict[str, dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("results") if isinstance(document, dict) else document
    by_id: dict[str, dict] = {}
    for row in rows:
        if row["query_id"] in by_id:
            raise SystemExit(f"duplicate query_id {row['query_id']!r} in {path}")
        by_id[row["query_id"]] = row
    return by_id


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def metric_means(rows: list[dict]) -> dict[str, float | None]:
    return {
        "strict_success": mean([1.0 if row["correct"] else 0.0 for row in rows]),
        "mean_precision": mean([row["meta"]["retrieval_precision"] for row in rows
                                if row["meta"].get("retrieval_precision") is not None]),
        "mean_recall": mean([row["meta"]["retrieval_recall"] for row in rows
                             if row["meta"].get("retrieval_recall") is not None]),
    }


def mcnemar_exact(fixed: int, broken: int) -> float:
    n = fixed + broken
    if n == 0:
        return 1.0
    k = min(fixed, broken)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def bootstrap(ids: list[str], before: dict, after: dict) -> dict[str, list[float]]:
    rng = random.Random(SEED)
    draws: dict[str, list[float]] = {key: [] for key in ("strict_success", "mean_precision", "mean_recall")}
    for _ in range(RESAMPLES):
        sample = [ids[rng.randrange(len(ids))] for _ in ids]
        b = metric_means([before[i] for i in sample])
        a = metric_means([after[i] for i in sample])
        for key in draws:
            if a[key] is not None and b[key] is not None:
                draws[key].append(a[key] - b[key])
    intervals = {}
    for key, values in draws.items():
        values.sort()
        intervals[key] = [round(values[int(0.025 * len(values))], 4), round(values[int(0.975 * len(values)) - 1], 4)]
    return intervals


def compare(before_path: Path, after_path: Path) -> dict:
    before, after = load(before_path), load(after_path)
    if set(before) != set(after):
        raise SystemExit("the two runs do not cover the same cases")
    ids = sorted(before)
    fixed = [i for i in ids if after[i]["correct"] and not before[i]["correct"]]
    broken = [i for i in ids if before[i]["correct"] and not after[i]["correct"]]
    categories: dict[str, Counter] = {}
    for i in ids:
        counter = categories.setdefault(before[i]["meta"].get("category") or "?", Counter())
        counter["cases"] += 1
        counter["before"] += bool(before[i]["correct"])
        counter["after"] += bool(after[i]["correct"])
    b, a = metric_means([before[i] for i in ids]), metric_means([after[i] for i in ids])
    return {
        "cases": len(ids),
        "before": {"correct": sum(bool(before[i]["correct"]) for i in ids), **{k: round(v, 4) for k, v in b.items()}},
        "after": {"correct": sum(bool(after[i]["correct"]) for i in ids), **{k: round(v, 4) for k, v in a.items()}},
        "paired": {
            "fixed": fixed,
            "broken": broken,
            "mcnemar_exact_p": mcnemar_exact(len(fixed), len(broken)),
            "bootstrap_95ci_after_minus_before": bootstrap(ids, before, after),
            "bootstrap": {"resamples": RESAMPLES, "seed": SEED, "unit": "case"},
        },
        "by_category": {k: dict(v) for k, v in sorted(categories.items())},
        "returned_count": {
            "before_mean": round(mean([float(before[i]["meta"].get("retrieved_count") or 0) for i in ids]), 3),
            "after_mean": round(mean([float(after[i]["meta"].get("retrieved_count") or 0) for i in ids]), 3),
        },
        "per_case": {i: {"before": bool(before[i]["correct"]), "after": bool(after[i]["correct"]),
                         "before_relevant": before[i]["meta"].get("relevant_beliefs"),
                         "after_relevant": after[i]["meta"].get("relevant_beliefs")} for i in ids},
    }


def markdown(report: dict) -> str:
    b, a, p = report["before"], report["after"], report["paired"]
    ci = p["bootstrap_95ci_after_minus_before"]
    lines = [
        "| Metric | Before | After | After - before (95% paired bootstrap CI) |",
        "|---|---:|---:|---|",
        f"| Strict case success | {b['correct']}/{report['cases']} | {a['correct']}/{report['cases']} | "
        f"{a['strict_success'] - b['strict_success']:+.4f} [{ci['strict_success'][0]:+.4f}, {ci['strict_success'][1]:+.4f}] |",
        f"| Mean precision | {b['mean_precision']:.4f} | {a['mean_precision']:.4f} | "
        f"{a['mean_precision'] - b['mean_precision']:+.4f} [{ci['mean_precision'][0]:+.4f}, {ci['mean_precision'][1]:+.4f}] |",
        f"| Mean recall | {b['mean_recall']:.4f} | {a['mean_recall']:.4f} | "
        f"{a['mean_recall'] - b['mean_recall']:+.4f} [{ci['mean_recall'][0]:+.4f}, {ci['mean_recall'][1]:+.4f}] |",
        f"| Mean documents returned | {report['returned_count']['before_mean']} | {report['returned_count']['after_mean']} | |",
        "",
        f"Paired: **{len(p['fixed'])} fixed, {len(p['broken'])} broken**; exact McNemar p = {p['mcnemar_exact_p']:.2e}.",
        "",
        "| Category | Cases | Before | After |",
        "|---|---:|---:|---:|",
    ]
    for name, counts in report["by_category"].items():
        lines.append(f"| {name} | {counts['cases']} | {counts['before']} | {counts['after']} |")
    lines += ["", "Fixed: " + (", ".join(f"`{i}`" for i in p["fixed"]) or "none"),
              "", "Broken: " + (", ".join(f"`{i}`" for i in p["broken"]) or "none")]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    report = compare(args.before, args.after)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    text = markdown(report)
    if args.markdown:
        args.markdown.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
