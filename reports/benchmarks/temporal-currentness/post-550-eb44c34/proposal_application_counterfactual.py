"""#550: what would a governed caller's acceptance of the runtime's own proposals change?

Usage: PYTHONPATH=reference python reports/benchmarks/temporal-currentness/post-550-eb44c34/proposal_application_counterfactual.py <out.json>

Evaluation-only counterfactual over the frozen #580 corpus (gold untouched). For each
case: run the fixture setup exactly as the evaluator does, list the write-time
``state_change`` proposals the runtime emitted, then play a *reviewing caller* who
applies every open proposal through ``AgentMemory.apply_semantic_proposal`` (the
ordinary governed ``correct(replacement_kind="state_change")``, with qualified review
evidence), re-observe every probe, and score it with the unmodified evaluator.

The runtime itself never applies a proposal. This shows which frozen target failures a
proposal resolves *if* governance accepts it, and it shows the price: the fixture's
``no_mutation`` assertions fail by construction once the caller chooses to mutate.
Nothing here is written back into the gauntlet's scored results.
"""
import json
import sys
import tempfile
from pathlib import Path

from agentmem_ref.evaluation import temporal_currentness as tc

FIXTURE = Path(__file__).resolve().parents[4] / "reference" / "fixtures" / "benchmarks" / "temporal-currentness" / "temporal-currentness-gauntlet-v1.json"


def run_case(case, apply: bool):
    case = tc._apply_patch(case, None, None)
    with tempfile.TemporaryDirectory() as root:
        memory = tc._open(root)
        try:
            memory, keys, declared, targets = tc._run_setup(memory, root, case)
            emitted = memory.semantic_proposals()
            applied = []
            if apply:
                for proposal in memory.semantic_proposals(status="open"):
                    result = memory.apply_semantic_proposal(
                        proposal["proposal_id"], evidence=tc._correction_evidence(tc.SCOPE), risk_class="low")
                    applied.append({"proposal_id": proposal["proposal_id"], "target": proposal["target_reference"],
                                    "committed": bool(result.get("committed")), "refusal": result.get("refusal")})
            probes = {p["probe_id"]: tc._observe(memory, p, keys, targets) for p in case["probes"]}
            by_uuid = {uuid: key for key, uuid in keys.items()}
            semantics = {key: memory.write_semantics(uuid) for key, uuid in keys.items()}
        finally:
            memory.close()
    run = {"case": case, "keys": keys, "declared": declared, "probes": probes, "restart_digests": {}, "metabolism": {}}
    named = lambda uuid: by_uuid.get(uuid, uuid)
    classification = {
        key: [{"classification": r["classification"], "basis": r["basis"], "other": named(r["other_fact_uuid"])}
              for r in (value or {}).get("relations", ())]
        for key, value in semantics.items()
    }
    proposals = [{"source": named(p["source_fact_uuid"]), "target": named(p["target_fact_uuid"]), "status": p["status"],
                  "basis": p["basis"]} for p in emitted]
    return tc.score_case(run), proposals, applied, classification


def main() -> int:
    suite = tc.load_suite(FIXTURE)
    out = {"fixture_sha256": tc.suite_digest(FIXTURE), "evidence_class": suite["evidence_class"],
           "external_validation": False, "counterfactual": "reviewing caller applies every open write-time proposal",
           "cases": {}}
    for case in suite["cases"]:
        live_rows, proposals, _, classification = run_case(case, apply=False)
        applied_rows, _, applied, _ = run_case(case, apply=True)
        live, after = tc.units(live_rows), tc.units(applied_rows)
        changed = {"/".join(k): [live[k], after.get(k)] for k in sorted(live) if after.get(k) != live[k]}
        out["cases"][case["case_id"]] = {"write_time_classification": {k: v for k, v in classification.items() if v},
                                         "proposals_emitted": proposals, "applied": applied, "units_changed_by_application": changed}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
