"""#769 validation: realise the frozen 32-case contract against the LIVE runtime.

The contract (evaluation/769-untyped-competition-contract-no-ci @ 0c4b470) is an
abstract classifier over six facets. This harness never edits its inputs or
expected outcomes: it reads both with ``git show`` at the pinned SHA, runs the
frozen evaluator's own self-check, then, per case, builds a real SQLite-backed
store whose state realises the case's facets, runs the opt-in observer, and
projects the runtime diagnostic back into contract vocabulary.

Per case it checks
  safety     -- abstain / no authority / never reviewable / never attested
  receipt    -- a non-verified receipt facet must yield an unverified diagnostic
  facets     -- typed_conflict / untyped_competitor / support are preserved;
                a divergence is "conservative" (runtime more cautious) or "unsafe"
  state      -- contract state of the projection is at least as conservative
                as the contract's own expected state

Facets the runtime cannot express (attested_complete, partial, admission
"unverified", controller_estimate) are recorded as not realisable and the
runtime's stricter state is checked instead.

Usage: python evaluate_contract_against_runtime.py --repo <checkout> --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

CONTRACT_SHA = "0c4b47060bfecc4f1d38374925f5f8d81ee89c2a"
FIXTURE = "reference/fixtures/runtime/769-untyped-competition-v1.json"
EVALUATOR = "scripts/check_769_untyped_competition_contract.py"
RANK = {
    "no_competitor_observed": 0, "untyped_identity_unverified": 1, "typed_conflict": 2,
    "admission_scope_unverified": 3, "enumeration_unattested": 4,
    "observation_integrity_unknown": 5,
}


def _git_show(repo: Path, rev: str, path: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"],
                          check=True, capture_output=True).stdout


def _load_frozen(repo: Path, workdir: Path):
    fixture_bytes = _git_show(repo, CONTRACT_SHA, FIXTURE)
    evaluator_bytes = _git_show(repo, CONTRACT_SHA, EVALUATOR)
    (workdir / "fixture.json").write_bytes(fixture_bytes)
    (workdir / "evaluator.py").write_bytes(evaluator_bytes)
    spec = importlib.util.spec_from_file_location("frozen_769_contract", workdir / "evaluator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, json.loads(fixture_bytes), {
        "contract_sha": CONTRACT_SHA,
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "evaluator_sha256": hashlib.sha256(evaluator_bytes).hexdigest(),
    }


class Runtime:
    """Imports the runtime under test from the checkout passed with --repo."""

    def __init__(self, repo: Path):
        sys.path.insert(0, str(repo / "reference"))
        from agentmem_ref import policy
        from agentmem_ref.recall_control import (
            ControlledRecallPlanner, RecallControlPlan, RecallRouteBudget,
        )
        from agentmem_ref.runtime import typed_proposition as typed
        from agentmem_ref.runtime.adapter import GovernedMemoryAdapter
        from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
        from agentmem_ref.runtime.runtime_composition import (
            ConfiguredCompositionRuntime, LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE,
            SHARED_EVIDENCE_ROUTE,
        )
        from tests.test_recall_control import _plan, _proposal, _context, PROJECT, _FixedController
        self.__dict__.update(locals())
        self.need = CoverageNeed(typed.typed_slot("Aster service", "endpoint"))
        self._temps: list[tempfile.TemporaryDirectory] = []

    def store(self):
        temp = tempfile.TemporaryDirectory()
        self._temps.append(temp)
        rt = self.ConfiguredCompositionRuntime.create(Path(temp.name), tenant="tenant-recall-control",
                                                      plan=self._plan())
        planner = self.ControlledRecallPlanner(rt.adapter, controller=self._FixedController(
            self.RecallControlPlan(
                controller_ref="validation:769-contract", controller_version="1",
                route_budgets=(self.RecallRouteBudget(self.LEXICAL_ROUTE, 20),
                               self.RecallRouteBudget(self.EXACT_IDENTITY_ROUTE, 0),
                               self.RecallRouteBudget(self.SHARED_EVIDENCE_ROUTE, 0)),
                evidence_sufficiency_target=1,
            )))
        return rt, planner

    def typed_write(self, value, *, cardinality="single", **flags):
        validated = self.typed.validate({
            "subject": "Aster service", "attribute": "endpoint", "value": value,
            "assertion": "state", "cardinality": cardinality, "flags": flags,
        })
        return {"typed_proposition": self.typed.typed_record(validated, self.typed.CALLER_DECLARED)}

    def retain(self, rt, name, text, typed_write=None, project=None):
        kw = {"typed_write": typed_write} if typed_write else {}
        out = rt.retain(self._proposal(name, evidence_refs=("session:" + name,),
                                       project_ref=project or self.PROJECT), text, **kw)
        assert out.committed, out
        return out.fact_uuid

    def delete(self, rt, name):
        proposal = replace(self._proposal(name, evidence_refs=("evidence:prune",)),
                           proposal_id=f"prune:{name}", operation="pruning",
                           target_class=self.policy.M1, proposed_strength="tentative",
                           review_satisfied=True, approval_refs=("approver:fixture",))
        assert rt.delete_current(proposal).committed

    def foreign(self, rt, name, text):
        tenant = "tenant-foreign"
        adapter = self.GovernedMemoryAdapter(rt.adapter.checkpoint_substrate(), tenant=tenant)
        proposal = replace(self._proposal(name, evidence_refs=("session:" + name,)),
                           scope=tenant, tenant_ref=tenant,
                           isolation_domain_refs=(tenant, self.PROJECT))
        assert adapter.commit_proposal(proposal, text).committed


def realise(rt_api: Runtime, case: dict) -> tuple[dict, dict]:
    """Build a live store for one case; return (runtime projection dict, realisation notes)."""
    facets = case["input"]
    group = case["group"]
    rt, planner = rt_api.store()
    notes: dict[str, object] = {"not_realisable": []}
    if facets["scope_enumeration"] != "read_path_observed":
        notes["not_realisable"].append(f"scope_enumeration={facets['scope_enumeration']}")
    if facets["admission_boundary"] != "admitted_only":
        notes["not_realisable"].append("admission_boundary=unverified")
    support = facets["support_posture"]
    if support == "controller_estimate":
        notes["not_realisable"].append("support_posture=controller_estimate (controller target=1 supplied; runtime must ignore it)")

    if support == "typed_support":
        if group == "metamorphic_surface" and case["id"] == "C02":
            rt_api.retain(rt, "memory:t1", "Aster service endpoint is /health", rt_api.typed_write("/health"))
            rt_api.retain(rt, "memory:t2", "Aster service endpoint is  /health ", rt_api.typed_write(" /health  "))
        elif group == "metamorphic_surface" and case["id"] == "C03":
            rt_api.retain(rt, "memory:t1", "Aster service endpoint is /health", rt_api.typed_write("/health"))
            rt_api.retain(rt, "memory:t2", "Aster service endpoint is /HEALTH", rt_api.typed_write("/HEALTH"))
        elif group in ("metamorphic_surface", "typed_agreement"):
            rt_api.retain(rt, "memory:t1", "Aster service endpoint is /health", rt_api.typed_write("/health"))
            rt_api.retain(rt, "memory:t2", "The Aster service endpoint remains /health", rt_api.typed_write("/health"))
        elif group == "coexistence":
            rt_api.retain(rt, "memory:t1", "Aster service endpoint is /health",
                          rt_api.typed_write("/health", cardinality="multi"))
            rt_api.retain(rt, "memory:t2", "Aster service endpoint is /ready",
                          rt_api.typed_write("/ready", cardinality="multi"))
        elif group == "cardinality_unknown":
            rt_api.retain(rt, "memory:t1", "Aster service endpoint is /health",
                          rt_api.typed_write("/health", cardinality=None))
        else:
            rt_api.retain(rt, "memory:t1", "Aster service endpoint is /health", rt_api.typed_write("/health"))
    if facets["typed_conflict"]:
        rt_api.retain(rt, "memory:c1", "Aster service endpoint is /legacy", rt_api.typed_write("/legacy"))
    if facets["untyped_competitor"]:
        rt_api.retain(rt, "memory:u1", "Aster service endpoint may have moved last week")
    if group == "lexical_nonmatching":
        rt_api.retain(rt, "memory:u-unrelated", "Weather in Lisbon is warm today")
    if group == "noninterference":
        kind = {"C21": "project", "C22": "deleted", "C23": "disputed", "C24": "foreign"}[case["id"]]
        notes["hidden_kind"] = kind
        text = "Aster service endpoint is /hidden"
        if kind == "project":
            rt_api.retain(rt, "memory:h", text, rt_api.typed_write("/hidden"), project="project-secret")
        elif kind == "deleted":
            rt_api.retain(rt, "memory:h", text, rt_api.typed_write("/hidden"))
            rt_api.delete(rt, "memory:h")
        elif kind == "disputed":
            uuid = rt_api.retain(rt, "memory:h", text, rt_api.typed_write("/hidden"))
            rt.adapter._disputed.add(uuid)  # durable adapters forbid mark_disputed()
        else:
            rt_api.foreign(rt, "memory:h", text)

    result = planner.recall("Aster service endpoint", rt_api._context())
    receipt = facets["receipt_state"]
    if receipt == "missing":
        result = replace(result, observation_receipt=None)
    elif receipt == "mismatch":
        result.recall.admitted.reverse() if len(result.recall.admitted) > 1 else result.recall.admitted.append("ref-9999")
    elif receipt == "stale":
        # An admitted fact is deleted through governance after recall.
        rt_api.delete(rt, "memory:t1")
    diagnostic = planner.observe_competition_diagnostic(result, rt_api._context(), needs=(rt_api.need,))
    return diagnostic.to_dict(), notes


def project(runtime: dict) -> dict:
    return {
        "receipt_state": "verified" if runtime["receipt_state"] == "mutable_receipt_match" else "mismatch",
        "scope_enumeration": runtime["scope_enumeration"],
        "admission_boundary": "admitted_only",
        "support_posture": "typed_support" if runtime["typed_coverage_observed"] else "none",
        "typed_conflict": runtime["diagnosis"] in ("typed_values_unresolved", "typed_value_posture_unresolved"),
        "untyped_competitor": runtime["admitted_untyped_count"] > 0,
    }


def check(contract, case: dict, runtime: dict) -> dict:
    facets = case["input"]
    projected = project(runtime)
    assessed = contract.assess(projected)
    problems: list[str] = []
    conservative: list[str] = []
    if (runtime["stop_recommendation"] != "abstain" or runtime["authority_effect"] != "none"
            or runtime["complete_enumeration_attested"] is not False
            or assessed["reviewable_for_future_positive_policy"]):
        problems.append("safety: authority, attestation or reviewable signal leaked")
    receipt_failure = facets["receipt_state"] != "verified"
    if receipt_failure != (runtime["receipt_state"] == "unverified"):
        problems.append(f"receipt: contract {facets['receipt_state']} -> runtime {runtime['receipt_state']}")
    if not receipt_failure:
        for facet in ("typed_conflict", "untyped_competitor"):
            if projected[facet] != facets[facet]:
                (conservative if projected[facet] else problems).append(
                    f"{facet}: contract {facets[facet]} -> runtime {projected[facet]}")
        expected_support = "typed_support" if facets["support_posture"] == "typed_support" else "none"
        if projected["support_posture"] != expected_support:
            (problems if projected["support_posture"] == "typed_support" else conservative).append(
                f"support: contract {facets['support_posture']} -> runtime {projected['support_posture']}")
    if RANK[assessed["competition_state"]] < RANK[case["expected"]["competition_state"]]:
        problems.append("state: runtime projection less conservative than contract expectation")
    return {
        "id": case["id"], "group": case["group"],
        "contract_expected": case["expected"]["competition_state"],
        "runtime_diagnosis": runtime["diagnosis"],
        "runtime_receipt_state": runtime["receipt_state"],
        "projected_contract_state": assessed["competition_state"],
        "conservative_divergences": conservative,
        "problems": problems,
        "verdict": "FAIL" if problems else "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    head = subprocess.run(["git", "-C", str(args.repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as work:
        contract, fixture, provenance = _load_frozen(args.repo, Path(work))
        self_check = contract.verify_fixture(Path(work) / "fixture.json")
        rt_api = Runtime(args.repo)
        rows = []
        for case in fixture["cases"]:
            runtime, notes = realise(rt_api, case)
            row = check(contract, case, runtime)
            row["realisation"] = notes
            rows.append(row)
    report = {
        "schema": "769-contract-runtime-realisation-v1",
        "runtime_head": head,
        "contract": provenance,
        "frozen_evaluator_self_check": self_check,
        "cases": rows,
        "summary": {
            "cases": len(rows),
            "pass": sum(r["verdict"] == "PASS" for r in rows),
            "fail": [r["id"] for r in rows if r["verdict"] == "FAIL"],
            "conservative_divergence_cases": [r["id"] for r in rows if r["conservative_divergences"]],
            "positive_stops": 0,
        },
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0 if not report["summary"]["fail"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
