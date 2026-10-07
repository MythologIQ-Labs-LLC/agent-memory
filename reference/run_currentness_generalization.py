#!/usr/bin/env python3
"""#732 independent currentness generalization measurement (plan-732-generalization-gate G3-G5, G8).

This is an evaluation harness only. It runs each frozen case through the public facade on a
fresh store, assigns it the first stage that applies from S0 to S7 (G4), and computes the
pre-registered metrics, gate and per-family classes (G5). Nothing under ``reference/agentmem_ref``
imports it, and it changes no runtime behaviour. The measurement runs once on ``main``, after the
freeze, against Runtime Baseline v5 unchanged.

The frozen harness is as follows:

* handles A and B map to ``agent:gen732-a`` and ``agent:gen732-b``;
* scopes S1 and S2 map to ``project:gen732-s1`` and ``project:gen732-s2``;
* the tenant is ``tenant:gen732`` and the purpose is ``currentness generalization (#732)``;
* each write opens and closes its own ``(handle, scope)`` facade on the case's store root;
* write-time semantics are read immediately after the last write and before any action, each
  through the reading write's own handle;
* dispute uses ``evidence_for(skill:gen732-governed-dispute v1)`` scoped to the acting scope;
* recall runs as ``recall_as`` with ``{"mode": "current"}`` at ``2026-10-08T12:00:00Z``;
* a second recall runs on the same store under ``cross_fact_mechanism_off.mechanism("off")``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime import cross_fact_currentness as cf  # noqa: E402
from agentmem_ref.runtime import proposition_semantics as ps  # noqa: E402
from agentmem_ref.runtime.temporal_order_constraints import POLICY_VERSION  # noqa: E402

from cross_fact_mechanism_off import mechanism  # noqa: E402

HANDLES = {"A": "agent:gen732-a", "B": "agent:gen732-b"}
SCOPES = {"S1": "project:gen732-s1", "S2": "project:gen732-s2"}
TENANT = "tenant:gen732"
PURPOSE = "currentness generalization (#732)"
REFERENCE_TIME = "2026-10-08T12:00:00Z"
CURRENT = {"mode": "current"}
SKILL_ID = "skill:gen732-governed-dispute"

P_FAMILIES = [f"P{i}" for i in range(1, 14)]
R_FAMILIES = [f"R{i}" for i in range(1, 8)]
N_FAMILIES = [f"N{i}" for i in range(1, 14)]
POSITIVE = P_FAMILIES + R_FAMILIES
STRUCTURAL = ["N7", "N8", "N9", "N10", "N13"]
NON_STRUCTURAL = [f for f in N_FAMILIES if f not in STRUCTURAL]
EXACT_SIZE = {**{f: 12 for f in P_FAMILIES}, **{f: 8 for f in R_FAMILIES + N_FAMILIES}}
MUST_CHANGE = ["hedge", "attribution", "conditional", "coexistent", "change_source_ref", "change_actor", "change_scope", "dispute"]

# Appendix B: the frozen refusal-string-to-guard table.
GUARD_TABLE = [
    ("not_explicit_current_profile", "G1"),
    ("relation_not_state_change", "G2"),
    ("relation_basis_not_accepted", "G3"),
    ("no_open_proposal", "G4"),
    ("proposal_not_open:", "G5"),
    ("hedged_or_untrusted_claim", "G6"),
    ("cross_fact_identity_unavailable", "G7"),
    ("actor_mismatch", "G8"),
    ("source_mismatch", "G9"),
    ("scope_mismatch", "G10"),
    ("contradictory_cross_fact_evidence", "G11"),
    ("change_evidence_not_assertive:", "G12"),
    ("declared_clock_contradicts_direction", "G13"),
    ("declared_clock_unconfirmed", "G13"),
    ("target_has_temporal_basis", "policy"),
    ("source_has_temporal_basis", "policy"),
]


def guard_for(reason: str | None) -> str:
    if reason is None:
        return "unreported"
    for key, guard in GUARD_TABLE:
        if reason == key or (key.endswith(":") and reason.startswith(key)):
            return guard
    return f"unmapped:{reason}"


# --- harness ------------------------------------------------------------------------------------

def _open(root: str, handle: str, scope: str) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id=HANDLES[handle], scope=SCOPES[scope], purpose=PURPOSE)


def _dispute_evidence(scope: str):
    scope_ref = SCOPES[scope]
    skill = pm.SkillArtifact(
        skill_id=SKILL_ID,
        version=1,
        purpose="govern a dispute of retained generalization-test memory",
        scope=scope_ref,
        isolation_domain_refs=(TENANT, scope_ref),
        required_isolation_domain_refs=(TENANT, scope_ref),
        procedure_markdown="# verify\nConfirm the dispute against the source conversation.",
        provenance_refs=("evidence:gen732-governed-dispute",),
    )
    return pm.evidence_for(skill)


def _evidence(recalled: dict, ref: str) -> dict:
    return ((recalled.get("admissions") or {}).get(ref) or {}).get("ranking_evidence") or {}


def run_record(record: dict) -> dict:
    """Execute one case or variant and return its observations and G4 stage."""

    writes = record["writes"]
    older_i, newer_i = record["older_write"], record["newer_write"]
    with tempfile.TemporaryDirectory(prefix="gen732-") as root:
        uuids: list[str | None] = []
        for write in writes:
            with _open(root, write["handle"], write["scope"]) as memory:
                kwargs = {} if write["source_ref"] is None else {"source_ref": write["source_ref"]}
                result = memory.remember(write["target_reference"], write["text"], **kwargs)
            if not result.get("committed"):
                return {"stage": "S0", "reason": "invalid_harness:write_not_committed"}
            uuids.append(result["fact_uuid"])
        older, newer = uuids[older_i], uuids[newer_i]

        semantics: dict[int, dict] = {}
        for index, write in enumerate(writes):
            if index == older_i:
                continue
            with _open(root, write["handle"], write["scope"]) as memory:
                semantics[index] = memory.write_semantics(uuids[index]) or {}
        for index, sem in semantics.items():
            if index == newer_i:
                continue
            if any(rel.get("other_fact_uuid") == older for rel in sem.get("relations") or ()):
                return {"stage": "S0", "reason": "invalid_harness:ambiguous_relation"}
        newer_relations = [rel for rel in semantics[newer_i].get("relations") or () if rel.get("other_fact_uuid") == older]

        for action in record["actions"]:
            write = writes[action["write"]]
            with _open(root, write["handle"], write["scope"]) as memory:
                if action["action"] == "dispute":
                    outcome = memory.dispute(
                        write["target_reference"],
                        fact_uuid=uuids[action["write"]],
                        evidence=_dispute_evidence(write["scope"]),
                        risk_class="low",
                    )
                else:
                    outcome = memory.forget(write["target_reference"])
            if not outcome.get("committed"):
                return {"stage": "S0", "reason": "invalid_harness:action_not_committed"}

        recall_as = record["recall_as"]
        with _open(root, recall_as["handle"], recall_as["scope"]) as memory:
            on = memory.recall(record["query"], temporal_intent=CURRENT, reference_time=REFERENCE_TIME)
            with mechanism("off"):
                off = memory.recall(record["query"], temporal_intent=CURRENT, reference_time=REFERENCE_TIME)

    admitted_on = [str(ref) for ref in on.get("admitted") or ()]
    admitted_off = [str(ref) for ref in off.get("admitted") or ()]
    any_limitation = any(_evidence(on, ref).get("cross_fact_limitation") for ref in admitted_on)
    unattributed = admitted_on != admitted_off and not any_limitation
    old_evidence = _evidence(on, older)
    limitation_sources = [entry.get("source_fact_uuid") for entry in old_evidence.get("cross_fact_limitation") or ()]
    labelled = (
        old_evidence.get("temporal_applicability") == cf.CROSS_FACT_LABEL and newer in limitation_sources
    )
    observations = {
        "relations_to_older": [rel.get("classification") for rel in newer_relations],
        "older_label": old_evidence.get("temporal_applicability"),
        "limitation_sources_newer": newer in limitation_sources,
        "refusal_reason": old_evidence.get("cross_fact_refusal_reason"),
        "older_rank": admitted_on.index(older) if older in admitted_on else None,
        "newer_rank": admitted_on.index(newer) if newer in admitted_on else None,
        "admitted_order_changed_by_mechanism": admitted_on != admitted_off,
        "unattributed": unattributed,
    }
    if older not in admitted_on:
        stage, reason = "S1", "older_not_admitted"
    elif newer not in admitted_on:
        stage, reason = "S2", "newer_not_admitted"
    elif not newer_relations:
        stage, reason = "S3", "no_write_time_relation"
    elif not any(c == ps.STATE_CHANGE_CANDIDATE for c in observations["relations_to_older"]):
        stage, reason = "S4", "relation_not_state_change"
    elif not labelled:
        stage, reason = "S5", f"guard_refusal:{guard_for(observations['refusal_reason'])}"
    elif admitted_on.index(newer) > admitted_on.index(older):
        stage, reason = "S6", "labelled_not_reordered"
    else:
        stage, reason = "S7", "engaged"
    return {"stage": stage, "reason": reason, "observations": observations}


# --- metrics (G5) -------------------------------------------------------------------------------

def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def score(corpus: list, variants: list, selection: list, results: dict) -> dict:
    by_family: dict[str, list] = {f: [] for f in POSITIVE + N_FAMILIES}
    for case in corpus:
        by_family[case["family"]].append(case["case_id"])
    valid = {cid for cid, r in results.items() if r["stage"] != "S0"}
    engaged = {cid for cid, r in results.items() if r["stage"] == "S7"}

    families: dict[str, dict] = {}
    for family, ids in by_family.items():
        valid_ids = [cid for cid in ids if cid in valid]
        hits = sum(1 for cid in valid_ids if cid in engaged)
        entry = {
            "valid": len(valid_ids),
            "exact_size": EXACT_SIZE[family],
            "insufficient": len(valid_ids) < EXACT_SIZE[family],
            "engaged": hits,
            "stages": dict(sorted(Counter(results[cid]["stage"] for cid in ids if cid in results).items())),
        }
        if family in POSITIVE:
            recall = _rate(hits, len(valid_ids))
            entry["recall"] = recall
            entry["class"] = (
                "deficient" if recall is None or recall < 0.60 else "adequate" if recall < 0.80 else "supported"
            )
        elif family in NON_STRUCTURAL:
            entry["false_engagements"] = hits
            entry["class"] = "unsafe" if hits else "safe"
        else:
            entry["false_engagements"] = hits
            entry["class"] = "structural_false_engagement" if hits else "safe"
        families[family] = entry

    positive_valid = [cid for f in POSITIVE for cid in by_family[f] if cid in valid]
    overall = _rate(sum(1 for cid in positive_valid if cid in engaged), len(positive_valid))
    structural_fe = sum(families[f]["false_engagements"] for f in STRUCTURAL)
    non_structural_fe = sum(families[f]["false_engagements"] for f in NON_STRUCTURAL)

    family_of = {case["case_id"]: case["family"] for case in corpus}
    inv_total = inv_match = flip_total = flip_refrain = 0
    inv_mismatch_families: Counter = Counter()
    flip_fail_families: Counter = Counter()
    inv_excluded_s0_base: list[str] = []
    present_must_change: set = set()
    for variant in variants:
        if "na_reason" in variant:
            continue
        vid, base = variant["variant_id"], variant["base_case_id"]
        outcome = results[vid]
        if variant["kind"] == "invariance":
            if base not in valid:
                inv_excluded_s0_base.append(vid)
                continue
            if outcome["stage"] == "S0":
                continue
            inv_total += 1
            if (outcome["stage"] == "S7") == (base in engaged):
                inv_match += 1
            else:
                inv_mismatch_families[family_of[base]] += 1
        else:
            present_must_change.add((base, variant["variant_type"]))
            if outcome["stage"] == "S0":
                continue
            flip_total += 1
            if outcome["stage"] != "S7":
                flip_refrain += 1
            else:
                flip_fail_families[family_of[base]] += 1
    missing_must_change = sorted(
        f"{base}:{vtype}" for base in selection for vtype in MUST_CHANGE if (base, vtype) not in present_must_change
    )
    m_inv = _rate(inv_match, inv_total)
    m_flip = _rate(flip_refrain, flip_total)
    m_attr = sum(1 for r in results.values() if (r.get("observations") or {}).get("unattributed"))

    fail_reasons = []
    if overall is None or overall < 0.50:
        fail_reasons.append("overall_recall_below_0.50")
    if m_attr > 0:
        fail_reasons.append("m_attr_nonzero")
    if structural_fe > 0:
        fail_reasons.append("structural_guard_false_engagement")
    if m_flip is not None and m_flip < 1.0:
        fail_reasons.append("m_flip_below_100")

    causes = []
    for f in POSITIVE:
        if families[f]["class"] == "deficient":
            causes.append({"cause": "i_deficient", "families": [f]})
    for f in NON_STRUCTURAL:
        if families[f]["class"] == "unsafe":
            causes.append({"cause": "ii_unsafe", "families": [f]})
    if overall is not None and 0.50 <= overall < 0.80:
        causes.append({"cause": "iii_overall_recall", "families": [f for f in POSITIVE if families[f]["class"] != "supported"]})
    if m_inv is None or m_inv < 0.95:
        causes.append({"cause": "iv_invariance", "families": sorted(inv_mismatch_families)})
    for f in POSITIVE + N_FAMILIES:
        if families[f]["insufficient"]:
            causes.append({"cause": "v_insufficient", "families": [f]})
    if missing_must_change:
        causes.append({
            "cause": "vi_missing_must_change",
            "families": sorted({family_of[item.split(":", 1)[0]] for item in missing_must_change}),
        })

    pass_criteria = {
        "overall_recall_ge_0.80": overall is not None and overall >= 0.80,
        "every_positive_family_ge_0.60": all(families[f]["class"] != "deficient" for f in POSITIVE),
        "non_structural_false_engagements_le_1": non_structural_fe <= 1,
        "m_inv_ge_0.95": m_inv is not None and m_inv >= 0.95,
        "m_attr_eq_0": m_attr == 0,
        "structural_false_engagements_eq_0": structural_fe == 0,
        "m_flip_eq_1": m_flip == 1.0,
        "no_family_insufficient": not any(families[f]["insufficient"] for f in families),
        "no_missing_must_change": not missing_must_change,
    }
    if fail_reasons:
        verdict = "FAIL"
    elif all(pass_criteria.values()):
        verdict = "PASS"
    else:
        verdict = "MIXED"
    return {
        "verdict": verdict,
        "fail_reasons": fail_reasons,
        "pass_criteria": pass_criteria,
        "mixed_causes": causes if verdict != "PASS" else [],
        "overall_recall": overall,
        "non_structural_false_engagements": non_structural_fe,
        "structural_false_engagements": structural_fe,
        "m_inv": m_inv,
        "m_inv_counts": {"matched": inv_match, "total": inv_total},
        "m_inv_engaged_bases_diagnostic": _engaged_inv(variants, results, engaged, valid),
        "m_inv_excluded_s0_base": sorted(inv_excluded_s0_base),
        "m_inv_mismatch_families": dict(sorted(inv_mismatch_families.items())),
        "m_flip": m_flip,
        "m_flip_counts": {"refrained": flip_refrain, "total": flip_total},
        "m_flip_fail_families": dict(sorted(flip_fail_families.items())),
        "missing_must_change": missing_must_change,
        "m_attr": m_attr,
        "families": families,
        "s0": sorted(cid for cid, r in results.items() if r["stage"] == "S0"),
    }


def _engaged_inv(variants: list, results: dict, engaged: set, valid: set) -> float | None:
    matched = total = 0
    for variant in variants:
        if "na_reason" in variant or variant["kind"] != "invariance" or variant["base_case_id"] not in engaged:
            continue
        if results[variant["variant_id"]]["stage"] == "S0":
            continue
        total += 1
        matched += results[variant["variant_id"]]["stage"] == "S7"
    return _rate(matched, total)


# --- driver -------------------------------------------------------------------------------------

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(corpus_path: Path, variants_path: Path, selection_path: Path) -> dict:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    variants = json.loads(variants_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    results: dict[str, dict] = {}
    for case in corpus:
        results[case["case_id"]] = run_record(case)
    for variant in variants:
        if "na_reason" not in variant:
            results[variant["variant_id"]] = run_record(variant)
    return {
        "scores": score(corpus, variants, selection, results),
        "results": results,
        "inputs": {
            "corpus_sha256": _sha(corpus_path),
            "variants_sha256": _sha(variants_path),
            "selection_sha256": _sha(selection_path),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", type=Path)
    parser.add_argument("variants", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binding", type=Path, help="JSON with frozen hashes to verify and copy into the report")
    args = parser.parse_args(argv)
    binding = json.loads(args.binding.read_text(encoding="utf-8")) if args.binding else {}
    for key, path in (("corpus_sha256", args.corpus), ("variants_sha256", args.variants), ("selection_sha256", args.selection)):
        if key in binding and binding[key] != _sha(path):
            raise SystemExit(f"{key} does not match the frozen binding")
    report = measure(args.corpus, args.variants, args.selection)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    checker = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_runtime_baseline_equivalence.py"), "--candidate", "HEAD"],
        cwd=ROOT, capture_output=True, text=True,
    )
    report["binding"] = {
        **binding,
        "executing_commit": commit,
        "checker_exit": checker.returncode,
        "checker_output_tail": checker.stdout.strip().splitlines()[-3:],
        "assertion_filter_version": cf.ASSERTION_FILTER_VERSION,
        "ranking_policy_version": POLICY_VERSION,
        "scope_statement": "explicit change assertions only; bare restatements of a new value are not measured (plan-732 D4)",
        "authority_effect": "none",
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report["scores"][k] for k in ("verdict", "fail_reasons", "overall_recall", "m_inv", "m_flip", "m_attr")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
