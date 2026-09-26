"""Side-by-side analysis of LongMemEval_S replays across ranking configurations (#538, ADR-039).

Diagnostic only. It reads committed report JSON (with rows inline or in a ``.rows.json.gz``
sidecar) and prints markdown tables that keep retrieval, currentness, question-type
deltas, and failures separate. There is no aggregate score.

Currentness is split by the temporal intent the frozen deterministic interpreter assigns
to each question text (``--dataset`` supplies the text). That split only explains results;
the interpreter never sees benchmark labels.

Usage::

    python reference/analyze_applicability_replay.py --dataset longmemeval_s_cleaned.json \\
        --baseline universal_bm25 \\
        frozen=REPORT.json:ROWS.json.gz universal_bm25=REPORT.json:ROWS.json.gz qca=REPORT.json ...
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentmem_ref.runtime.temporal_intent import interpret_query  # noqa: E402

PLANES = {"session": ("recall_all@5", "ndcg_any@5", "recall_all@10", "ndcg_any@10"),
          "turn": ("recall_all@5", "ndcg_any@5", "recall_all@10", "recall_all@50")}
TYPE_METRIC = {"session": "recall_all@5", "turn": "recall_all@10"}


def load(spec: str) -> tuple[str, dict]:
    label, _, paths = spec.partition("=")
    report_path, _, rows_path = paths.partition(":")
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if rows_path:
        sidecar = json.load(gzip.open(rows_path))
        for plane, backends in sidecar.items():
            for backend, rows in backends.items():
                report["planes"][plane]["backends"][backend]["rows"] = rows
    return label, report


def rows(report: dict, plane: str, backend: str = "agent_memory") -> dict[str, dict]:
    return {row["question_id"]: row for row in report["planes"][plane]["backends"][backend]["rows"]}


def intent_class(question: str) -> str:
    intent = interpret_query(question)
    if intent.orders_temporally:
        return f"{intent.mode} (orders)"
    return "no temporal ordering"


def paired(after: dict, before: dict, plane: str, metric: str, ids: list[str]) -> tuple[float, float, float, int, int]:
    deltas = [after[q]["metrics"][plane][metric] - before[q]["metrics"][plane][metric] for q in ids]
    if not deltas:
        return 0.0, 0.0, 0.0, 0, 0
    rng = random.Random(2027)
    boot = sorted(statistics.fmean(rng.choices(deltas, k=len(deltas))) for _ in range(2000))
    return statistics.fmean(deltas), boot[50], boot[1949], sum(d > 0 for d in deltas), sum(d < 0 for d in deltas)


def latest_first(table: dict[str, dict], ids: list[str]) -> tuple[float | None, int]:
    applicable = [table[q]["latest_gold_first"] for q in ids if table[q].get("latest_gold_first") is not None]
    return (sum(applicable) / len(applicable) if applicable else None), len(applicable)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("reports", nargs="+")
    args = parser.parse_args()
    questions = {str(row["question_id"]): str(row["question"]) for row in json.loads(args.dataset.read_text(encoding="utf-8"))}
    loaded = dict(load(spec) for spec in args.reports)
    labels = list(loaded)
    print("| config | revision | ranking variant | temporal metadata | policy |\n| --- | --- | --- | --- | --- |")
    for label, report in loaded.items():
        execution = report["execution"]
        configuration = execution.get("agent_memory_configuration", {"ranking_variant": "n/a (pre-option)", "temporal_metadata": "none"})
        print(f"| {label} | `{execution['agent_memory_revision'][:7]}` | {configuration['ranking_variant']} | {configuration['temporal_metadata']} | "
              f"{'dirty' if execution['agent_memory_worktree_dirty'] else 'clean'} |")
    for plane, metrics in PLANES.items():
        tables = {label: rows(report, plane) for label, report in loaded.items()}
        base = tables[args.baseline]
        scored = sorted(q for q, row in base.items() if row["status"] == "scored")
        lexical = loaded[labels[0]]["planes"][plane]["backends"]["lexical_overlap"]["aggregate"]["headline"]
        print(f"\n### {plane} plane (scored n={len(scored)})\n")
        print("| metric | lexical | " + " | ".join(labels) + " |\n| --- |" + " ---: |" * (len(labels) + 1))
        for metric in metrics:
            values = [loaded[label]["planes"][plane]["backends"]["agent_memory"]["aggregate"]["headline"][metric] for label in labels]
            print(f"| {metric} | {lexical[metric]:.3f} | " + " | ".join(f"{value:.3f}" for value in values) + " |")
        types = sorted({row["question_type"] for row in base.values()})
        ku = [q for q in scored if base[q]["question_type"] == "knowledge-update"]
        for name, ids in (("knowledge-update", ku), ("all multi-date gold", scored)):
            cells = []
            for label in labels:
                rate, count = latest_first(tables[label], ids)
                cells.append("n/a" if rate is None else f"{rate:.3f} (n={count})")
            print(f"| latest_gold_first, {name} | | " + " | ".join(cells) + " |")
        failures = [loaded[label]["planes"][plane]["backends"]["agent_memory"]["failures"] for label in labels]
        print("| failures (runtime/ingest/out-of-corpus) | | " + " | ".join(
            f"{f['runtime_failure_count']}/{f['ingestion_failure_count']}/{f['out_of_corpus_returned_count']}" for f in failures) + " |")

        metric = TYPE_METRIC[plane]
        print(f"\n{metric} by question type; Δ columns are paired vs `{args.baseline}`, mean [95% CI] better/worse\n")
        print("| question type | n | " + " | ".join(labels) + " | " + " | ".join(f"Δ {label}" for label in labels if label != args.baseline) + " |")
        print("| --- | ---: |" + " ---: |" * len(labels) + " --- |" * (len(labels) - 1))
        for question_type in types + ["ALL"]:
            ids = scored if question_type == "ALL" else [q for q in scored if base[q]["question_type"] == question_type]
            values = [statistics.fmean(tables[label][q]["metrics"][plane][metric] for q in ids) for label in labels]
            deltas = []
            for label in labels:
                if label == args.baseline:
                    continue
                mean, low, high, better, worse = paired(tables[label], base, plane, metric, ids)
                deltas.append(f"{mean:+.3f} [{low:+.3f},{high:+.3f}] {better}/{worse}")
            print(f"| {question_type} | {len(ids)} | " + " | ".join(f"{value:.3f}" for value in values) + " | " + " | ".join(deltas) + " |")

        print("\nlatest_gold_first by interpreted intent class (knowledge-update)\n")
        print("| intent class | n | " + " | ".join(labels) + " |\n| --- | ---: |" + " ---: |" * len(labels))
        classes = sorted({intent_class(questions[q]) for q in ku})
        for cls in classes:
            ids = [q for q in ku if intent_class(questions[q]) == cls]
            cells = []
            for label in labels:
                rate, count = latest_first(tables[label], ids)
                cells.append("n/a" if rate is None else f"{rate:.3f} ({count})")
            print(f"| {cls} | {len(ids)} | " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
