#!/usr/bin/env python3
"""Independently verify committed #644 v7 replay evidence against fixtures, runner and runtime.

    python scripts/verify_644_v7_replays.py [--reexecute] [--evidence-root DIR]

For every replay the v7 declaration requires, this checks that:

- the manifest names the replay and binds the exact report bytes;
- the fixture and runner bytes on disk equal the recorded hashes;
- the recorded runtime tree equals the tree of the recorded source commit, that commit is
  an ancestor of HEAD, and the working tree's runtime files equal that commit's (the
  Runtime Baseline source boundary, which excludes `reference/agentmem_ref/evaluation/**`:
  lane records and evaluation machinery committed later do not make the evidence stale);
- the report covers every fixture case exactly once, and each check corresponds to a
  fixture expectation;
- every recorded verdict, `holds` flag and observation digest recomputes from the report's
  own observations.

With `--reexecute` it runs the replay again and requires identical observations.

Verification is not acceptance. A VERIFIED replay is reproducible, untampered evidence for
an independent reviewer. v7 acceptance additionally requires that reviewer's decision,
recorded in META_LEDGER, which this tool can neither make nor infer. The evidence inventory
(`scripts/check_644_v7_replay_inventory.py`) deliberately stays BLOCKED.
Exit status: 0 when every replay is VERIFIED with verdict PASS; otherwise 1.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))
import run_644_v7_replays as runner  # noqa: E402

DECLARATION = ROOT / "reports/runtime/baseline-v7-declaration.json"
EVIDENCE_ROOT = ROOT / "reports/validation/644-v7-replays"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=check)


# The Runtime Baseline source boundary (reports/runtime/baseline-v1-source-boundary.json).
RUNTIME_PATHSPECS = ("reference/agentmem_ref", ":(exclude)reference/agentmem_ref/evaluation/**")


def runtime_changed_since(commit: str) -> bool:
    """True when the working tree's runtime files differ from ``commit``'s or are untracked."""
    changed = git("diff", "--quiet", commit, "--", *RUNTIME_PATHSPECS, check=False).returncode != 0
    untracked = git("ls-files", "--others", "--exclude-standard", "--", *RUNTIME_PATHSPECS).stdout.strip()
    return changed or bool(untracked)


def declared_replays(declaration: Path) -> list[str]:
    record = json.loads(declaration.read_text(encoding="utf-8"))
    ids = [x["ref"] for x in record.get("acceptance_evidence_required", []) if x.get("kind") == "replay"]
    if not ids or len(ids) != len(set(ids)) or any("/" in i or ".." in i for i in ids):
        raise ValueError("replay declarations missing, duplicated or unsafe")
    return ids


def observations_digest(report: dict) -> str:
    return runner.sha256_bytes(runner.canonical(
        [{k: c[k] for k in ("id", "outcome", "checks", "recorded", "observations")} for c in report["cases"]]))


def verify_one(replay_id: str, evidence_root: Path, fixture_dir: Path, reexecute: bool) -> dict:
    problems: list[str] = []
    base = evidence_root / replay_id
    manifest_path, report_path = base / "manifest.json", base / "report.json"
    if not manifest_path.is_file() or not report_path.is_file():
        return {"replay": replay_id, "status": "MISSING", "problems": ["manifest or report absent"]}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report_bytes = report_path.read_bytes()
        report = json.loads(report_bytes)
    except (OSError, ValueError) as exc:
        return {"replay": replay_id, "status": "TAMPERED", "problems": [f"unreadable evidence: {type(exc).__name__}"]}
    if manifest.get("replay_id") != replay_id or report.get("replay_id") != replay_id:
        problems.append("replay identity mismatch")
    if manifest.get("report", {}).get("sha256") != runner.sha256_bytes(report_bytes):
        problems.append("report bytes do not match manifest hash")
    prov = report.get("provenance", {})
    fixture_path = fixture_dir / f"{replay_id}.json"
    if not fixture_path.is_file():
        problems.append("fixture absent")
        fixture = {"cases": []}
    else:
        fixture_sha = runner.sha256_file(fixture_path)
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        if fixture_sha != prov.get("fixture", {}).get("sha256") or fixture_sha != manifest.get("fixture", {}).get("sha256"):
            problems.append("fixture bytes differ from the recorded fixture hash")
    runner_sha = runner.sha256_file(Path(runner.__file__).resolve())
    if runner_sha != prov.get("runner", {}).get("sha256") or runner_sha != manifest.get("runner", {}).get("sha256"):
        problems.append("runner bytes differ from the recorded runner hash")
    commit, tree = prov.get("source_commit", ""), prov.get("runtime_tree", "")
    if manifest.get("source_commit") != commit or manifest.get("runtime_tree") != tree:
        problems.append("manifest and report provenance disagree")
    recorded_tree = git("rev-parse", f"{commit}:reference/agentmem_ref", check=False)
    if recorded_tree.returncode != 0 or recorded_tree.stdout.strip() != tree:
        problems.append("recorded source commit does not carry the recorded runtime tree")
    if git("merge-base", "--is-ancestor", commit, "HEAD", check=False).returncode != 0:
        problems.append("recorded source commit is not an ancestor of HEAD")
    stale = runtime_changed_since(commit)
    # Report internal consistency against the frozen fixture.
    fixture_cases = {c["id"]: c for c in fixture.get("cases", [])}
    report_cases = report.get("cases", [])
    ids = [c.get("id") for c in report_cases]
    if sorted(ids) != sorted(fixture_cases) or len(ids) != len(set(ids)):
        problems.append("report cases differ from fixture cases")
    for case in report_cases:
        spec = fixture_cases.get(case.get("id"))
        if spec is None:
            continue
        if case.get("outcome") != "error":
            expected = {k: v for k, v in spec["expect"].items()}
            got = {c["observable"]: c["matcher"] for c in case.get("checks", [])}
            if got != expected:
                problems.append(f"{case['id']}: checks do not match fixture expectations")
            for check in case.get("checks", []):
                if check["observable"] in case.get("observations", {}) and case["observations"][check["observable"]] != check["observed"]:
                    problems.append(f"{case['id']}: check observation differs from recorded observation")
                if runner.match(check["matcher"], check["observed"]) != check["holds"]:
                    problems.append(f"{case['id']}: recorded 'holds' does not recompute")
            outcome = "pass" if all(c["holds"] for c in case.get("checks", [])) else "fail"
            if case.get("outcome") != outcome:
                problems.append(f"{case['id']}: outcome does not recompute")
    if observations_digest(report) != report.get("observations_sha256") or report.get("observations_sha256") != manifest.get("observations_sha256"):
        problems.append("observations digest does not recompute")
    any_fail = any(c.get("outcome") != "pass" for c in report_cases)
    expected_verdict = "FAIL" if any_fail else ("BLOCKED" if prov.get("dirty_paths") else "PASS")
    if report.get("verdict") != expected_verdict or manifest.get("verdict") != expected_verdict:
        problems.append(f"verdict does not recompute (expected {expected_verdict})")
    if reexecute and not problems:
        with tempfile.TemporaryDirectory():
            again = runner.run_replay(replay_id, fixture_dir=fixture_dir, allow_dirty=True)
        if again["observations_sha256"] != report.get("observations_sha256"):
            problems.append("re-execution produced different observations")
    if problems:
        status = "TAMPERED"
    elif stale:
        status = "STALE"
        problems.append("runtime files differ from the evidence source commit")
    else:
        status = "VERIFIED"
    return {"replay": replay_id, "status": status, "verdict": report.get("verdict"), "problems": problems,
            "reexecuted": bool(reexecute and status == "VERIFIED")}


def verify(evidence_root: Path = EVIDENCE_ROOT, declaration: Path = DECLARATION,
           fixture_dir: Path = runner.FIXTURE_DIR, reexecute: bool = False) -> dict:
    rows = [verify_one(r, evidence_root, fixture_dir, reexecute) for r in declared_replays(declaration)]
    complete = all(r["status"] == "VERIFIED" and r["verdict"] == "PASS" for r in rows)
    return {"replays": rows, "evidence_verified": complete,
            "acceptance": "NOT GRANTED: requires an independent reviewer's decision recorded in META_LEDGER"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    parser.add_argument("--declaration", type=Path, default=DECLARATION)
    parser.add_argument("--reexecute", action="store_true")
    args = parser.parse_args(argv)
    result = verify(args.evidence_root, args.declaration, reexecute=args.reexecute)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["evidence_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
