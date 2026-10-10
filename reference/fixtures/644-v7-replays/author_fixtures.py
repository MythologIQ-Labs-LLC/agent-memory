"""Author the five frozen #644 v7 replay fixtures (one-shot, before any runner exists).

Expectations are written from the contract documents (docs 76, 77, 78, 79, 81 and
META_LEDGER Entry #125), never from executing the implementation. Vocabulary is new:
no entity, value or category of the original 126-case independent holdout is used.
usage: author_fixtures.py <repo_root>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
OUT = ROOT / "reference/fixtures/644-v7-replays"
BASE_COMMIT = "c4827f9fef055b0bc2a9bd94b28adba22bfc42d0"
DSL = "644-v7-replay-dsl/1"


def doc_hash(path):
    blob = subprocess.run(["git", "show", f"{BASE_COMMIT}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    return {"path": path, "sha256_at_base": hashlib.sha256(blob).hexdigest()}


def P(s, a, v, assertion="state", cardinality="single", **flags):
    out = {"s": s, "a": a, "v": v, "assertion": assertion, "cardinality": cardinality}
    if flags:
        out["flags"] = flags
    return out


def rem(ref, text, prop=None, **kw):
    op = {"op": "remember", "ref": ref, "text": text}
    if prop is not None:
        op["prop"] = prop
    op.update(kw)
    return op


EQ = lambda v: {"eq": v}  # noqa: E731
NE = lambda v: {"ne": v}  # noqa: E731
NOT_CLEAN = {"not_in": ["coverage_observed_unattested", "mechanical_coverage_observed"]}
NO_STOP = {"continuation_proposal": EQ("continue_if_permitted"), "stop_attested": EQ(False)}
AUTH_FIXED = {"answer_quality_verified": EQ(False), "can_admit": EQ(False), "can_mutate": EQ(False),
              "authority_effect": EQ("none"), "stop_attested": EQ(False)}

COMMON = {
    "dsl_version": DSL,
    "owning_issue": 644,
    "frozen_on": "2026-10-10",
    "status": "frozen_before_execution",
    "base_commit": BASE_COMMIT,
    "independence": (
        "Expected outcomes were written from the contract documents listed in contract_sources before "
        "any replay runner existed or executed. They are not derived from running the implementation "
        "under test. The original 126-case independent holdout (heldout_bench.py, sha256 25ce88eb...) and "
        "its vocabulary were not used. A failing expectation is a finding, never a reason to edit this "
        "fixture; a corrected expectation requires a superseding fixture version with a recorded reason."),
    "stop_lines": [
        "no fixture edit after first execution; supersede with -v2 and record why",
        "no expectation weakened to obtain PASS",
        "no runtime change motivated by a replay outcome without a preregistered reproducer",
        "a replay verdict is evidence, not v7 acceptance; acceptance requires independent review",
    ],
}

# ---------------------------------------------------------------------------------------------
# 1. typed-sufficiency-noninterference-and-negative-controls-v1
V, VA = "Vireo cluster", "storage tier"
VQ = "Vireo cluster storage tier"
R1 = {
    "replay_id": "typed-sufficiency-noninterference-and-negative-controls-v1",
    "title": "Typed sufficiency observation is read-only, never confers authority, and refuses malformed input",
    "contract_sources": [doc_hash("docs/76-typed-recall-evidence-sufficiency.md"),
                         doc_hash("docs/79-independent-644-qualification-reconciliation.md")],
    "invariants": [
        {"id": "N1", "statement": "Running every #644 observer (persisted coverage, manual coverage, transition witness, receipt verification) between operations leaves all facade-visible outputs, the persisted canonical facts and the audit event sequence identical to an identical twin run without observers.",
         "falsified_by": "any normalized output, fact or event that differs between the twin runs"},
        {"id": "N2", "statement": "A single observation changes neither the substrate state digest, the audit event count, nor the recall result's candidates, admitted, ranked or refusals.",
         "falsified_by": "a digest, count or list differing before and after observation"},
        {"id": "N3", "statement": "Meeting the admitted-count target is not typed sufficiency: untyped admitted facts leave a typed need missing and never produce a stop proposal.",
         "falsified_by": "mechanical coverage reported, or the need not missing, with only untyped facts"},
        {"id": "N4", "statement": "Controller-estimate coverage cannot satisfy a typed need.",
         "falsified_by": "mechanical_coverage_met true from controller_estimate observations only"},
        {"id": "N5", "statement": "Caller-labelled (manual) coverage never proposes a stop, even when labelled runtime_typed_observation and covering every need.",
         "falsified_by": "continuation_proposal review_stop from the manual observer"},
        {"id": "N6", "statement": "Report authority fields are fixed (answer_quality_verified, can_admit, can_mutate false; authority none; stop_attested false) and a report constructed with any forged authority value is refused.",
         "falsified_by": "a report exposing a different value or accepting a forged one"},
        {"id": "N7", "statement": "Malformed needs fail closed with ValueError: empty, duplicate, non-canonical slot spelling and non-typed keys.",
         "falsified_by": "a report produced for a malformed need"},
        {"id": "N8", "statement": "The report is independent of the order in which needs are declared.",
         "falsified_by": "different serialized reports for permuted needs"},
        {"id": "N9", "statement": "Route budget diagnostics are conservative: a route that returned exactly its limit is budget-bound, a planned route not executed is reported unexecuted, and neither yields a stop proposal.",
         "falsified_by": "a capped route not reported budget-bound, an unexecuted route not reported, or review_stop"},
        {"id": "N10", "statement": "Manual coverage may refer only to admitted references.",
         "falsified_by": "a report accepting coverage for a non-admitted reference"},
    ],
    "cases": [
        {"id": "N1-twin-lifecycle", "invariants": ["N1"], "kind": "twin",
         "setup": [
             rem("memory:v1", f"{V} {VA} is cold", P(V, VA, "cold")),
             {"op": "observe_all", "query": VQ, "needs": [{"s": V, "a": VA}]},
             rem("memory:v2", f"{V} {VA} is warm", P(V, VA, "warm")),
             rem("memory:v3", f"{V} {VA} changed to frozen", P(V, VA, "frozen", assertion="change")),
             rem("memory:v4", f"{V} operator note about maintenance windows"),
             {"op": "observe_all", "query": VQ, "needs": [{"s": V, "a": VA}]},
             {"op": "dispute", "ref": "memory:v2"},
             {"op": "forget", "ref": "memory:v4"},
             {"op": "correct", "ref": "memory:v1", "text": f"{V} {VA} is glacial", "kind": "state_change", "cite": "none"},
             {"op": "observe_all", "query": VQ, "needs": [{"s": V, "a": VA}]},
             {"op": "reopen"},
             {"op": "observe_all", "query": VQ, "needs": [{"s": V, "a": VA}]},
         ],
         "expect": {"twin_identical": EQ(True)}},
        {"id": "N2-read-only-single-observation", "invariants": ["N2"], "kind": "coverage",
         "setup": [rem("memory:v1", f"{V} {VA} is cold", P(V, VA, "cold")),
                   rem("memory:v2", f"{V} {VA} is warm", P(V, VA, "warm"))],
         "query": VQ, "needs": [{"s": V, "a": VA}], "probes": ["state_unchanged", "result_unchanged"],
         "expect": {"state_unchanged": EQ(True), "result_unchanged": EQ(True), **NO_STOP}},
        {"id": "N3-count-target-is-not-typed-sufficiency", "invariants": ["N3"], "kind": "coverage",
         "setup": [rem("memory:v1", f"{V} {VA} notes from Monday"),
                   rem("memory:v2", f"{V} {VA} notes from Tuesday"),
                   rem("memory:v3", f"{V} {VA} notes from Friday")],
         "query": VQ, "count_target": 3, "needs": [{"s": V, "a": VA}],
         "expect": {"count_target_met": EQ(True), "mechanical_coverage_met": EQ(False),
                    "need_missing": EQ(True), "support_refs": EQ([]), **NO_STOP}},
        {"id": "N4-controller-estimate-cannot-cover", "invariants": ["N4"], "kind": "manual_coverage",
         "setup": [rem("memory:v1", f"{V} {VA} is cold", P(V, VA, "cold"))],
         "query": VQ, "needs": [{"s": V, "a": VA}],
         "coverage": [{"ref": "memory:v1", "origin": "controller_estimate"}],
         "expect": {"mechanical_coverage_met": EQ(False), "need_missing": EQ(True), **NO_STOP}},
        {"id": "N5-forged-typed-label-never-stops", "invariants": ["N5"], "kind": "manual_coverage",
         "setup": [rem("memory:v1", f"{V} {VA} is cold", P(V, VA, "cold"))],
         "query": VQ, "needs": [{"s": V, "a": VA}],
         "coverage": [{"ref": "memory:v1", "origin": "runtime_typed_observation"}],
         "expect": {"mechanical_coverage_met": EQ(True), **NO_STOP}},
        {"id": "N6-authority-fields-fixed", "invariants": ["N6"], "kind": "coverage",
         "setup": [rem("memory:v1", f"{V} {VA} is cold", P(V, VA, "cold"))],
         "query": VQ, "needs": [{"s": V, "a": VA}], "expect": AUTH_FIXED},
        *[{"id": f"N6-forged-report-{field}", "invariants": ["N6"], "kind": "forge_report",
           "field": field, "value": value, "expect": {"raises": EQ("ValueError")}}
          for field, value in (("answer_quality_verified", True), ("can_admit", True), ("can_mutate", True),
                               ("authority_effect", "stop"), ("stop_attested", True))],
        *[{"id": f"N7-malformed-needs-{name}", "invariants": ["N7"], "kind": "coverage",
           "setup": [rem("memory:v1", f"{V} {VA} is cold", P(V, VA, "cold"))],
           "query": VQ, "need_keys": keys, "expect": {"raises": EQ("ValueError")}}
          for name, keys in (("empty", []),
                             ("duplicate", ["@canonical:Vireo cluster|storage tier", "@canonical:Vireo cluster|storage tier"]),
                             ("non-canonical-spelling", ["typed:Vireo Cluster|Storage Tier"]),
                             ("untyped-key", ["vireo cluster storage tier"]))],
        {"id": "N8-need-order-invariance", "invariants": ["N8"], "kind": "coverage",
         "setup": [rem("memory:v1", f"{V} {VA} is cold", P(V, VA, "cold")),
                   rem("memory:v2", f"{V} backup cadence is nightly", P(V, "backup cadence", "nightly"))],
         "query": "Vireo cluster storage tier backup cadence",
         "needs": [{"s": V, "a": VA}, {"s": V, "a": "backup cadence"}], "probes": ["permutation_invariant"],
         "expect": {"permutation_invariant": EQ(True)}},
        {"id": "N9-capped-route-is-budget-bound", "invariants": ["N9"], "kind": "pure_assess",
         "admitted": ["fact-a", "fact-b"], "needs": [{"s": V, "a": VA}],
         "coverage": [{"ref": "fact-a", "origin": "runtime_typed_observation"}],
         "route_work": [{"route_id": "lexical", "candidate_limit": 2, "returned_count": 2, "executed": True}],
         "expect": {"budget_bound_routes": EQ(["lexical"]), "continuation_proposal": EQ("continue_if_permitted")}},
        {"id": "N9-unexecuted-route-reported", "invariants": ["N9"], "kind": "pure_assess",
         "admitted": ["fact-a"], "needs": [{"s": V, "a": VA}],
         "coverage": [{"ref": "fact-a", "origin": "runtime_typed_observation"}],
         "route_work": [{"route_id": "lexical", "candidate_limit": 5, "returned_count": 1, "executed": True},
                        {"route_id": "semantic_vector", "candidate_limit": 4, "returned_count": 0, "executed": False}],
         "expect": {"unexecuted_routes": EQ(["semantic_vector"]), "continuation_proposal": EQ("continue_if_permitted")}},
        {"id": "N10-coverage-outside-admitted-refused", "invariants": ["N10"], "kind": "manual_coverage",
         "setup": [rem("memory:v1", f"{V} {VA} is cold", P(V, VA, "cold"))],
         "query": VQ, "needs": [{"s": V, "a": VA}],
         "coverage": [{"ref": "@literal:not-an-admitted-fact", "origin": "runtime_typed_observation"}],
         "expect": {"raises": EQ("ValueError")}},
    ],
}

# ---------------------------------------------------------------------------------------------
# 2. governed-persisted-typed-slot-sufficiency-admission-recheck-v1
Q, QA = "Pellucid queue", "retention window"
QQ = "Pellucid queue retention window"
HIDDEN = "Since the audit the purge horizon became ninety days"  # shares no token with QQ
NEED = [{"s": Q, "a": QA}]
R2 = {
    "replay_id": "governed-persisted-typed-slot-sufficiency-admission-recheck-v1",
    "title": "Persisted typed-slot support is rechecked against current admission and the slot census sees non-retrieved evidence",
    "contract_sources": [doc_hash("docs/76-typed-recall-evidence-sufficiency.md"),
                         doc_hash("docs/79-independent-644-qualification-reconciliation.md"),
                         doc_hash("docs/81-indexed-slot-audit-qualification.md")],
    "invariants": [
        {"id": "A1", "statement": "Support comes only from currently admitted facts carrying a persisted caller-declared, unflagged typed proposition in exactly the requested slot.",
         "falsified_by": "support_refs differing from that set"},
        {"id": "A2", "statement": "Untyped, extracted and flagged (hedged, negated, attributed) same-slot facts contribute zero support; flagged and extracted ones remain visible as qualified counter-evidence.",
         "falsified_by": "any of them in support_refs, or the qualified counter-evidence count differing"},
        {"id": "A3", "statement": "Admission is rechecked at observation time: a fact forgotten, disputed or superseded after recall contributes zero support.",
         "falsified_by": "such a fact in support_refs"},
        {"id": "A4", "statement": "A reference injected into the admitted list from another project, or a nonexistent reference, contributes zero support and exposes no value.",
         "falsified_by": "support or a leaked value from the injected reference"},
        {"id": "A5", "statement": "Observation under another project's context yields no support from this project's facts.",
         "falsified_by": "non-empty support"},
        {"id": "A6", "statement": "Same-slot facts admissible to the reader but absent from the admitted set are counted as eligible_unretrieved and block clean coverage; facts invisible to the reader (other project, forgotten, disputed, superseded) are never counted.",
         "falsified_by": "eligible_unretrieved differing from the number of admissible non-retrieved same-slot facts"},
        {"id": "A7", "statement": "Any declared valid_until, or a valid_from later than recording time, is a declared_temporal_boundary obstacle; an earlier valid_from is not.",
         "falsified_by": "the temporal counter differing"},
        {"id": "A8", "statement": "A requested slot with no typed facts is reported missing with zero support.",
         "falsified_by": "coverage reported or support non-zero"},
        {"id": "A9", "statement": "The slot census equals an independent full-store enumeration performed under the same reader context.",
         "falsified_by": "any counter differing from the enumeration"},
        {"id": "A10", "statement": "Reopening the store yields an identical report for an identical query.",
         "falsified_by": "a different serialized report after restart"},
        {"id": "A11", "statement": "A minimum support multiplicity counts distinct admitted facts.",
         "falsified_by": "a need with min 2 covered by one fact, or not covered by two"},
    ],
    "cases": [
        {"id": "A1-only-caller-declared-exact-slot-support", "invariants": ["A1"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                   rem("memory:q2", f"{Q} {QA} was discussed at standup"),
                   rem("memory:q3", f"{Q} {QA} owner is the data team", P(Q, "owner", "data team"))],
         "query": QQ, "needs": NEED,
         "expect": {"support_refs": EQ(["memory:q1"]), "mechanical_coverage_met": EQ(True),
                    "diagnosis": EQ("coverage_observed_unattested"), **NO_STOP}},
        {"id": "A2-weaker-same-slot-claims-are-not-support", "invariants": ["A2"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                   {"op": "retain_extracted", "ref": "memory:q2", "text": f"{Q} {QA} is sixty days", "prop": P(Q, QA, "sixty days")},
                   rem("memory:q3", f"{Q} {QA} might be sixty days", P(Q, QA, "sixty days", hedged=True)),
                   rem("memory:q4", f"{Q} {QA} is not thirty days", P(Q, QA, "thirty days", negated=True)),
                   rem("memory:q5", f"Vendors say {Q} {QA} is ninety days", P(Q, QA, "ninety days", attributed_to_other=True))],
         "query": QQ, "needs": NEED,
         "expect": {"support_refs": EQ(["memory:q1"]), "obstacles.qualified_counter_evidence": EQ(4),
                    "diagnosis": NOT_CLEAN, **NO_STOP}},
        *[{"id": f"A3-recheck-after-{op}", "invariants": ["A3"], "kind": "coverage",
           "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                     rem("memory:q2", f"{Q} {QA} confirmed thirty days", P(Q, QA, "thirty days"))],
           "query": QQ, "needs": NEED, "between": [between],
           "expect": {"support_refs": EQ(["memory:q1"]), **NO_STOP}}
          for op, between in (("forget", {"op": "forget", "ref": "memory:q2"}),
                              ("dispute", {"op": "dispute", "ref": "memory:q2"}),
                              ("supersede", {"op": "correct", "ref": "memory:q2", "text": "Pellucid queue retention window review pending",
                                             "kind": "error_correction", "cite": "none"}))],
        {"id": "A4-injected-foreign-and-missing-references", "invariants": ["A4"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                   rem("memory:qb", f"{Q} {QA} is forty five days", P(Q, QA, "forty five days"), scope="project:b")],
         "query": QQ, "needs": NEED,
         "mutations": [{"m": "inject_admitted", "ref": "b:memory:qb"}, {"m": "inject_admitted", "ref": "@literal:ref-9999"}],
         "probes": ["values_absent:forty five days"],
         "expect": {"support_refs": EQ(["memory:q1"]), "values_absent": EQ(True), **NO_STOP}},
        {"id": "A5-other-project-context-sees-nothing", "invariants": ["A5"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days"))],
         "query": QQ, "needs": NEED, "observe_scope": "project:b",
         "expect": {"support_refs": EQ([]), "need_missing": EQ(True), **NO_STOP}},
        {"id": "A6-hidden-admissible-competitor-counted", "invariants": ["A6"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                   rem("memory:q2", HIDDEN, P(Q, QA, "ninety days")),
                   rem("memory:qb", "Purge horizon for the other team is weekly", P(Q, QA, "weekly"), scope="project:b"),
                   rem("memory:q3", "The archive horizon was briefly two days", P(Q, QA, "two days")),
                   {"op": "forget", "ref": "memory:q3"},
                   rem("memory:q4", "The purge horizon was rumoured at one day", P(Q, QA, "one day")),
                   {"op": "dispute", "ref": "memory:q4"}],
         "query": QQ, "needs": NEED,
         "expect": {"obstacles.eligible_unretrieved": EQ(1), "support_refs": EQ(["memory:q1"]),
                    "diagnosis": NOT_CLEAN, **NO_STOP}},
        {"id": "A6-budget-capped-same-slot-counted", "invariants": ["A6"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                   rem("memory:q2", f"{Q} {QA} is ninety days", P(Q, QA, "ninety days"))],
         "query": QQ, "lexical_limit": 1, "needs": NEED,
         "expect": {"obstacles.eligible_unretrieved": EQ(1), "diagnosis": NOT_CLEAN, **NO_STOP}},
        {"id": "A7-future-valid-until", "invariants": ["A7"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days"),
                       valid_from="2020-01-01", valid_until="2099-01-01")],
         "query": QQ, "needs": NEED,
         "expect": {"obstacles.declared_temporal_boundary": EQ(1), "diagnosis": NOT_CLEAN, **NO_STOP}},
        {"id": "A7-expired-valid-until", "invariants": ["A7"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days"),
                       valid_from="2018-01-01", valid_until="2018-12-31")],
         "query": QQ, "needs": NEED,
         "expect": {"obstacles.declared_temporal_boundary": EQ(1), "diagnosis": NOT_CLEAN, **NO_STOP}},
        {"id": "A7-prospective-valid-from", "invariants": ["A7"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days"), valid_from="2099-06-01")],
         "query": QQ, "needs": NEED,
         "expect": {"obstacles.declared_temporal_boundary": EQ(1), "diagnosis": NOT_CLEAN, **NO_STOP}},
        {"id": "A7-past-valid-from-is-not-an-obstacle", "invariants": ["A7"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days"), valid_from="2001-01-01")],
         "query": QQ, "needs": NEED,
         "expect": {"obstacles.declared_temporal_boundary": EQ(0), "diagnosis": EQ("coverage_observed_unattested"), **NO_STOP}},
        {"id": "A8-missing-evidence", "invariants": ["A8"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days"))],
         "query": QQ, "needs": [{"s": Q, "a": "encryption mode"}],
         "expect": {"support_refs": EQ([]), "need_missing": EQ(True), "mechanical_coverage_met": EQ(False), **NO_STOP}},
        {"id": "A9-census-equals-full-enumeration", "invariants": ["A9"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                   rem("memory:q2", HIDDEN, P(Q, QA, "ninety days")),
                   rem("memory:q3", f"{Q} {QA} might be sixty days", P(Q, QA, "sixty days", hedged=True)),
                   rem("memory:q4", f"{Q} {QA} was ten days", P(Q, QA, "ten days"), valid_from="2015-01-01", valid_until="2015-02-01"),
                   rem("memory:qb", "Purge horizon elsewhere is weekly", P(Q, QA, "weekly"), scope="project:b"),
                   rem("memory:q5", "Purge horizon draft value", P(Q, QA, "draft")),
                   {"op": "forget", "ref": "memory:q5"},
                   {"op": "correct", "ref": "memory:q1", "text": f"{Q} {QA} is thirty one days", "kind": "state_change", "cite": "none"},
                   {"op": "reopen"}],
         "query": QQ, "needs": NEED, "probes": ["census_oracle"],
         "expect": {"census_matches_full_scan": EQ(True)}},
        {"id": "A10-restart-stable-report", "invariants": ["A10"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                   rem("memory:q2", HIDDEN, P(Q, QA, "ninety days"))],
         "query": QQ, "needs": NEED, "probes": ["restart_identical"],
         "expect": {"restart_identical": EQ(True)}},
        {"id": "A11-multiplicity-one-fact", "invariants": ["A11"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days"))],
         "query": QQ, "needs": [{"s": Q, "a": QA, "min": 2}],
         "expect": {"need_missing": EQ(True), "mechanical_coverage_met": EQ(False), **NO_STOP}},
        {"id": "A11-multiplicity-two-facts", "invariants": ["A11"], "kind": "coverage",
         "setup": [rem("memory:q1", f"{Q} {QA} is thirty days", P(Q, QA, "thirty days")),
                   rem("memory:q2", f"{Q} {QA} confirmed thirty days", P(Q, QA, "thirty days"))],
         "query": QQ, "needs": [{"s": Q, "a": QA, "min": 2}],
         "expect": {"need_missing": EQ(False), "support_refs": EQ(["memory:q1", "memory:q2"]), **NO_STOP}},
    ],
}

# ---------------------------------------------------------------------------------------------
# 3. governed-admitted-typed-value-coherence-v1  (doc 77 disposition table)
C, CA = "Corvid console", "owner team"
CQ = "Corvid console owner team"
NC = [{"s": C, "a": CA}]


def coh(cid, inv, setup, status, groups=None, extra=None, query=CQ, needs=NC):
    exp = {"coherence_status": EQ(status), **NO_STOP}
    if groups is not None:
        exp["coherence_groups"] = EQ(groups)
    exp.update(extra or {})
    return {"id": cid, "invariants": inv, "kind": "coverage", "setup": setup, "query": query, "needs": needs,
            "expect": exp}


R3 = {
    "replay_id": "governed-admitted-typed-value-coherence-v1",
    "title": "Same-slot admitted typed values are classified by the documented disposition table and never resolved implicitly",
    "contract_sources": [doc_hash("docs/77-governed-admitted-value-coherence.md")],
    "invariants": [
        {"id": "V1", "statement": "No eligible typed value among admitted facts: disposition no_eligible_value.", "falsified_by": "another or no disposition"},
        {"id": "V2", "statement": "One or more exactly equal single-valued values without asserted change: same_value_observed, one group holding every supporting fact.", "falsified_by": "another disposition or grouping"},
        {"id": "V3", "statement": "Different single-valued values without asserted change: competing_values_unresolved, one group per value.", "falsified_by": "another disposition or grouping"},
        {"id": "V4", "statement": "Any multi-valued claim, even a single value: coexistence_possible.", "falsified_by": "another disposition"},
        {"id": "V5", "statement": "Any unknown cardinality, even a single value: cardinality_unresolved.", "falsified_by": "another disposition"},
        {"id": "V6", "statement": "Any asserted change, including a single current claim: change_assertion_unresolved; an asserted change is never treated as an applied correction.", "falsified_by": "another disposition"},
        {"id": "V7", "statement": "Comparison is strict literal equality: capitalization variants compete.", "falsified_by": "same_value_observed for case variants"},
        {"id": "V8", "statement": "An unresolved disposition yields diagnosis value_coherence_unresolved and continuation, even when mechanical coverage is met.", "falsified_by": "another diagnosis or a stop proposal"},
        {"id": "V9", "statement": "Disputed or forgotten facts never contribute a value.", "falsified_by": "their reference in any value group"},
        {"id": "V10", "statement": "The serialized report contains no raw claim values.", "falsified_by": "a claim value string in the report"},
        {"id": "V11", "statement": "Grouping is independent of write order.", "falsified_by": "different groups or disposition for permuted write order"},
        {"id": "V12", "statement": "A report carrying an unresolved disposition cannot be constructed with a stop proposal.", "falsified_by": "construction succeeding"},
        {"id": "V13", "statement": "Multiplicity counts distinct facts, not independent sources (recorded boundary).", "falsified_by": "two agreeing facts from one source counted once"},
    ],
    "cases": [
        coh("V1-no-eligible-typed-value", ["V1"], [rem("memory:c1", f"{C} {CA} discussed in review")], "no_eligible_value"),
        coh("V2-single-value", ["V2"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline"))],
            "same_value_observed", [["memory:c1"]], {"diagnosis": EQ("coverage_observed_unattested")}),
        coh("V2-equal-values", ["V2"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline")),
                                        rem("memory:c2", f"{C} {CA} confirmed as Ledgerline", P(C, CA, "Ledgerline"))],
            "same_value_observed", [["memory:c1", "memory:c2"]]),
        coh("V3-competing-values", ["V3", "V8"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline")),
                                                  rem("memory:c2", f"{C} {CA} is Northwind", P(C, CA, "Northwind"))],
            "competing_values_unresolved", [["memory:c1"], ["memory:c2"]],
            {"diagnosis": EQ("value_coherence_unresolved"), "mechanical_coverage_met": EQ(True)}),
        coh("V4-multi-single-value", ["V4", "V8"], [rem("memory:c1", f"{C} {CA} includes Ledgerline", P(C, CA, "Ledgerline", cardinality="multi"))],
            "coexistence_possible", None, {"diagnosis": EQ("value_coherence_unresolved")}),
        coh("V4-multi-two-values", ["V4"], [rem("memory:c1", f"{C} {CA} includes Ledgerline", P(C, CA, "Ledgerline", cardinality="multi")),
                                            rem("memory:c2", f"{C} {CA} includes Northwind", P(C, CA, "Northwind", cardinality="multi"))],
            "coexistence_possible"),
        coh("V5-unknown-cardinality", ["V5", "V8"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline", cardinality=None))],
            "cardinality_unresolved", None, {"diagnosis": EQ("value_coherence_unresolved")}),
        coh("V6-single-change-assertion", ["V6", "V8"], [rem("memory:c1", f"{C} {CA} changed to Northwind", P(C, CA, "Northwind", assertion="change"))],
            "change_assertion_unresolved", None, {"diagnosis": EQ("value_coherence_unresolved")}),
        coh("V6-change-over-prior-state", ["V6"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline")),
                                                    rem("memory:c2", f"{C} {CA} changed to Northwind", P(C, CA, "Northwind", assertion="change"))],
            "change_assertion_unresolved"),
        coh("V7-capitalization-competes", ["V7"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline")),
                                                    rem("memory:c2", f"{C} {CA} is ledgerline", P(C, CA, "ledgerline"))],
            "competing_values_unresolved", [["memory:c1"], ["memory:c2"]]),
        coh("V9-disputed-and-forgotten-excluded", ["V9"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline")),
                                                            rem("memory:c2", f"{C} {CA} is Northwind", P(C, CA, "Northwind")),
                                                            rem("memory:c3", f"{C} {CA} is Halcyon", P(C, CA, "Halcyon")),
                                                            {"op": "dispute", "ref": "memory:c2"},
                                                            {"op": "forget", "ref": "memory:c3"}],
            "same_value_observed", [["memory:c1"]]),
        {"id": "V10-no-raw-values-in-report", "invariants": ["V10"], "kind": "coverage",
         "setup": [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline")),
                   rem("memory:c2", f"{C} {CA} is Northwind", P(C, CA, "Northwind"))],
         "query": CQ, "needs": NC, "probes": ["values_absent:Ledgerline", "values_absent:Northwind"],
         "expect": {"values_absent": EQ(True)}},
        coh("V11-write-order-a", ["V11"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline")),
                                           rem("memory:c2", f"{C} {CA} is Northwind", P(C, CA, "Northwind")),
                                           rem("memory:c3", f"{C} {CA} also Ledgerline", P(C, CA, "Ledgerline"))],
            "competing_values_unresolved", [["memory:c1", "memory:c3"], ["memory:c2"]]),
        coh("V11-write-order-b", ["V11"], [rem("memory:c3", f"{C} {CA} also Ledgerline", P(C, CA, "Ledgerline")),
                                           rem("memory:c2", f"{C} {CA} is Northwind", P(C, CA, "Northwind")),
                                           rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline"))],
            "competing_values_unresolved", [["memory:c1", "memory:c3"], ["memory:c2"]]),
        {"id": "V12-stop-with-unresolved-values-refused", "invariants": ["V12"], "kind": "forge_report",
         "field": "continuation_proposal", "value": "review_stop", "with_unresolved_values": True,
         "expect": {"raises": EQ("ValueError")}},
        coh("V13-one-source-two-facts", ["V13"], [rem("memory:c1", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline")),
                                                  rem("memory:c2", f"{C} {CA} is Ledgerline", P(C, CA, "Ledgerline"))],
            "same_value_observed", [["memory:c1", "memory:c2"]], {"support_count": EQ(2)}),
    ],
}

# ---------------------------------------------------------------------------------------------
# 4. committed-governed-transition-witness-v1  (doc 78)
H, HA = "Halyard bridge", "wire protocol"
HQ = "Halyard bridge wire protocol"


def hprop(v, assertion):
    p = P(H, HA, v, assertion=assertion)
    if assertion == "change":
        p["replaces"] = "serial"
    return p


TBASE = [rem("memory:prior", f"{H} {HA} is serial", hprop("serial", "state")),
         rem("memory:source", f"{H} {HA} changed to ethernet", hprop("ethernet", "change"))]
W_FIXED = {"immediate_successor_verified_any": EQ(False), "can_stop_any": EQ(False),
           "answer_quality_verified_any": EQ(False), "authority_effect_all_none": EQ(True)}
R4 = {
    "replay_id": "committed-governed-transition-witness-v1",
    "title": "A transition witness appears only for a committed, cited, scoped governed replacement and never asserts more",
    "contract_sources": [doc_hash("docs/78-committed-governed-transition-witness.md")],
    "invariants": [
        {"id": "T1", "statement": "An asserted change without a committed governed application produces no witness.", "falsified_by": "any witness"},
        {"id": "T2", "statement": "An explicit governed application of the semantic proposal produces exactly one applied_state_change_observed witness naming the source, the prior, the supplied current head and the original semantic proposal.", "falsified_by": "count, status or references differing"},
        {"id": "T3", "statement": "A witness never asserts the immediate successor, answer quality, stop or mutation authority.", "falsified_by": "any of those flags true or authority not none"},
        {"id": "T4", "statement": "A witness requires both the source and the current head in the supplied admitted set.", "falsified_by": "a witness from either alone"},
        {"id": "T5", "statement": "A reader in another project sees no witness.", "falsified_by": "any witness"},
        {"id": "T6", "statement": "A correction that does not cite the semantic proposal, or cites a fabricated proposal identity, produces no witness.", "falsified_by": "any witness"},
        {"id": "T7", "statement": "A cited error correction yields applied_error_correction_observed, never a state-change witness.", "falsified_by": "another status"},
        {"id": "T8", "statement": "Duplicate admitted references are refused.", "falsified_by": "no ValueError"},
        {"id": "T9", "statement": "The witness survives restart unchanged.", "falsified_by": "different witness after reopen"},
        {"id": "T10", "statement": "A later governed change of the same target still yields a witness whose current head is the latest head, with immediate_successor_verified false.", "falsified_by": "no witness or immediate successor asserted"},
        {"id": "T11", "statement": "If the source fact is no longer current (forgotten) no witness is produced.", "falsified_by": "any witness"},
        {"id": "T12", "statement": "Witness serialization contains no raw fact text or values, and observation writes nothing.", "falsified_by": "fact text in output, or a changed state digest or event count"},
    ],
    "cases": [
        {"id": "T1-asserted-change-only", "invariants": ["T1"], "kind": "witness", "setup": TBASE,
         "admitted": ["memory:prior", "memory:source"], "expect": {"witness_count": EQ(0)}},
        {"id": "T2-applied-state-change", "invariants": ["T2", "T3", "T12"], "kind": "witness",
         "setup": TBASE + [{"op": "apply_open_proposal"}], "admitted": ["memory:source", "memory:prior@2"],
         "probes": ["state_unchanged", "text_absent"],
         "expect": {"witness_count": EQ(1),
                    "witnesses": EQ([{"status": "applied_state_change_observed", "source": "memory:source",
                                      "prior": "memory:prior", "current": "memory:prior@2",
                                      "proposal": "open_proposal"}]),
                    "state_unchanged": EQ(True), "text_absent": EQ(True), **W_FIXED}},
        {"id": "T4-source-only", "invariants": ["T4"], "kind": "witness",
         "setup": TBASE + [{"op": "apply_open_proposal"}], "admitted": ["memory:source"], "expect": {"witness_count": EQ(0)}},
        {"id": "T4-current-only", "invariants": ["T4"], "kind": "witness",
         "setup": TBASE + [{"op": "apply_open_proposal"}], "admitted": ["memory:prior@2"], "expect": {"witness_count": EQ(0)}},
        {"id": "T5-other-project-reader", "invariants": ["T5"], "kind": "witness",
         "setup": TBASE + [{"op": "apply_open_proposal"}], "admitted": ["memory:source", "memory:prior@2"],
         "observe_scope": "project:b", "expect": {"witness_count": EQ(0)}},
        {"id": "T6-uncited-correction", "invariants": ["T6"], "kind": "witness",
         "setup": TBASE + [{"op": "correct", "ref": "memory:prior", "text": f"{H} {HA} is ethernet", "kind": "state_change", "cite": "none"}],
         "admitted": ["memory:source", "memory:prior@2"], "expect": {"witness_count": EQ(0)}},
        {"id": "T6-forged-proposal-citation", "invariants": ["T6"], "kind": "witness",
         "setup": TBASE + [{"op": "correct", "ref": "memory:prior", "text": f"{H} {HA} is ethernet", "kind": "state_change", "cite": "forged"}],
         "admitted": ["memory:source", "memory:prior@2"], "expect": {"witness_count": EQ(0)}},
        {"id": "T7-cited-error-correction", "invariants": ["T7", "T3"], "kind": "witness",
         "setup": TBASE + [{"op": "correct", "ref": "memory:prior", "text": f"{H} {HA} is ethernet", "kind": "error_correction", "cite": "open_proposal"}],
         "admitted": ["memory:source", "memory:prior@2"],
         "expect": {"witness_count": EQ(1), "witness_statuses": EQ(["applied_error_correction_observed"]), **W_FIXED}},
        {"id": "T8-duplicate-admitted", "invariants": ["T8"], "kind": "witness",
         "setup": TBASE + [{"op": "apply_open_proposal"}], "admitted": ["memory:source", "memory:source"],
         "expect": {"raises": EQ("ValueError")}},
        {"id": "T9-restart", "invariants": ["T9"], "kind": "witness",
         "setup": TBASE + [{"op": "apply_open_proposal"}, {"op": "reopen"}], "admitted": ["memory:source", "memory:prior@2"],
         "expect": {"witness_count": EQ(1), "witness_statuses": EQ(["applied_state_change_observed"])}},
        {"id": "T10-later-governed-change", "invariants": ["T10", "T3"], "kind": "witness",
         "setup": TBASE + [{"op": "apply_open_proposal"},
                           {"op": "correct", "ref": "memory:prior", "text": f"{H} {HA} is fibre", "kind": "state_change", "cite": "none"}],
         "admitted": ["memory:source", "memory:prior@3"],
         "expect": {"witness_count": EQ(1),
                    "witnesses": EQ([{"status": "applied_state_change_observed", "source": "memory:source",
                                      "prior": "memory:prior", "current": "memory:prior@3", "proposal": "open_proposal"}]),
                    **W_FIXED}},
        {"id": "T11-source-forgotten", "invariants": ["T11"], "kind": "witness",
         "setup": TBASE + [{"op": "apply_open_proposal"}, {"op": "forget", "ref": "memory:source"}],
         "admitted": ["memory:source", "memory:prior@2"], "expect": {"witness_count": EQ(0)}},
    ],
}

# ---------------------------------------------------------------------------------------------
# 5. same-slot-safety-counterevidence-and-immutable-stop-gate-v1
S, SA = "Tamarack site", "power feed"
SQ = "Tamarack site power feed"
NS = [{"s": S, "a": SA}]
SBASE = [rem("memory:s1", f"{S} {SA} is grid north", P(S, SA, "grid north"))]
SAGREE = SBASE + [rem("memory:s2", f"{S} {SA} confirmed grid north", P(S, SA, "grid north"))]
R5 = {
    "replay_id": "same-slot-safety-counterevidence-and-immutable-stop-gate-v1",
    "title": "Same-slot counter-evidence blocks clean coverage, the recall receipt detects tampering without conferring authority, and no stop is ever proposed",
    "contract_sources": [doc_hash("docs/79-independent-644-qualification-reconciliation.md"),
                         doc_hash("docs/81-indexed-slot-audit-qualification.md"),
                         doc_hash("docs/META_LEDGER.md")],
    "contract_note": "Receipt semantics are taken from META_LEDGER Entry #125 and the module contract of runtime/recall_observation_receipt.py (docstring only).",
    "invariants": [
        {"id": "S1", "statement": "No observation ever proposes a stop or attests one, including fully agreeing typed coverage.", "falsified_by": "review_stop or stop_attested true"},
        {"id": "S2", "statement": "Same-slot counter-evidence (extracted, negated, hedged change, attributed, non-retrieved, budget-capped, temporally bounded) prevents a clean coverage diagnosis.", "falsified_by": "coverage_observed_unattested in any such case"},
        {"id": "S3", "statement": "Every controlled recall carries a captured receipt that is immutable and internally consistent with the untampered result.", "falsified_by": "missing receipt, assignable fields, or a fresh result failing verification"},
        {"id": "S4", "statement": "Any post-capture mutation of candidates, admitted, ranked, route counts, query, controller plan, refusals or policy is detected, and the observer then never reports clean coverage.", "falsified_by": "verification true after mutation, or a clean diagnosis"},
        {"id": "S5", "statement": "A result with no receipt never reads as clean coverage.", "falsified_by": "coverage_observed_unattested"},
        {"id": "S6", "statement": "The receipt is change detection, not authentication: a caller can re-mint a matching receipt over altered contents, so a matching receipt never confers stop authority.", "falsified_by": "a re-minted receipt failing to verify (the limitation would be mis-described) or any stop"},
        {"id": "S7", "statement": "The receipt claims no state revision, snapshot or slot-closure attestation and no stop authority; forging those claims is refused.", "falsified_by": "any such claim present or accepted"},
        {"id": "S8", "statement": "Receipt public serialization discloses no refused or hidden candidate identity.", "falsified_by": "a refused identity in the serialization"},
        {"id": "S9", "statement": "Missing or corrupted slot enumeration fails closed with an exception, never a clean report.", "falsified_by": "a report produced"},
        {"id": "S10", "statement": "A controller plan claiming authority is refused before recall.", "falsified_by": "recall proceeding"},
        {"id": "S11", "statement": "Malformed or hostile mutable inputs make receipt verification return false, never raise.", "falsified_by": "an exception or true"},
        {"id": "S12", "statement": "F6 (untyped same-slot competitor) remains unresolved: the replay records whether it is detected but requires only that no stop is proposed.", "falsified_by": "a stop proposal"},
    ],
    "cases": [
        {"id": "S1-agreeing-coverage-never-stops", "invariants": ["S1"], "kind": "coverage", "setup": SAGREE,
         "query": SQ, "needs": NS, "expect": {"mechanical_coverage_met": EQ(True), "diagnosis": EQ("coverage_observed_unattested"), **NO_STOP}},
        *[{"id": f"S2-{name}", "invariants": ["S2", "S1"], "kind": "coverage", "setup": SBASE + extra,
           "query": SQ, "needs": NS, **({"lexical_limit": 1} if name == "budget-capped" else {}),
           "expect": {"diagnosis": NOT_CLEAN, **NO_STOP}}
          for name, extra in (
              ("extracted", [{"op": "retain_extracted", "ref": "memory:s2", "text": f"{S} {SA} is diesel", "prop": P(S, SA, "diesel")}]),
              ("negated", [rem("memory:s2", f"{S} {SA} is not grid north", P(S, SA, "grid north", negated=True))]),
              ("hedged-change", [rem("memory:s2", f"{S} {SA} may have moved to solar", P(S, SA, "solar", assertion="change", hedged=True))]),
              ("attributed", [rem("memory:s2", f"Contractors claim {S} {SA} is diesel", P(S, SA, "diesel", attributed_to_other=True))]),
              ("non-retrieved", [rem("memory:s2", "Since the outage the substation runs on battery", P(S, SA, "battery"))]),
              ("budget-capped", [rem("memory:s2", f"{S} {SA} is battery", P(S, SA, "battery"))]),
              ("expired", [rem("memory:s2", f"{S} {SA} was diesel", P(S, SA, "diesel"), valid_from="2010-01-01", valid_until="2010-06-01")]),
              ("prospective", [rem("memory:s2", f"{S} {SA} will be solar", P(S, SA, "solar"), valid_from="2099-01-01")]))],
        {"id": "S3-receipt-captured-immutable", "invariants": ["S3", "S7"], "kind": "receipt", "setup": SAGREE, "query": SQ,
         "expect": {"receipt_present": EQ(True), "receipt_unchanged": EQ(True), "receipt_assignment_refused": EQ(True),
                    "receipt_state_revision": EQ(None), "receipt_snapshot_attested": EQ(False),
                    "receipt_slot_closure_attested": EQ(False), "receipt_can_stop": EQ(False)}},
        *[{"id": f"S4-mutation-{m}", "invariants": ["S4"], "kind": "coverage",
           "setup": SAGREE + [rem("memory:s9", f"{S} {SA} was diesel", P(S, SA, "diesel")), {"op": "forget", "ref": "memory:s9"}],
           "query": SQ, "needs": NS, "mutations": [{"m": m}],
           "expect": {"receipt_unchanged": EQ(False), "diagnosis": NOT_CLEAN, **NO_STOP}}
          for m in ("drop_candidate", "drop_admitted", "reverse_ranked", "zero_route_counts", "change_query",
                    "change_plan", "clear_refusals", "change_policy", "change_admission_mode", "change_evaluated_at")],
        {"id": "S5-missing-receipt", "invariants": ["S5"], "kind": "coverage", "setup": SAGREE, "query": SQ, "needs": NS,
         "mutations": [{"m": "remove_receipt"}],
         "expect": {"receipt_unchanged": EQ(False), "diagnosis": NOT_CLEAN, **NO_STOP}},
        {"id": "S6-reminted-receipt-is-not-authentication", "invariants": ["S6", "S1"], "kind": "coverage", "setup": SAGREE,
         "query": SQ, "needs": NS, "mutations": [{"m": "drop_admitted"}, {"m": "remint_receipt"}],
         "expect": {"receipt_unchanged": EQ(True), **NO_STOP}},
        *[{"id": f"S7-forged-receipt-{field}", "invariants": ["S7"], "kind": "forge_receipt", "setup": SBASE, "query": SQ,
           "field": field, "value": value, "expect": {"raises": EQ("ValueError")}}
          for field, value in (("can_stop", True), ("snapshot_attested", True), ("slot_closure_attested", True),
                               ("state_revision", "rev-1"), ("authority_effect", "stop"))],
        {"id": "S8-receipt-hides-refused-identities", "invariants": ["S8"], "kind": "receipt",
         "setup": SAGREE + [rem("memory:s9", f"{S} {SA} was diesel", P(S, SA, "diesel")), {"op": "forget", "ref": "memory:s9"}],
         "query": SQ, "expect": {"refused_identities_present": EQ(True), "refused_identities_disclosed": EQ(False)}},
        *[{"id": f"S9-enumeration-fault-{fault}", "invariants": ["S9"], "kind": "coverage", "setup": SAGREE, "query": SQ,
           "needs": NS, "fault": fault, "expect": {"raises_any": EQ(True)}}
          for fault in ("no_census_reader", "no_substrate_enumeration", "corrupt_index_key")],
        {"id": "S10-controller-authority-claim", "invariants": ["S10"], "kind": "controller_authority", "setup": SBASE,
         "query": SQ, "expect": {"raises_any": EQ(True)}},
        *[{"id": f"S11-hostile-input-{m}", "invariants": ["S11"], "kind": "receipt", "setup": SAGREE, "query": SQ,
           "mutations": [{"m": m}], "expect": {"receipt_unchanged": EQ(False), "verification_raised": EQ(False)}}
          for m in ("hostile_route_counts", "hostile_refusals", "plan_object", "recall_none", "receipt_garbage", "counts_bool")],
        {"id": "S12-F6-untyped-competitor", "invariants": ["S12", "S1"], "kind": "coverage",
         "setup": SBASE + [rem("memory:s2", f"{S} {SA} is diesel")], "query": SQ, "needs": NS,
         "record": ["diagnosis"], "expect": {**NO_STOP}},
    ],
}

for replay in (R1, R2, R3, R4, R5):
    doc = {**{"replay_id": replay["replay_id"], "fixture_version": 1}, **COMMON,
           **{k: v for k, v in replay.items() if k != "replay_id"}}
    path = OUT / f"{replay['replay_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=False, ensure_ascii=True) + "\n", encoding="utf-8")
    print(path.name, len(doc["cases"]), "cases", len(doc["invariants"]), "invariants",
          hashlib.sha256(path.read_bytes()).hexdigest()[:16])
