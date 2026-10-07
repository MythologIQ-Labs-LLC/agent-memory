#!/usr/bin/env python3
"""Apply the plan-671-evidence-v5 E1 causal attribution rule to one same-harness lane pair.

The ``-v5`` Agent Memory control runs Runtime Baseline v5 (ranking policy 3.3.0). Against the
accepted ``-v4`` control of the same lane, each LongMemEval question (both planes) and each AMB
case is classified:

* ``EQUAL`` -- the ``-v5`` output equals ``-v4`` on the L1 fields of plan-644-lanes-v4
  (LongMemEval: ``ranked_top`` and ``metrics``; AMB: ``correct``, ``context`` and the nine
  ``meta`` fields, by ``query_id``). A question with a runtime error must carry no
  ``cross_fact`` record and be equal; a blank-query AMB case runs no recall and must be equal.
* ``ATTRIBUTED`` -- the output differs, the ``-v5`` record carries ``limited_count > 0``, and
  its mechanism-off recompute reproduces ``-v4``: LongMemEval ``ranked_top_mechanism_off``
  equals the ``-v4`` ``ranked_top``; AMB ``returned_document_ids_mechanism_off``, rendered with
  the frozen harness renderer (AMB ``src/memory_bench/modes/retrieval.py:50-54`` at
  ``03c1d0f``, blob ``416dd4df``) over the ``-v4`` case's own documents, reproduces the
  ``-v4`` case ``context`` byte for byte.
* ``UNATTRIBUTED`` -- anything else. Any ``UNATTRIBUTED`` result exits 1: the only difference
  from ``-v4`` allowed at v5 is the cross-fact mechanism.

Up/down counts, the knowledge-update slice, ``latest_gold_ranked_first`` and the AMB summary
deltas are reported, never gated. The script reads committed evidence only and has
``authority_effect: none``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
LONGMEMEVAL_LANES = ("longmemeval-s-retrieval-parity-v4", "longmemeval-s-retrieval-parity-v5")
AMB_LANES = ("amb-precisionmembench-retrieval-v4", "amb-precisionmembench-retrieval-v5")
PLANES = ("session", "turn")
HEADLINE = {
    "session": ("recall_all@5", "ndcg_any@5", "recall_all@10", "ndcg_any@10"),
    "turn": ("recall_all@5", "ndcg_any@5", "recall_all@10", "ndcg_any@10", "recall_all@50", "ndcg_any@50"),
}
AMB_CASE_FIELDS = ("correct", "context")
AMB_META_FIELDS = (
    "relevant_beliefs",
    "pinned_beliefs",
    "retrieved_questions",
    "retrieval_precision",
    "retrieval_recall",
    "pinned_coverage",
    "resolution",
    "failures",
    "retrieved_count",
)
AMB_SUMMARY_FIELDS = ("active_passes", "mean_precision", "mean_recall", "correct", "accuracy")
CROSS_FACT_SIDECAR_NAME = "cross-fact.jsonl"
EQUAL, ATTRIBUTED, UNATTRIBUTED = "EQUAL", "ATTRIBUTED", "UNATTRIBUTED"
_AMB_CONTROL_DIR = re.compile(r"^agent-memory-[0-9a-f]{12}$")


class AttributionError(RuntimeError):
    """The evidence cannot be read or joined; a blocked check, never a verdict."""


# --------------------------------------------------------------------------- AMB renderer
def render_retrieval_context(documents: Sequence[Mapping[str, Any]]) -> str:
    """AMB ``RetrievalMode.async_answer`` lines 50-54 at 03c1d0f, reproduced verbatim.

    ``documents`` are ``{"id", "source_ids", "content"}`` mappings in returned order.
    """

    lines = [f"## Retrieved memories ({len(documents)})"]
    for i, d in enumerate(documents):
        src = f" ← {', '.join(d['source_ids'])}" if d.get("source_ids") else ""
        lines.append(f"{i + 1}. [{d['id']}]{src}\n{d['content']}")
    return "\n\n".join(lines)


def parse_retrieval_context(context: str) -> list[dict[str, Any]]:
    """The ordered documents a rendered context shows; refused unless it re-renders byte for byte."""

    head = re.match(r"## Retrieved memories \((\d+)\)", context)
    if head is None:
        raise AttributionError("context does not start with the frozen renderer's header")
    count = int(head.group(1))
    documents: list[dict[str, Any]] = []
    position = head.end()
    for index in range(1, count + 1):
        prefix = f"\n\n{index}. ["
        if not context.startswith(prefix, position):
            raise AttributionError(f"context entry {index} is not where the frozen renderer puts it")
        header_end = context.index("\n", position + len(prefix))
        header = context[position + len(prefix):header_end]
        document_id, _, rest = header.partition("]")
        source_ids = rest.removeprefix(" ← ").split(", ") if rest else []
        following = context.find(f"\n\n{index + 1}. [", header_end) if index < count else -1
        content_end = len(context) if following == -1 else following
        documents.append({"id": document_id, "source_ids": source_ids, "content": context[header_end + 1:content_end]})
        position = content_end
    if render_retrieval_context(documents) != context:
        raise AttributionError("context does not re-render byte for byte from its parsed documents")
    return documents


# --------------------------------------------------------------------------- LongMemEval
def _metric_direction(before: Mapping[str, Any], after: Mapping[str, Any], keys: Iterable[str]) -> str:
    deltas = [float(after.get(key) or 0.0) - float(before.get(key) or 0.0) for key in keys]
    up, down = any(delta > 0 for delta in deltas), any(delta < 0 for delta in deltas)
    return "mixed" if up and down else "up" if up else "down" if down else "unchanged"


def attribute_longmemeval_rows(v4_rows: Sequence[Mapping[str, Any]], v5_rows: Sequence[Mapping[str, Any]], plane: str) -> list[dict[str, Any]]:
    """One verdict per question, in ``-v5`` row order (both lanes carry the frozen 500)."""

    before = {str(row["question_id"]): row for row in v4_rows}
    if len(before) != len(v4_rows) or sorted(before) != sorted(str(row["question_id"]) for row in v5_rows) or len(v5_rows) != len(v4_rows):
        raise AttributionError(f"{plane}: the -v4 and -v5 rows do not cover the same questions")
    verdicts = []
    for row in v5_rows:
        question = str(row["question_id"])
        old = before[question]
        record = row.get("cross_fact")
        same = row["ranked_top"] == old["ranked_top"] and row["metrics"] == old["metrics"]
        if row.get("runtime_error") is not None:
            verdict = EQUAL if same and record is None else UNATTRIBUTED
            reason = "runtime error, equal to -v4" if verdict == EQUAL else "runtime error row differs from -v4 or carries a cross_fact record"
        elif not isinstance(record, Mapping):
            verdict, reason = UNATTRIBUTED, "error-free question without a cross_fact record"
        elif same:
            verdict, reason = EQUAL, "ranked_top and metrics equal -v4"
        elif record.get("limited_count", 0) > 0 and record.get("ranked_top_mechanism_off") == old["ranked_top"]:
            verdict, reason = ATTRIBUTED, "limited, and the mechanism-off ranked_top reproduces -v4"
        elif record.get("limited_count", 0) > 0:
            verdict, reason = UNATTRIBUTED, "limited, but the mechanism-off ranked_top differs from -v4"
        else:
            verdict, reason = UNATTRIBUTED, "differs from -v4 with no cross-fact limitation"
        verdicts.append(
            {
                "plane": plane,
                "id": question,
                "question_type": row.get("question_type"),
                "verdict": verdict,
                "reason": reason,
                "limited_count": (record or {}).get("limited_count") if isinstance(record, Mapping) else None,
                "direction": "unchanged" if verdict == EQUAL else _metric_direction(old["metrics"], row["metrics"], HEADLINE[plane]),
            }
        )
    return verdicts


def _lme_control_dir(lane_root: Path, plane: str) -> Path:
    found = sorted(path for path in lane_root.glob(f"agent_memory-{plane}-*") if path.is_dir())
    if len(found) != 1:
        raise AttributionError(f"expected exactly one agent_memory {plane} evidence directory under {lane_root}, found {len(found)}")
    return found[0]


def _lme_rows(directory: Path, plane: str) -> list[dict[str, Any]]:
    with gzip.open(directory / "report.rows.json.gz") as handle:
        return json.loads(handle.read())[plane]["agent_memory"]


def check_longmemeval(v4_root: Path, v5_root: Path) -> dict[str, Any]:
    verdicts: list[dict[str, Any]] = []
    reported: dict[str, Any] = {}
    for plane in PLANES:
        old_dir, new_dir = _lme_control_dir(v4_root, plane), _lme_control_dir(v5_root, plane)
        plane_verdicts = attribute_longmemeval_rows(_lme_rows(old_dir, plane), _lme_rows(new_dir, plane), plane)
        verdicts.extend(plane_verdicts)
        old_native = json.loads((old_dir / "evidence.json").read_text(encoding="utf-8"))["native_summary"]
        new_native = json.loads((new_dir / "evidence.json").read_text(encoding="utf-8"))["native_summary"]
        changed = [item for item in plane_verdicts if item["verdict"] != EQUAL]
        reported[plane] = {
            "direction_counts": _counts(item["direction"] for item in changed),
            "knowledge_update_changed": sum(1 for item in changed if item["question_type"] == "knowledge-update"),
            "latest_gold_ranked_first": {"v4": old_native.get("latest_gold_ranked_first"), "v5": new_native.get("latest_gold_ranked_first")},
            "headline": {"v4": old_native.get("headline"), "v5": new_native.get("headline")},
        }
    return {"verdicts": verdicts, "reported_never_gated": reported}


# --------------------------------------------------------------------------- AMB
def _amb_view(case: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    meta = case.get("meta") or {}
    return {field: case.get(field) for field in AMB_CASE_FIELDS}, {field: meta.get(field) for field in AMB_META_FIELDS}


def attribute_amb_cases(v4_results: Sequence[Mapping[str, Any]], v5_results: Sequence[Mapping[str, Any]], sidecar_lines: Sequence[str]) -> list[dict[str, Any]]:
    """One verdict per case, in ``-v5`` results order; the sidecar joins over non-blank queries (L9)."""

    before = {str(case["query_id"]): case for case in v4_results}
    if len(before) != len(v4_results) or sorted(before) != sorted(str(case["query_id"]) for case in v5_results) or len(v5_results) != len(v4_results):
        raise AttributionError("the -v4 and -v5 EvalSummaries do not cover the same cases")
    records = [json.loads(line) for line in sidecar_lines if line.strip()]
    asked = [case for case in v5_results if (case.get("query") or "").strip()]
    if len(records) != len(asked) or [record.get("call_index") for record in records] != list(range(len(records))):
        raise AttributionError(f"cross-fact sidecar has {len(records)} records for {len(asked)} non-blank-query cases, or is out of order")
    joined: dict[str, Mapping[str, Any]] = {}
    for record, case in zip(records, asked):
        if record.get("query_sha256") != hashlib.sha256(str(case["query"]).encode("utf-8")).hexdigest():
            raise AttributionError(f"cross-fact record {record.get('call_index')} does not match case {case['query_id']}")
        joined[str(case["query_id"])] = record
    verdicts = []
    for case in v5_results:
        query_id = str(case["query_id"])
        old = before[query_id]
        record = joined.get(query_id)
        same = _amb_view(case) == _amb_view(old)
        if query_id not in joined:
            verdict, reason = (EQUAL, "blank query, no recall, equal to -v4") if same else (UNATTRIBUTED, "blank-query case differs from -v4")
        elif same:
            verdict, reason = EQUAL, "case fields equal -v4"
        elif record.get("limited_count", 0) > 0:
            documents = {item["id"]: item for item in parse_retrieval_context(str(old["context"]))}
            off = record.get("returned_document_ids_mechanism_off") or []
            if all(document_id in documents for document_id in off) and render_retrieval_context([documents[i] for i in off]) == old["context"]:
                verdict, reason = ATTRIBUTED, "limited, and the mechanism-off documents re-render the -v4 context byte for byte"
            else:
                verdict, reason = UNATTRIBUTED, "limited, but the mechanism-off documents do not re-render the -v4 context"
        else:
            verdict, reason = UNATTRIBUTED, "differs from -v4 with no cross-fact limitation"
        verdicts.append(
            {
                "id": query_id,
                "verdict": verdict,
                "reason": reason,
                "limited_count": None if record is None else record.get("limited_count"),
                "correct": {"v4": old.get("correct"), "v5": case.get("correct")},
            }
        )
    return verdicts


def _amb_control_dir(lane_root: Path) -> Path:
    found = sorted(path for path in lane_root.iterdir() if path.is_dir() and _AMB_CONTROL_DIR.match(path.name))
    if len(found) != 1:
        raise AttributionError(f"expected exactly one agent-memory evidence directory under {lane_root}, found {len(found)}")
    return found[0]


def check_amb(v4_root: Path, v5_root: Path) -> dict[str, Any]:
    old_dir, new_dir = _amb_control_dir(v4_root), _amb_control_dir(v5_root)
    old = json.loads((old_dir / "single-turn.json").read_text(encoding="utf-8"))
    new = json.loads((new_dir / "single-turn.json").read_text(encoding="utf-8"))
    sidecar = new_dir / CROSS_FACT_SIDECAR_NAME
    if not sidecar.is_file():
        raise AttributionError(f"{new_dir} carries no {CROSS_FACT_SIDECAR_NAME}")
    verdicts = attribute_amb_cases(old["results"], new["results"], sidecar.read_text(encoding="utf-8").splitlines())
    changed = [item for item in verdicts if item["verdict"] != EQUAL]
    deltas = {}
    for field in AMB_SUMMARY_FIELDS:
        before, after = old.get(field), new.get(field)
        deltas[field] = {"v4": before, "v5": after, "delta": None if before is None or after is None else round(after - before, 6)}
    reported = {
        "correct_flips": _counts(f"{item['correct']['v4']}->{item['correct']['v5']}" for item in changed if item["correct"]["v4"] != item["correct"]["v5"]),
        "summary_deltas": deltas,
    }
    return {"verdicts": verdicts, "reported_never_gated": reported}


# --------------------------------------------------------------------------- CLI
def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--benchmark", required=True, choices=("longmemeval", "amb"))
    parser.add_argument("--v4-dir", type=Path, help="the accepted -v4 lane's evidence directory (default: the committed one)")
    parser.add_argument("--v5-dir", type=Path, help="the imported -v5 lane's evidence directory (default: the committed one)")
    parser.add_argument("--output", type=Path, help="also write the full result as JSON")
    args = parser.parse_args(argv)
    lanes = LONGMEMEVAL_LANES if args.benchmark == "longmemeval" else AMB_LANES
    root = REPO_ROOT / "reports" / "benchmarks" / args.benchmark
    v4_root, v5_root = args.v4_dir or root / lanes[0], args.v5_dir or root / lanes[1]
    try:
        result = check_longmemeval(v4_root, v5_root) if args.benchmark == "longmemeval" else check_amb(v4_root, v5_root)
    except (AttributionError, OSError, KeyError, ValueError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2
    for item in result["verdicts"]:
        where = f"{item['plane']}:" if "plane" in item else ""
        print(f"{item['verdict']}\t{where}{item['id']}\t{item['reason']}")
    summary = {
        "benchmark": args.benchmark,
        "lanes": {"v4": lanes[0], "v5": lanes[1]},
        "verdict_counts": _counts(item["verdict"] for item in result["verdicts"]),
        "reported_never_gated": result["reported_never_gated"],
        "authority_effect": "none",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({**summary, "verdicts": result["verdicts"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if any(item["verdict"] == UNATTRIBUTED for item in result["verdicts"]) else 0


if __name__ == "__main__":
    sys.exit(main())
