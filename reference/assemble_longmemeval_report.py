"""Assemble a runner-shaped LongMemEval report from a resumable run's committed outputs.

`run_longmemeval_resumable.py --finalize` writes one `<plane>.<backend>.summary.json` per plane,
using the frozen runner's own `summarize`. This tool only re-arranges those summaries and the
run's `preregistration.json` into the `input` + `planes.<plane>.backends.<backend>` layout of a
`run_longmemeval.py` report, so readers that consume that layout can verify it. Nothing is
re-scored or recomputed. It refuses incomplete planes or summaries that recorded failures.

Usage: assemble_longmemeval_report.py RUN_DIR BACKEND OUTPUT
"""
from __future__ import annotations

import hashlib, json, sys
from pathlib import Path


def main() -> int:
    run, backend, output = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    prereg = json.loads((run / "preregistration.json").read_text())
    planes, sources = {}, {}
    for plane in ("session", "turn"):  # every finalized plane; the selection is plane-independent
        path = run / f"{plane}.{backend}.summary.json"
        if not path.exists():
            continue
        s = json.loads(path.read_text())
        if s["missing_question_ids"] or s["question_count_completed"] != s["question_count_preregistered"]:
            raise SystemExit(f"{plane}: incomplete ({s['question_count_completed']}/{s['question_count_preregistered']})")
        if any(s["failures"].get(k) for k in ("runtime_failure_count", "ingestion_failure_count", "out_of_corpus_returned_count")):
            raise SystemExit(f"{plane}: summary records failures {s['failures']}")
        planes[plane] = {"backends": {backend: {k: s[k] for k in ("aggregate", "by_question_type", "currentness", "failures", "external_system") if k in s}}}
        sources[plane] = {"uri": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    if not planes:
        raise SystemExit("no finalized plane summaries")
    report = {
        "schema_version": "assembled-from-resumable/1",
        "input": {**prereg["input"], "question_count": len(prereg["question_ids"]), "selection": prereg["selection"]},
        "planes": planes,
        "assembly": {"tool": "reference/assemble_longmemeval_report.py", "preregistration_sha256":
                     hashlib.sha256((run / "preregistration.json").read_bytes()).hexdigest(), "plane_summaries": sources,
                     "note": "re-arranged, not re-scored; per-question rows are in <plane>.<backend>.rows.jsonl"},
        "authority_effect": "none",
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
