#!/usr/bin/env python3
"""Execute the governed paths and emit a conformance report.

The report conforms to `schemas/conformance-report.schema.json`. It
deliberately claims **conformance level 0**: these paths execute against a
substrate *model*, not a running substrate, so under the evidence rules in
`docs/programs/runtime-evidence/README.md` they are not runtime evidence and
cannot substantiate a level claim. The exemption is stated in the report
itself rather than left for a reader to infer.

Usage:
    python reference/run_conformance.py [-o report.json]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import unittest
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parent
ROOT = REFERENCE_DIR.parent
sys.path.insert(0, str(REFERENCE_DIR))

from agentmem_ref import policy, receipts  # noqa: E402
from agentmem_ref.graphiti_driver import graphiti_available  # noqa: E402

ADAPTER_VERSION = "0.1.0"
DOCTRINE_VERSION = "v0.3"
SUBSTRATE_MODEL = "in-memory temporal graph modelling graphiti-core 0.29.3 verified semantics"
REAL_SUBSTRATE = "graphiti-core 0.29.3 over embedded kuzu, no LLM and no embedder invoked"


def _run_suite() -> tuple[list[str], list[str], list[str]]:
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(REFERENCE_DIR / "tests"), top_level_dir=str(REFERENCE_DIR))
    # Names must be collected before the run: the runner drains the suite.
    names = _collect_names(suite)
    result = unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)

    failed = sorted({_short(test) for test, _ in list(result.failures) + list(result.errors)})
    passed = [name for name in names if name not in failed]
    return names, passed, failed


def _collect_names(suite) -> list[str]:
    names: list[str] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            names.extend(_collect_names(item))
        else:
            names.append(_short(item))
    return sorted(names)


def _short(test) -> str:
    return test.id().rsplit(".", 1)[-1]


def _exemptions(substrate_executed: bool) -> list[str]:
    common = [
        "The fixture corpus is not driven through the adapter, so no conformance level is claimed. "
        "Levels require the doctrine fixtures, not governance paths alone.",
        "Retrieval ranking is lexical rather than hybrid, so recall quality is not measured "
        "and no calibration claim is made.",
        "The policy implements the subset of the decision table these paths require.",
    ]
    if not substrate_executed:
        return common + [
            "The real substrate is not installed, so only substrate-model paths ran. "
            "Model execution is a precondition, not runtime evidence."
        ]
    return common + [
        "Substrate paths executed against an embedded backend deprecated upstream, chosen because "
        "it needs no server. No governance behavior under test depends on the backend.",
        "Node topology is simplified to one edge per fact; this exercises governance invariants, "
        "not knowledge modelling.",
    ]


def build_report() -> dict:
    substrate_executed = graphiti_available()
    names, passed, failed = _run_suite()
    report = {
        "schema_version": "1.0.0",
        "implementation": "agent-memory reference governed adapter",
        "version": ADAPTER_VERSION,
        "doctrine_version": DOCTRINE_VERSION,
        "policy_version": policy.POLICY_VERSION,
        "conformance_level": 0,
        "fixtures_run": names,
        "fixtures_passed": passed,
        "fixtures_failed": failed,
        "trials_run": len(names),
        "known_exemptions": _exemptions(substrate_executed),
        "known_failures": failed,
        "metric_extensions": {
            "substrate_model": SUBSTRATE_MODEL,
            "real_substrate_executed": substrate_executed,
            "real_substrate": REAL_SUBSTRATE if substrate_executed else None,
            "governance_paths_executed": len(names),
            "negative_paths_executed": len([name for name in names if "positive" not in name]),
        },
    }
    receipts.validate("conformance-report.schema.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", help="Write the report here instead of stdout.")
    args = parser.parse_args()

    report = build_report()
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
        print(f"Wrote conformance report to {args.output}")
    else:
        print(rendered, end="")
    return 1 if report["fixtures_failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
