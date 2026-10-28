#!/usr/bin/env python3
"""Execute the #786 security replay contracts written in ``786-security-replay-dsl/5`` (v7 integration).

    python reference/run_786_security_replays_dsl5.py --all --output-dir <dir>
    python reference/run_786_security_replays_dsl5.py --replay <replay_id> --output-dir <dir>

DSL/5 replays the #786/#809 security families on the store the integrated v7 candidate supports
for several projects: a ``scope_distinct_v1`` store (store-open contract ``1.0.0``,
docs/44-public-api-contract.md), opened through the public ``AgentMemory.open``. The step and
probe grammar is DSL/1-3, inherited unchanged from the byte-frozen runners
``run_786_security_replays.py``, ``run_786_security_replays_dsl2.py`` and
``run_786_security_replays_dsl3.py`` (whose committed evidence keeps verifying against the hashes
it recorded). Exactly three things differ, all forced by scope-distinct keys:

1. every handle is opened with ``store_profile="scope_distinct_v1"``;
2. a host-level step (``delete_version``, ``commit_with_episode``) and a canonical probe
   (``canonical_head``, ``canonical_version``, ``version_in_effect``) name the canonical memory
   of the acting handle's public key, as the facade itself would; ``ref_scope`` names another
   project's canonical memory explicitly (a host-layer, defense-in-depth probe of the canonical
   write gate);
3. canonical keys are mapped back to the public key before any comparison or scan. A key of the
   observing handle's own project reads as the public key, and a key of any other project reads
   as ``<project>key``. A byte-equality probe therefore still differs when another project's
   memory is named, and a mention scan still finds a disclosed foreign key.

This module records its own hash and the three base runners' hashes in the provenance.
Verdict: PASS, FAIL or BLOCKED (dirty source tree). Exit 0 PASS, 1 FAIL, 2 BLOCKED.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent
ROOT = REFERENCE.parent
sys.path.insert(0, str(REFERENCE))

import run_786_security_replays as root_runner  # noqa: E402
import run_786_security_replays_dsl2 as dsl2  # noqa: E402
import run_786_security_replays_dsl3 as base  # noqa: E402
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api import contract  # noqa: E402
from agentmem_ref.api.scoped_identity import scope_distinct_key  # noqa: E402
from agentmem_ref.api.surface import STORE_PROFILE_SCOPE_DISTINCT  # noqa: E402
from agentmem_ref.substrate import Episode  # noqa: E402

RUNNER_VERSION = "786-security-replay-runner/5"
DSL_VERSION = "786-security-replay-dsl/5"
FIXTURE_DIR = root_runner.FIXTURE_DIR
DEFAULT_OUTPUT = ROOT / "reports" / "validation" / "v7-integration" / "security-replays-dsl5"
OUTPUT_REL = "reports/validation/v7-integration/security-replays-dsl5/"
REPLAYS = (
    "cross-scope-write-authority-denial-v4",
    "deleted-lineage-generations-and-restart-v4",
    "public-tombstone-redaction-and-observer-separation-v4",
    "evidence-reference-authorization-v2",
)

sha256_bytes = root_runner.sha256_bytes
sha256_file = root_runner.sha256_file
canonical = root_runner.canonical
match = root_runner.match
ReplayError = root_runner.ReplayError
OWNER, TENANT, ACTOR, PURPOSE = root_runner.OWNER, root_runner.TENANT, root_runner.ACTOR, root_runner.PURPOSE
NEVER = root_runner.NEVER


def _case_keys(case: Mapping) -> tuple[set[str], set[str]]:
    """Every project and public key a case can name: its ``as`` scopes and every ``ref``-like field."""
    scopes, keys = {OWNER}, {NEVER}

    def visit(item):
        if isinstance(item, Mapping):
            for name, value in item.items():
                if name in ("as", "ref_scope") and isinstance(value, str):
                    scopes.add(value)
                elif name in ("ref", "other", "other_ref") and isinstance(value, str) and value.startswith("memory:"):
                    keys.add(value)
                elif name == "logical_refs":
                    keys.update(v for v in value if isinstance(v, str))
                visit(value)
        elif isinstance(item, list):
            for value in item:
                visit(value)

    visit(case)
    return scopes, keys


class Scenario(base.Scenario):
    """DSL/1-3 scenario on a ``scope_distinct_v1`` store; see the module docstring for the three differences."""

    def __init__(self, root: Path, scopes: set[str], keys: set[str]):
        super().__init__(root)
        self._canonical_keys = {(scope, key): scope_distinct_key(TENANT, scope, key)
                                for scope in scopes for key in keys}

    # -- 1. supported multi-project store ------------------------------------------------
    def use(self, scope: str) -> AgentMemory:
        if self.memory is not None and self.scope == scope:
            return self.memory
        self.close()
        self.memory = AgentMemory.open(self.root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose=PURPOSE,
                                       store_profile=STORE_PROFILE_SCOPE_DISTINCT)
        self.scope = scope
        return self.memory

    # -- 2. canonical memory of a public key --------------------------------------------
    def canonical(self, scope: str, key: str) -> str:
        return self._canonical_keys.get((scope, key)) or scope_distinct_key(TENANT, scope, key)

    # -- 3. canonical keys read as public keys, foreign ones marked ------------------------
    def publicize(self, text: str) -> str:
        for (scope, key), canonical_key in self._canonical_keys.items():
            if canonical_key in text:
                text = text.replace(canonical_key, key if scope == self.scope else f"<{scope}>{key}")
        return text

    def labeller(self, text: str) -> str:
        return self.publicize(super().labeller(text))

    def apply(self, op: Mapping) -> None:
        kind = op["op"]
        if kind not in ("delete_version", "commit_with_episode"):
            super().apply(op)
            return
        scope = op.get("as", OWNER)
        m = self.use(scope)
        target = self.canonical(op.get("ref_scope", scope), op["ref"])
        if kind == "delete_version":
            env = m._proposal(target_reference=target, operation="pruning", current_strength="reinforced",
                              proposed_strength="archived", reversibility="reversible", risk_class="low")
            with m.runtime.serialization_lock:
                out = m.runtime.durable_runtime.governed_delete(contract.proposal_from_envelope(env),
                                                                self.resolve(op["fact"]))
            result = {"committed": bool(out.committed), "refusal": out.refusal}
        else:
            env = m._proposal(target_reference=target, operation="promotion", fact_text=op["text"],
                              risk_class=op.get("risk", "low"))
            episode = Episode(uuid=op["episode"], content=op["text"] + " (raw)", source_description="chat",
                              valid_at="2026-01-01T00:00:00Z", group_id=scope)
            with m.runtime.serialization_lock:
                out = m.runtime.durable_runtime.commit_proposal(contract.proposal_from_envelope(env), op["text"], episode)
            result = {"committed": bool(out.committed), "refusal": out.refusal, "outcome": out.decision.outcome,
                      "before_state": out.receipt["before_state"], "after_state": out.receipt["after_state"]}
            if out.committed and out.fact_uuid:
                self.bind(op.get("label") or self._auto_label(scope, op["ref"]), out.fact_uuid)
        if op.get("name"):
            result["full"] = out
            self.ops[op["name"]] = result
        if op.get("require_committed") and not result.get("committed"):
            raise ReplayError(f"{kind} {op.get('ref')} as {scope} did not commit: {result}")

    def _mentions(self, serial: str, tokens) -> list[str]:
        serial = self.publicize(serial)
        return [t for t in tokens if self.labels.get(t, t) in serial]

    def probe(self, spec: Mapping):
        kind = spec["probe"]
        scope = spec.get("as", OWNER)
        if kind in ("canonical_head", "canonical_version"):
            m = self.use(scope)
            record = m._canonical_history(self.canonical(spec.get("ref_scope", scope), spec["ref"]))["history"]
            return self.label(record["current_fact_uuid"]) if kind == "canonical_head" else record["state_version"]
        if kind == "version_in_effect":
            m = self.use(scope)
            adapter = m.runtime.adapter
            instant = adapter._substrate.get_fact(self.resolve(spec["at"])).created_at
            with m.runtime.serialization_lock:
                chosen = adapter.version_in_effect(self.canonical(spec.get("ref_scope", scope), spec["ref"]),
                                                   instant, m._handle_recall_context())
            return self.label(chosen)
        if kind == "op_mentions":
            op = self.ops.get(spec["name"], {})
            full = op.get("full")
            return self._mentions(json.dumps(full if full is not None else {k: v for k, v in op.items() if k != "full"},
                                             sort_keys=True, default=str), spec["tokens"])
        if kind == "history_mentions":
            m = self.use(scope)
            kw = {"fact_text": spec["fact_text"]} if "fact_text" in spec else {}
            return self._mentions(json.dumps(m.history(spec["ref"], **kw), sort_keys=True, default=str), spec["tokens"])
        if kind == "recall_mentions":
            m = self.use(scope)
            kw = {"temporal_intent": root_runner.HIST} if spec.get("historical") else {}
            return self._mentions(json.dumps(m.recall(spec["query"], **kw), sort_keys=True, default=str), spec["tokens"])
        return super().probe(spec)


def run_case(case: Mapping, workdir: Path) -> dict:
    sc = Scenario(workdir / "store", *_case_keys(case))
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
    for name, module in (("runner_base", base), ("runner_dsl2", dsl2), ("runner_root", root_runner)):
        prov[name] = {"path": str(Path(module.__file__).resolve().relative_to(ROOT)),
                      "sha256": sha256_file(Path(module.__file__).resolve()), "version": module.RUNNER_VERSION}
    prov["store_profile"] = STORE_PROFILE_SCOPE_DISTINCT
    return prov


def run_replay(replay_id: str, *, fixture_dir: Path = FIXTURE_DIR, allow_dirty: bool = False) -> dict:
    fixture_path = fixture_dir / f"{replay_id}.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("replay_id") != replay_id or fixture.get("dsl_version") != DSL_VERSION:
        raise ValueError("fixture identity or DSL version mismatch")
    if fixture.get("store_profile") != STORE_PROFILE_SCOPE_DISTINCT:
        raise ValueError("a DSL/5 fixture must declare the scope_distinct_v1 store profile")
    prov = provenance(fixture_path)
    cases = []
    with tempfile.TemporaryDirectory(prefix="s786-dsl5-replay-") as tmp:
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
        "schema": "786-security-replay-report/5", "replay_id": replay_id, "dsl_version": DSL_VERSION,
        "store_profile": STORE_PROFILE_SCOPE_DISTINCT, "verdict": verdict, "verdict_reasons": reasons,
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
    manifest["schema"] = "786-security-replay-manifest/5"
    for name in ("runner_base", "runner_dsl2", "runner_root", "store_profile"):
        manifest[name] = report["provenance"][name]
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
    command = "python reference/run_786_security_replays_dsl5.py " + ("--all" if args.all else f"--replay {args.replay}")
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
