"""Author the three #786 security replay fixtures (``786-security-replay-dsl/1``).

Expectations are written from the contract documents named in each fixture's
``contract_sources`` (docs/786, docs/44, docs/774-776 contract, docs/774 policy, docs/777
successor qualification), never from a replay outcome. Vocabulary is new: no entity, value
or phrase of the frozen theatre/vineyard holdouts or of the #644 v7 fixtures is used.
usage: author_fixtures.py <repo_root> <base_commit>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
BASE_COMMIT = sys.argv[2]
OUT = ROOT / "reference/fixtures/786-security-replays"
DSL = "786-security-replay-dsl/1"
T, A, B, NEVER = "tenant:s786", "project:a", "project:b", "memory:never"
FOUR = ["memory.propose", "memory.authorize", "memory.commit", "memory.receipt"]
PARKED_THEN_FOUR = ["memory.propose", "memory.authorize", "memory.receipt"] + FOUR  # the writer's own parked proposal, then its commit


def doc_hash(path):
    blob = subprocess.run(["git", "show", f"{BASE_COMMIT}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    return {"path": path, "sha256_at_base": hashlib.sha256(blob).hexdigest()}


def P(s, a, v, assertion="state"):
    return {"s": s, "a": a, "v": v, "assertion": assertion, "cardinality": "single"}


def rem(ref, text, prop=None, **kw):
    op = {"op": "remember", "ref": ref, "text": text}
    if prop is not None:
        op["prop"] = prop
    op.update(kw)
    return op


def cor(ref, text, **kw):
    return {"op": "correct", "ref": ref, "text": text, "kind": "state_change", **kw}


EQ = lambda v: {"eq": v}  # noqa: E731
NE = lambda v: {"ne": v}  # noqa: E731
REFUSED = {"committed": EQ(False)}

COMMON = {
    "dsl_version": DSL,
    "owning_issue": 786,
    "frozen_on": "2026-10-13",
    "status": "supersedes_v1",
    "supersession_reason": ("The -v1 fixtures (frozen at b70ff58a) are superseded, not edited. The second independent "
                            "review read them against their contract sources and found: op_mentions could only scan a "
                            "7-field outcome shape (the runner now scans the full result); W3 and L3 probed only "
                            "`committed` after restart; the documented superset forget/dispute admission and the "
                            "forged-complete-scope commit were unpinned; refused or parked proposals on a tombstoned "
                            "id (docs/44 'reports 0 to any writer') were untested and falsified (review F-A); "
                            "re-deletion of a deleted head/version (review F-C/F-D) and a former owner's dispute "
                            "attempts (review F-E) were untested and falsified; R1's owner view cites "
                            "docs/plan-776-777-772-exact-head-qualification.md, which v1 did not list; L2's "
                            "'content recoverable after a pruning' is implementation evidence, now labelled so. "
                            "Every v1 case is carried forward unchanged in substance."),
    "development_history": ("v1 was executed once with --allow-dirty before its freeze; its single corrected "
                            "expectation (fixture 1, W5: a disputed head is withheld from the owner's own admission, "
                            "docs/44) is carried into v2. v2 expectations were written from the contracts and the "
                            "second review's findings before v2 was first executed. That first execution (on the "
                            "working tree after the second review's remediation) failed four probes: W7c "
                            "`a_del_refusal` was a runtime finding (a former owner's re-deletion or dispute of its "
                            "own deleted generation answered `fact_not_found` once another scope held the live "
                            "head and `already_deleted` otherwise, disclosing the re-creation; repaired at the "
                            "governed delete/dispute boundary, pytest ReplayV2Findings), and three were expectation "
                            "errors corrected to the owner-only control behaviour: W4b `k2_owner_recall` (a second "
                            "remember onto an owner-visible head appends a version, both stay admitted), W5 "
                            "`owner_candidates` (candidates carry the owner's superseded version; admission withholds "
                            "the disputed head) and R6b `other_history` (the writer's own parked proposal precedes "
                            "its commit in its own history). No expectation was changed to match a refusal string."),
    "base_commit": BASE_COMMIT,
    "independence": ("Expected outcomes were written from the contract documents listed in contract_sources by the "
                     "session that implemented the #786 repair, before this fixture was first executed by the runner. "
                     "They are therefore preregistered but not independent of the implementer; an independent reviewer "
                     "must read them against the contracts before any acceptance. A failing expectation is a finding, "
                     "never a reason to edit this fixture; a corrected expectation requires a superseding fixture "
                     "version with a recorded reason. No frozen holdout phrase or #644 fixture vocabulary is used."),
    "stop_lines": [
        "no fixture edit after first execution; supersede with -v2 and record why",
        "no expectation weakened to obtain PASS",
        "no runtime change motivated by a replay outcome without a preregistered reproducer",
        "a replay verdict is evidence, not successor acceptance; acceptance requires independent review",
    ],
}

# ------------------------------------------------------------- 1. cross-scope-write-authority-denial-v1
K, KA = "Marrow lighthouse keeper", "shift"
KQ = f"{K} {KA}"
KT = lambda v: f"{K} {KA} is {v}"  # noqa: E731
SUPERSET = {"isolation_domain_refs": [T, A, B], "project_ref": A}
COMPLETE = {"scope": A, "project_ref": A, "isolation_domain_refs": [T, A], "required_isolation_domain_refs": [T, A]}
INCONSISTENT = {"isolation_domain_refs": [T, A]}
R1 = {
    "replay_id": "cross-scope-write-authority-denial-v2",
    "title": "A live logical memory is writable only by a writer eligible for its scope; refusals change and disclose nothing",
    "contract_sources": [doc_hash("docs/786-cross-scope-write-authority.md"), doc_hash("docs/44-public-api-contract.md")],
    "invariants": [
        {"id": "W1", "statement": "A promotion from another project onto a live head is refused with target_unavailable, reports v0/v0 and a v0 snapshot, and leaves head, version, recall and history of the owner byte-identical.",
         "falsified_by": "a commit, any other refusal token, a non-v0 state, or any owner-side change"},
        {"id": "W2", "statement": "correct, forget, permanent forget and dispute from another project read byte-identically (ids and timestamps folded) to the same call on an id nobody wrote, and change nothing.",
         "falsified_by": "any difference from the unknown-id result, a tombstone, a dispute mark or an invalidated head"},
        {"id": "W3", "statement": "The refusal holds after every restart; the scope binding is durable.",
         "falsified_by": "a commit after a reopen"},
        {"id": "W4", "statement": "An override leaving required isolation domains outside the bound domains is a malformed proposal (ValueError) for any target; an override declaring a superset of domains plus the owner's project cannot replace or correct the head, while (documented) it may delete or dispute it as an eligible reader, and a complete re-declaration of the owner's scope commits as the owner would (the facade is a host-bound trust boundary).",
         "falsified_by": "a result instead of ValueError, a ValueError that differs by target, a commit of remember/correct under the superset override, or a documented disposition silently changing"},
        {"id": "W5", "statement": "The owner's own remember, correct and dispute stay admitted (a disputed head is recorded as disputed and, as documented, withheld from the owner's own admission), and the same text in an unrelated memory of another project is independent.",
         "falsified_by": "an owner operation refused, or either project's recall admitting the other's fact"},
        {"id": "W6", "statement": "A proposal refused for its target, and one parked by policy review, persist no episode, live and after restart; a committed proposal keeps its episode.",
         "falsified_by": "an episode retrievable after a refusal or review park, or absent after a commit"},
        {"id": "W7", "statement": "A refused remember, correct, forget or dispute attempt by another project, and a former owner's attempts on a re-created id, leave no event in the live generation's public history; the refused project's history of the memory stays blank.",
         "falsified_by": "any extra event in the live generation's history or a non-blank view for the refused project"},
        {"id": "W8", "statement": "A governed-deleted id reports 0 to any writer: a re-created generation starts its own counter (snapshot v0, before v0, after v1, history 1), a refused or policy-parked proposal on the tombstoned id reports v0/v0, and the former owner's view keeps the version its deletion recorded and cannot write, dispute or re-delete the id while the new generation is live.",
         "falsified_by": "the former count in any writer's receipt, snapshot or history, a changed former-owner view, or a former-owner act admitted"},
    ],
    "cases": [
        {"id": "W1-remember-over-live-head", "invariants": ["W1"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), name="a1", require_committed=True),
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, name="b1")],
         "probes": {"b1_committed": {"probe": "op_result", "name": "b1", "field": "committed"},
                    "b1_refusal": {"probe": "op_result", "name": "b1", "field": "refusal"},
                    "b1_before": {"probe": "op_result", "name": "b1", "field": "before_state"},
                    "b1_after": {"probe": "op_result", "name": "b1", "field": "after_state"},
                    "b1_snapshot": {"probe": "op_result", "name": "b1", "field": "state_snapshot"},
                    "b1_mentions": {"probe": "op_mentions", "name": "b1", "tokens": ["memory:k", A, "dawn", "v1"]},
                    "head": {"probe": "canonical_head", "ref": "memory:k"},
                    "owner_history": {"probe": "history", "ref": "memory:k"},
                    "owner_recall": {"probe": "recall_admitted", "query": KQ},
                    "other_recall": {"probe": "recall_admitted", "query": KQ, "as": B},
                    "other_history_unknown": {"probe": "history_same_as_unknown", "ref": "memory:k", "as": B}},
         "expect": {"b1_committed": EQ(False), "b1_refusal": EQ("target_unavailable"), "b1_before": EQ("v0"),
                    "b1_after": EQ("v0"), "b1_snapshot": EQ("v0"), "b1_mentions": EQ([]), "head": EQ("memory:k"),
                    "owner_history": EQ({"current": "memory:k", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "owner_recall": EQ(["memory:k"]), "other_recall": EQ([]), "other_history_unknown": EQ(True)}},
        {"id": "W2-correct-forget-dispute-by-other", "invariants": ["W2"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True)],
         "probes": {"correct_unknown": {"probe": "op_same_as_unknown", "op": "correct", "ref": "memory:k", "text": KT("dusk"), "as": B},
                    "forget_unknown": {"probe": "op_same_as_unknown", "op": "forget", "ref": "memory:k", "as": B},
                    "permanent_unknown": {"probe": "op_same_as_unknown", "op": "forget", "ref": "memory:k", "permanent": True, "as": B},
                    "dispute_unknown": {"probe": "op_same_as_unknown", "op": "dispute", "ref": "memory:k", "as": B},
                    "tombstones": {"probe": "tombstoned_ids"}, "disputed": {"probe": "disputed"},
                    "head": {"probe": "canonical_head", "ref": "memory:k"}, "valid": {"probe": "fact_valid", "fact": "memory:k"},
                    "owner_recall": {"probe": "recall_admitted", "query": KQ}},
         "expect": {"correct_unknown": EQ(True), "forget_unknown": EQ(True), "permanent_unknown": EQ(True),
                    "dispute_unknown": EQ(True), "tombstones": EQ([]), "disputed": EQ([]), "head": EQ("memory:k"),
                    "valid": EQ(True), "owner_recall": EQ(["memory:k"])}},
        {"id": "W3-refusal-survives-restart", "invariants": ["W3", "W1"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   cor("memory:k", KT("noon"), require_committed=True), {"op": "reopen"},
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, name="b1"),
                   cor("memory:k", KT("dusk"), **{"as": B}, name="b2"), {"op": "reopen"},
                   {"op": "forget", "ref": "memory:k", "as": B, "name": "b3"},
                   {"op": "dispute", "ref": "memory:k", "as": B, "name": "b4"}],
         "probes": {"b1": {"probe": "op_result", "name": "b1", "field": "committed"},
                    "b1_refusal": {"probe": "op_result", "name": "b1", "field": "refusal"},
                    "b1_after": {"probe": "op_result", "name": "b1", "field": "after_state"},
                    "b1_mentions": {"probe": "op_mentions", "name": "b1", "tokens": ["memory:k", "memory:k@2", "v2", "dawn", "noon", A]},
                    "b2": {"probe": "op_result", "name": "b2", "field": "committed"},
                    "b2_refusal": {"probe": "op_result", "name": "b2", "field": "refusal"},
                    "b3": {"probe": "op_result", "name": "b3", "field": "committed"},
                    "b3_refusal": {"probe": "op_result", "name": "b3", "field": "refusal"},
                    "b4": {"probe": "op_result", "name": "b4", "field": "committed"},
                    "b4_refusal": {"probe": "op_result", "name": "b4", "field": "refusal"},
                    "head": {"probe": "canonical_head", "ref": "memory:k"},
                    "owner_history": {"probe": "history", "ref": "memory:k"},
                    "owner_recall": {"probe": "recall_admitted", "query": KQ}},
         "expect": {"b1": EQ(False), "b1_refusal": EQ("target_unavailable"), "b1_after": EQ("v0"), "b1_mentions": EQ([]),
                    "b2": EQ(False), "b2_refusal": EQ("fact_not_found"), "b3": EQ(False), "b3_refusal": EQ("fact_not_found"),
                    "b4": EQ(False), "b4_refusal": EQ("fact_not_found"), "head": EQ("memory:k@2"),
                    "owner_history": EQ({"current": "memory:k@2", "state_version": 2, "tombstoned": False, "events": FOUR + FOUR}),
                    "owner_recall": EQ(["memory:k@2"])}},
        {"id": "W4-overrides", "invariants": ["W4"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   rem("memory:k", KT("dusk"), **{"as": B}, overrides=INCONSISTENT, name="bad_target"),
                   rem(NEVER, KT("dusk"), **{"as": B}, overrides=INCONSISTENT, name="bad_unknown"),
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, overrides=SUPERSET, name="sup_rem"),
                   cor("memory:k", KT("dusk"), **{"as": B}, overrides=SUPERSET, name="sup_cor")],
         "probes": {"bad_target": {"probe": "op_result", "name": "bad_target", "field": "raised"},
                    "bad_unknown": {"probe": "op_result", "name": "bad_unknown", "field": "raised"},
                    "sup_rem_committed": {"probe": "op_result", "name": "sup_rem", "field": "committed"},
                    "sup_rem_refusal": {"probe": "op_result", "name": "sup_rem", "field": "refusal"},
                    "sup_rem_before": {"probe": "op_result", "name": "sup_rem", "field": "before_state"},
                    "sup_cor_committed": {"probe": "op_result", "name": "sup_cor", "field": "committed"},
                    "head": {"probe": "canonical_head", "ref": "memory:k"}, "valid": {"probe": "fact_valid", "fact": "memory:k"},
                    "owner_recall": {"probe": "recall_admitted", "query": KQ}, "tombstones": {"probe": "tombstoned_ids"}},
         "expect": {"bad_target": EQ("ValueError"), "bad_unknown": EQ("ValueError"), "sup_rem_committed": EQ(False),
                    "sup_rem_refusal": EQ("target_unavailable"), "sup_rem_before": EQ("v0"), "sup_cor_committed": EQ(False),
                    "head": EQ("memory:k"), "valid": EQ(True), "owner_recall": EQ(["memory:k"]), "tombstones": EQ([])}},
        {"id": "W4b-documented-dispositions-of-complete-and-superset-declarations", "invariants": ["W4"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   {"op": "dispute", "ref": "memory:k", "as": B, "overrides": SUPERSET, "name": "sup_disp"},
                   {"op": "forget", "ref": "memory:k", "as": B, "overrides": SUPERSET, "name": "sup_forget"},
                   rem("memory:k2", KT("noon"), P(K, KA, "noon"), require_committed=True),
                   rem("memory:k2", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, overrides=COMPLETE, label="complete", name="complete")],
         "probes": {"sup_disp": {"probe": "op_result", "name": "sup_disp", "field": "committed"},
                    "sup_forget": {"probe": "op_result", "name": "sup_forget", "field": "committed"},
                    "tombstones": {"probe": "tombstoned_ids"},
                    "complete": {"probe": "op_result", "name": "complete", "field": "committed"},
                    "k2_head": {"probe": "canonical_head", "ref": "memory:k2"},
                    "k2_owner_recall": {"probe": "recall_admitted", "query": KQ}},
         "expect": {"sup_disp": EQ(True), "sup_forget": EQ(True), "tombstones": EQ(["memory:k"]), "complete": EQ(True),
                    "k2_head": EQ("complete"), "k2_owner_recall": EQ(["memory:k2", "complete"])}},
        {"id": "W5-positive-controls-and-unrelated-same-text", "invariants": ["W5"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), name="a1"),
                   cor("memory:k", KT("noon"), name="a2"),
                   {"op": "dispute", "ref": "memory:k", "name": "a3"},
                   rem("memory:other", KT("noon"), P(K, KA, "noon"), **{"as": B}, label="other", name="b1")],
         "probes": {"a1": {"probe": "op_result", "name": "a1", "field": "committed"},
                    "a2": {"probe": "op_result", "name": "a2", "field": "committed"},
                    "a3": {"probe": "op_result", "name": "a3", "field": "committed"},
                    "b1": {"probe": "op_result", "name": "b1", "field": "committed"},
                    "owner_recall": {"probe": "recall_admitted", "query": KQ},
                    "owner_candidates": {"probe": "recall_candidates", "query": KQ},
                    "disputed": {"probe": "disputed"}, "head": {"probe": "canonical_head", "ref": "memory:k"},
                    "other_recall": {"probe": "recall_admitted", "query": KQ, "as": B},
                    "other_view_of_k": {"probe": "history_same_as_unknown", "ref": "memory:k", "as": B},
                    "owner_view_of_other": {"probe": "history_same_as_unknown", "ref": "memory:other"}},
         "expect": {"a1": EQ(True), "a2": EQ(True), "a3": EQ(True), "b1": EQ(True), "owner_recall": EQ([]),
                    "owner_candidates": EQ(["memory:k", "memory:k@2"]), "disputed": EQ(["memory:k@2"]), "head": EQ("memory:k@2"),
                    "other_recall": EQ(["other"]), "other_view_of_k": EQ(True), "owner_view_of_other": EQ(True)}},
        {"id": "W6-denied-proposals-persist-no-episode", "invariants": ["W6"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   {"op": "commit_with_episode", "ref": "memory:k", "text": KT("dusk"), "episode": "episode:denied", "as": B, "name": "denied"},
                   {"op": "commit_with_episode", "ref": "memory:parked", "text": KT("noon"), "episode": "episode:parked", "risk": "high", "name": "parked"},
                   {"op": "commit_with_episode", "ref": "memory:kept", "text": KT("night"), "episode": "episode:kept", "name": "kept"},
                   {"op": "reopen"}],
         "probes": {"denied_committed": {"probe": "op_result", "name": "denied", "field": "committed"},
                    "denied_refusal": {"probe": "op_result", "name": "denied", "field": "refusal"},
                    "denied_before": {"probe": "op_result", "name": "denied", "field": "before_state"},
                    "parked_committed": {"probe": "op_result", "name": "parked", "field": "committed"},
                    "kept_committed": {"probe": "op_result", "name": "kept", "field": "committed"},
                    "episode_denied": {"probe": "episode_present", "episode": "episode:denied"},
                    "episode_parked": {"probe": "episode_present", "episode": "episode:parked"},
                    "episode_kept": {"probe": "episode_present", "episode": "episode:kept"},
                    "head": {"probe": "canonical_head", "ref": "memory:k"}, "parked_head": {"probe": "canonical_head", "ref": "memory:parked"}},
         "expect": {"denied_committed": EQ(False), "denied_refusal": EQ("target_unavailable"), "denied_before": EQ("v0"),
                    "parked_committed": EQ(False), "kept_committed": EQ(True), "episode_denied": EQ(False),
                    "episode_parked": EQ(False), "episode_kept": EQ(True), "head": EQ("memory:k"), "parked_head": EQ(None)}},
        {"id": "W7-refused-attempt-leaves-no-public-trace", "invariants": ["W7"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, name="b1"),
                   cor("memory:k", KT("noon"), require_committed=True)],
         "probes": {"b1": {"probe": "op_result", "name": "b1", "field": "committed"},
                    "owner_history": {"probe": "history", "ref": "memory:k"},
                    "other_history_unknown": {"probe": "history_same_as_unknown", "ref": "memory:k", "as": B},
                    "canonical_version": {"probe": "canonical_version", "ref": "memory:k"}},
         "expect": {"b1": EQ(False), "other_history_unknown": EQ(True), "canonical_version": EQ(2),
                    "owner_history": EQ({"current": "memory:k@2", "state_version": 2, "tombstoned": False, "events": FOUR + FOUR})}},
        {"id": "W7b-refused-dispute-and-forget-attempts-leave-no-public-trace", "invariants": ["W7"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   {"op": "dispute", "ref": "memory:k", "as": B, "name": "bd"},
                   {"op": "forget", "ref": "memory:k", "as": B, "name": "bf"},
                   {"op": "dispute", "ref": "memory:k", "fact": "memory:k", "as": B, "name": "bdf"}],
         "probes": {"bd": {"probe": "op_result", "name": "bd", "field": "committed"},
                    "bf": {"probe": "op_result", "name": "bf", "field": "committed"},
                    "bdf": {"probe": "op_result", "name": "bdf", "field": "committed"},
                    "owner_history": {"probe": "history", "ref": "memory:k"},
                    "other_history_unknown": {"probe": "history_same_as_unknown", "ref": "memory:k", "as": B}},
         "expect": {"bd": EQ(False), "bf": EQ(False), "bdf": EQ(False), "other_history_unknown": EQ(True),
                    "owner_history": EQ({"current": "memory:k", "state_version": 1, "tombstoned": False, "events": FOUR})}},
        {"id": "W7c-former-owner-attempts-leave-no-trace-in-the-new-generation", "invariants": ["W7", "W8"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   {"op": "forget", "ref": "memory:k", "require_committed": True},
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, label="gen-b", require_committed=True),
                   rem("memory:k", KT("night"), name="a_rem"),
                   {"op": "dispute", "ref": "memory:k", "fact": "memory:k", "name": "a_disp"},
                   {"op": "delete_version", "ref": "memory:k", "fact": "memory:k", "name": "a_del"},
                   {"op": "forget", "ref": "memory:k", "name": "a_forget"}],
         "probes": {"a_rem": {"probe": "op_result", "name": "a_rem", "field": "committed"},
                    "a_disp": {"probe": "op_result", "name": "a_disp", "field": "committed"},
                    "a_disp_mentions": {"probe": "op_mentions", "name": "a_disp", "tokens": ["gen-b", "dusk", "v1", "v2"]},
                    "a_del": {"probe": "op_result", "name": "a_del", "field": "committed"},
                    "a_del_refusal": {"probe": "op_result", "name": "a_del", "field": "refusal"},
                    "a_forget": {"probe": "op_result", "name": "a_forget", "field": "committed"},
                    "other_history": {"probe": "history", "ref": "memory:k", "as": B},
                    "other_recall": {"probe": "recall_admitted", "query": KQ, "as": B}},
         "expect": {"a_rem": EQ(False), "a_disp": EQ(False), "a_disp_mentions": EQ([]), "a_del": EQ(False),
                    "a_del_refusal": EQ("already_deleted"), "a_forget": EQ(False),
                    "other_history": EQ({"current": "gen-b", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "other_recall": EQ(["gen-b"])}},
        {"id": "W8b-refused-and-parked-proposals-on-a-tombstoned-id-report-v0", "invariants": ["W8"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   cor("memory:k", KT("noon"), require_committed=True),
                   {"op": "forget", "ref": "memory:k", "require_committed": True},
                   rem("memory:k", KT("dusk"), **{"as": B}, overrides={"risk_class": "medium"}, name="parked_b"),
                   rem("memory:k", KT("dusk"), overrides={"risk_class": "high"}, name="parked_a"),
                   {"op": "reopen"},
                   rem("memory:k", KT("dusk"), **{"as": B}, overrides={"risk_class": "medium"}, name="parked_b2")],
         "probes": {"parked_b": {"probe": "op_result", "name": "parked_b", "field": "committed"},
                    "parked_b_states": {"probe": "op_mentions", "name": "parked_b", "tokens": ["v1", "v2", "v3", "memory:k", "memory:k@2"]},
                    "parked_b_after": {"probe": "op_result", "name": "parked_b", "field": "after_state"},
                    "parked_a_after": {"probe": "op_result", "name": "parked_a", "field": "after_state"},
                    "parked_a_snapshot": {"probe": "op_result", "name": "parked_a", "field": "state_snapshot"},
                    "parked_b2_after": {"probe": "op_result", "name": "parked_b2", "field": "after_state"},
                    "other_history": {"probe": "history", "ref": "memory:k", "as": B},
                    "owner_history": {"probe": "history", "ref": "memory:k"}},
         "expect": {"parked_b": EQ(False), "parked_b_states": EQ([]), "parked_b_after": EQ("v0"), "parked_a_after": EQ("v0"),
                    "parked_a_snapshot": EQ("v0"), "parked_b2_after": EQ("v0"),
                    "other_history": EQ({"current": None, "state_version": 0, "tombstoned": False, "events": []}),
                    "owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []})}},
        {"id": "W8-recreated-generation-starts-its-own-counter", "invariants": ["W8"],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   cor("memory:k", KT("noon"), require_committed=True),
                   {"op": "forget", "ref": "memory:k", "name": "a_del", "require_committed": True},
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, label="gen-b", name="b1"),
                   rem("memory:k", KT("night"), P(K, KA, "night"), name="a_back"),
                   {"op": "reopen"},
                   cor("memory:k", KT("midnight"), **{"as": B}, label="gen-b@2", name="b2")],
         "probes": {"b1_snapshot": {"probe": "op_result", "name": "b1", "field": "state_snapshot"},
                    "b1_before": {"probe": "op_result", "name": "b1", "field": "before_state"},
                    "b1_after": {"probe": "op_result", "name": "b1", "field": "after_state"},
                    "b1_mentions": {"probe": "op_mentions", "name": "b1", "tokens": ["v3", "memory:k", "memory:k@2", "dawn", "noon"]},
                    "b2_before": {"probe": "op_result", "name": "b2", "field": "before_state"},
                    "b2_after": {"probe": "op_result", "name": "b2", "field": "after_state"},
                    "a_back": {"probe": "op_result", "name": "a_back", "field": "committed"},
                    "a_back_refusal": {"probe": "op_result", "name": "a_back", "field": "refusal"},
                    "owner_history": {"probe": "history", "ref": "memory:k"},
                    "other_history": {"probe": "history", "ref": "memory:k", "as": B},
                    "head": {"probe": "canonical_head", "ref": "memory:k"}},
         "expect": {"b1_snapshot": EQ("v0"), "b1_before": EQ("v0"), "b1_after": EQ("v1"), "b1_mentions": EQ([]),
                    "b2_before": EQ("v1"), "b2_after": EQ("v2"), "a_back": EQ(False), "a_back_refusal": EQ("target_unavailable"),
                    "owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []}),
                    "other_history": EQ({"current": "gen-b@2", "state_version": 2, "tombstoned": False, "events": FOUR + FOUR}),
                    "head": EQ("gen-b@2")}},
    ],
}

# ------------------------------------------------------------- 2. deleted-lineage-generations-and-restart-v1
F, FA = "Quillon ferry schedule", "departure"
FQ = f"{F} {FA}"
FT = lambda v: f"{F} {FA} is {v}"  # noqa: E731
def seed_two():
    return [rem("memory:f", FT("dawn"), P(F, FA, "dawn"), require_committed=True),
            cor("memory:f", FT("noon"), require_committed=True)]
R2 = {
    "replay_id": "deleted-lineage-generations-and-restart-v2",
    "title": "A governed deletion withholds its whole generation; re-creation is a fresh, isolated generation; deleted versions are as-of barriers",
    "contract_sources": [doc_hash("docs/774-776-lineage-integration-contract.md"), doc_hash("docs/774-strict-successor-target-policy.md"),
                         doc_hash("docs/786-cross-scope-write-authority.md")],
    "invariants": [
        {"id": "L1", "statement": "After a governed deletion no version of the deleted generation is admitted to current or historical recall, nor by logical reference, and the owner's history reads tombstoned with no events, live and after restart.",
         "falsified_by": "any deleted version admitted or any event served"},
        {"id": "L2", "statement": "The owner's re-creation is visible only as its own generation: old versions are withheld from recall, history and write_semantics. (The probe that a pruned version's content remains physically present is implementation evidence of the pruning/permanent-deletion distinction, docs/786 table, not a clause of the cited lineage contract.)",
         "falsified_by": "an old version or its text surfacing"},
        {"id": "L3", "statement": "Another project's re-creation is isolated both ways: the former owner reads nothing of it and cannot write, correct, delete or dispute it; the new generation reads nothing of the former.",
         "falsified_by": "any cross-generation read or an admitted former-owner write"},
        {"id": "L4", "statement": "Every deleted version is an as-of barrier for every reader, and a live generation resolves only for its owner, only from its own start.",
         "falsified_by": "version_in_effect resolving a deleted version, or resolving the live generation for a non-owner"},
        {"id": "L5", "statement": "A governed deletion of one superseded version withholds only that version; a deleted head or lineage member cannot be deleted again (already_deleted), so a recorded generation is never rewritten or shrunk, live and after restart.",
         "falsified_by": "the deleted version admitted, a sibling version withheld, or a re-deletion committed or a former version resurfacing after restart"},
        {"id": "L6", "statement": "A permanent deletion removes every version of the lineage from the substrate and no byte of their content reaches a public read; the owner still reads tombstoned.",
         "falsified_by": "a surviving fact, a surviving byte of content, or a non-tombstoned owner view"},
    ],
    "cases": [
        {"id": "L1-deletion-withholds-live", "invariants": ["L1"],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True}],
         "probes": {"current": {"probe": "recall_admitted", "query": FQ},
                    "historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "by_ref_unknown": {"probe": "recall_same_as_unknown", "query": FQ, "ref": "memory:f"},
                    "owner_history": {"probe": "history", "ref": "memory:f"},
                    "mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]}},
         "expect": {"current": EQ([]), "historical": EQ([]), "by_ref_unknown": EQ(True), "mentions": EQ([]),
                    "owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []})}},
        {"id": "L1-deletion-withholds-after-restart", "invariants": ["L1"],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True}, {"op": "reopen"}],
         "probes": {"current": {"probe": "recall_admitted", "query": FQ},
                    "historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "by_ref_unknown": {"probe": "recall_same_as_unknown", "query": FQ, "ref": "memory:f"},
                    "owner_history": {"probe": "history", "ref": "memory:f"}},
         "expect": {"current": EQ([]), "historical": EQ([]), "by_ref_unknown": EQ(True),
                    "owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []})}},
        {"id": "L2-owner-recreation", "invariants": ["L2"],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True},
                                rem("memory:f", FT("dusk"), P(F, FA, "dusk"), label="gen2", require_committed=True), {"op": "reopen"}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:f"},
                    "historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]},
                    "old_semantics": {"probe": "write_semantics_present", "fact": "memory:f"},
                    "new_semantics": {"probe": "write_semantics_present", "fact": "gen2"},
                    "old_exists": {"probe": "fact_exists", "fact": "memory:f"}},
         "expect": {"owner_history": EQ({"current": "gen2", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "historical": EQ(["gen2"]), "mentions": EQ([]), "old_semantics": EQ(False), "new_semantics": EQ(True),
                    "old_exists": EQ(True)}},
        {"id": "L3-other-project-recreation-is-isolated", "invariants": ["L3"],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True},
                                rem("memory:f", FT("dusk"), P(F, FA, "dusk"), **{"as": B}, label="gen-b", require_committed=True),
                                {"op": "reopen"},
                                rem("memory:f", FT("midnight"), P(F, FA, "midnight"), name="a_rem"),
                                cor("memory:f", FT("midnight"), name="a_cor"),
                                {"op": "forget", "ref": "memory:f", "name": "a_del"},
                                {"op": "dispute", "ref": "memory:f", "name": "a_disp"}],
         "probes": {"owner_historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "owner_mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["gen-b", "dusk"]},
                    "owner_history": {"probe": "history", "ref": "memory:f"},
                    "other_mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "as": B, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]},
                    "other_history": {"probe": "history", "ref": "memory:f", "as": B},
                    "a_rem": {"probe": "op_result", "name": "a_rem", "field": "committed"},
                    "a_rem_refusal": {"probe": "op_result", "name": "a_rem", "field": "refusal"},
                    "a_rem_after": {"probe": "op_result", "name": "a_rem", "field": "after_state"},
                    "a_cor": {"probe": "op_result", "name": "a_cor", "field": "committed"},
                    "a_cor_refusal": {"probe": "op_result", "name": "a_cor", "field": "refusal"},
                    "a_del": {"probe": "op_result", "name": "a_del", "field": "committed"},
                    "a_del_refusal": {"probe": "op_result", "name": "a_del", "field": "refusal"},
                    "a_disp": {"probe": "op_result", "name": "a_disp", "field": "committed"},
                    "a_disp_refusal": {"probe": "op_result", "name": "a_disp", "field": "refusal"},
                    "a_mentions": {"probe": "op_mentions", "name": "a_rem", "tokens": ["gen-b", "dusk", "v1"]},
                    "head": {"probe": "canonical_head", "ref": "memory:f"}},
         "expect": {"owner_historical": EQ([]), "owner_mentions": EQ([]),
                    "owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []}),
                    "other_mentions": EQ([]), "other_history": EQ({"current": "gen-b", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "a_rem": EQ(False), "a_rem_refusal": EQ("target_unavailable"), "a_rem_after": EQ("v0"),
                    "a_cor": EQ(False), "a_cor_refusal": EQ("fact_not_found"), "a_del": EQ(False), "a_del_refusal": EQ("fact_not_found"),
                    "a_disp": EQ(False), "a_disp_refusal": EQ("fact_not_found"), "a_mentions": EQ([]), "head": EQ("gen-b")}},
        {"id": "L5b-a-deleted-head-or-version-cannot-be-deleted-again", "invariants": ["L5", "L1"],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True},
                                {"op": "delete_version", "ref": "memory:f", "fact": "memory:f@2", "name": "again_head"},
                                {"op": "delete_version", "ref": "memory:f", "fact": "memory:f", "name": "again_member"},
                                {"op": "reopen"}],
         "probes": {"again_head": {"probe": "op_result", "name": "again_head", "field": "committed"},
                    "again_head_refusal": {"probe": "op_result", "name": "again_head", "field": "refusal"},
                    "again_member": {"probe": "op_result", "name": "again_member", "field": "committed"},
                    "again_member_refusal": {"probe": "op_result", "name": "again_member", "field": "refusal"},
                    "historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "old_semantics": {"probe": "write_semantics_present", "fact": "memory:f"},
                    "at_v1": {"probe": "version_in_effect", "ref": "memory:f", "at": "memory:f"},
                    "owner_history": {"probe": "history", "ref": "memory:f"}},
         "expect": {"again_head": EQ(False), "again_head_refusal": EQ("already_deleted"), "again_member": EQ(False),
                    "again_member_refusal": EQ("already_deleted"), "historical": EQ([]), "old_semantics": EQ(False), "at_v1": EQ(None),
                    "owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []})}},
        {"id": "L4-three-generations-as-of-barriers", "invariants": ["L4", "L3"],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True},
                                rem("memory:f", FT("dusk"), P(F, FA, "dusk"), **{"as": B}, label="gen-b", require_committed=True),
                                {"op": "forget", "ref": "memory:f", "as": B, "require_committed": True},
                                rem("memory:f", FT("midnight"), P(F, FA, "midnight"), label="gen3", require_committed=True),
                                {"op": "reopen"},
                                rem("memory:f", FT("twilight"), P(F, FA, "twilight"), **{"as": B}, name="b_back")],
         "probes": {"owner_at_gen3": {"probe": "version_in_effect", "ref": "memory:f", "at": "gen3"},
                    "other_at_gen3": {"probe": "version_in_effect", "ref": "memory:f", "at": "gen3", "as": B},
                    "owner_at_v1": {"probe": "version_in_effect", "ref": "memory:f", "at": "memory:f"},
                    "owner_at_v2": {"probe": "version_in_effect", "ref": "memory:f", "at": "memory:f@2"},
                    "owner_at_genb": {"probe": "version_in_effect", "ref": "memory:f", "at": "gen-b"},
                    "other_at_genb": {"probe": "version_in_effect", "ref": "memory:f", "at": "gen-b", "as": B},
                    "other_at_v2": {"probe": "version_in_effect", "ref": "memory:f", "at": "memory:f@2", "as": B},
                    "head": {"probe": "canonical_head", "ref": "memory:f"},
                    "b_back": {"probe": "op_result", "name": "b_back", "field": "committed"},
                    "other_history": {"probe": "history", "ref": "memory:f", "as": B}},
         "expect": {"owner_at_gen3": EQ("gen3"), "other_at_gen3": EQ(None), "owner_at_v1": EQ(None), "owner_at_v2": EQ(None),
                    "owner_at_genb": EQ(None), "other_at_genb": EQ(None), "other_at_v2": EQ(None), "head": EQ("gen3"),
                    "b_back": EQ(False), "other_history": EQ({"current": None, "state_version": 2, "tombstoned": True, "events": []})}},
        {"id": "L5-partial-deletion-withholds-only-that-version", "invariants": ["L5"],
         "steps": seed_two() + [cor("memory:f", FT("dusk"), require_committed=True),
                                {"op": "delete_version", "ref": "memory:f", "fact": "memory:f@2", "name": "d1"}],
         "probes": {"d1": {"probe": "op_result", "name": "d1", "field": "committed"},
                    "deleted_mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f@2", "noon"]},
                    "kept_mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@3"]},
                    "head": {"probe": "canonical_head", "ref": "memory:f"}, "current": {"probe": "recall_admitted", "query": FQ}},
         "expect": {"d1": EQ(True), "deleted_mentions": EQ([]), "kept_mentions": EQ(["memory:f", "memory:f@3"]),
                    "head": EQ("memory:f@3"), "current": EQ(["memory:f@3"])}},
        {"id": "L6-permanent-deletion-erases", "invariants": ["L6"],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "permanent": True, "name": "p1"}, {"op": "reopen"}],
         "probes": {"p1": {"probe": "op_result", "name": "p1", "field": "committed"},
                    "v1_exists": {"probe": "fact_exists", "fact": "memory:f"}, "v2_exists": {"probe": "fact_exists", "fact": "memory:f@2"},
                    "owner_history": {"probe": "history", "ref": "memory:f"},
                    "mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]},
                    "other_unknown": {"probe": "history_same_as_unknown", "ref": "memory:f", "as": B},
                    "old_semantics": {"probe": "write_semantics_present", "fact": "memory:f"}},
         "expect": {"p1": EQ(True), "v1_exists": EQ(False), "v2_exists": EQ(False), "mentions": EQ([]), "other_unknown": EQ(True),
                    "old_semantics": EQ(False), "owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []})}},
    ],
}

# ------------------------------------------------------------- 3. public-tombstone-redaction-and-observer-separation-v1
O, OA = "Tessaly orchard harvest", "window"
OQ = f"{O} {OA}"
OT = lambda v: f"{O} {OA} is {v}"  # noqa: E731
def seed_o():
    return [rem("memory:t", OT("early"), P(O, OA, "early"), require_committed=True),
            cor("memory:t", OT("late"), require_committed=True)]
R3 = {
    "replay_id": "public-tombstone-redaction-and-observer-separation-v2",
    "title": "The owner of a deleted memory reads only its tombstone; every other observer reads nothing; views are stable under other scopes and restart",
    "contract_sources": [doc_hash("docs/777-public-contract-1-7-successor-qualification.md"), doc_hash("docs/44-public-api-contract.md"),
                         doc_hash("docs/786-cross-scope-write-authority.md"),
                         doc_hash("docs/plan-776-777-772-exact-head-qualification.md")],
    "invariants": [
        {"id": "R1", "statement": "The owner of a governed-deleted memory reads tombstoned, no current fact, no events, no rejected values, the version its deletion recorded, and no identifier or text of the deleted generation, live and after restart.",
         "falsified_by": "any identifier, text, event or rejected value, or a different version"},
        {"id": "R2", "statement": "Another project reads the deleted memory byte-identically (ids and timestamps folded) to an id nobody wrote: history, a value probe, recall by logical reference, and historical recall, live and after restart.",
         "falsified_by": "any difference from the unknown-id result"},
        {"id": "R3", "statement": "The owner's deleted view does not change when another project re-creates, corrects and deletes the same id.",
         "falsified_by": "any field of the owner's view changing"},
        {"id": "R4", "statement": "A memory derived from a deleted fact is withheld from public recall while a live derivation keeps its provenance.",
         "falsified_by": "the derived-from-deleted memory or the deleted fact surfacing, or the live derivation lost"},
        {"id": "R5", "statement": "A re-created generation's public history carries only its own events; another scope's refused attempt leaves no trace in it.",
         "falsified_by": "an event from the former generation or from a refused attempt"},
        {"id": "R6", "statement": "No receipt on a governed-deleted id -- committed, refused or policy-parked, from any writer -- and no history of a new generation carries the former generation's version count.",
         "falsified_by": "a before_state, after_state, snapshot or history version continuing the former count"},
    ],
    "cases": [
        {"id": "R1-owner-tombstone-live", "invariants": ["R1"],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:t"},
                    "owner_probe": {"probe": "history", "ref": "memory:t", "fact_text": OT("early")},
                    "mentions": {"probe": "recall_mentions", "query": OQ, "historical": True, "tokens": ["memory:t", "memory:t@2", "early", "late"]}},
         "expect": {"owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []}),
                    "owner_probe": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": [], "rejected_values": 0}),
                    "mentions": EQ([])}},
        {"id": "R1-owner-tombstone-after-restart", "invariants": ["R1"],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True}, {"op": "reopen"}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:t"},
                    "mentions": {"probe": "recall_mentions", "query": OQ, "historical": True, "tokens": ["memory:t", "memory:t@2", "early", "late"]}},
         "expect": {"owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []}), "mentions": EQ([])}},
        {"id": "R2-other-reads-unknown-live", "invariants": ["R2"],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True}],
         "probes": {"history": {"probe": "history_same_as_unknown", "ref": "memory:t", "as": B},
                    "value_probe": {"probe": "history_same_as_unknown", "ref": "memory:t", "fact_text": OT("early"), "as": B},
                    "by_ref": {"probe": "recall_same_as_unknown", "query": OQ, "ref": "memory:t", "as": B},
                    "historical": {"probe": "recall_admitted", "query": OQ, "historical": True, "as": B}},
         "expect": {"history": EQ(True), "value_probe": EQ(True), "by_ref": EQ(True), "historical": EQ([])}},
        {"id": "R2-other-reads-unknown-after-restart", "invariants": ["R2"],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True}, {"op": "reopen"}],
         "probes": {"history": {"probe": "history_same_as_unknown", "ref": "memory:t", "as": B},
                    "value_probe": {"probe": "history_same_as_unknown", "ref": "memory:t", "fact_text": OT("early"), "as": B},
                    "by_ref": {"probe": "recall_same_as_unknown", "query": OQ, "ref": "memory:t", "as": B}},
         "expect": {"history": EQ(True), "value_probe": EQ(True), "by_ref": EQ(True)}},
        {"id": "R3-owner-view-stable-under-other-scope", "invariants": ["R3", "R6"],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True},
                              rem("memory:t", OT("mid"), P(O, OA, "mid"), **{"as": B}, label="gen-b", name="b1", require_committed=True),
                              cor("memory:t", OT("very late"), **{"as": B}, label="gen-b@2", name="b2", require_committed=True),
                              {"op": "reopen"},
                              {"op": "forget", "ref": "memory:t", "as": B, "name": "b3", "require_committed": True}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:t"},
                    "owner_mentions": {"probe": "recall_mentions", "query": OQ, "historical": True, "tokens": ["gen-b", "gen-b@2", "mid", "very late"]},
                    "other_history": {"probe": "history", "ref": "memory:t", "as": B},
                    "b1_before": {"probe": "op_result", "name": "b1", "field": "before_state"},
                    "b1_after": {"probe": "op_result", "name": "b1", "field": "after_state"},
                    "b2_after": {"probe": "op_result", "name": "b2", "field": "after_state"}},
         "expect": {"owner_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []}), "owner_mentions": EQ([]),
                    "other_history": EQ({"current": None, "state_version": 3, "tombstoned": True, "events": []}),
                    "b1_before": EQ("v0"), "b1_after": EQ("v1"), "b2_after": EQ("v2")}},
        {"id": "R4-derived-from-deleted-withheld-live-derivation-kept", "invariants": ["R4"],
         "steps": [rem("memory:t", OT("early"), P(O, OA, "early"), require_committed=True),
                   rem("memory:d", f"Digest: {O} {OA} used to be early", evidence_refs=["memory:t"], label="digest", require_committed=True),
                   rem("memory:l", f"{O} steward is Team Larch", P(O, "steward", "Team Larch"), label="live", require_committed=True),
                   rem("memory:ld", f"Digest: {O} steward Team Larch", evidence_refs=["live"], label="live-digest", require_committed=True),
                   {"op": "forget", "ref": "memory:t", "require_committed": True}],
         "probes": {"withheld": {"probe": "recall_mentions", "query": f"{O} {OA} steward Team Larch digest early", "historical": True,
                                 "tokens": ["digest", "memory:t", "early"]},
                    "kept": {"probe": "recall_mentions", "query": f"{O} {OA} steward Team Larch digest early", "historical": True,
                             "tokens": ["live", "live-digest"]}},
         "expect": {"withheld": EQ([]), "kept": EQ(["live", "live-digest"])}},
        {"id": "R6b-refused-proposals-on-the-tombstoned-id-carry-no-former-count", "invariants": ["R6"],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True},
                              rem("memory:t", OT("mid"), **{"as": B}, overrides={"risk_class": "medium"}, name="parked"),
                              rem("memory:t", OT("mid"), P(O, OA, "mid"), **{"as": B}, label="gen-b", require_committed=True),
                              rem("memory:t", OT("late"), name="a_back"),
                              {"op": "dispute", "ref": "memory:t", "fact": "memory:t@2", "name": "a_disp"}],
         "probes": {"parked_after": {"probe": "op_result", "name": "parked", "field": "after_state"},
                    "parked_mentions": {"probe": "op_mentions", "name": "parked", "tokens": ["v3", "memory:t", "memory:t@2", "early", "late"]},
                    "a_back_mentions": {"probe": "op_mentions", "name": "a_back", "tokens": ["gen-b", "mid", "v1"]},
                    "a_disp": {"probe": "op_result", "name": "a_disp", "field": "committed"},
                    "a_disp_mentions": {"probe": "op_mentions", "name": "a_disp", "tokens": ["gen-b", "mid", "v1"]},
                    "other_history": {"probe": "history", "ref": "memory:t", "as": B}},
         "expect": {"parked_after": EQ("v0"), "parked_mentions": EQ([]), "a_back_mentions": EQ([]), "a_disp": EQ(False),
                    "a_disp_mentions": EQ([]),
                    "other_history": EQ({"current": "gen-b", "state_version": 1, "tombstoned": False, "events": PARKED_THEN_FOUR})}},
        {"id": "R5-recreated-history-only-own-events", "invariants": ["R5", "R6"],
         "steps": [rem("memory:t", OT("early"), P(O, OA, "early"), require_committed=True),
                   {"op": "forget", "ref": "memory:t", "require_committed": True},
                   rem("memory:t", OT("mid"), P(O, OA, "mid"), **{"as": B}, label="gen-b", name="b1", require_committed=True),
                   rem("memory:t", OT("late"), P(O, OA, "late"), name="a_back"),
                   {"op": "reopen"}],
         "probes": {"other_history": {"probe": "history", "ref": "memory:t", "as": B},
                    "a_back": {"probe": "op_result", "name": "a_back", "field": "committed"},
                    "b1_snapshot": {"probe": "op_result", "name": "b1", "field": "state_snapshot"},
                    "b1_before": {"probe": "op_result", "name": "b1", "field": "before_state"},
                    "b1_after": {"probe": "op_result", "name": "b1", "field": "after_state"}},
         "expect": {"other_history": EQ({"current": "gen-b", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "a_back": EQ(False), "b1_snapshot": EQ("v0"), "b1_before": EQ("v0"), "b1_after": EQ("v1")}},
    ],
}

for fixture in (R1, R2, R3):
    doc = {"replay_id": fixture["replay_id"], "fixture_version": 1, **COMMON, "title": fixture["title"],
           "contract_sources": fixture["contract_sources"], "invariants": fixture["invariants"], "cases": fixture["cases"]}
    ids = [c["id"] for c in doc["cases"]]
    assert len(ids) == len(set(ids)), ids
    covered = {i for c in doc["cases"] for i in c["invariants"]}
    assert covered == {i["id"] for i in doc["invariants"]}, (fixture["replay_id"], covered)
    (OUT / f"{fixture['replay_id']}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(fixture["replay_id"], len(doc["cases"]), "cases")
