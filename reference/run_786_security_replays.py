#!/usr/bin/env python3
"""Execute the #786 security replay contracts (``786-security-replay-dsl/1``).

    python reference/run_786_security_replays.py --all --output-dir reports/validation/786-security-replays
    python reference/run_786_security_replays.py --replay <replay_id> --output-dir <dir>

A separate replay family beside the five frozen #644 v7 contracts: the v7 runner, fixtures,
evidence and verifier are not touched, so their recorded hashes keep binding. This runner
drives the public ``AgentMemory`` facade with one live handle at a time (every scope switch
closes the handle and recovers a fresh one, so a step never acts on a stale in-memory view);
the only non-facade calls are the documented adapter read methods the fixtures name
(``version_in_effect``, the canonical history used as the ground truth of a case, the
substrate episode lookup for the denied-episode contract) and the governed partial deletion
the #777 review used. Private state is never written.

Input: a frozen fixture ``reference/fixtures/786-security-replays/<replay_id>.json``.
Output: ``<dir>/<replay_id>/report.json`` and ``manifest.json`` binding fixture, runner, report
and runtime tree by sha256 (integrity bindings for review, never signatures or acceptance).
Verdict: PASS, FAIL or BLOCKED (dirty source tree). Exit 0 PASS, 1 FAIL, 2 BLOCKED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent
ROOT = REFERENCE.parent
sys.path.insert(0, str(REFERENCE))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api import contract  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.substrate import Episode  # noqa: E402

RUNNER_VERSION = "786-security-replay-runner/1"
DSL_VERSION = "786-security-replay-dsl/1"
FIXTURE_DIR = REFERENCE / "fixtures" / "786-security-replays"
DEFAULT_OUTPUT = ROOT / "reports" / "validation" / "786-security-replays"
OUTPUT_REL = "reports/validation/786-security-replays/"
REPLAYS = (
    "cross-scope-write-authority-denial-v1",
    "deleted-lineage-generations-and-restart-v1",
    "public-tombstone-redaction-and-observer-separation-v1",
)
TENANT, ACTOR, PURPOSE = "tenant:s786", "agent:s786", "786 security replay"
OWNER, OTHER, NEVER = "project:a", "project:b", "memory:never"
HIST = {"mode": "historical"}


class ReplayError(Exception):
    """A case could not execute as specified (a harness or scenario failure)."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def _prop(spec: Mapping) -> dict:
    out = {"subject": spec["s"], "attribute": spec["a"], "value": spec["v"],
           "assertion": spec.get("assertion", "state"), "cardinality": spec.get("cardinality", "single"),
           "flags": dict(spec.get("flags", {}))}
    if "replaces" in spec:
        out["replaces_value"] = spec["replaces"]
    return out


def _evidence(scope: str):
    skill = pm.SkillArtifact(
        skill_id="skill:s786", version=1, purpose=PURPOSE, scope=scope,
        isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# v\nok", provenance_refs=("evidence:s786",))
    return pm.evidence_for(skill)


def _normalised(value, labeller) -> str:
    """Serialize after folding volatile identifiers and target ids, mapping fact uuids to labels."""
    text = json.dumps(value, sort_keys=True, default=str)
    text = labeller(text)
    text = re.sub(r"ref-\d+", "ref-X", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "T", text)
    text = re.sub(r"facade:[0-9a-f]{64}", "facade:H", text)
    text = re.sub(r"content:sha256:[0-9a-f]{64}", "content:H", text)
    return text


class Scenario:
    """A fresh store driven through the public facade; one live handle, labelled facts."""

    def __init__(self, root: Path):
        self.root = root
        self.scope: str | None = None
        self.memory: AgentMemory | None = None
        self.labels: dict[str, str] = {}
        self.uuid_label: dict[str, str] = {}
        self.heads: dict[tuple[str, str], int] = {}
        self.ops: dict[str, dict] = {}
        self.counter = 0

    # -- handles ----------------------------------------------------------------------
    def use(self, scope: str) -> AgentMemory:
        if self.memory is not None and self.scope == scope:
            return self.memory
        self.close()
        self.memory = AgentMemory.open(self.root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose=PURPOSE)
        self.scope = scope
        return self.memory

    def reopen(self) -> None:
        scope = self.scope or OWNER
        self.close()
        self.use(scope)

    def close(self) -> None:
        if self.memory is not None and not self.memory.closed:
            self.memory.close()
        self.memory = None
        self.scope = None

    # -- labels -----------------------------------------------------------------------
    def bind(self, label: str, fact_uuid: str) -> None:
        self.labels[label] = fact_uuid
        self.uuid_label[fact_uuid] = label

    def resolve(self, label: str) -> str:
        if label.startswith("@literal:"):
            return label[len("@literal:"):]
        if label not in self.labels:
            raise ReplayError(f"unknown fact label {label}")
        return self.labels[label]

    def label(self, fact_uuid) -> str | None:
        if fact_uuid is None:
            return None
        return self.uuid_label.get(fact_uuid, f"@unlabelled")

    def labeller(self, text: str) -> str:
        for uuid, label in sorted(self.uuid_label.items(), key=lambda kv: -len(kv[0])):
            text = text.replace(uuid, f"<{label}>")
        return text

    def _auto_label(self, scope: str, ref: str) -> str:
        n = self.heads.get((scope, ref), 0) + 1
        self.heads[(scope, ref)] = n
        base = ref if scope == OWNER else f"{scope}|{ref}"
        return base if n == 1 else f"{base}@{n}"

    # -- outcome shape ----------------------------------------------------------------
    @staticmethod
    def outcome(out: Mapping) -> dict:
        receipt = out.get("receipt") or {}
        return {"committed": bool(out.get("committed")), "refusal": out.get("refusal"),
                "outcome": out.get("outcome"), "before_state": receipt.get("before_state"),
                "after_state": receipt.get("after_state"), "state_snapshot": receipt.get("state_snapshot"),
                "has_receipt": bool(receipt)}

    # -- operations ---------------------------------------------------------------------
    def apply(self, op: Mapping) -> None:
        kind = op["op"]
        scope = op.get("as", OWNER)
        name = op.get("name")
        if kind == "reopen":
            self.reopen()
            return
        m = self.use(scope)
        result: dict
        if kind == "remember":
            kw: dict = {}
            if "prop" in op:
                kw["proposition"] = _prop(op["prop"])
            if "evidence_refs" in op:
                kw["evidence_refs"] = tuple(self.resolve(x) for x in op["evidence_refs"])
            if "overrides" in op:
                kw["overrides"] = dict(op["overrides"])
            try:
                out = m.remember(op["ref"], op["text"], **kw)
            except ValueError as exc:
                result = {"raised": type(exc).__name__, "committed": False}
            else:
                result = self.outcome(out)
                if out.get("committed"):
                    self.bind(op.get("label") or self._auto_label(scope, op["ref"]), out["fact_uuid"])
        elif kind == "correct":
            kw = {"evidence": _evidence(scope), "risk_class": "low", "replacement_kind": op.get("kind", "state_change")}
            if "overrides" in op:
                kw["overrides"] = dict(op["overrides"])
            try:
                out = m.correct(op["ref"], op["text"], **kw)
            except ValueError as exc:
                result = {"raised": type(exc).__name__, "committed": False}
            else:
                result = self.outcome(out)
                if out.get("committed"):
                    self.bind(op.get("label") or self._auto_label(scope, op["ref"]), out["fact_uuid"])
        elif kind == "forget":
            kw = {"permanent": bool(op.get("permanent", False))}
            if op.get("permanent"):
                kw["evidence"] = _evidence(scope)
                kw["risk_class"] = "low"
            if "overrides" in op:
                kw["overrides"] = dict(op["overrides"])
            try:
                out = m.forget(op["ref"], **kw)
            except ValueError as exc:
                result = {"raised": type(exc).__name__, "committed": False}
            else:
                result = self.outcome(out)
        elif kind == "dispute":
            kw = {"evidence": _evidence(scope), "risk_class": "low"}
            if "fact" in op:
                kw["fact_uuid"] = self.resolve(op["fact"])
            if "overrides" in op:
                kw["overrides"] = dict(op["overrides"])
            try:
                out = m.dispute(op["ref"], **kw)
            except ValueError as exc:
                result = {"raised": type(exc).__name__, "committed": False}
            else:
                result = self.outcome(out)
        elif kind == "delete_version":
            # the #777 review's governed partial deletion of one superseded version
            env = m._proposal(target_reference=op["ref"], operation="pruning", current_strength="reinforced",
                              proposed_strength="archived", reversibility="reversible", risk_class="low")
            with m.runtime.serialization_lock:
                out = m.runtime.durable_runtime.governed_delete(contract.proposal_from_envelope(env), self.resolve(op["fact"]))
            result = {"committed": bool(out.committed), "refusal": out.refusal}
        elif kind == "commit_with_episode":
            env = m._proposal(target_reference=op["ref"], operation="promotion", fact_text=op["text"],
                              risk_class=op.get("risk", "low"))
            proposal = contract.proposal_from_envelope(env)
            episode = Episode(uuid=op["episode"], content=op["text"] + " (raw)", source_description="chat",
                              valid_at="2026-01-01T00:00:00Z", group_id=scope)
            with m.runtime.serialization_lock:
                out = m.runtime.durable_runtime.commit_proposal(proposal, op["text"], episode)
            result = {"committed": bool(out.committed), "refusal": out.refusal, "outcome": out.decision.outcome,
                      "before_state": out.receipt["before_state"], "after_state": out.receipt["after_state"]}
            if out.committed and out.fact_uuid:
                self.bind(op.get("label") or self._auto_label(scope, op["ref"]), out.fact_uuid)
        else:
            raise ReplayError(f"unknown operation {kind}")
        if name:
            self.ops[name] = result
        if op.get("require_committed") and not result.get("committed"):
            raise ReplayError(f"{kind} {op.get('ref')} as {scope} did not commit: {result}")

    # -- probes -------------------------------------------------------------------------
    def probe(self, spec: Mapping):
        kind = spec["probe"]
        scope = spec.get("as", OWNER)
        if kind == "canonical_head":
            m = self.use(scope)
            return self.label(m._canonical_history(spec["ref"])["history"]["current_fact_uuid"])
        if kind == "canonical_version":
            return self.use(scope)._canonical_history(spec["ref"])["history"]["state_version"]
        if kind == "history":
            m = self.use(scope)
            kw = {"fact_text": spec["fact_text"]} if "fact_text" in spec else {}
            record = m.history(spec["ref"], **kw)["history"]
            out = {"current": self.label(record["current_fact_uuid"]), "state_version": record["state_version"],
                   "tombstoned": record["tombstoned"], "events": [e["event_type"] for e in record["events"]]}
            if "rejected_values" in record:
                out["rejected_values"] = len(record["rejected_values"])
            return out
        if kind == "history_same_as_unknown":
            m = self.use(scope)
            kw = {"fact_text": spec["fact_text"]} if "fact_text" in spec else {}
            a = _normalised(m.history(spec["ref"], **kw), self.labeller).replace(spec["ref"], NEVER)
            b = _normalised(m.history(NEVER, **kw), self.labeller)
            return a == b
        if kind == "op_same_as_unknown":
            m = self.use(scope)
            def run(ref):
                if spec["op"] == "correct":
                    return m.correct(ref, spec["text"], evidence=_evidence(scope), risk_class="low",
                                     replacement_kind="state_change")
                if spec["op"] == "forget":
                    kw = {"permanent": bool(spec.get("permanent", False))}
                    if spec.get("permanent"):
                        kw.update(evidence=_evidence(scope), risk_class="low")
                    return m.forget(ref, **kw)
                if spec["op"] == "dispute":
                    return m.dispute(ref, evidence=_evidence(scope), risk_class="low")
                raise ReplayError(f"unknown op {spec['op']}")
            a = _normalised(run(spec["ref"]), self.labeller).replace(spec["ref"], NEVER)
            b = _normalised(run(NEVER), self.labeller)
            return a == b
        if kind == "recall_admitted":
            m = self.use(scope)
            kw = {}
            if spec.get("historical"):
                kw["temporal_intent"] = HIST
            if "logical_refs" in spec:
                kw["logical_memory_refs"] = tuple(spec["logical_refs"])
            out = m.recall(spec["query"], **kw)
            return [self.label(x) for x in out["admitted"]]
        if kind == "recall_mentions":
            m = self.use(scope)
            kw = {"temporal_intent": HIST} if spec.get("historical") else {}
            serial = json.dumps(m.recall(spec["query"], **kw), sort_keys=True, default=str)
            found = []
            for token in spec["tokens"]:
                needle = self.labels.get(token, token)
                if needle in serial:
                    found.append(token)
            return found
        if kind == "recall_same_as_unknown":
            m = self.use(scope)
            def rec(ref):
                out = m.recall(spec["query"], logical_memory_refs=(ref,), temporal_intent=HIST)
                out.get("recall_control", {}).get("usage", {}).pop("elapsed_ms", None)
                return out
            a = _normalised(rec(spec["ref"]), self.labeller).replace(spec["ref"], NEVER)
            return a == _normalised(rec(NEVER), self.labeller)
        if kind == "fact_valid":
            fact = self.use(scope).runtime.adapter._substrate.get_fact(self.resolve(spec["fact"]))
            return None if fact is None else fact.invalid_at is None
        if kind == "fact_exists":
            return self.use(scope).runtime.adapter._substrate.get_fact(self.resolve(spec["fact"])) is not None
        if kind == "tombstoned_ids":
            return sorted(self.use(scope).runtime.adapter.tombstoned_ids())
        if kind == "disputed":
            adapter = self.use(scope).runtime.adapter
            return sorted(self.label(x) for x in adapter._disputed)
        if kind == "episode_present":
            return self.use(scope).runtime.adapter._substrate.get_episode(spec["episode"]) is not None
        if kind == "write_semantics_present":
            return self.use(scope).write_semantics(self.resolve(spec["fact"])) is not None
        if kind == "version_in_effect":
            m = self.use(scope)
            adapter = m.runtime.adapter
            instant = adapter._substrate.get_fact(self.resolve(spec["at"])).created_at
            with m.runtime.serialization_lock:
                chosen = adapter.version_in_effect(spec["ref"], instant, m._handle_recall_context())
            return self.label(chosen)
        if kind == "op_result":
            return self.ops.get(spec["name"], {}).get(spec["field"])
        if kind == "op_mentions":
            serial = json.dumps(self.ops.get(spec["name"], {}), sort_keys=True, default=str)
            return [t for t in spec["tokens"] if self.labels.get(t, t) in serial]
        raise ReplayError(f"unknown probe {kind}")


def match(matcher: Mapping, value) -> bool:
    (op, expected), = matcher.items()
    if op == "eq":
        return value == expected
    if op == "ne":
        return value != expected
    if op == "in":
        return value in expected
    if op == "not_in":
        return value not in expected
    raise ReplayError(f"unknown matcher {op}")


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
            "error": error, "checks": checks, "recorded": recorded, "observations": obs}


# ------------------------------------------------------------------------------- provenance

def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def provenance(fixture_path: Path) -> dict:
    status = [line for line in git("status", "--porcelain", "--untracked-files=all").splitlines()
              if line[3:].strip('"') and not line[3:].strip('"').startswith(OUTPUT_REL)]
    return {
        "source_commit": git("rev-parse", "HEAD"),
        "runtime_tree": git("rev-parse", "HEAD:reference/agentmem_ref"),
        "dirty_paths": sorted(line[3:] for line in status),
        "dirty_exclusion": OUTPUT_REL,
        "fixture": {"path": (str(fixture_path.resolve().relative_to(ROOT)) if fixture_path.resolve().is_relative_to(ROOT)
                             else str(fixture_path.resolve())), "sha256": sha256_file(fixture_path)},
        "runner": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve()),
                   "version": RUNNER_VERSION},
        "python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "platform": platform.platform(),
    }


def run_replay(replay_id: str, *, fixture_dir: Path = FIXTURE_DIR, allow_dirty: bool = False) -> dict:
    fixture_path = fixture_dir / f"{replay_id}.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("replay_id") != replay_id or fixture.get("dsl_version") != DSL_VERSION:
        raise ValueError("fixture identity or DSL version mismatch")
    prov = provenance(fixture_path)
    cases = []
    with tempfile.TemporaryDirectory(prefix="s786-replay-") as tmp:
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
        "schema": "786-security-replay-report/1", "replay_id": replay_id, "dsl_version": DSL_VERSION,
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
    target = output_dir / report["replay_id"]
    target.mkdir(parents=True, exist_ok=True)
    report_bytes = json.dumps(report, indent=1, sort_keys=True, default=str).encode() + b"\n"
    (target / "report.json").write_bytes(report_bytes)
    manifest = {
        "schema": "786-security-replay-manifest/1", "replay_id": report["replay_id"], "verdict": report["verdict"],
        "fixture": report["provenance"]["fixture"], "runner": report["provenance"]["runner"],
        "report": {"path": "report.json", "sha256": sha256_bytes(report_bytes)},
        "observations_sha256": report["observations_sha256"],
        "source_commit": report["provenance"]["source_commit"], "runtime_tree": report["provenance"]["runtime_tree"],
        "command": command,
        "attestation": "none: hashes bind contents for review; they are not signatures and confer no acceptance",
    }
    (target / "manifest.json").write_bytes(json.dumps(manifest, indent=1, sort_keys=True).encode() + b"\n")
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
    command = "python reference/run_786_security_replays.py " + ("--all" if args.all else f"--replay {args.replay}")
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
