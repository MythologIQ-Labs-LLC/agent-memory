#!/usr/bin/env python3
"""Compare two LongMemEval executions of the same system question by question.

Each side is either a one-shot ``run_longmemeval.py`` output (``.json`` or ``.json.gz``, rows under
``planes.<plane>.backends.<backend>.rows``) or a resumable driver ``<plane>.<backend>.rows.jsonl``.
For every question present on both sides it compares the scored outcome (``metrics``, ``status``,
``runtime_error``) and the returned ranking (``ranked_top``). Timing and host fields are ignored. A
missing question, or a question present twice on one side, is a difference. The default
``--scope intersection`` compares the questions both sides ran and reports what each side lacks.
Exits 1 on any difference.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

COMPARED = ("metrics", "status", "runtime_error", "ranked_top", "gold", "question_type")


def load_rows(path: Path, plane: str, backend: str) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload["planes"][plane]["backends"][backend]["rows"]


def index(rows: list[dict], side: str, differences: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in rows:
        qid = row["question_id"]
        if qid in out:
            differences.append(f"{qid}: duplicate on {side}")
        out[qid] = row
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--plane", required=True, choices=("session", "turn"))
    parser.add_argument("--backend", required=True)
    parser.add_argument("--right-backend", help="backend name on the right side if different")
    parser.add_argument("--scope", choices=("intersection", "exact"), default="intersection")
    args = parser.parse_args(argv)

    differences: list[str] = []
    left = index(load_rows(args.left, args.plane, args.backend), "left", differences)
    right = index(load_rows(args.right, args.plane, args.right_backend or args.backend), "right", differences)
    common = [qid for qid in left if qid in right]
    only_left = sorted(set(left) - set(right))
    only_right = sorted(set(right) - set(left))
    if args.scope == "exact":
        differences += [f"{qid}: only on left" for qid in only_left] + [f"{qid}: only on right" for qid in only_right]
    differing_questions = set()
    for qid in common:
        for field in COMPARED:
            a, b = left[qid].get(field, "<missing>"), right[qid].get(field, "<missing>")
            if a != b:
                differences.append(f"{qid}.{field}: {json.dumps(a)[:160]} != {json.dumps(b)[:160]}")
                differing_questions.add(qid)
    verdict = {
        "left": str(args.left), "right": str(args.right), "plane": args.plane, "backend": args.backend,
        "scope": args.scope, "compared_fields": list(COMPARED),
        "left_questions": len(left), "right_questions": len(right), "compared_questions": len(common),
        "only_left": len(only_left), "only_right": len(only_right),
        "differing_questions": len(differing_questions), "differences": len(differences),
        "equal": not differences,
    }
    for line in differences:
        print(line, file=sys.stderr)
    print(json.dumps(verdict, indent=2))
    return 0 if not differences else 1


if __name__ == "__main__":
    sys.exit(main())
