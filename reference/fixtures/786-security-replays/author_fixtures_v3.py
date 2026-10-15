"""Author the three #786 security replay fixtures of generation -v3 (``786-security-replay-dsl/2``).

The -v3 generation supersedes -v2 after the independent invariant-by-invariant review
(``reports/validation/805-at-head/independent-replay-review-v2.md``) and the owner's
direction on PR #805. The -v1 and -v2 fixtures and ``author_fixtures.py`` are byte-frozen;
this script writes only ``*-v3.json``.

What changes against -v2, finding by finding:

* finding 1: ``contract_sources`` are hashed at ``base_commit``, a revision whose docs/44 and
  docs/786 carry the closed-generation clauses (``already_deleted``, generation-relative
  versions, "Scope is privileged host input") that W7c, W8b, L5b and W4 expect;
* finding 2: W4/W4b state that a complete-scope override is admitted because ``overrides``
  is privileged host input, not because the facade authenticates anyone;
* finding 7: every live-generation history is also scanned as a whole payload for the
  other generation's identifiers and text (``history_mentions``);
* the W7c/L3 rows and finding 9 (former-owner observables had no no-re-creation control):
  control cases without a re-creation pin the same tokens the re-creation cases pin
  (W7c-control, L3-control);
* finding 8: R3 gives the two generations different lengths (A deletes at v3, B at v2);
* finding 10: L5 restarts and re-probes;
* finding 11: W4 pins the ``ValueError`` message, so a target-dependent message would fail;
* finding 13: the L family lists docs/44, docs/plan-776-777-772 and docs/28 as sources;
* finding 6: L6 claims only what it probes (canonical facts gone, no public read serves
  the content, the derived-store reconciliation reports complete) and names what it does
  not claim;
* findings 4/5 (not derivable sub-expectations): ``k2_owner_recall`` (W4b), ``old_exists``
  (L2) and the event list of R6b are recorded as implementation evidence, not expected;
  L5b checks that re-deletion attempts leave the recorded tombstone unchanged
  (``snapshot_tombstone`` / ``tombstone_unchanged``) instead of inferring it from a version;
* traceability: every case carries ``clauses`` naming the source document and the quoted
  clause each expected observable follows from; the author asserts full coverage;
* per-fixture ``development_history``; expectations preregistered and compared to the
  contracts by an independent reviewer before the first execution. That pre-execution review
  (``reports/validation/805-at-head/independent-replay-review-v3-preexecution.md``, no
  expectation WRONG, none BLOCKING) asked for citation precision before execution, applied
  here with no expectation changed: clauses quoted verbatim with marked elisions (its F-1,
  F-3), observables re-cited to the sentence that derives them (F-4), positive controls and
  policy preconditions labelled as such instead of as derivations (F-5, R4 ``kept``), L5b's
  tombstone comparison made blind to nothing (``deleted_at`` compared unfolded; F-2), W8's
  write-back text chosen so no token is a substring of in-scope text (F-6), L2's recorded
  ``old_exists`` left uncited (F-11), and the finding pointer corrected (F-12).

Expectations are written from the contract documents named in each fixture's
``contract_sources``, never from a replay outcome. Vocabulary is new: no entity, value or
phrase of the frozen theatre/vineyard holdouts or of the #644 v7 fixtures is used.
usage: author_fixtures_v3.py <repo_root> <base_commit>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
BASE_COMMIT = sys.argv[2]
OUT = ROOT / "reference/fixtures/786-security-replays"
DSL = "786-security-replay-dsl/2"
T, A, B, NEVER = "tenant:s786", "project:a", "project:b", "memory:never"
FOUR = ["memory.propose", "memory.authorize", "memory.commit", "memory.receipt"]
PARKED_THEN_FOUR = ["memory.propose", "memory.authorize", "memory.receipt"] + FOUR
MALFORMED = "required isolation domains must also be bound isolation domains"
REVIEW_V2 = "reports/validation/805-at-head/independent-replay-review-v2.md"

D44, D786 = "docs/44-public-api-contract.md", "docs/786-cross-scope-write-authority.md"
D774_776, D774 = "docs/774-776-lineage-integration-contract.md", "docs/774-strict-successor-target-policy.md"
D777, DPLAN, D28 = ("docs/777-public-contract-1-7-successor-qualification.md",
                    "docs/plan-776-777-772-exact-head-qualification.md", "docs/28-retention-deletion-and-tombstones.md")


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


def C(source, clause, *observables):
    """One traceability entry: the quoted contract clause these observables follow from."""
    return {"source": source, "clause": clause, "observables": list(observables)}


EQ = lambda v: {"eq": v}  # noqa: E731
NE = lambda v: {"ne": v}  # noqa: E731
TOMB = lambda v: {"current": None, "state_version": v, "tombstoned": True, "events": []}  # noqa: E731
BLANK = {"current": None, "state_version": 0, "tombstoned": False, "events": []}

# ---- clause anchors (quoted from the sources at BASE_COMMIT; the reviewer verifies each) ----
Q_REM = ("`remember` onto a live head outside the writer's scope: `committed: false`, `refusal: \"target_unavailable\"`, "
         "receipt `before_state`/`after_state` `v0`, `state_snapshot` `v0`. Nothing is written, no episode is retained, no version moves.")
Q_CFD = "`correct`, `forget`, `dispute` on such a memory: the bare `fact_not_found` result, byte-identical to the result for an id nobody wrote."
Q_OPEN = ("An id with no live head (never written or governed-deleted) is open to any writer in the tenant: creation and the #776 "
          "re-creation of a deleted id as a fresh generation are unchanged.")
Q_OVR = ("`overrides` re-declares the proposal's scope and is judged under that scope, exactly as a handle opened with it would be; "
         "it does not widen a partial claim (... an override that leaves `required_isolation_domain_refs` outside "
         "`isolation_domain_refs` is a malformed proposal and raises `ValueError` before any target is resolved).")
Q_CONT = ("A write that replaces a live head must also keep the memory within reach of the scope that holds it (scope continuity) "
          "... A project handle therefore cannot capture a tenant-wide or shared memory into its own scope")
Q_HOST = ("Scope is privileged host input. ... the facade does not authenticate who submits them. ... a complete-scope override "
          "(replay case W4) is admitted exactly because the host is trusted to declare it. An exposed multi-user service must "
          "bind authenticated authority to the scope it submits before the facade sees it")
Q_CLOSED = ("A governed-deleted generation is closed. At the fact level (`dispute` of a tombstoned fact by its uuid, a governed "
            "pruning of one of its versions, the adapter's delete of a member of a deleted lineage) the answer is "
            "`already_deleted`; at the facade's logical-reference level (`forget`, permanent `forget`, `correct`, `dispute` by "
            "`target_reference`) the former owner reads the bare `fact_not_found` result, because the reference has no visible "
            "head. Either answer is the same whether or not another scope has since re-created the id, and neither moves or "
            "reads the live generation [...] The one further governed act is the escalation of a reversible pruning to a "
            "permanent deletion by a writer eligible for that generation: it keeps the tombstone's `deleted_at`, recorded "
            "version and lineage, erases the content, and neither reads nor moves a live generation another scope holds.")
Q_V0 = ("Staleness and the `before_state` of a committed deletion or dispute are judged against the version the writer may see: "
        "a memory whose live head lies outside the writer's scope reads `0` to that writer, the same `v0` its proposal's "
        "`state_snapshot` resolves.")
Q_GEN = ("Versions are generation-relative ... After a governed deletion of the head the id reports `0` to any writer, a "
         "re-creation's receipt reads `v0 -> v1`, and the former generation's count never reaches the new one; the owner of the "
         "deleted generation still reads the version its deletion recorded (`tombstoned`, DUR-DEL-001).")
Q_CAND = ("Lifecycle refusals within the caller's own domain (`superseded_not_current`, `tombstoned`, `disputed`, ...) remain "
          "visible candidates with decisions")
Q_786_SUP = ("override with a superset of domains + the owner's project | ... `remember`/`correct` refused by scope continuity "
             "(review F2); `forget`/`dispute` admitted as an eligible reader's")
Q_786_COMPLETE = ("forged **complete** scope via `overrides` | ... commits (documented: `overrides` is the host re-declaring scope "
                  "exactly as `AgentMemory.open(scope=...)` would; ... the facade is not an authentication boundary)")
Q_786_EP = "the `episode` is now added only inside the commit branch, so no refused or parked proposal leaves episodic content"
Q_786_REFUSAL = ("`promotion` reports `target_unavailable` (`WRITE_TARGET_REFUSAL`); every operation that presupposes an existing "
                 "fact reports `fact_not_found`, the same token an id nobody wrote reports.")
Q_786_V0 = "a refused target selects as a blocked action, commits nothing, reports `before_state = after_state = \"v0\"`"
Q_786_F2 = ("`write_target_refusal` now also requires **scope continuity** -- the head's own scope, read as a context, must be "
            "eligible for the scope the new fact would be stored under. A write cannot move a live memory out of its holders' reach")
Q_786_F7 = ("the authorize event of a write-target-refused proposal carries `authority_refs: [\"write-target:refused\"]` "
            "(schema-valid) and the public history projection withholds that correlation")
Q_786_RESTART = "| wrong-scope correction after restart (x2) | commits | refused; `_fact_scope` survives every restart |"
Q_786_SAME = "| same text in unrelated memories of two projects | independent | independent (positive control) |"
Q_786_RECREATE = ("| B re-creates A's **deleted** id | allowed (fresh generation) | unchanged, with isolation proven (A cannot write "
                  "it back while B's generation is live) |")
Q_786_BARRIER = "every deleted generation stays a #774 as-of barrier for everyone"
Q_786_PHYS = "| B `forget` / permanent forget of A's memory | commits, tombstones / physically deletes A's lineage | bare `fact_not_found`; no tombstone |"
Q_786_FC = ("FIXED: `already_deleted` for a tombstoned fact or a direct member of a deleted lineage; only pruning -> permanent "
            "deletion is a further governed act, and that escalation keeps `deleted_at`, `state_version` and the lineage (the "
            "tombstone is reassigned, not mutated, so the durable maps see it)")
Q_786_DERIVED = "a write deriving from a deleted source is withheld (`derived_from_tombstoned_source`)"
Q_786_W4 = ("Replay case W4 (a complete-scope override is admitted) holds only in that privileged-host model and must not be "
            "read as end-user isolation: a user who controls the handle controls the declared scope.")
Q_786_DISCLOSED = "A refused `promotion` tells the writer that the id is unavailable to it."
Q_L1 = ("Deleting an old lineage, then re-creating the same logical memory ... without returning any old deleted version in "
        "explicit historical retrieval")
Q_L2 = "The new generation's head must not traverse into the deleted generation"
Q_L3 = "Tombstoning only one superseded version must not mark its still-live current successor deleted or hide it from current recall"
Q_LX1 = ("Historical predecessor traversal must not cross generation boundaries after memory-ID re-creation. Ordinary stated "
         "state-change history remains reachable when not deleted.")
Q_LX2 = "Deletion of one superseded fact must not hide its live successor."
Q_774 = ("Verify admission and logical-generation membership before resolving a predecessor, including #776 deletion and "
         "re-created memory IDs. Never cross a deleted-lineage boundary")
Q_PLAN_OWNER = ("a reader who could have read the deleted head (same tenant; domain, project and task eligible against the "
                "canonical `_fact_scope`, which survives pruning and permanent deletion) reads `{\"current_fact_uuid\": null, "
                "\"tombstoned\": true, \"events\": [], \"state_version\": <canonical>}` and, with a value probe, "
                "`rejected_values: []`; no deleted-generation identifier, timestamp, event or value is served")
Q_PLAN_OTHER = "a reader outside that scope reads byte-identically to a memory that never existed"
Q_PLAN_RECREATED = "a re-created memory shows only its live generation"
Q_28_PRUNE = "### Prune versus delete [...] Expected: pruned memory remains recoverable under policy; deleted memory follows stronger semantics."
Q_28_PURGE = "| purge | no | intended no recoverable copies | no | required full deletion outcome |"
Q_28_CLAIM = "The system should not claim full deletion where it cannot demonstrate it."
Q_DERIVED = ("Authorized permanent `forget` and every `open` reconcile them against canonical facts and report the outcome in "
             "`semantic_retrieval_posture()[\"derived_reconciliation\"]` ... None of this is an erasure claim about rollback "
             "journals, backups, snapshots or the filesystem.")

COMMON = {
    "dsl_version": DSL,
    "owning_issue": 786,
    "frozen_on": "2026-10-15",
    "status": "supersedes_v2",
    "supersession_reason": ("The -v2 fixtures (frozen at a7a81c45, sources hashed at 560785a8) are superseded, not edited. The "
                            f"independent invariant-by-invariant review ({REVIEW_V2}) found: the hashed contract sources predate "
                            "the closed-generation clauses the cases expect (finding 1); W4/W4b described the facade as a "
                            "host-bound trust boundary without the privileged-host qualification (finding 2); live-generation "
                            "histories were compared by event type and count only (finding 7); former-owner observables had no "
                            "no-re-creation control (finding 5); R3's two deletions recorded the same version (finding 8); L5 "
                            "promised a restart it did not perform (finding 10); W4's ValueError was pinned by type only (finding "
                            "11); the L family omitted the documents that define the owner tombstone view (finding 13); L6's "
                            "wording outran its probes (finding 6); three sub-expectations were not derivable from any cited "
                            "clause (finding 4); former-owner observables had no no-re-creation control (the W7c/L3 rows and "
                            "finding 9). Every -v2 case is carried forward in substance; the 28 -v2 scenarios remain and "
                            "control and restart cases are added."),
    "preexecution_review": {"record": "reports/validation/805-at-head/independent-replay-review-v3-preexecution.md",
                            "reviewed_commit": "679cefbf510a95b847e8897ddf6e66e2a1922c46",
                            "outcome": "no expectation WRONG, none BLOCKING; citation precision applied before first execution "
                                       "(F-1..F-6, F-11, F-12) with no expectation changed; the revised fixtures were "
                                       "re-compared before execution"},
    "base_commit": BASE_COMMIT,
    "independence": ("Expected outcomes were written from the contract documents listed in contract_sources at base_commit, "
                     "clause by clause (`clauses` on every case), before this fixture was first executed by the runner, and "
                     "compared to those clauses by a separate reviewer before that first execution (the record is committed "
                     "beside the evidence). A failing expectation is a finding, never a reason to edit this fixture; a corrected "
                     "expectation requires a superseding -v4 with a recorded reason. Observables listed under "
                     "`implementation_evidence` are recorded, never expected, and never count toward acceptance; observables "
                     "listed under `controls` are positive controls expected for falsifiability (a refuse-everything runtime "
                     "must fail), not derivations of a clause. No frozen holdout phrase or #644 fixture vocabulary is used."),
    "stop_lines": [
        "no fixture edit after first execution; supersede with -v4 and record why",
        "no expectation weakened to obtain PASS",
        "no runtime change motivated by a replay outcome without a preregistered reproducer",
        "a replay verdict is evidence, not successor acceptance; acceptance requires independent review",
        "a complete-scope override proves host re-declaration, never end-user isolation",
    ],
}

# ============================================================ 1. cross-scope-write-authority-denial-v3
K, KA = "Marrow lighthouse keeper", "shift"
KQ = f"{K} {KA}"
KT = lambda v: f"{K} {KA} is {v}"  # noqa: E731
SUPERSET = {"isolation_domain_refs": [T, A, B], "project_ref": A}
COMPLETE = {"scope": A, "project_ref": A, "isolation_domain_refs": [T, A], "required_isolation_domain_refs": [T, A]}
INCONSISTENT = {"isolation_domain_refs": [T, A]}
R1 = {
    "replay_id": "cross-scope-write-authority-denial-v3",
    "title": "A live logical memory is writable only by a writer eligible for its scope; refusals change and disclose nothing",
    "contract_sources": [doc_hash(D786), doc_hash(D44), doc_hash(DPLAN)],
    "development_history": ("v3 authored from the contract sources at base_commit before any execution; the -v2 history "
                            "(W4b `k2_owner_recall` and W5 `owner_candidates` corrections, the W7c runtime finding) is kept in "
                            "the frozen -v2 fixture. Nothing in v3 was executed before the independent comparison."),
    "invariants": [
        {"id": "W1", "statement": "A promotion from another project onto a live head is refused with target_unavailable, reports v0/v0 and a v0 snapshot, and leaves head, version, recall and history of the owner byte-identical.",
         "falsified_by": "a commit, any other refusal token, a non-v0 state, or any owner-side change"},
        {"id": "W2", "statement": "correct, forget, permanent forget and dispute from another project read byte-identically (ids and timestamps folded) to the same call on an id nobody wrote, and change nothing.",
         "falsified_by": "any difference from the unknown-id result, a tombstone, a dispute mark or an invalidated head"},
        {"id": "W3", "statement": "The refusal holds after every restart; the scope binding is durable.",
         "falsified_by": "a commit after a reopen"},
        {"id": "W4", "statement": "An override leaving required isolation domains outside the bound domains is a malformed proposal (ValueError with one fixed message) for any target; an override declaring a superset of domains plus the owner's project cannot replace or correct the head while (documented) it may delete or dispute it as an eligible reader; and a complete re-declaration of the owner's scope commits as the owner would ONLY because `overrides` is privileged host input that the facade does not authenticate (docs/44 'Scope is privileged host input'): this is host re-declaration, never end-user isolation.",
         "falsified_by": "a result instead of ValueError, a ValueError whose message differs by target, a commit of remember/correct under the superset override, or a documented disposition silently changing"},
        {"id": "W5", "statement": "The owner's own remember, correct and dispute stay admitted (a disputed head is recorded as disputed and, as documented, withheld from the owner's own admission while staying a visible candidate), and the same text in an unrelated memory of another project is independent.",
         "falsified_by": "an owner operation refused, or either project's recall admitting the other's fact"},
        {"id": "W6", "statement": "A proposal refused for its target, and one parked by policy review, persist no episode, live and after restart; a committed proposal keeps its episode.",
         "falsified_by": "an episode retrievable after a refusal or review park, or absent after a commit"},
        {"id": "W7", "statement": "A refused remember, correct, forget or dispute attempt by another project, and a former owner's attempts on a re-created id, leave no event and no identifier or text in the live generation's public history payload; the refused project's history of the memory stays blank; the former owner's answers are the same with and without a re-creation.",
         "falsified_by": "any extra event, identifier or text in the live generation's history, a non-blank view for the refused project, or a former-owner answer that differs between the control and the re-creation case"},
        {"id": "W8", "statement": "A governed-deleted id reports 0 to any writer: a re-created generation starts its own counter (snapshot v0, before v0, after v1, history 1), a refused or policy-parked proposal on the tombstoned id reports v0/v0, and the former owner's view keeps the version its deletion recorded and cannot write, dispute or re-delete the id while the new generation is live.",
         "falsified_by": "the former count in any writer's receipt, snapshot or history, a changed former-owner view, or a former-owner act admitted"},
    ],
    "cases": [
        {"id": "W1-remember-over-live-head", "invariants": ["W1"],
         "clauses": [C(D44, Q_REM, "b1_committed", "b1_refusal", "b1_before", "b1_after", "b1_snapshot", "b1_mentions", "head", "owner_history", "owner_recall"),
                     C(DPLAN, Q_PLAN_OTHER, "other_history_unknown"), C(D786, Q_786_SAME, "other_recall")],
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
         "clauses": [C(D44, Q_CFD, "correct_unknown", "forget_unknown", "permanent_unknown", "dispute_unknown", "tombstones", "disputed", "head", "valid", "owner_recall")],
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
         "clauses": [C(D786, Q_786_RESTART, "b1", "b2", "b3", "b4"), C(D44, Q_REM, "b1_refusal", "b1_after", "b1_mentions", "head", "owner_history", "owner_recall"),
                     C(D44, Q_CFD, "b2_refusal", "b3_refusal", "b4_refusal")],
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
         "clauses": [C(D44, Q_OVR, "bad_target", "bad_unknown", "bad_target_message", "bad_unknown_message"),
                     C(D786, Q_786_SUP, "sup_rem_committed", "sup_cor_committed"), C(D786, Q_786_F2, "sup_rem_committed", "sup_cor_committed"),
                     C(D44, Q_CONT, "sup_rem_committed", "sup_cor_committed"),
                     C(D786, Q_786_REFUSAL, "sup_rem_refusal"), C(D786, Q_786_V0, "sup_rem_before"),
                     C(D44, Q_REM, "head", "valid", "owner_recall", "tombstones")],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   rem("memory:k", KT("dusk"), **{"as": B}, overrides=INCONSISTENT, name="bad_target"),
                   rem(NEVER, KT("dusk"), **{"as": B}, overrides=INCONSISTENT, name="bad_unknown"),
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, overrides=SUPERSET, name="sup_rem"),
                   cor("memory:k", KT("dusk"), **{"as": B}, overrides=SUPERSET, name="sup_cor")],
         "probes": {"bad_target": {"probe": "op_result", "name": "bad_target", "field": "raised"},
                    "bad_unknown": {"probe": "op_result", "name": "bad_unknown", "field": "raised"},
                    "bad_target_message": {"probe": "op_raised_message", "name": "bad_target"},
                    "bad_unknown_message": {"probe": "op_raised_message", "name": "bad_unknown"},
                    "sup_rem_committed": {"probe": "op_result", "name": "sup_rem", "field": "committed"},
                    "sup_rem_refusal": {"probe": "op_result", "name": "sup_rem", "field": "refusal"},
                    "sup_rem_before": {"probe": "op_result", "name": "sup_rem", "field": "before_state"},
                    "sup_cor_committed": {"probe": "op_result", "name": "sup_cor", "field": "committed"},
                    "sup_cor_refusal": {"probe": "op_result", "name": "sup_cor", "field": "refusal"},
                    "head": {"probe": "canonical_head", "ref": "memory:k"}, "valid": {"probe": "fact_valid", "fact": "memory:k"},
                    "owner_recall": {"probe": "recall_admitted", "query": KQ}, "tombstones": {"probe": "tombstoned_ids"}},
         "expect": {"bad_target": EQ("ValueError"), "bad_unknown": EQ("ValueError"), "bad_target_message": EQ(MALFORMED),
                    "bad_unknown_message": EQ(MALFORMED), "sup_rem_committed": EQ(False),
                    "sup_rem_refusal": EQ("target_unavailable"), "sup_rem_before": EQ("v0"), "sup_cor_committed": EQ(False),
                    "head": EQ("memory:k"), "valid": EQ(True), "owner_recall": EQ(["memory:k"]), "tombstones": EQ([])},
         "record": ["sup_cor_refusal"],
         "implementation_evidence": ["sup_cor_refusal"]},
        {"id": "W4b-documented-dispositions-of-complete-and-superset-declarations", "invariants": ["W4"],
         "clauses": [C(D786, Q_786_SUP, "sup_disp", "sup_forget", "tombstones"),
                     C(D786, Q_786_COMPLETE, "complete", "k2_head"), C(D44, Q_HOST, "complete", "k2_head"), C(D786, Q_786_W4, "complete")],
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
                    "k2_head": EQ("complete")},
         "record": ["k2_owner_recall"],
         "implementation_evidence": ["k2_owner_recall"]},
        {"id": "W5-positive-controls-and-unrelated-same-text", "invariants": ["W5"],
         "clauses": [C(D786, Q_786_SAME, "a1", "a2", "a3", "b1", "other_recall", "other_view_of_k", "owner_view_of_other"),
                     C(D44, Q_CAND, "owner_recall", "owner_candidates", "disputed", "head")],
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
         "clauses": [C(D786, Q_786_EP, "denied_committed", "kept_committed", "episode_denied", "episode_parked", "episode_kept", "head", "parked_head"),
                     C(D44, Q_REM, "denied_refusal", "denied_before")],
         "record": ["parked_committed"],
         "implementation_evidence": ["parked_committed"],
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
                    "kept_committed": EQ(True), "episode_denied": EQ(False),
                    "episode_parked": EQ(False), "episode_kept": EQ(True), "head": EQ("memory:k"), "parked_head": EQ(None)}},
        {"id": "W7-refused-attempt-leaves-no-public-trace", "invariants": ["W7"],
         "clauses": [C(D786, Q_786_F7, "b1", "owner_history", "owner_history_mentions", "canonical_version"), C(DPLAN, Q_PLAN_OTHER, "other_history_unknown")],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, name="b1"),
                   cor("memory:k", KT("noon"), require_committed=True)],
         "probes": {"b1": {"probe": "op_result", "name": "b1", "field": "committed"},
                    "owner_history": {"probe": "history", "ref": "memory:k"},
                    "owner_history_mentions": {"probe": "history_mentions", "ref": "memory:k", "tokens": ["dusk", B]},
                    "other_history_unknown": {"probe": "history_same_as_unknown", "ref": "memory:k", "as": B},
                    "canonical_version": {"probe": "canonical_version", "ref": "memory:k"}},
         "expect": {"b1": EQ(False), "other_history_unknown": EQ(True), "canonical_version": EQ(2), "owner_history_mentions": EQ([]),
                    "owner_history": EQ({"current": "memory:k@2", "state_version": 2, "tombstoned": False, "events": FOUR + FOUR})}},
        {"id": "W7b-refused-dispute-and-forget-attempts-leave-no-public-trace", "invariants": ["W7"],
         "clauses": [C(D786, Q_786_F7, "bd", "bf", "bdf", "owner_history", "owner_history_mentions"), C(DPLAN, Q_PLAN_OTHER, "other_history_unknown")],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   {"op": "dispute", "ref": "memory:k", "as": B, "name": "bd"},
                   {"op": "forget", "ref": "memory:k", "as": B, "name": "bf"},
                   {"op": "dispute", "ref": "memory:k", "fact": "memory:k", "as": B, "name": "bdf"}],
         "probes": {"bd": {"probe": "op_result", "name": "bd", "field": "committed"},
                    "bf": {"probe": "op_result", "name": "bf", "field": "committed"},
                    "bdf": {"probe": "op_result", "name": "bdf", "field": "committed"},
                    "owner_history": {"probe": "history", "ref": "memory:k"},
                    "owner_history_mentions": {"probe": "history_mentions", "ref": "memory:k", "tokens": [B, "dispute", "forget"]},
                    "other_history_unknown": {"probe": "history_same_as_unknown", "ref": "memory:k", "as": B}},
         "expect": {"bd": EQ(False), "bf": EQ(False), "bdf": EQ(False), "other_history_unknown": EQ(True), "owner_history_mentions": EQ([]),
                    "owner_history": EQ({"current": "memory:k", "state_version": 1, "tombstoned": False, "events": FOUR})}},
        {"id": "W7c-former-owner-attempts-leave-no-trace-in-the-new-generation", "invariants": ["W7", "W8"],
         "clauses": [C(D44, Q_CLOSED, "a_disp", "a_disp_refusal", "a_del", "a_del_refusal", "a_forget", "a_forget_refusal"),
                     C(D44, Q_REM, "a_rem", "a_rem_refusal"), C(D786, Q_786_RECREATE, "a_rem", "other_recall"),
                     C(D44, Q_V0, "a_disp_mentions"), C(D786, Q_786_F7, "other_history", "other_history_mentions"), C(DPLAN, Q_PLAN_RECREATED, "other_history_mentions")],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   {"op": "forget", "ref": "memory:k", "require_committed": True},
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, label="gen-b", require_committed=True),
                   rem("memory:k", KT("night"), name="a_rem"),
                   {"op": "dispute", "ref": "memory:k", "fact": "memory:k", "name": "a_disp"},
                   {"op": "delete_version", "ref": "memory:k", "fact": "memory:k", "name": "a_del"},
                   {"op": "forget", "ref": "memory:k", "name": "a_forget"}],
         "probes": {"a_rem": {"probe": "op_result", "name": "a_rem", "field": "committed"},
                    "a_rem_refusal": {"probe": "op_result", "name": "a_rem", "field": "refusal"},
                    "a_disp": {"probe": "op_result", "name": "a_disp", "field": "committed"},
                    "a_disp_refusal": {"probe": "op_result", "name": "a_disp", "field": "refusal"},
                    "a_disp_mentions": {"probe": "op_mentions", "name": "a_disp", "tokens": ["gen-b", "dusk", "v1", "v2"]},
                    "a_del": {"probe": "op_result", "name": "a_del", "field": "committed"},
                    "a_del_refusal": {"probe": "op_result", "name": "a_del", "field": "refusal"},
                    "a_forget": {"probe": "op_result", "name": "a_forget", "field": "committed"},
                    "a_forget_refusal": {"probe": "op_result", "name": "a_forget", "field": "refusal"},
                    "other_history": {"probe": "history", "ref": "memory:k", "as": B},
                    "other_history_mentions": {"probe": "history_mentions", "ref": "memory:k", "as": B, "tokens": ["memory:k", "dawn", "night", A]},
                    "other_recall": {"probe": "recall_admitted", "query": KQ, "as": B}},
         "expect": {"a_rem": EQ(False), "a_rem_refusal": EQ("target_unavailable"), "a_disp": EQ(False), "a_disp_refusal": EQ("already_deleted"),
                    "a_disp_mentions": EQ([]), "a_del": EQ(False), "a_del_refusal": EQ("already_deleted"), "a_forget": EQ(False),
                    "a_forget_refusal": EQ("fact_not_found"), "other_history_mentions": EQ([]),
                    "other_history": EQ({"current": "gen-b", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "other_recall": EQ(["gen-b"])}},
        {"id": "W7c-control-former-owner-attempts-without-a-re-creation", "invariants": ["W7", "W8"],
         "clauses": [C(D44, Q_CLOSED, "a_disp", "a_disp_refusal", "a_del", "a_del_refusal", "a_forget", "a_forget_refusal", "a_disp_mentions"),
                     C(D44, Q_GEN, "owner_history")],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   {"op": "forget", "ref": "memory:k", "require_committed": True},
                   {"op": "dispute", "ref": "memory:k", "fact": "memory:k", "name": "a_disp"},
                   {"op": "delete_version", "ref": "memory:k", "fact": "memory:k", "name": "a_del"},
                   {"op": "forget", "ref": "memory:k", "name": "a_forget"}],
         "probes": {"a_disp": {"probe": "op_result", "name": "a_disp", "field": "committed"},
                    "a_disp_refusal": {"probe": "op_result", "name": "a_disp", "field": "refusal"},
                    "a_disp_mentions": {"probe": "op_mentions", "name": "a_disp", "tokens": ["v1", "v2"]},
                    "a_del": {"probe": "op_result", "name": "a_del", "field": "committed"},
                    "a_del_refusal": {"probe": "op_result", "name": "a_del", "field": "refusal"},
                    "a_forget": {"probe": "op_result", "name": "a_forget", "field": "committed"},
                    "a_forget_refusal": {"probe": "op_result", "name": "a_forget", "field": "refusal"},
                    "owner_history": {"probe": "history", "ref": "memory:k"}},
         "expect": {"a_disp": EQ(False), "a_disp_refusal": EQ("already_deleted"), "a_disp_mentions": EQ([]), "a_del": EQ(False),
                    "a_del_refusal": EQ("already_deleted"), "a_forget": EQ(False), "a_forget_refusal": EQ("fact_not_found"),
                    "owner_history": EQ(TOMB(2))}},
        {"id": "W8b-refused-and-parked-proposals-on-a-tombstoned-id-report-v0", "invariants": ["W8"],
         "clauses": [C(D44, Q_GEN, "parked_b_states", "parked_b_after", "parked_a_after", "parked_a_snapshot", "parked_b2_after", "owner_history"),
                     C(DPLAN, Q_PLAN_OTHER, "other_history", "other_history_unknown")],
         "record": ["parked_b"],
         "implementation_evidence": ["parked_b"],
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
                    "other_history_unknown": {"probe": "history_same_as_unknown", "ref": "memory:k", "as": B},
                    "owner_history": {"probe": "history", "ref": "memory:k"}},
         "expect": {"parked_b_states": EQ([]), "parked_b_after": EQ("v0"), "parked_a_after": EQ("v0"),
                    "parked_a_snapshot": EQ("v0"), "parked_b2_after": EQ("v0"), "other_history": EQ(BLANK),
                    "other_history_unknown": EQ(True), "owner_history": EQ(TOMB(3))}},
        {"id": "W8-recreated-generation-starts-its-own-counter", "invariants": ["W8"],
         "clauses": [C(D44, Q_GEN, "b1_snapshot", "b1_before", "b1_after", "b1_mentions", "b2_before", "b2_after", "owner_history", "other_history", "head"),
                     C(D44, Q_REM, "a_back", "a_back_refusal"), C(D786, Q_786_RECREATE, "a_back"),
                     C(DPLAN, Q_PLAN_RECREATED, "other_history_mentions")],
         "steps": [rem("memory:k", KT("dawn"), P(K, KA, "dawn"), require_committed=True),
                   cor("memory:k", KT("noon"), require_committed=True),
                   {"op": "forget", "ref": "memory:k", "name": "a_del", "require_committed": True},
                   rem("memory:k", KT("dusk"), P(K, KA, "dusk"), **{"as": B}, label="gen-b", name="b1"),
                   rem("memory:k", KT("evening"), P(K, KA, "evening"), name="a_back"),
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
                    "other_history_mentions": {"probe": "history_mentions", "ref": "memory:k", "as": B, "tokens": ["memory:k", "memory:k@2", "dawn", "noon", "evening", "v3", A]},
                    "head": {"probe": "canonical_head", "ref": "memory:k"}},
         "expect": {"b1_snapshot": EQ("v0"), "b1_before": EQ("v0"), "b1_after": EQ("v1"), "b1_mentions": EQ([]),
                    "b2_before": EQ("v1"), "b2_after": EQ("v2"), "a_back": EQ(False), "a_back_refusal": EQ("target_unavailable"),
                    "owner_history": EQ(TOMB(3)), "other_history_mentions": EQ([]),
                    "other_history": EQ({"current": "gen-b@2", "state_version": 2, "tombstoned": False, "events": FOUR + FOUR}),
                    "head": EQ("gen-b@2")}},
    ],
}

# ============================================================ 2. deleted-lineage-generations-and-restart-v3
F, FA = "Quillon ferry schedule", "departure"
FQ = f"{F} {FA}"
FT = lambda v: f"{F} {FA} is {v}"  # noqa: E731


def seed_two():
    return [rem("memory:f", FT("dawn"), P(F, FA, "dawn"), require_committed=True),
            cor("memory:f", FT("noon"), require_committed=True)]


R2 = {
    "replay_id": "deleted-lineage-generations-and-restart-v3",
    "title": "A governed deletion withholds its whole generation; re-creation is a fresh, isolated generation; deleted versions are as-of barriers",
    "contract_sources": [doc_hash(D774_776), doc_hash(D774), doc_hash(D786), doc_hash(D44), doc_hash(DPLAN), doc_hash(D28)],
    "development_history": ("v3 authored from the contract sources at base_commit before any execution. Changes against -v2: "
                            "docs/44, docs/plan-776-777-772 and docs/28 added as sources (they define the owner tombstone view "
                            "and the prune/delete distinction the cases rely on); L5 restarts; L5b checks the recorded tombstone "
                            "before and after the re-deletion attempts; L3 gains a no-re-creation control and a dispute by fact "
                            "uuid; L6 is renamed and claims only what it probes; L2's `old_exists` is implementation evidence."),
    "invariants": [
        {"id": "L1", "statement": "After a governed deletion no version of the deleted generation is admitted to current or historical recall, nor by logical reference, and the owner's history reads tombstoned with no events, live and after restart.",
         "falsified_by": "any deleted version admitted or any event served"},
        {"id": "L2", "statement": "The owner's re-creation is visible only as its own generation: old versions are withheld from recall, history (its whole payload) and write_semantics.",
         "falsified_by": "an old version, its identifier or its text surfacing"},
        {"id": "L3", "statement": "Another project's re-creation is isolated both ways: the former owner reads nothing of it and cannot write, correct, delete or dispute it (answering exactly as it would with no re-creation, except that a remember on an open id is the documented disclosure); the new generation reads nothing of the former.",
         "falsified_by": "any cross-generation read, an admitted former-owner write, or a former-owner answer that differs from the control"},
        {"id": "L4", "statement": "Every deleted version is an as-of barrier for every reader, and a live generation resolves only for its owner, only from its own start.",
         "falsified_by": "version_in_effect resolving a deleted version, or resolving the live generation for a non-owner"},
        {"id": "L5", "statement": "A governed deletion of one superseded version withholds only that version, live and after restart; a deleted head or lineage member cannot be deleted again (already_deleted) and the attempt leaves the recorded tombstone (deleted_at, version, lineage) unchanged, live and after restart.",
         "falsified_by": "the deleted version admitted, a sibling version withheld, a re-deletion committed, a changed tombstone record, or a former version resurfacing after restart"},
        {"id": "L6", "statement": "After a permanent deletion the canonical substrate holds no fact of the lineage, no public read of any scope serves an identifier or text of it, the derived-store reconciliation reports complete, and the owner still reads tombstoned. This is a claim about canonical facts and public reads only, not about rollback journals, WAL frames, backups, snapshots or the filesystem (docs/28: no full-deletion claim where it cannot be demonstrated).",
         "falsified_by": "a surviving canonical fact, an identifier or text in any public read, an incomplete reconciliation, or a non-tombstoned owner view"},
    ],
    "cases": [
        {"id": "L1-deletion-withholds-live", "invariants": ["L1"],
         "clauses": [C(D774_776, Q_L1, "current", "historical", "mentions"), C(DPLAN, Q_PLAN_OWNER, "by_ref_unknown", "owner_history"),
                     C(D44, Q_GEN, "owner_history")],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True}],
         "probes": {"current": {"probe": "recall_admitted", "query": FQ},
                    "historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "by_ref_unknown": {"probe": "recall_same_as_unknown", "query": FQ, "ref": "memory:f"},
                    "owner_history": {"probe": "history", "ref": "memory:f"},
                    "mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]}},
         "expect": {"current": EQ([]), "historical": EQ([]), "by_ref_unknown": EQ(True), "mentions": EQ([]), "owner_history": EQ(TOMB(3))}},
        {"id": "L1-deletion-withholds-after-restart", "invariants": ["L1"],
         "clauses": [C(D774_776, Q_L1, "current", "historical", "mentions"), C(DPLAN, Q_PLAN_OWNER, "by_ref_unknown", "owner_history"),
                     C(D44, Q_GEN, "owner_history")],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True}, {"op": "reopen"}],
         "probes": {"current": {"probe": "recall_admitted", "query": FQ},
                    "historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "by_ref_unknown": {"probe": "recall_same_as_unknown", "query": FQ, "ref": "memory:f"},
                    "owner_history": {"probe": "history", "ref": "memory:f"},
                    "mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]}},
         "expect": {"current": EQ([]), "historical": EQ([]), "by_ref_unknown": EQ(True), "mentions": EQ([]), "owner_history": EQ(TOMB(3))}},
        {"id": "L2-owner-recreation", "invariants": ["L2"],
         "clauses": [C(D774_776, Q_L1, "historical", "mentions"), C(D774_776, Q_L2, "owner_history", "old_semantics", "new_semantics"),
                     C(DPLAN, Q_PLAN_RECREATED, "owner_history", "owner_history_mentions")],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True},
                                rem("memory:f", FT("dusk"), P(F, FA, "dusk"), label="gen2", require_committed=True), {"op": "reopen"}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:f"},
                    "owner_history_mentions": {"probe": "history_mentions", "ref": "memory:f", "tokens": ["memory:f", "memory:f@2", "dawn", "noon", "v3"]},
                    "historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]},
                    "old_semantics": {"probe": "write_semantics_present", "fact": "memory:f"},
                    "new_semantics": {"probe": "write_semantics_present", "fact": "gen2"},
                    "old_exists": {"probe": "fact_exists", "fact": "memory:f"}},
         "expect": {"owner_history": EQ({"current": "gen2", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "owner_history_mentions": EQ([]), "historical": EQ(["gen2"]), "mentions": EQ([]), "old_semantics": EQ(False),
                    "new_semantics": EQ(True)},
         "record": ["old_exists"],
         "implementation_evidence": ["old_exists"]},
        {"id": "L3-other-project-recreation-is-isolated", "invariants": ["L3"],
         "clauses": [C(D786, Q_786_RECREATE, "owner_historical", "owner_mentions", "other_mentions", "head", "a_rem"),
                     C(DPLAN, Q_PLAN_OWNER, "owner_history"), C(D44, Q_GEN, "owner_history"),
                     C(DPLAN, Q_PLAN_RECREATED, "other_history", "other_history_mentions"),
                     C(D44, Q_REM, "a_rem_refusal", "a_rem_after", "a_mentions"), C(D786, Q_786_DISCLOSED, "a_rem_refusal"),
                     C(D44, Q_CLOSED, "a_cor", "a_cor_refusal", "a_del", "a_del_refusal", "a_disp", "a_disp_refusal", "a_disp_fact", "a_disp_fact_refusal")],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True},
                                rem("memory:f", FT("dusk"), P(F, FA, "dusk"), **{"as": B}, label="gen-b", require_committed=True),
                                {"op": "reopen"},
                                rem("memory:f", FT("midnight"), P(F, FA, "midnight"), name="a_rem"),
                                cor("memory:f", FT("midnight"), name="a_cor"),
                                {"op": "forget", "ref": "memory:f", "name": "a_del"},
                                {"op": "dispute", "ref": "memory:f", "name": "a_disp"},
                                {"op": "dispute", "ref": "memory:f", "fact": "memory:f@2", "name": "a_disp_fact"}],
         "probes": {"owner_historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "owner_mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["gen-b", "dusk"]},
                    "owner_history": {"probe": "history", "ref": "memory:f"},
                    "other_mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "as": B, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]},
                    "other_history": {"probe": "history", "ref": "memory:f", "as": B},
                    "other_history_mentions": {"probe": "history_mentions", "ref": "memory:f", "as": B, "tokens": ["memory:f", "memory:f@2", "dawn", "noon", "midnight", "v3", A]},
                    "a_rem": {"probe": "op_result", "name": "a_rem", "field": "committed"},
                    "a_rem_refusal": {"probe": "op_result", "name": "a_rem", "field": "refusal"},
                    "a_rem_after": {"probe": "op_result", "name": "a_rem", "field": "after_state"},
                    "a_cor": {"probe": "op_result", "name": "a_cor", "field": "committed"},
                    "a_cor_refusal": {"probe": "op_result", "name": "a_cor", "field": "refusal"},
                    "a_del": {"probe": "op_result", "name": "a_del", "field": "committed"},
                    "a_del_refusal": {"probe": "op_result", "name": "a_del", "field": "refusal"},
                    "a_disp": {"probe": "op_result", "name": "a_disp", "field": "committed"},
                    "a_disp_refusal": {"probe": "op_result", "name": "a_disp", "field": "refusal"},
                    "a_disp_fact": {"probe": "op_result", "name": "a_disp_fact", "field": "committed"},
                    "a_disp_fact_refusal": {"probe": "op_result", "name": "a_disp_fact", "field": "refusal"},
                    "a_mentions": {"probe": "op_mentions", "name": "a_rem", "tokens": ["gen-b", "dusk", "v1"]},
                    "head": {"probe": "canonical_head", "ref": "memory:f"}},
         "expect": {"owner_historical": EQ([]), "owner_mentions": EQ([]), "owner_history": EQ(TOMB(3)),
                    "other_mentions": EQ([]), "other_history": EQ({"current": "gen-b", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "other_history_mentions": EQ([]),
                    "a_rem": EQ(False), "a_rem_refusal": EQ("target_unavailable"), "a_rem_after": EQ("v0"),
                    "a_cor": EQ(False), "a_cor_refusal": EQ("fact_not_found"), "a_del": EQ(False), "a_del_refusal": EQ("fact_not_found"),
                    "a_disp": EQ(False), "a_disp_refusal": EQ("fact_not_found"), "a_disp_fact": EQ(False), "a_disp_fact_refusal": EQ("already_deleted"),
                    "a_mentions": EQ([]), "head": EQ("gen-b")}},
        {"id": "L3-control-former-owner-answers-without-a-re-creation", "invariants": ["L3"],
         "clauses": [C(D44, Q_CLOSED, "a_cor", "a_cor_refusal", "a_del", "a_del_refusal", "a_disp", "a_disp_refusal", "a_disp_fact", "a_disp_fact_refusal"),
                     C(DPLAN, Q_PLAN_OWNER, "owner_history"), C(D44, Q_GEN, "owner_history")],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True}, {"op": "reopen"},
                                cor("memory:f", FT("midnight"), name="a_cor"),
                                {"op": "forget", "ref": "memory:f", "name": "a_del"},
                                {"op": "dispute", "ref": "memory:f", "name": "a_disp"},
                                {"op": "dispute", "ref": "memory:f", "fact": "memory:f@2", "name": "a_disp_fact"}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:f"},
                    "a_cor": {"probe": "op_result", "name": "a_cor", "field": "committed"},
                    "a_cor_refusal": {"probe": "op_result", "name": "a_cor", "field": "refusal"},
                    "a_del": {"probe": "op_result", "name": "a_del", "field": "committed"},
                    "a_del_refusal": {"probe": "op_result", "name": "a_del", "field": "refusal"},
                    "a_disp": {"probe": "op_result", "name": "a_disp", "field": "committed"},
                    "a_disp_refusal": {"probe": "op_result", "name": "a_disp", "field": "refusal"},
                    "a_disp_fact": {"probe": "op_result", "name": "a_disp_fact", "field": "committed"},
                    "a_disp_fact_refusal": {"probe": "op_result", "name": "a_disp_fact", "field": "refusal"}},
         "expect": {"owner_history": EQ(TOMB(3)), "a_cor": EQ(False), "a_cor_refusal": EQ("fact_not_found"), "a_del": EQ(False),
                    "a_del_refusal": EQ("fact_not_found"), "a_disp": EQ(False), "a_disp_refusal": EQ("fact_not_found"),
                    "a_disp_fact": EQ(False), "a_disp_fact_refusal": EQ("already_deleted")}},
        {"id": "L5b-a-deleted-head-or-version-cannot-be-deleted-again", "invariants": ["L5", "L1"],
         "clauses": [C(D44, Q_CLOSED, "again_head", "again_head_refusal", "again_member", "again_member_refusal"),
                     C(D786, Q_786_FC, "head_tombstone_unchanged"), C(D44, Q_CLOSED, "head_tombstone_unchanged"),
                     C(D774_776, Q_L1, "historical", "old_semantics"), C(D774, Q_774, "at_v1"),
                     C(DPLAN, Q_PLAN_OWNER, "owner_history"), C(D44, Q_GEN, "owner_history")],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "require_committed": True},
                                {"op": "snapshot_tombstone", "fact": "memory:f@2", "name": "ts_head"},
                                {"op": "snapshot_tombstone", "fact": "memory:f", "name": "ts_member"},
                                {"op": "delete_version", "ref": "memory:f", "fact": "memory:f@2", "name": "again_head"},
                                {"op": "delete_version", "ref": "memory:f", "fact": "memory:f", "name": "again_member"},
                                {"op": "reopen"}],
         "probes": {"again_head": {"probe": "op_result", "name": "again_head", "field": "committed"},
                    "again_head_refusal": {"probe": "op_result", "name": "again_head", "field": "refusal"},
                    "again_member": {"probe": "op_result", "name": "again_member", "field": "committed"},
                    "again_member_refusal": {"probe": "op_result", "name": "again_member", "field": "refusal"},
                    "head_tombstone_unchanged": {"probe": "tombstone_unchanged", "name": "ts_head", "fact": "memory:f@2"},
                    "member_tombstone_record": {"probe": "tombstone_record", "fact": "memory:f"},
                    "head_tombstone": {"probe": "tombstone_record", "fact": "memory:f@2"},
                    "historical": {"probe": "recall_admitted", "query": FQ, "historical": True},
                    "old_semantics": {"probe": "write_semantics_present", "fact": "memory:f"},
                    "at_v1": {"probe": "version_in_effect", "ref": "memory:f", "at": "memory:f"},
                    "owner_history": {"probe": "history", "ref": "memory:f"}},
         "expect": {"again_head": EQ(False), "again_head_refusal": EQ("already_deleted"), "again_member": EQ(False),
                    "again_member_refusal": EQ("already_deleted"), "head_tombstone_unchanged": EQ(True),
                    "historical": EQ([]), "old_semantics": EQ(False), "at_v1": EQ(None), "owner_history": EQ(TOMB(3))},
         "record": ["head_tombstone", "member_tombstone_record"],
         "implementation_evidence": ["head_tombstone", "member_tombstone_record"]},
        {"id": "L4-three-generations-as-of-barriers", "invariants": ["L4", "L3"],
         "clauses": [C(D774, Q_774, "owner_at_gen3", "other_at_gen3", "owner_at_v1", "owner_at_v2", "owner_at_genb", "other_at_genb", "other_at_v2"),
                     C(D774_776, Q_LX1, "owner_at_v1", "owner_at_v2", "head"), C(D786, Q_786_RECREATE, "b_back", "head"), C(D786, Q_786_BARRIER, "owner_at_v1", "owner_at_v2", "other_at_v2"),
                     C(D44, Q_GEN, "other_history"), C(DPLAN, Q_PLAN_OWNER, "other_history")],
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
                    "b_back": EQ(False), "other_history": EQ(TOMB(2))}},
        {"id": "L5-partial-deletion-withholds-only-that-version", "invariants": ["L5"],
         "clauses": [C(D774_776, Q_L3, "d1", "deleted_mentions", "kept_mentions", "head", "current"),
                     C(D774_776, Q_LX1, "kept_mentions"), C(D774_776, Q_LX2, "head", "current")],
         "steps": seed_two() + [cor("memory:f", FT("dusk"), require_committed=True),
                                {"op": "delete_version", "ref": "memory:f", "fact": "memory:f@2", "name": "d1"}],
         "probes": {"d1": {"probe": "op_result", "name": "d1", "field": "committed"},
                    "deleted_mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f@2", "noon"]},
                    "kept_mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@3"]},
                    "head": {"probe": "canonical_head", "ref": "memory:f"}, "current": {"probe": "recall_admitted", "query": FQ}},
         "expect": {"d1": EQ(True), "deleted_mentions": EQ([]), "kept_mentions": EQ(["memory:f", "memory:f@3"]),
                    "head": EQ("memory:f@3"), "current": EQ(["memory:f@3"])}},
        {"id": "L5-partial-deletion-withholds-only-that-version-after-restart", "invariants": ["L5"],
         "clauses": [C(D774_776, Q_L3, "d1", "deleted_mentions_after", "kept_mentions_after", "head_after", "current_after"),
                     C(D774_776, Q_LX1, "kept_mentions_after"), C(D774_776, Q_LX2, "head_after", "current_after")],
         "steps": seed_two() + [cor("memory:f", FT("dusk"), require_committed=True),
                                {"op": "delete_version", "ref": "memory:f", "fact": "memory:f@2", "name": "d1"}, {"op": "reopen"}],
         "probes": {"d1": {"probe": "op_result", "name": "d1", "field": "committed"},
                    "deleted_mentions_after": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f@2", "noon"]},
                    "kept_mentions_after": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@3"]},
                    "head_after": {"probe": "canonical_head", "ref": "memory:f"}, "current_after": {"probe": "recall_admitted", "query": FQ}},
         "expect": {"d1": EQ(True), "deleted_mentions_after": EQ([]), "kept_mentions_after": EQ(["memory:f", "memory:f@3"]),
                    "head_after": EQ("memory:f@3"), "current_after": EQ(["memory:f@3"])}},
        {"id": "L6-permanent-deletion-removes-canonical-facts-and-withholds-every-public-read", "invariants": ["L6"],
         "clauses": [C(D786, Q_786_PHYS, "p1", "v1_exists", "v2_exists"), C(D28, Q_28_PURGE, "v1_exists", "v2_exists"), C(D28, Q_28_PRUNE, "p1"),
                     C(D774_776, Q_L1, "mentions", "old_semantics"),
                     C(DPLAN, Q_PLAN_OTHER, "other_unknown", "other_history_mentions"), C(DPLAN, Q_PLAN_OWNER, "owner_history"), C(D44, Q_GEN, "owner_history"),
                     C(D44, Q_DERIVED, "derived"), C(D28, Q_28_CLAIM, "derived")],
         "steps": seed_two() + [{"op": "forget", "ref": "memory:f", "permanent": True, "name": "p1"}, {"op": "reopen"}],
         "probes": {"p1": {"probe": "op_result", "name": "p1", "field": "committed"},
                    "v1_exists": {"probe": "fact_exists", "fact": "memory:f"}, "v2_exists": {"probe": "fact_exists", "fact": "memory:f@2"},
                    "owner_history": {"probe": "history", "ref": "memory:f"},
                    "mentions": {"probe": "recall_mentions", "query": FQ, "historical": True, "tokens": ["memory:f", "memory:f@2", "dawn", "noon"]},
                    "other_unknown": {"probe": "history_same_as_unknown", "ref": "memory:f", "as": B},
                    "other_history_mentions": {"probe": "history_mentions", "ref": "memory:f", "as": B, "tokens": ["memory:f", "memory:f@2", "dawn", "noon", "v3"]},
                    "old_semantics": {"probe": "write_semantics_present", "fact": "memory:f"},
                    "derived": {"probe": "derived_reconciliation"},
                    "derived_stores_checked": {"probe": "derived_stores_checked"}},
         "expect": {"p1": EQ(True), "v1_exists": EQ(False), "v2_exists": EQ(False), "mentions": EQ([]), "other_unknown": EQ(True),
                    "other_history_mentions": EQ([]), "old_semantics": EQ(False), "owner_history": EQ(TOMB(3)),
                    "derived": EQ({"status": "complete", "pending": []})},
         "record": ["derived_stores_checked"],
         "implementation_evidence": ["derived_stores_checked"]},
    ],
}

# ============================================================ 3. public-tombstone-redaction-and-observer-separation-v3
O, OA = "Tessaly orchard harvest", "window"
OQ = f"{O} {OA}"
OT = lambda v: f"{O} {OA} is {v}"  # noqa: E731


def seed_o():
    return [rem("memory:t", OT("early"), P(O, OA, "early"), require_committed=True),
            cor("memory:t", OT("late"), require_committed=True)]


R3 = {
    "replay_id": "public-tombstone-redaction-and-observer-separation-v3",
    "title": "The owner of a deleted memory reads only its tombstone; every other observer reads nothing; views are stable under other scopes and restart",
    "contract_sources": [doc_hash(D777), doc_hash(D44), doc_hash(D786), doc_hash(DPLAN)],
    "development_history": ("v3 authored from the contract sources at base_commit before any execution. Changes against -v2: "
                            "docs/777 stays listed as the successor-qualification source the family descends from, but no "
                            "expectation cites it (the pre-execution review found its 'out-of-scope indistinguishability' "
                            "wording lives in docs/plan-776-777-772, which the cases cite instead); R1 repeats the value probe after restart; R3 gives A's and B's generations different lengths so the "
                            "two deletions record different versions (A v3, B v2) and pins each owner's own version; R5 and R6b "
                            "scan the whole history payload of the re-created generation; R6b's event list is implementation "
                            "evidence and its public view is pinned without the event list."),
    "invariants": [
        {"id": "R1", "statement": "The owner of a governed-deleted memory reads tombstoned, no current fact, no events, no rejected values, the version its deletion recorded, and no identifier or text of the deleted generation, live and after restart.",
         "falsified_by": "any identifier, text, event or rejected value, or a different version"},
        {"id": "R2", "statement": "Another project reads the deleted memory byte-identically (ids and timestamps folded) to an id nobody wrote: history, a value probe, recall by logical reference, and historical recall, live and after restart.",
         "falsified_by": "any difference from the unknown-id result"},
        {"id": "R3", "statement": "The owner's deleted view does not change when another project re-creates, corrects and deletes the same id, and each deleting scope reads exactly the version its own deletion recorded (the two generations have different lengths, so a view serving the largest or latest deletion would differ).",
         "falsified_by": "any field of the owner's view changing, or either scope reading the other's recorded version"},
        {"id": "R4", "statement": "A memory derived from a deleted fact is withheld from public recall while a live derivation keeps its provenance.",
         "falsified_by": "the derived-from-deleted memory or the deleted fact surfacing, or the live derivation lost"},
        {"id": "R5", "statement": "A re-created generation's public history carries only its own events and nothing of the former generation in any payload; another scope's refused attempt leaves no trace in it.",
         "falsified_by": "an event, identifier or text from the former generation or from a refused attempt"},
        {"id": "R6", "statement": "No receipt on a governed-deleted id -- committed, refused or policy-parked, from any writer -- and no history of a new generation carries the former generation's version count.",
         "falsified_by": "a before_state, after_state, snapshot or history version continuing the former count"},
    ],
    "cases": [
        {"id": "R1-owner-tombstone-live", "invariants": ["R1"],
         "clauses": [C(DPLAN, Q_PLAN_OWNER, "owner_history", "owner_probe", "mentions"), C(D44, Q_GEN, "owner_history")],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:t"},
                    "owner_probe": {"probe": "history", "ref": "memory:t", "fact_text": OT("early")},
                    "mentions": {"probe": "recall_mentions", "query": OQ, "historical": True, "tokens": ["memory:t", "memory:t@2", "early", "late"]}},
         "expect": {"owner_history": EQ(TOMB(3)), "owner_probe": EQ({**TOMB(3), "rejected_values": 0}), "mentions": EQ([])}},
        {"id": "R1-owner-tombstone-after-restart", "invariants": ["R1"],
         "clauses": [C(DPLAN, Q_PLAN_OWNER, "owner_history", "owner_probe", "mentions"), C(D44, Q_GEN, "owner_history")],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True}, {"op": "reopen"}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:t"},
                    "owner_probe": {"probe": "history", "ref": "memory:t", "fact_text": OT("early")},
                    "mentions": {"probe": "recall_mentions", "query": OQ, "historical": True, "tokens": ["memory:t", "memory:t@2", "early", "late"]}},
         "expect": {"owner_history": EQ(TOMB(3)), "owner_probe": EQ({**TOMB(3), "rejected_values": 0}), "mentions": EQ([])}},
        {"id": "R2-other-reads-unknown-live", "invariants": ["R2"],
         "clauses": [C(DPLAN, Q_PLAN_OTHER, "history", "value_probe", "by_ref", "historical")],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True}],
         "probes": {"history": {"probe": "history_same_as_unknown", "ref": "memory:t", "as": B},
                    "value_probe": {"probe": "history_same_as_unknown", "ref": "memory:t", "fact_text": OT("early"), "as": B},
                    "by_ref": {"probe": "recall_same_as_unknown", "query": OQ, "ref": "memory:t", "as": B},
                    "historical": {"probe": "recall_admitted", "query": OQ, "historical": True, "as": B}},
         "expect": {"history": EQ(True), "value_probe": EQ(True), "by_ref": EQ(True), "historical": EQ([])}},
        {"id": "R2-other-reads-unknown-after-restart", "invariants": ["R2"],
         "clauses": [C(DPLAN, Q_PLAN_OTHER, "history", "value_probe", "by_ref")],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True}, {"op": "reopen"}],
         "probes": {"history": {"probe": "history_same_as_unknown", "ref": "memory:t", "as": B},
                    "value_probe": {"probe": "history_same_as_unknown", "ref": "memory:t", "fact_text": OT("early"), "as": B},
                    "by_ref": {"probe": "recall_same_as_unknown", "query": OQ, "ref": "memory:t", "as": B}},
         "expect": {"history": EQ(True), "value_probe": EQ(True), "by_ref": EQ(True)}},
        {"id": "R3-owner-view-stable-under-other-scope-with-distinct-generation-lengths", "invariants": ["R3", "R6"],
         "clauses": [C(D44, Q_GEN, "owner_history", "other_history", "b1_before", "b1_after", "b3_after"),
                     C(DPLAN, Q_PLAN_OWNER, "owner_history", "other_history"), C(D786, Q_786_RECREATE, "owner_mentions")],
         "steps": seed_o() + [{"op": "forget", "ref": "memory:t", "require_committed": True},
                              rem("memory:t", OT("mid"), P(O, OA, "mid"), **{"as": B}, label="gen-b", name="b1", require_committed=True),
                              {"op": "reopen"},
                              {"op": "forget", "ref": "memory:t", "as": B, "name": "b3", "require_committed": True}],
         "probes": {"owner_history": {"probe": "history", "ref": "memory:t"},
                    "owner_mentions": {"probe": "recall_mentions", "query": OQ, "historical": True, "tokens": ["gen-b", "mid"]},
                    "other_history": {"probe": "history", "ref": "memory:t", "as": B},
                    "b1_before": {"probe": "op_result", "name": "b1", "field": "before_state"},
                    "b1_after": {"probe": "op_result", "name": "b1", "field": "after_state"},
                    "b3_after": {"probe": "op_result", "name": "b3", "field": "after_state"}},
         "expect": {"owner_history": EQ(TOMB(3)), "owner_mentions": EQ([]), "other_history": EQ(TOMB(2)),
                    "b1_before": EQ("v0"), "b1_after": EQ("v1"), "b3_after": EQ("v2")}},
        {"id": "R4-derived-from-deleted-withheld-live-derivation-kept", "invariants": ["R4"],
         "clauses": [C(D786, Q_786_DERIVED, "withheld"), C(DPLAN, Q_PLAN_OWNER, "withheld")],
         "controls": ["kept"],
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
         "clauses": [C(D44, Q_GEN, "parked_after", "parked_mentions", "a_back_mentions", "other_view"),
                     C(D44, Q_CLOSED, "a_disp", "a_disp_mentions"), C(DPLAN, Q_PLAN_RECREATED, "other_history_mentions")],
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
                    "other_view": {"probe": "history_summary", "ref": "memory:t", "as": B},
                    "other_history": {"probe": "history", "ref": "memory:t", "as": B},
                    "other_history_mentions": {"probe": "history_mentions", "ref": "memory:t", "as": B, "tokens": ["memory:t", "memory:t@2", "early", "late", "v3", A]}},
         "expect": {"parked_after": EQ("v0"), "parked_mentions": EQ([]), "a_back_mentions": EQ([]), "a_disp": EQ(False),
                    "a_disp_mentions": EQ([]), "other_view": EQ({"current": "gen-b", "state_version": 1, "tombstoned": False}),
                    "other_history_mentions": EQ([])},
         "record": ["other_history"],
         "implementation_evidence": ["other_history"]},
        {"id": "R5-recreated-history-only-own-events", "invariants": ["R5", "R6"],
         "clauses": [C(D786, Q_786_F7, "other_history", "a_back"), C(DPLAN, Q_PLAN_RECREATED, "other_history", "other_history_mentions"),
                     C(D44, Q_GEN, "b1_snapshot", "b1_before", "b1_after"), C(D44, Q_REM, "a_back")],
         "steps": [rem("memory:t", OT("early"), P(O, OA, "early"), require_committed=True),
                   {"op": "forget", "ref": "memory:t", "require_committed": True},
                   rem("memory:t", OT("mid"), P(O, OA, "mid"), **{"as": B}, label="gen-b", name="b1", require_committed=True),
                   rem("memory:t", OT("late"), P(O, OA, "late"), name="a_back"),
                   {"op": "reopen"}],
         "probes": {"other_history": {"probe": "history", "ref": "memory:t", "as": B},
                    "other_history_mentions": {"probe": "history_mentions", "ref": "memory:t", "as": B, "tokens": ["memory:t", "early", "late", "v2", A]},
                    "a_back": {"probe": "op_result", "name": "a_back", "field": "committed"},
                    "b1_snapshot": {"probe": "op_result", "name": "b1", "field": "state_snapshot"},
                    "b1_before": {"probe": "op_result", "name": "b1", "field": "before_state"},
                    "b1_after": {"probe": "op_result", "name": "b1", "field": "after_state"}},
         "expect": {"other_history": EQ({"current": "gen-b", "state_version": 1, "tombstoned": False, "events": FOUR}),
                    "other_history_mentions": EQ([]), "a_back": EQ(False), "b1_snapshot": EQ("v0"), "b1_before": EQ("v0"), "b1_after": EQ("v1")}},
    ],
}

for fixture in (R1, R2, R3):
    doc = {"replay_id": fixture["replay_id"], "fixture_version": 3, **COMMON,
           "development_history": fixture["development_history"], "title": fixture["title"],
           "contract_sources": fixture["contract_sources"], "invariants": fixture["invariants"], "cases": fixture["cases"]}
    ids = [c["id"] for c in doc["cases"]]
    assert len(ids) == len(set(ids)), ids
    covered = {i for c in doc["cases"] for i in c["invariants"]}
    assert covered == {i["id"] for i in doc["invariants"]}, (fixture["replay_id"], covered)
    sources = {s["path"] for s in doc["contract_sources"]}
    for case in doc["cases"]:
        expected = set(case["expect"])
        traced = {o for clause in case["clauses"] for o in clause["observables"]}
        controls = set(case.get("controls", ()))
        assert controls <= expected and not (controls & traced), (case["id"], "controls are expected, not clause-derived")
        assert expected <= traced | controls, (case["id"], expected - traced - controls)  # every expectation follows from a quoted clause or is a declared positive control
        assert traced <= expected | set(case.get("record", ())), (case["id"], traced - expected)
        assert {clause["source"] for clause in case["clauses"]} <= sources, (case["id"], "clause source not in contract_sources")
        assert set(case.get("implementation_evidence", ())) <= set(case.get("record", ())) and not (
            set(case.get("implementation_evidence", ())) & expected), case["id"]
        assert set(case["probes"]) >= expected | set(case.get("record", ())), (case["id"], "probe missing")
    (OUT / f"{fixture['replay_id']}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(fixture["replay_id"], len(doc["cases"]), "cases")
