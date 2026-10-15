#!/usr/bin/env python3
"""Execute the #809 security replay contract written in ``786-security-replay-dsl/3``.

    python reference/run_786_security_replays_dsl3.py --all --output-dir <dir>
    python reference/run_786_security_replays_dsl3.py --replay <replay_id> --output-dir <dir>

DSL/3 is DSL/2 plus what the F-R3-2 repair (#809) needs to be falsifiable through the public
facade: same-shape probes that compare two whole public payloads of the citer (``remember``
results, ``history``, ``recall`` by logical reference, ``write_semantics``) after mapping the
citer's own identifiers, the cited strings and the case tokens to placeholders, so that a
foreign-deleted, a foreign-live and an unknown citation must read byte-identically; and a
``dispute`` operation that carries ``evidence_refs``. Every DSL/1 and DSL/2 operation and probe
is inherited unchanged from ``run_786_security_replays.py`` and ``run_786_security_replays_dsl2.py``,
which stay byte-frozen so the committed -v1/-v2/-v3 evidence keeps verifying against the
runner hashes it recorded. This module records its own hash and both base runners' hashes.

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

import run_786_security_replays as root_runner  # noqa: E402
import run_786_security_replays_dsl2 as base  # noqa: E402

RUNNER_VERSION = "786-security-replay-runner/3"
DSL_VERSION = "786-security-replay-dsl/3"
FIXTURE_DIR = base.FIXTURE_DIR
DEFAULT_OUTPUT = ROOT / "reports" / "validation" / "809-security-replays"
OUTPUT_REL = "reports/validation/809-security-replays/"
REPLAYS = ("evidence-reference-authorization-v1",)
SUPERSEDED = base.REPLAYS + base.SUPERSEDED  # executable on request through their own runners only

sha256_bytes = base.sha256_bytes
sha256_file = base.sha256_file
canonical = base.canonical
match = base.match
ReplayError = base.ReplayError
OWNER = base.OWNER
_normalised = root_runner._normalised
_UUID = re.compile(r"^ref-\d+$")


def _canonical(item, fold):
    """Maps keyed by fact uuid become ``[key, value]`` pair lists and lists of fact uuids are
    sorted, both by their folded text, so that order alone never distinguishes two payloads."""
    if isinstance(item, dict):
        if item and all(isinstance(k, str) and _UUID.match(k) for k in item):
            pairs = [[k, _canonical(v, fold)] for k, v in item.items()]
            return sorted(pairs, key=fold)
        return {k: _canonical(v, fold) for k, v in item.items()}
    if isinstance(item, list):
        items = [_canonical(v, fold) for v in item]
        if items and all(isinstance(v, str) and _UUID.match(v) for v in items):
            return sorted(items, key=fold)
        return items
    return item


class Scenario(base.Scenario):
    """DSL/2 scenario plus the DSL/3 same-shape probes and ``dispute`` with ``evidence_refs``."""

    def apply(self, op: Mapping) -> None:
        if op["op"] == "dispute" and "evidence_refs" in op:
            scope = op.get("as", OWNER)
            m = self.use(scope)
            kw = {"evidence": root_runner._evidence(scope), "risk_class": "low",
                  "evidence_refs": tuple(self.resolve(x) for x in op["evidence_refs"])}
            if "fact" in op:
                kw["fact_uuid"] = self.resolve(op["fact"])
            if "overrides" in op:
                kw["overrides"] = dict(op["overrides"])
            try:
                out = m.dispute(op["ref"], **kw)
            except ValueError as exc:
                result = {"raised": type(exc).__name__, "committed": False}
                out = None
            else:
                result = self.outcome(out)
            if op.get("name"):
                result["full"] = out
                self.ops[op["name"]] = result
            if op.get("require_committed") and not result.get("committed"):
                raise ReplayError(f"dispute {op.get('ref')} as {scope} did not commit: {result}")
            return
        super().apply(op)

    # -- same-shape probes ------------------------------------------------------------
    def _placeholders(self, spec: Mapping, text: str) -> str:
        """Map the case's own distinguishing strings to placeholders: each ``substitute``
        entry is ``[needle, placeholder]`` where the needle is a fact label, an ``@literal:``
        string or a plain token; longer needles are replaced first."""
        pairs = []
        for needle, placeholder in spec.get("substitute", ()):
            if needle.startswith("@literal:"):
                pairs.append((needle[len("@literal:"):], placeholder))
            elif needle in self.labels:
                pairs.append((f"<{needle}>", placeholder))  # the labeller already mapped the uuid
            else:
                pairs.append((needle, placeholder))
        for needle, placeholder in sorted(pairs, key=lambda kv: -len(kv[0])):
            text = text.replace(needle, placeholder)
        return text

    def _shape(self, spec: Mapping, value, *, own_ref: str) -> str:
        """The folded, placeholder-substituted serialization of one public payload.

        Beyond DSL/1 ``_normalised`` (uuids to labels, ``ref-N``, ISO timestamps, hashes) this
        folds what the #809 unit module had to fold for the same comparison to be
        satisfiable (independent-preregistration-review SF-1, replay review RF-1): fractional
        ISO timestamps, wall-clock ``"seconds"`` of transaction clocks, every ``*score*``
        float rounded to 1e-6 (an accepted tolerance), and maps keyed by fact uuid and lists
        of fact uuids anywhere in the payload compared without regard to order (sorted by
        their folded text, nothing dropped: the citer's other memories are candidates of
        every recall and rank by the query text, which carries the case token)."""

        def fold(obj) -> str:
            text = _normalised(obj, self.labeller).replace(own_ref, "<memory>")
            text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", "T", text)
            text = re.sub(r"\"seconds\": [0-9.e+-]+", "\"seconds\": S", text)
            text = re.sub(r"(\"[a-z_]*score[a-z_]*\": )(-?[0-9]+\.[0-9]+(?:e-?[0-9]+)?)",
                          lambda m: m.group(1) + format(round(float(m.group(2)), 6), ".6f"), text)
            return self._placeholders(spec, text)

        return fold(_canonical(value, fold))

    def probe(self, spec: Mapping):
        kind = spec["probe"]
        scope = spec.get("as", OWNER)
        if kind == "history_same_as":
            m = self.use(scope)
            a = self._shape(spec, m.history(spec["ref"]), own_ref=spec["ref"])
            b = self._shape(spec, m.history(spec["other"]), own_ref=spec["other"])
            return a == b
        if kind == "op_same_as":
            a_op, b_op = self.ops.get(spec["name"], {}), self.ops.get(spec["other"], {})
            a = self._shape(spec, a_op.get("full"), own_ref=spec["ref"])
            b = self._shape(spec, b_op.get("full"), own_ref=spec["other_ref"])
            return a_op.get("full") is not None and a == b
        if kind == "recall_same_as":
            m = self.use(scope)
            kw = {"temporal_intent": root_runner.HIST} if spec.get("historical") else {}

            def rec(ref, query):
                out = m.recall(query, logical_memory_refs=(ref,), **kw)
                out.get("recall_control", {}).get("usage", {}).pop("elapsed_ms", None)
                return out
            a = self._shape(spec, rec(spec["ref"], spec["query"]), own_ref=spec["ref"])
            b = self._shape(spec, rec(spec["other"], spec.get("other_query", spec["query"])), own_ref=spec["other"])
            return a == b
        if kind == "write_semantics_same_as":
            m = self.use(scope)
            a = self._shape(spec, m.write_semantics(self.resolve(spec["fact"])), own_ref="\0")
            b = self._shape(spec, m.write_semantics(self.resolve(spec["other"])), own_ref="\0")
            return m.write_semantics(self.resolve(spec["fact"])) is not None and a == b
        if kind == "history_events":
            m = self.use(scope)
            return [e["event_type"] for e in m.history(spec["ref"])["history"]["events"]]
        if kind == "history_has_event":
            m = self.use(scope)
            return spec["event_type"] in [e["event_type"] for e in m.history(spec["ref"])["history"]["events"]]
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
            "clauses": case.get("clauses", []), "implementation_evidence": case.get("implementation_evidence", []),
            "controls": case.get("controls", [])}


def provenance(fixture_path: Path) -> dict:
    status = [line for line in root_runner.git("status", "--porcelain", "--untracked-files=all").splitlines()
              if line[3:].strip('"') and not line[3:].strip('"').startswith(OUTPUT_REL)]
    prov = root_runner.provenance(fixture_path)
    prov["dirty_paths"] = sorted(line[3:] for line in status)
    prov["dirty_exclusion"] = OUTPUT_REL
    prov["runner"] = {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve()),
                      "version": RUNNER_VERSION}
    prov["runner_base"] = {"path": str(Path(base.__file__).resolve().relative_to(ROOT)),
                           "sha256": sha256_file(Path(base.__file__).resolve()), "version": base.RUNNER_VERSION}
    prov["runner_root"] = {"path": str(Path(root_runner.__file__).resolve().relative_to(ROOT)),
                           "sha256": sha256_file(Path(root_runner.__file__).resolve()), "version": root_runner.RUNNER_VERSION}
    return prov


def run_replay(replay_id: str, *, fixture_dir: Path = FIXTURE_DIR, allow_dirty: bool = False) -> dict:
    fixture_path = fixture_dir / f"{replay_id}.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("replay_id") != replay_id or fixture.get("dsl_version") != DSL_VERSION:
        raise ValueError("fixture identity or DSL version mismatch")
    prov = provenance(fixture_path)
    cases = []
    with tempfile.TemporaryDirectory(prefix="s809-replay-") as tmp:
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
        "schema": "786-security-replay-report/3", "replay_id": replay_id, "dsl_version": DSL_VERSION,
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
    manifest = root_runner.write_outputs(report, output_dir, command)
    manifest["schema"] = "786-security-replay-manifest/3"
    manifest["runner_base"] = report["provenance"]["runner_base"]
    manifest["runner_root"] = report["provenance"]["runner_root"]
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
    command = "python reference/run_786_security_replays_dsl3.py " + ("--all" if args.all else f"--replay {args.replay}")
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
    sys.exit(main())
