#!/usr/bin/env python3
"""Adversarial challenge of the committed #644 v7 replay evidence (copies only; nothing in place).

    python reports/validation/644-v7-replays/tamper_challenge.py [--output tamper-challenge.json]

Each mutation is applied to a fresh temporary copy of the committed fixtures, evidence
and runner. `scripts/verify_644_v7_replays.py` must then report something other than
VERIFIED for the mutated replay. The baseline (no mutation) must verify.
"""
from __future__ import annotations

import argparse
import json
import runpy
import shutil
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "reports/validation/644-v7-replays"
FIXTURES = ROOT / "reference/fixtures/644-v7-replays"
verifier = runpy.run_path(str(ROOT / "scripts/verify_644_v7_replays.py"))
runner = verifier["runner"]
R2 = "governed-persisted-typed-slot-sufficiency-admission-recheck-v1"
R4 = "committed-governed-transition-witness-v1"


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def save_report(ev: Path, replay: str, report: dict, *, rehash: bool = True, digest: bool = False) -> None:
    if digest:
        report["observations_sha256"] = verifier["observations_digest"](report)
    data = json.dumps(report, indent=1, sort_keys=True).encode() + b"\n"
    (ev / replay / "report.json").write_bytes(data)
    manifest = load(ev / replay / "manifest.json")
    if rehash:
        manifest["report"]["sha256"] = runner.sha256_bytes(data)
    if digest:
        manifest["observations_sha256"] = report["observations_sha256"]
    (ev / replay / "manifest.json").write_text(json.dumps(manifest))


def case(report: dict, cid: str) -> dict:
    return next(c for c in report["cases"] if c["id"] == cid)


def m_fixture_expectation(ev, fx):
    path = fx / f"{R4}.json"
    doc = load(path)
    doc["cases"][0]["expect"]["witness_count"] = {"eq": 3}
    path.write_text(json.dumps(doc))
    return R4


def m_output_unhashed(ev, fx):
    r = load(ev / R2 / "report.json")
    case(r, "A1-only-caller-declared-exact-slot-support")["observations"]["support_count"] = 7
    save_report(ev, R2, r, rehash=False)
    return R2


def m_output_rehashed_check(ev, fx):
    r = load(ev / R4 / "report.json")
    chk = case(r, "T2-applied-state-change")["checks"][0]
    chk["observed"] = 0
    save_report(ev, R4, r)
    return R4


def m_membership_forged_consistently(ev, fx):
    # Forge which facts supported the slot, keep every check, outcome and digest consistent:
    # only re-execution against the runtime can expose it.
    r = load(ev / R2 / "report.json")
    c = case(r, "A6-hidden-admissible-competitor-counted")
    c["observations"]["support_count"] = 2
    save_report(ev, R2, r, digest=True)
    return R2


def m_membership_forged_with_checks(ev, fx):
    r = load(ev / R2 / "report.json")
    c = case(r, "A3-recheck-after-forget")
    for chk in c["checks"]:
        if chk["observable"] == "support_refs":
            chk["observed"] = chk["matcher"]["eq"] = ["memory:q1", "memory:q2"]
    c["observations"]["support_refs"] = ["memory:q1", "memory:q2"]
    save_report(ev, R2, r, digest=True)
    return R2


def m_provenance_commit(ev, fx):
    r = load(ev / R4 / "report.json")
    r["provenance"]["source_commit"] = "1" * 40
    save_report(ev, R4, r)
    m = load(ev / R4 / "manifest.json")
    m["source_commit"] = "1" * 40
    (ev / R4 / "manifest.json").write_text(json.dumps(m))
    return R4


def m_runtime_tree(ev, fx):
    r = load(ev / R4 / "report.json")
    r["provenance"]["runtime_tree"] = "2" * 40
    save_report(ev, R4, r)
    m = load(ev / R4 / "manifest.json")
    m["runtime_tree"] = "2" * 40
    (ev / R4 / "manifest.json").write_text(json.dumps(m))
    return R4


def m_verdict_upgrade(ev, fx):
    r = load(ev / R4 / "report.json")
    r["cases"][0]["outcome"] = "fail"
    save_report(ev, R4, r, digest=True)
    return R4


def m_dropped_check(ev, fx):
    r = load(ev / R2 / "report.json")
    c = case(r, "A2-weaker-same-slot-claims-are-not-support")
    c["checks"] = c["checks"][1:]
    save_report(ev, R2, r, digest=True)
    return R2


def m_identity_swap(ev, fx):
    m = load(ev / R4 / "manifest.json")
    m["replay_id"] = R2
    (ev / R4 / "manifest.json").write_text(json.dumps(m))
    return R4


def m_deleted_evidence(ev, fx):
    shutil.rmtree(ev / R4)
    return R4


def m_runner_hash(ev, fx):
    m = load(ev / R4 / "manifest.json")
    m["runner"]["sha256"] = "3" * 64
    (ev / R4 / "manifest.json").write_text(json.dumps(m))
    return R4


# A consistent forgery of unasserted observations with recomputed (unkeyed) digests cannot be
# detected statically: sha256 bindings are not signatures. Only re-execution exposes it, so a
# reviewer must run the verifier with --reexecute. That row is expected to VERIFY statically.
STATIC_LIMITATION = {"membership-forged-consistently-static"}

MUTATIONS = {
    "baseline-no-mutation": (None, False),
    "fixture-expectation-edited": (m_fixture_expectation, False),
    "output-edited-without-rehash": (m_output_unhashed, False),
    "output-check-edited-and-rehashed": (m_output_rehashed_check, False),
    "membership-forged-consistently-static": (m_membership_forged_consistently, False),
    "membership-forged-consistently-reexecuted": (m_membership_forged_consistently, True),
    "membership-forged-with-checks": (m_membership_forged_with_checks, False),
    "provenance-commit-forged": (m_provenance_commit, False),
    "runtime-tree-substituted": (m_runtime_tree, False),
    "verdict-upgraded-over-failing-case": (m_verdict_upgrade, False),
    "failing-check-dropped": (m_dropped_check, False),
    "manifest-identity-swapped": (m_identity_swap, False),
    "evidence-deleted": (m_deleted_evidence, False),
    "runner-hash-substituted": (m_runner_hash, False),
}


def challenge() -> list[dict]:
    rows = []
    for name, (mutation, reexecute) in MUTATIONS.items():
        with tempfile.TemporaryDirectory() as tmp:
            ev, fx = Path(tmp) / "evidence", Path(tmp) / "fixtures"
            shutil.copytree(EVIDENCE, ev, ignore=shutil.ignore_patterns("*.py", "*.md", "tamper-challenge.json"))
            shutil.copytree(FIXTURES, fx)
            target = mutation(ev, fx) if mutation else None
            with mock.patch.object(runner, "FIXTURE_DIR", fx):
                result = verifier["verify"](ev, verifier["DECLARATION"], fx, reexecute)
        statuses = {r["replay"]: r["status"] for r in result["replays"]}
        problems = {r["replay"]: r["problems"] for r in result["replays"]}
        if target is None:
            detected, expected = all(s == "VERIFIED" for s in statuses.values()), "all VERIFIED"
        elif name in STATIC_LIMITATION:
            detected = statuses[target] == "VERIFIED"
            expected = "VERIFIED statically (documented limitation: unkeyed hashes); caught only by --reexecute"
        else:
            detected, expected = statuses[target] != "VERIFIED", "target not VERIFIED"
        rows.append({"mutation": name, "target": target, "reexecute": reexecute, "statuses": statuses,
                     "target_problems": problems.get(target, []) if target else [],
                     "expected": expected, "detected_as_expected": detected})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = challenge()
    out = {"challenge": "644-v7-replay-tamper-challenge/1", "rows": rows,
           "all_detected_as_expected": all(r["detected_as_expected"] for r in rows)}
    text = json.dumps(out, indent=1, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    for r in rows:
        print(f"{r['mutation']:45s} {'OK ' if r['detected_as_expected'] else 'MISS'} "
              f"{r['statuses'].get(r['target']) if r['target'] else 'baseline'} {r['target_problems'][:1]}")
    return 0 if out["all_detected_as_expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
