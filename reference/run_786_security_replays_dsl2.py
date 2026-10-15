#!/usr/bin/env python3
"""Execute the #786 security replay contracts written in ``786-security-replay-dsl/2`` (the -v3 fixtures).

    python reference/run_786_security_replays_dsl2.py --all --output-dir <dir>
    python reference/run_786_security_replays_dsl2.py --replay <replay_id> --output-dir <dir>

DSL/2 is DSL/1 plus the probes the independent review of the -v2 fixtures found missing
(``reports/validation/805-at-head/independent-replay-review-v2.md``): payload-level scans of
a public ``history`` result, a history summary without the event list, the adapter's
tombstone record (timestamps folded), the recorded message of a raised ``ValueError``, and
the derived-store reconciliation status after a permanent deletion. Every DSL/1 operation
and probe is inherited unchanged from ``run_786_security_replays.py``, which stays
byte-frozen so the committed -v1/-v2 evidence keeps verifying against its recorded runner
hash. This module records both its own hash and the base runner's hash in the provenance.

Verdict: PASS, FAIL or BLOCKED (dirty source tree). Exit 0 PASS, 1 FAIL, 2 BLOCKED.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent
ROOT = REFERENCE.parent
sys.path.insert(0, str(REFERENCE))

import run_786_security_replays as base  # noqa: E402

RUNNER_VERSION = "786-security-replay-runner/2"
DSL_VERSION = "786-security-replay-dsl/2"
FIXTURE_DIR = base.FIXTURE_DIR
DEFAULT_OUTPUT = ROOT / "reports" / "validation" / "786-security-replays-v3"
OUTPUT_REL = "reports/validation/786-security-replays-v3/"
REPLAYS = (
    "cross-scope-write-authority-denial-v3",
    "deleted-lineage-generations-and-restart-v3",
    "public-tombstone-redaction-and-observer-separation-v3",
)
SUPERSEDED = base.REPLAYS + base.SUPERSEDED  # executable on request through the DSL/1 runner only

sha256_bytes = base.sha256_bytes
sha256_file = base.sha256_file
canonical = base.canonical
match = base.match
ReplayError = base.ReplayError
OWNER = base.OWNER


def _fold(text: str) -> str:
    text = re.sub(r"ref-\d+", "ref-X", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", "T", text)
    text = re.sub(r"facade:[0-9a-f]{64}", "facade:H", text)
    text = re.sub(r"content:sha256:[0-9a-f]{64}", "content:H", text)
    return text


class Scenario(base.Scenario):
    """DSL/1 scenario plus the DSL/2 probes; operations are inherited unchanged except that a
    raised ``ValueError`` also records its message."""

    def apply(self, op: Mapping) -> None:
        if op["op"] == "snapshot_tombstone":
            # record the adapter's tombstone of a fact at this point of the scenario (folded)
            self.ops[op["name"]] = {"record": self._tombstone(op.get("as", OWNER), op["fact"])}
            return
        super().apply(op)
        name = op.get("name")
        if name and self.ops.get(name, {}).get("raised") and "raised_message" not in self.ops[name]:
            # DSL/1 keeps only the exception type; re-run the same call to record the message.
            # The facade raises before any target is resolved, so the second call is side-effect free.
            self.ops[name]["raised_message"] = self._raised_message(op)

    def _tombstone(self, scope: str, fact_label: str):
        adapter = self.use(scope).runtime.adapter
        record = adapter.tombstone(self.resolve(fact_label))
        if record is None:
            return None
        return json.loads(_fold(self.labeller(json.dumps(record, sort_keys=True, default=str))))

    def _raised_message(self, op: Mapping) -> str | None:
        m = self.use(op.get("as", OWNER))
        kw: dict = {}
        if "overrides" in op:
            kw["overrides"] = dict(op["overrides"])
        try:
            if op["op"] == "remember":
                if "prop" in op:
                    kw["proposition"] = base._prop(op["prop"])
                m.remember(op["ref"], op["text"], **kw)
            elif op["op"] == "correct":
                m.correct(op["ref"], op["text"], evidence=base._evidence(op.get("as", OWNER)), risk_class="low",
                          replacement_kind=op.get("kind", "state_change"), **kw)
            elif op["op"] == "forget":
                m.forget(op["ref"], permanent=bool(op.get("permanent", False)), **kw)
            elif op["op"] == "dispute":
                m.dispute(op["ref"], evidence=base._evidence(op.get("as", OWNER)), risk_class="low", **kw)
            else:
                return None
        except ValueError as exc:
            return str(exc)
        return None

    def probe(self, spec: Mapping):
        kind = spec["probe"]
        scope = spec.get("as", OWNER)
        if kind == "history_mentions":
            # finding 7: scan the WHOLE serialised history result (event payloads included)
            m = self.use(scope)
            kw = {"fact_text": spec["fact_text"]} if "fact_text" in spec else {}
            serial = json.dumps(m.history(spec["ref"], **kw), sort_keys=True, default=str)
            return [t for t in spec["tokens"] if self.labels.get(t, t) in serial]
        if kind == "history_summary":
            # the public history without its event list (current, version, tombstoned)
            m = self.use(scope)
            record = m.history(spec["ref"])["history"]
            return {"current": self.label(record["current_fact_uuid"]), "state_version": record["state_version"],
                    "tombstoned": record["tombstoned"]}
        if kind == "tombstone_record":
            # the adapter's recorded tombstone for a fact, uuids mapped to labels, times folded
            return self._tombstone(scope, spec["fact"])
        if kind == "tombstone_unchanged":
            # True when the tombstone now equals the one a ``snapshot_tombstone`` step recorded
            before = self.ops.get(spec["name"], {}).get("record", "<absent>")
            return before != "<absent>" and before == self._tombstone(scope, spec["fact"])
        if kind == "op_raised_message":
            return self.ops.get(spec["name"], {}).get("raised_message")
        if kind == "derived_reconciliation":
            posture = self.use(scope).semantic_retrieval_posture()["derived_reconciliation"]
            return {"status": posture["status"], "stores_checked": posture["stores_checked"],
                    "pending": list(posture.get("pending", []))}
        return super().probe(spec)


def run_case(case: Mapping, workdir: Path) -> dict:
    sc = Scenario(workdir / "store")
    obs: dict = {}
    error = None
    try:
        try:
            for op in case.get("steps", ()):
                sc.apply(op)
            for name, spec in case.get("probes", {}).items():
                obs[name] = sc.probe(spec)
        except ReplayError as exc:
            error = f"scenario error: {exc}"
        except Exception as exc:  # noqa: BLE001 - a harness failure is an error, never a pass
            error = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            sc.close()
        except Exception:  # noqa: BLE001
            pass
    checks = []
    if error is None:
        for key, matcher in case["expect"].items():
            value = obs.get(key, "<absent>")
            checks.append({"observable": key, "matcher": matcher, "observed": value, "holds": match(matcher, value)})
    recorded = {k: obs.get(k) for k in case.get("record", ())}
    outcome = "error" if error else ("pass" if all(c["holds"] for c in checks) else "fail")
    return {"id": case["id"], "invariants": case["invariants"], "kind": "lifecycle", "outcome": outcome,
            "error": error, "checks": checks, "recorded": recorded, "observations": obs,
            "clauses": case.get("clauses", []), "implementation_evidence": case.get("implementation_evidence", [])}


def provenance(fixture_path: Path) -> dict:
    status = [line for line in base.git("status", "--porcelain", "--untracked-files=all").splitlines()
              if line[3:].strip('"') and not line[3:].strip('"').startswith(OUTPUT_REL)]
    prov = base.provenance(fixture_path)
    prov["dirty_paths"] = sorted(line[3:] for line in status)
    prov["dirty_exclusion"] = OUTPUT_REL
    prov["runner"] = {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve()),
                      "version": RUNNER_VERSION}
    prov["runner_base"] = {"path": str(Path(base.__file__).resolve().relative_to(ROOT)),
                           "sha256": sha256_file(Path(base.__file__).resolve()), "version": base.RUNNER_VERSION}
    return prov


def run_replay(replay_id: str, *, fixture_dir: Path = FIXTURE_DIR, allow_dirty: bool = False) -> dict:
    fixture_path = fixture_dir / f"{replay_id}.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("replay_id") != replay_id or fixture.get("dsl_version") != DSL_VERSION:
        raise ValueError("fixture identity or DSL version mismatch")
    prov = provenance(fixture_path)
    cases = []
    with tempfile.TemporaryDirectory(prefix="s786v3-replay-") as tmp:
        for i, case in enumerate(fixture["cases"]):
            workdir = Path(tmp) / f"case-{i:03d}"
            workdir.mkdir()
            cases.append(run_case(case, workdir))
    failed = [c["id"] for c in cases if c["outcome"] != "pass"]
    reasons = []
    if failed:
        verdict = "FAIL"
        reasons.append(f"{len(failed)} case(s) did not pass: {', '.join(failed)}")
    elif prov["dirty_paths"] and not allow_dirty:
        verdict = "BLOCKED"
        reasons.append("source tree is dirty outside the evidence directory")
    elif prov["dirty_paths"]:
        verdict = "BLOCKED"
        reasons.append("--allow-dirty: development run, not evidence")
    else:
        verdict = "PASS"
        reasons.append("every expectation held on a clean source tree")
    invariants = {inv["id"]: {"statement": inv["statement"], "cases": [], "holds": True} for inv in fixture["invariants"]}
    for c in cases:
        for inv in c["invariants"]:
            invariants[inv]["cases"].append(c["id"])
            invariants[inv]["holds"] = invariants[inv]["holds"] and c["outcome"] == "pass"
    observations_sha256 = sha256_bytes(canonical([{k: c[k] for k in ("id", "outcome", "checks", "recorded", "observations")}
                                                  for c in cases]))
    return {
        "schema": "786-security-replay-report/2", "replay_id": replay_id, "dsl_version": DSL_VERSION,
        "verdict": verdict, "verdict_reasons": reasons,
        "summary": {"cases": len(cases), "passed": sum(c["outcome"] == "pass" for c in cases),
                    "failed": sum(c["outcome"] == "fail" for c in cases),
                    "errors": sum(c["outcome"] == "error" for c in cases)},
        "invariants": invariants, "cases": cases, "observations_sha256": observations_sha256,
        "provenance": prov,
        "authority_boundary": ("A replay verdict is evidence for independent review. It is not successor acceptance, "
                               "not publication, and not stop authority. sha256 values are integrity bindings, not signatures."),
    }


def write_outputs(report: dict, output_dir: Path, command: str) -> dict:
    manifest = base.write_outputs(report, output_dir, command)
    manifest["schema"] = "786-security-replay-manifest/2"
    manifest["runner_base"] = report["provenance"]["runner_base"]
    (output_dir / report["replay_id"] / "manifest.json").write_bytes(
        json.dumps(manifest, indent=1, sort_keys=True).encode() + b"\n")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--replay", choices=REPLAYS)
    group.add_argument("--all", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--allow-dirty", action="store_true", help="development only; the verdict is then BLOCKED")
    args = parser.parse_args(argv)
    replays = REPLAYS if args.all else (args.replay,)
    command = "python reference/run_786_security_replays_dsl2.py " + ("--all" if args.all else f"--replay {args.replay}")
    worst = 0
    for replay_id in replays:
        report = run_replay(replay_id, fixture_dir=args.fixture_dir, allow_dirty=args.allow_dirty)
        manifest = write_outputs(report, args.output_dir, command)
        s = report["summary"]
        print(f"{replay_id}: {report['verdict']} ({s['passed']}/{s['cases']} cases) report sha256 {manifest['report']['sha256']}")
        for reason in report["verdict_reasons"]:
            print(f"  - {reason}")
        for c in report["cases"]:
            if c["outcome"] != "pass":
                print(f"  {c['id']}: {c['outcome']} {c['error'] or ''}")
                for check in c["checks"]:
                    if not check["holds"]:
                        print(f"    {check['observable']}: expected {check['matcher']} observed {check['observed']!r}")
        worst = max(worst, {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[report["verdict"]])
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
