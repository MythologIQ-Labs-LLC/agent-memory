#!/usr/bin/env python3
"""Run the benchmark-author golden path evaluator-integrity controls (#652).

The controls prove that the golden keyed-retrieval evaluator detects the defects it claims
to measure (gold omission, rank inversion, identity corruption) and ignores an unrelated
defect (isolation control). Every arm runs through the same Gauntlet operation-envelope
surface as a real contestant. The output is evidence about the evaluator only; it is not
memory efficacy, benchmark comparability, or authority.

Exit status is 1 unless every declared control matches its declared expectation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentmem_ref._paths import REPO_ROOT  # noqa: E402
from agentmem_ref.evaluation.benchmark_golden_keyed_retrieval import run_integrity_controls  # noqa: E402
from agentmem_ref.evaluation.gauntlet_orchestrator import load_adapter_manifest  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "fixtures" / "gauntlet" / "lexical-adapter.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", default=str(DEFAULT_MANIFEST), help="Gauntlet system-adapter manifest to exercise")
    parser.add_argument("--allow-external-process", action="store_true", help="permit a stdio adapter startup command")
    parser.add_argument("--output", help="write the integrity report to this path")
    args = parser.parse_args(argv)

    manifest = load_adapter_manifest(args.system)
    report = run_integrity_controls(manifest, allow_external_process=args.allow_external_process)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        location = Path(args.output)
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    for control in report["controls"]:
        marker = "ok " if control["as_expected"] else "BAD"
        print(
            f"{marker} {control['control_id']}: exact_top1 {control['healthy_value']:.3f} -> "
            f"{control['control_value']:.3f} (expected_detection={control['expected_detection']}, "
            f"detected={control['detected']})",
            file=sys.stderr,
        )
    return 0 if report["all_as_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
