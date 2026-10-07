#!/usr/bin/env python3
"""Frozen metamorphic base selection for the #732 corpus (plan-732-generalization-gate G3c).

Eligible bases are the P and R cases that pass every check from K1 to K7, as listed in
``valid_case_ids`` of a ``check_generalization_corpus.py`` report. For each of the 20 P and R
families, the 2 eligible cases with the smallest
``sha256("plan-732-metamorphic-v1|" + case_id + "|" + writes[newer_write].text)`` are selected.
Digests are compared as hex strings. A family with fewer than 2 eligible cases contributes
what it has.

The output is the sorted ``case_id`` list as compact JSON. It is the ``{CASE_IDS}`` value
interpolated into the frozen ``variants.txt``. The script has ``authority_effect: none``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SALT = "plan-732-metamorphic-v1"
FAMILIES = [f"P{i}" for i in range(1, 14)] + [f"R{i}" for i in range(1, 8)]
PER_FAMILY = 2


def select(corpus: list, eligible: set) -> list[str]:
    chosen: list[str] = []
    for family in FAMILIES:
        ranked = sorted(
            (
                hashlib.sha256(
                    f"{SALT}|{case['case_id']}|{case['writes'][case['newer_write']]['text']}".encode("utf-8")
                ).hexdigest(),
                case["case_id"],
            )
            for case in corpus
            if isinstance(case, dict) and case.get("family") == family and case.get("case_id") in eligible
        )
        chosen += [case_id for _digest, case_id in ranked[:PER_FAMILY]]
    return sorted(chosen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("check_report", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    eligible = set(json.loads(args.check_report.read_text(encoding="utf-8"))["valid_case_ids"])
    text = json.dumps(select(corpus, eligible), separators=(",", ":"))
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
