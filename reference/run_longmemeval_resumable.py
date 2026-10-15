"""Resumable, per-question driver for slow external backends on the frozen LongMemEval profile (#817).

It adds NO scoring logic. Selection (``_scan`` + ``_subset``), corpus construction,
``score_record`` and ``summarize`` are imported unchanged from ``run_longmemeval.py``.
Each scored row is appended to ``<out>/<granularity>.<backend>.rows.jsonl`` as soon as it
exists, so a container restart loses at most one question. ``--finalize`` assembles the
same per-plane summary the one-shot runner emits, from exactly the preregistered IDs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_longmemeval as lme  # noqa: E402


def preregister(args) -> dict:
    summaries, stream = lme._scan(args.input)
    sha = stream.hexdigest()
    if args.expected_sha256 and sha != args.expected_sha256:
        raise SystemExit(f"input sha256 {sha} != expected {args.expected_sha256}")
    chosen, selection = lme._subset(summaries, size=args.subset_size, seed=args.subset_seed)
    ids = [str(row["question_id"]) for row in chosen]
    selection["question_ids_sha256"] = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return {"input": {"path_name": args.input.name, "sha256": sha, "source_question_count": len(summaries),
                      "abstention_question_count": sum(1 for r in chosen if r["abstention"]),
                      "no_user_target_question_count": sum(1 for r in chosen if r["no_user_target"])},
            "selection": selection, "question_ids": ids,
            "granularities": args.granularity, "backend": args.backend,
            "external_backend": args.external_backend}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--expected-sha256")
    p.add_argument("--subset-size", type=int)
    p.add_argument("--subset-seed", default=lme.DEFAULT_SUBSET_SEED)
    p.add_argument("--granularity", action="append", choices=("session", "turn"), required=True)
    p.add_argument("--backend", required=True)
    p.add_argument("--external-backend", action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--preregister-only", action="store_true")
    p.add_argument("--finalize", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    prereg_path = args.out / "preregistration.json"
    plan = preregister(args)
    if prereg_path.exists():
        frozen = json.loads(prereg_path.read_text())
        if frozen["question_ids"] != plan["question_ids"] or frozen["input"]["sha256"] != plan["input"]["sha256"]:
            raise SystemExit("selection or input differs from the preregistration; refusing")
    else:
        plan["registered_at"] = datetime.now(timezone.utc).isoformat()
        prereg_path.write_text(json.dumps(plan, indent=2) + "\n")
    if args.preregister_only:
        print(json.dumps({"preregistered": len(plan["question_ids"]), "ids_sha256": plan["selection"]["question_ids_sha256"]}))
        return 0
    lme.load_external_backends(args.external_backend)
    ids = plan["question_ids"]
    for gran in args.granularity:
        rows_path = args.out / f"{gran}.{args.backend}.rows.jsonl"
        done = {}
        if rows_path.exists():
            for line in rows_path.read_text().splitlines():
                rec = json.loads(line)
                done[rec["question_id"]] = rec
        if args.finalize:
            missing = [q for q in ids if q not in done]
            records = [done[q] for q in ids if q in done]
            summary = {**lme.summarize(records, gran), "question_count_completed": len(records),
                       "question_count_preregistered": len(ids), "missing_question_ids": missing,
                       "external_system": lme.EXTERNAL_BACKENDS.get(args.backend)}
            (args.out / f"{gran}.{args.backend}.summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(gran, json.dumps({"completed": len(records), "of": len(ids), "failures": summary["failures"],
                                    "headline": summary["aggregate"]["headline"]}))
            continue
        retriever = lme.RETRIEVERS[args.backend]
        passes: list = []
        for row_index, row in enumerate(lme._selected_questions(args.input, ids, plan["input"]["sha256"], passes, gran)):
            if row["question_id"] in done:
                continue
            items, _ = lme.corpus(row, gran)
            started = time.perf_counter()
            try:
                outcome = retriever(str(row["question"]), items, row_index, row)
                error = None
            except Exception as exc:  # identical policy to run_longmemeval._evaluate_backend
                outcome = {"ranked": []}
                error = f"{type(exc).__name__}: {exc}"
            ranked = list(outcome.pop("ranked"))
            outcome["question_wall_seconds"] = round(time.perf_counter() - started, 3)
            outcome["finished_at"] = datetime.now(timezone.utc).isoformat()
            rec = lme.score_record(row, gran, ranked, runtime_error=error, extra=outcome)
            with rows_path.open("a") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
            print(f"{gran} {row_index + 1}/{len(ids)} {row['question_id']} items={len(items)} "
                  f"s={outcome['question_wall_seconds']} err={error}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
