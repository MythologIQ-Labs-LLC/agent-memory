#!/usr/bin/env python3
"""Execute the scope-safe graph discovery replay written in ``786-security-replay-dsl/4`` (#835, #836).

    python reference/run_786_security_replays_dsl4.py --all --output-dir <dir>
    python reference/run_786_security_replays_dsl4.py --replay <replay_id> --output-dir <dir>

DSL/4 is a separate generation of the security replay family for the typed-graph discovery
boundary (docs/41 graph/provenance seed boundary; docs/44 #777 closed generations). It drives
the governed composition runtime directly, because the facts it needs carry project and
shared-domain scope declarations and the typed relations it traverses are canonical substrate
state with no public write surface: every ``remember`` is a governed ``retain`` of a proposal
that declares its scope, every ``relate`` is a canonical ``TypedRelation`` written to the
substrate, and every ``prune`` is a governed reversible deletion the host adjudicates. Every
recall runs through ``ControlledRecallPlanner`` on the composition runtime's adapter, exactly
as the planner's own tests do. The DSL/1-3 runners stay byte-frozen; this module records its own hash and the
root runner's hash (whose provenance, output and matcher helpers it reuses).

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

from agentmem_ref import policy  # noqa: E402
from agentmem_ref.adapter import RecallContext  # noqa: E402
from agentmem_ref.recall_control import (  # noqa: E402
    ControlledRecallPlanner,
    GraphTraversalSpec,
    NativeTypedGraphCandidateRetriever,
    RecallControlPlan,
    RecallRouteBudget,
    TYPED_GRAPH_ROUTE,
)
from agentmem_ref.runtime_composition import (  # noqa: E402
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    ConfiguredCompositionRuntime,
)
from agentmem_ref.runtime_config import validate_runtime_configuration  # noqa: E402
from agentmem_ref.substrate import TypedRelation  # noqa: E402

RUNNER_VERSION = "786-security-replay-runner/4"
DSL_VERSION = "786-security-replay-dsl/4"
FIXTURE_DIR = root_runner.FIXTURE_DIR
DEFAULT_OUTPUT = ROOT / "reports" / "validation" / "835-graph-discovery-replays"
OUTPUT_REL = "reports/validation/835-graph-discovery-replays/"
REPLAYS = ("scope-safe-graph-discovery-v2",)
SUPERSEDED: tuple[str, ...] = ("scope-safe-graph-discovery-v1",)  # executable on request; superseded, not evidence
CONFIG = REFERENCE / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT, ACTOR, PURPOSE = "tenant:g835", "agent:g835", "graph discovery replay"
PROJECTS = {"a": "project:a", "b": "project:b"}
SHARED = "shared:team"

sha256_bytes = root_runner.sha256_bytes
sha256_file = root_runner.sha256_file
canonical = root_runner.canonical
match = root_runner.match
ReplayError = root_runner.ReplayError


def _plan():
    return validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8")))


def _proposal(ref: str, *, project: str, domains: str | None, evidence_refs: tuple[str, ...],
              operation: str = "promotion", **overrides) -> policy.Proposal:
    project_ref = PROJECTS[project]
    if domains == "shared":
        isolation, required = (TENANT, SHARED), (SHARED,)
    else:
        isolation, required = (TENANT, project_ref), (project_ref,)
    fields = dict(
        proposal_id=f"proposal:g835:{ref}:{operation}", actor_id=ACTOR, charter_version="charter-v1",
        target_reference=ref, target_class=policy.M2, scope=TENANT, operation=operation,
        current_strength="observed", proposed_strength="promoted", downstream_authority=policy.A1,
        reversibility="reversible", risk_class="low", evidence_refs=evidence_refs, tenant_ref=TENANT,
        isolation_domain_refs=isolation, required_isolation_domain_refs=required, project_ref=project_ref,
        purpose=PURPOSE,
    )
    fields.update(overrides)
    return policy.Proposal(**fields)


def _context(reader: str, reader_domains: str | None) -> RecallContext:
    project_ref = PROJECTS[reader]
    domains = (TENANT, project_ref) + ((SHARED,) if reader_domains == "shared" else ())
    return RecallContext(target_domain_refs=domains, principal_ref=ACTOR, project_ref=project_ref, purpose=PURPOSE)


class _FixedController:
    def __init__(self, plan: RecallControlPlan) -> None:
        self._plan = plan

    def plan(self, query, *, logical_memory_refs, available_routes):
        return self._plan


class Scenario:
    """One governed composition store; labels are the logical references the fixture names."""

    def __init__(self, root: Path):
        self.root = root
        self.runtime = ConfiguredCompositionRuntime.create(root, tenant=TENANT, plan=_plan())
        self.labels: dict[str, str] = {}
        self.uuid_label: dict[str, str] = {}
        self.scopes: dict[str, tuple[str, str | None]] = {}
        self.results: dict[str, object] = {}

    def close(self) -> None:
        close = getattr(self.runtime.durable_runtime, "close", None)
        if callable(close):
            close()

    def resolve(self, label: str) -> str:
        if label not in self.labels:
            raise ReplayError(f"unknown fact label {label}")
        return self.labels[label]

    def label(self, fact_uuid: str) -> str:
        return self.uuid_label.get(fact_uuid, f"@unlabelled:{fact_uuid}")

    # -- operations ------------------------------------------------------------------------
    def _remember(self, ref: str, text: str, project: str, domains: str | None, cite: list[str]) -> None:
        refs = tuple(self.resolve(x) for x in cite) or (f"evidence:{ref}",)
        out = self.runtime.retain(_proposal(ref, project=project, domains=domains, evidence_refs=refs), text)
        if not out.committed:
            raise ReplayError(f"remember {ref} refused: {out.refusal}")
        self.labels[ref] = out.fact_uuid
        self.uuid_label[out.fact_uuid] = ref
        self.scopes[ref] = (project, domains)

    def apply(self, op: Mapping) -> None:
        kind = op["op"]
        if kind == "remember":
            self._remember(op["ref"], op["text"], op.get("project", "a"), op.get("domains"), list(op.get("cite", ())))
        elif kind == "remember_many":
            for i in range(int(op["count"])):
                self._remember(f"{op['prefix']}-{i:02d}", op["text"].format(i=i), op.get("project", "a"),
                               op.get("domains"), [])
        elif kind == "relate":
            self._relate(op["id"], op["from"], op["to"], float(op.get("weight", 1.0)), op.get("type", "supports"))
        elif kind == "relate_many":
            for i in range(int(op["count"])):
                self._relate(f"{op['id_prefix']}-{i:02d}", op["from"], f"{op['to_prefix']}-{i:02d}",
                             float(op.get("weight", 1.0)), op.get("type", "supports"))
        elif kind == "prune":
            project, domains = self.scopes[op["ref"]]
            proposal = _proposal(op["ref"], project=project, domains=domains, evidence_refs=(f"evidence:prune:{op['ref']}",),
                                 operation="pruning", target_class=policy.M1, proposed_strength="tentative",
                                 review_satisfied=True, approval_refs=("approval:g835",))
            out = self.runtime.delete_current(proposal)
            if not out.committed:
                raise ReplayError(f"prune {op['ref']} refused: {out.refusal}")
        elif kind == "graph_recall":
            self.results[op["name"]] = self._graph_recall(op)
        else:
            raise ReplayError(f"unknown operation {kind}")

    def _relate(self, rid: str, src: str, dst: str, weight: float, rtype: str) -> None:
        self.runtime.adapter.checkpoint_substrate().write_relation(TypedRelation(
            relation_id=rid, source_uuid=self.resolve(src), target_uuid=self.resolve(dst), relation_type=rtype,
            group_id=TENANT, evidence_refs=(), retrieval_weight=weight,
            created_at="2026-10-21T00:00:00Z", valid_at="2026-10-21T00:00:00Z"))

    # -- recall ------------------------------------------------------------------------------
    def _graph_recall(self, spec: Mapping):
        graph_limit = int(spec.get("graph_limit", 8))
        budgets = [RecallRouteBudget(LEXICAL_ROUTE, 0), RecallRouteBudget(EXACT_IDENTITY_ROUTE, int(spec.get("exact_limit", 1)))]
        if graph_limit:
            budgets.append(RecallRouteBudget(TYPED_GRAPH_ROUTE, graph_limit))
        budgets.append(RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0))
        planner = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=_FixedController(RecallControlPlan(controller_ref="g835", controller_version="1",
                                                          route_budgets=tuple(budgets))),
            graph_retriever=NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_depth=int(spec.get("max_depth", 2))))
            if graph_limit else None)
        ctx = _context(spec.get("reader", "a"), spec.get("reader_domains"))
        return planner.recall("", ctx, logical_memory_refs=tuple(spec["seeds"]))

    def probe(self, spec: Mapping):
        kind = spec["probe"]
        if kind == "graph_recall":
            self.results[spec["name"]] = self._graph_recall(spec)
            return sorted(self.label(ref) for ref in self.results[spec["name"]].candidates)
        result = self.results[spec["of"]]
        if kind == "candidate":
            return self.labels.get(spec["fact"]) in result.candidates
        if kind == "admitted":
            return self.labels.get(spec["fact"]) in result.admitted
        if kind == "reported":
            return self.labels.get(spec["fact"]) in result.graph_candidate_hits
        if kind == "path":
            hit = result.graph_candidate_hits.get(self.labels.get(spec["fact"]))
            return None if hit is None else [self.label(ref) for ref in hit.path_refs]
        if kind == "refusal":
            return result.recall.refusals.get(self.labels.get(spec["fact"]))
        if kind == "graph_count":
            return int(result.route_candidate_counts.get(TYPED_GRAPH_ROUTE, 0))
        if kind == "candidate_count":
            return len(result.candidates)
        if kind == "visible_with_prefix":
            return sum(self.label(ref).startswith(spec["prefix"]) for ref in result.candidates)
        raise ReplayError(f"unknown probe {kind}")


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
    return {"id": case["id"], "invariants": case["invariants"], "kind": "graph_discovery", "outcome": outcome,
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
    with tempfile.TemporaryDirectory(prefix="g835-replay-") as tmp:
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
        "schema": "786-security-replay-report/4", "replay_id": replay_id, "dsl_version": DSL_VERSION,
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
    manifest["schema"] = "786-security-replay-manifest/4"
    manifest["runner_root"] = report["provenance"]["runner_root"]
    (output_dir / report["replay_id"] / "manifest.json").write_bytes(
        json.dumps(manifest, indent=1, sort_keys=True).encode() + b"\n")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--replay", choices=REPLAYS + SUPERSEDED)
    group.add_argument("--all", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--allow-dirty", action="store_true", help="development only; the verdict is then BLOCKED")
    args = parser.parse_args(argv)
    replays = REPLAYS if args.all else (args.replay,)
    command = "python reference/run_786_security_replays_dsl4.py " + ("--all" if args.all else f"--replay {args.replay}")
    worst = 0
    for replay_id in replays:
        report = run_replay(replay_id, fixture_dir=args.fixture_dir, allow_dirty=args.allow_dirty)
        manifest = write_outputs(report, args.output_dir, command)
        print(f"{replay_id}: {report['verdict']} ({report['summary']['passed']}/{report['summary']['cases']} cases) "
              f"report sha256 {manifest['report']['sha256']}")
        for reason in report["verdict_reasons"]:
            print(f"  {reason}")
        worst = max(worst, {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[report["verdict"]])
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
