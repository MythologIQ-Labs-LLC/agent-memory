"""Author the #809 security replay fixture ``evidence-reference-authorization-v1`` (``786-security-replay-dsl/3``).

An additive generation: the three -v3 fixtures, their first-execution evidence and the DSL/1
and DSL/2 runners are byte-frozen and not edited; this script writes only
``evidence-reference-authorization-v1.json``. The fixture pins the repaired authorization
boundary of F-R3-2 (owner disposition (b), issue #809): a reference the writer cannot read is an
unknown reference. Every expectation is written from the contract clauses quoted below
(docs/44 "Canonical derivation is bound under the writer's own authority" and the docs/786
F-R3-2 row at ``base_commit``), never from a replay outcome, and the fixture is committed before
its first execution and compared to those clauses by a separate reviewer before that execution.

What the facade DSL can and cannot pin: the four references (foreign-deleted after pruning and
after permanent deletion, foreign-live, unknown, absent) at write and at every public read of
the citer, live and after an in-process reopen; the dispute channel; the canary; re-creation by
the citing scope; cross-scope chains; purged identifiers; own-scope deletion completeness with
physical erasure. Shared-domain membership, its revocation, project/task restrictions, a
genuine child-process restart and the recorded derivation attribute have no facade-level
operation in the DSL and are pinned by ``reference/tests/test_809_evidence_reference_authorization.py``.

Vocabulary is new (no frozen holdout phrase, no #644 or -v3 fixture entity).
usage: author_fixture_809.py <repo_root> <base_commit>
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
BASE_COMMIT = sys.argv[2]
OUT = ROOT / "reference/fixtures/786-security-replays"
DSL = "786-security-replay-dsl/3"
T, A, B = "tenant:s786", "project:a", "project:b"
FOUR = ["memory.propose", "memory.authorize", "memory.commit", "memory.receipt"]
D44, D786 = "docs/44-public-api-contract.md", "docs/786-cross-scope-write-authority.md"
D28 = "docs/28-retention-deletion-and-tombstones.md"
GUESS = "@literal:fact-guess-999999999999"
GUESS2 = "@literal:fact-guess-888888888888"
TICKET = "@literal:evidence:ticket-7"


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


def C(source, clause, *observables):
    return {"source": source, "clause": clause, "observables": list(observables)}


EQ = lambda v: {"eq": v}  # noqa: E731
LIVE = lambda label: {"current": label, "state_version": 1, "tombstoned": False, "events": FOUR}  # noqa: E731

# ---- clause anchors (quoted from the sources at BASE_COMMIT; the reviewer verifies each) ----
Q_BIND = ("A reference in `evidence_refs` becomes a canonical derivation link of the committed fact, and so carries "
          "deletion taint (`derived_from_tombstoned_source`, `derived_from_deleted_logical_memory`), only when it names a "
          "fact of the tenant the writer is eligible to read under the gates above; the decision is made once at commit "
          "and recorded with the fact.")
Q_UNKNOWN = ("Every other reference (an external evidence identifier, an id nobody wrote, a fact outside the writer's scope, "
             "an id that exists only later) is an unknown reference: it is retained verbatim as caller-supplied evidence "
             "(`episode_uuids`, receipts, audit events) and never withholds anything.")
Q_SAME = ("A write citing a reference outside the writer's scope therefore commits, reads back and stays admitted exactly "
          "as a write citing an id nobody wrote: the same receipt, `history`, recall payload and `write_semantics`, live, "
          "after a reopen and after a restart, and whether or not the cited fact is later pruned or permanently deleted.")
Q_OWN = ("Within the writer's own scope the #776/#777 rule is unchanged: direct and transitive derivations of a deleted "
         "source are withheld tenant-wide, including after the source's payload is physically erased, and a dependency "
         "bound while the writer was a member of a shared domain survives the writer's later revocation.")
Q_READER = ("A public projection withholds a deleted-generation identifier only from a reader whose own context could have "
            "read that generation. To any other reader such a string is an opaque identifier it cannot act on, whether the "
            "reader supplied it itself or meets it in a co-holder's audit evidence of a shared memory: citing it binds "
            "nothing, disputing it or looking up its write semantics reads exactly as an id nobody wrote, and recall cannot "
            "address it.")
Q_GEN = ("Versions are generation-relative: `state_version`, `state_snapshot`, `before_state` and `after_state` count within "
         "the live generation of a logical id. After a governed deletion of the head the id reports `0` to any writer, a "
         "re-creation's receipt reads `v0 -> v1`, and the former generation's count never reaches the new one")
Q_OPEN = ("An id with no live head (never written or governed-deleted) is open to any writer in the tenant: creation and "
          "the #776 re-creation of a deleted id as a fresh generation are unchanged.")
Q_786_FIX = ("A citation of a foreign deleted, foreign live or unknown id commits, reads and stays admitted identically; "
             "a canary citing a live foreign fact no longer vanishes; a dispute citing a foreign deleted id stays in the "
             "citer's history.")
Q_786_OWN = ("Within the writer's scope, including shared domains the writer was a member of at commit and sources later "
             "physically erased, derivations of deleted content are withheld as before.")
Q_28_PURGE = "| purge | no | intended no recoverable copies | no | required full deletion outcome |"

Q, QA = "Quillon ferry", "berth"
QT = lambda v: f"{Q} {QA} is {v}"  # noqa: E731
DIGEST = lambda token: f"{Q} {QA} digest {token}"  # noqa: E731
DQ = f"{Q} {QA} digest"

# the four citations by B, after A's deletion of memory:q (q1) with memory:q2 (q2) live
SUBS = [["q1", "<ref>"], ["q2", "<ref>"], [GUESS, "<ref>"],
        ["@literal:digest alpha", "digest <case>"], ["@literal:digest beta", "digest <case>"],
        ["@literal:digest gamma", "digest <case>"],
        ["bd", "<self>"], ["bl", "<self>"], ["bu", "<self>"]]


def seed():
    return [rem("memory:q", QT("north"), P(Q, QA, "north"), label="q1", require_committed=True),
            rem("memory:q2", QT("south"), P(Q, QA, "south"), label="q2", require_committed=True)]


def forget_q(permanent=False, ref="memory:q", **kw):
    op = {"op": "forget", "ref": ref, "require_committed": True}
    if permanent:
        op["permanent"] = True
    op.update(kw)
    return op


def cite_four():
    return [rem("memory:bd", DIGEST("alpha"), evidence_refs=["q1"], **{"as": B}, label="bd", name="bd", require_committed=True),
            rem("memory:bl", DIGEST("beta"), evidence_refs=["q2"], **{"as": B}, label="bl", name="bl", require_committed=True),
            rem("memory:bu", DIGEST("gamma"), evidence_refs=[GUESS], **{"as": B}, label="bu", name="bu", require_committed=True),
            rem("memory:bn", DIGEST("delta"), **{"as": B}, label="bn", name="bn", require_committed=True)]


def four_probes(*, reopened=False):
    probes = {}
    for label, memory, token in (("bd", "memory:bd", "alpha"), ("bl", "memory:bl", "beta"),
                                 ("bu", "memory:bu", "gamma"), ("bn", "memory:bn", "delta")):
        if not reopened:
            probes[f"committed_{label}"] = {"probe": "op_result", "name": label, "field": "committed"}
            probes[f"refusal_{label}"] = {"probe": "op_result", "name": label, "field": "refusal"}
            probes[f"before_{label}"] = {"probe": "op_result", "name": label, "field": "before_state"}
            probes[f"after_{label}"] = {"probe": "op_result", "name": label, "field": "after_state"}
        probes[f"admitted_{label}"] = {"probe": "recall_admitted", "query": DIGEST(token), "logical_refs": [memory], "as": B}
        probes[f"history_{label}"] = {"probe": "history", "ref": memory, "as": B}
        probes[f"semantics_{label}"] = {"probe": "write_semantics_present", "fact": label, "as": B}
    for label, memory, token in (("bd", "memory:bd", "alpha"), ("bl", "memory:bl", "beta")):
        if not reopened:
            probes[f"op_same_{label}"] = {"probe": "op_same_as", "name": label, "other": "bu", "ref": memory,
                                          "other_ref": "memory:bu", "substitute": SUBS}
        probes[f"history_same_{label}"] = {"probe": "history_same_as", "ref": memory, "other": "memory:bu", "as": B,
                                           "substitute": SUBS}
        probes[f"recall_same_{label}"] = {"probe": "recall_same_as", "query": DIGEST(token), "other_query": DIGEST("gamma"),
                                          "ref": memory, "other": "memory:bu", "as": B, "substitute": SUBS}
        probes[f"semantics_same_{label}"] = {"probe": "write_semantics_same_as", "fact": label, "other": "bu", "as": B,
                                             "substitute": SUBS}
    return probes


def four_expect(*, reopened=False):
    expect = {}
    for label in ("bd", "bl", "bu", "bn"):
        if not reopened:
            expect[f"committed_{label}"] = EQ(True)
            expect[f"refusal_{label}"] = EQ(None)
            expect[f"before_{label}"] = EQ("v0")
            expect[f"after_{label}"] = EQ("v1")
        expect[f"admitted_{label}"] = EQ([label])
        expect[f"history_{label}"] = EQ(LIVE(label))
        expect[f"semantics_{label}"] = EQ(True)
    for label in ("bd", "bl"):
        if not reopened:
            expect[f"op_same_{label}"] = EQ(True)
        expect[f"history_same_{label}"] = EQ(True)
        expect[f"recall_same_{label}"] = EQ(True)
        expect[f"semantics_same_{label}"] = EQ(True)
    return expect


def four_clauses(*, reopened=False):
    all_obs = list(four_expect(reopened=reopened))
    same = [o for o in all_obs if "_same_" in o]
    reads = [o for o in all_obs if o.split("_")[0] in ("admitted", "history", "semantics") and "_same_" not in o]
    writes = [o for o in all_obs if o.split("_")[0] in ("committed", "refusal", "before", "after")]
    return [C(D44, Q_SAME, *same, *reads, *writes), C(D44, Q_UNKNOWN, *[o for o in reads if o.startswith("admitted")]),
            C(D786, Q_786_FIX, *[o for o in all_obs if o.endswith("_bd") or o.endswith("_bl")]),
            *([C(D44, Q_GEN, *writes), C(D44, Q_OPEN, *writes)] if writes else [])]


FIXTURE = {
    "replay_id": "evidence-reference-authorization-v1",
    "fixture_version": 1,
    "dsl_version": DSL,
    "owning_issue": 809,
    "frozen_on": "2026-10-15",
    "status": "additive",
    "relation_to_v3": ("Additive generation beside the three -v3 fixtures (not a supersession): the -v3 fixtures, their "
                       "first-execution evidence at 842e5734 and the DSL/1 and DSL/2 runners are byte-frozen. This fixture "
                       "pins the authorization boundary the #809 repair introduces; it is executed by the DSL/3 runner "
                       "(reference/run_786_security_replays_dsl3.py), which inherits DSL/2 unchanged."),
    "base_commit": BASE_COMMIT,
    "contract_sources": [doc_hash(D44), doc_hash(D786), doc_hash(D28)],
    "title": "A reference the writer cannot read is an unknown reference: it binds no canonical derivation, withholds nothing and reads identically to an id nobody wrote",
    "development_history": ("Authored from the docs/44 clause 'Canonical derivation is bound under the writer's own authority' "
                            "and the docs/786 F-R3-2 row at base_commit (the repair commit b932bd2f), after the unit-level "
                            "expectations of reference/tests/test_809_evidence_reference_authorization.py were preregistered "
                            "(10a0d70e, superseded after independent review at 53268532 and 8272b38e; three fail-first baselines "
                            "on the unmodified runtime, the last 36 failed / 14 passed / 82 subtests) and executed once on the "
                            "repaired runtime (27 passed, 1 xfailed, 106 subtests; reports/validation/809-at-head). The first "
                            "fixture revision (871d2bbe) was executed once by its own family test inside a full-suite run before "
                            "its independent review; that run is disclosed, not used as evidence, and its failures were the "
                            "harness defect the review independently found (RF-1: unfolded clocks and scores in recall). This "
                            "revision answers that review before the runner's first execution."),
    "independence": ("Expected outcomes were written from the contract documents listed in contract_sources at base_commit, "
                     "clause by clause (`clauses` on every case), and compared to those clauses by a separate reviewer before "
                     "the runner's first execution. A failing expectation is a finding, never a reason to edit this fixture; a "
                     "corrected expectation requires a superseding -v2 of this generation with a recorded reason. This fixture "
                     "declares no `controls`; observables under `implementation_evidence` are recorded, never expected. No "
                     "frozen holdout phrase, #644 or -v3 fixture vocabulary is used."),
    "not_claimed": ("Process-level restart (every `reopen` is a handle close and open in one process); shared-domain "
                    "membership, its revocation and project/task restrictions (no facade operation); late binding of a "
                    "reference that names no fact at commit; direct probes of a foreign deleted id (dispute by uuid, write "
                    "semantics lookup); the owner's provenance audit (undeclared residue); facts persisted before #809 (legacy "
                    "rows); the owner's view after another scope re-creates the deleted id; co-holder audit evidence in the "
                    "history of a shared memory; timing side channels (not measured); erasure beyond the canonical substrate "
                    "and public reads (docs/28, docs/44). Each of these is pinned by the unit module named above."),
    "stop_lines": [
        "no fixture edit after first execution; supersede and record why",
        "no expectation weakened to obtain PASS",
        "no runtime change motivated by a replay outcome without a preregistered reproducer",
        "a replay verdict is evidence, not successor acceptance; acceptance requires independent review",
        "a passing replay on this revision certifies no other protected tree",
    ],
    "invariants": [
        {"id": "E1", "statement": "After A's pruning or attested permanent deletion of memory:q, B's writes citing the deleted foreign fact, a live foreign fact, an id nobody wrote and nothing at all each commit v0 -> v1 with no refusal, are admitted by logical reference, show one live generation of four events, have write semantics, and the deleted-foreign and live-foreign citations read byte-identically (ids, timestamps, cited strings and case tokens folded) to the unknown citation in the remember result, the history, the recall payload and the write semantics.",
         "falsified_by": "any citation refused, withheld, or differing in any of the four payloads from the unknown citation"},
        {"id": "E2", "statement": "E1 holds after an in-process reopen of the citing handle.",
         "falsified_by": "a citation withheld or a payload differing after reopen"},
        {"id": "E3", "statement": "A dispute by B of its own memory citing the deleted foreign id commits and leaves B's history byte-identical (folded) to the same dispute citing an id nobody wrote; the dispute event is present in both.",
         "falsified_by": "a withheld dispute event or a differing history"},
        {"id": "E4", "statement": "B's memory citing a live foreign fact (a canary) stays admitted with an unchanged history after A prunes or permanently deletes that fact.",
         "falsified_by": "the canary withheld or its history changed by the foreign deletion"},
        {"id": "E5", "statement": "Within A's own scope, direct and transitive derivations of memory:q are withheld after its pruning and after its permanent deletion (the source payload erased), live and after a reopen, while a memory citing only an external identifier stays admitted; a derivation written after the source was purged is withheld too, and the same purged identifier cited from B binds nothing.",
         "falsified_by": "a derivation admitted, the control withheld, or the purged id withholding B's write"},
        {"id": "E6", "statement": "B may re-create A's deleted id; B's derivation of its own new generation follows B's own deletion while B's citation of A's deleted fact stays admitted throughout, live and after reopen; a chain of B's memories rooted in A's deleted fact is admitted end to end.",
         "falsified_by": "the foreign citation withheld at any point, or B's own derivation surviving B's deletion"},
    ],
    "cases": [
        {"id": "E1-four-references-after-pruning", "invariants": ["E1"],
         "clauses": four_clauses(),
         "steps": seed() + [forget_q()] + cite_four(),
         "probes": four_probes(), "expect": four_expect()},
        {"id": "E1b-four-references-after-permanent-deletion", "invariants": ["E1"],
         "clauses": four_clauses() + [C(D28, Q_28_PURGE, "q1_exists")],
         "steps": seed() + [forget_q(permanent=True)] + cite_four(),
         "probes": {**four_probes(), "q1_exists": {"probe": "fact_exists", "fact": "q1"}},
         "expect": {**four_expect(), "q1_exists": EQ(False)}},
        {"id": "E2-four-references-after-reopen", "invariants": ["E2", "E1"],
         "clauses": four_clauses(reopened=True),
         "steps": seed() + [forget_q()] + cite_four() + [{"op": "reopen"}],
         "probes": four_probes(reopened=True), "expect": four_expect(reopened=True)},
        {"id": "E3-dispute-citing-the-deleted-foreign-id", "invariants": ["E3"],
         "clauses": [C(D786, Q_786_FIX, "disp_d_committed", "disp_u_committed", "history_same", "op_same",
                       "dispute_present_d", "dispute_present_u"),
                     C(D44, Q_READER, "history_same")],
         "record": ["events_d", "events_u"], "implementation_evidence": ["events_d", "events_u"],
         "steps": seed() + [forget_q(),
                            rem("memory:dd", DIGEST("epsilon"), **{"as": B}, label="dd", require_committed=True),
                            rem("memory:du", DIGEST("zeta"), **{"as": B}, label="du", require_committed=True),
                            {"op": "dispute", "ref": "memory:dd", "evidence_refs": ["q1"], "as": B, "name": "disp_d"},
                            {"op": "dispute", "ref": "memory:du", "evidence_refs": [GUESS2], "as": B, "name": "disp_u"}],
         "probes": {"disp_d_committed": {"probe": "op_result", "name": "disp_d", "field": "committed"},
                    "disp_u_committed": {"probe": "op_result", "name": "disp_u", "field": "committed"},
                    "events_d": {"probe": "history_events", "ref": "memory:dd", "as": B},
                    "events_u": {"probe": "history_events", "ref": "memory:du", "as": B},
                    "dispute_present_d": {"probe": "history_has_event", "ref": "memory:dd", "event_type": "memory.dispute", "as": B},
                    "dispute_present_u": {"probe": "history_has_event", "ref": "memory:du", "event_type": "memory.dispute", "as": B},
                    "history_same": {"probe": "history_same_as", "ref": "memory:dd", "other": "memory:du", "as": B,
                                     "substitute": [["q1", "<ref>"], [GUESS2, "<ref>"], ["@literal:digest epsilon", "digest <case>"], ["@literal:digest zeta", "digest <case>"],
                                                    ["dd", "<self>"], ["du", "<self>"]]},
                    "op_same": {"probe": "op_same_as", "name": "disp_d", "other": "disp_u", "ref": "memory:dd", "other_ref": "memory:du",
                                "substitute": [["q1", "<ref>"], [GUESS2, "<ref>"], ["@literal:digest epsilon", "digest <case>"], ["@literal:digest zeta", "digest <case>"],
                                               ["dd", "<self>"], ["du", "<self>"]]}},
         "expect": {"disp_d_committed": EQ(True), "disp_u_committed": EQ(True), "history_same": EQ(True), "op_same": EQ(True),
                    "dispute_present_d": EQ(True), "dispute_present_u": EQ(True)}},
        {"id": "E4-canary-survives-pruning-of-its-source", "invariants": ["E4"],
         "clauses": [C(D786, Q_786_FIX, "admitted", "history"), C(D44, Q_SAME, "admitted", "history")],
         "steps": seed() + [rem("memory:bc", DIGEST("eta"), evidence_refs=["q2"], **{"as": B}, label="bc", require_committed=True),
                            forget_q(ref="memory:q2")],
         "probes": {"admitted": {"probe": "recall_admitted", "query": DIGEST("eta"), "logical_refs": ["memory:bc"], "as": B},
                    "history": {"probe": "history", "ref": "memory:bc", "as": B}},
         "expect": {"admitted": EQ(["bc"]), "history": EQ(LIVE("bc"))}},
        {"id": "E4b-canary-survives-permanent-deletion-of-its-source", "invariants": ["E4"],
         "clauses": [C(D786, Q_786_FIX, "admitted", "history"), C(D44, Q_SAME, "admitted", "history"), C(D28, Q_28_PURGE, "q2_exists")],
         "steps": seed() + [rem("memory:bc", DIGEST("eta"), evidence_refs=["q2"], **{"as": B}, label="bc", require_committed=True),
                            forget_q(ref="memory:q2", permanent=True), {"op": "reopen"}],
         "probes": {"admitted": {"probe": "recall_admitted", "query": DIGEST("eta"), "logical_refs": ["memory:bc"], "as": B},
                    "history": {"probe": "history", "ref": "memory:bc", "as": B},
                    "q2_exists": {"probe": "fact_exists", "fact": "q2"}},
         "expect": {"admitted": EQ(["bc"]), "history": EQ(LIVE("bc")), "q2_exists": EQ(False)}},
        {"id": "E5-own-scope-derivations-withheld-after-pruning", "invariants": ["E5"],
         "clauses": [C(D44, Q_OWN, "withheld", "withheld_after_reopen"), C(D786, Q_786_OWN, "withheld"),
                     C(D44, Q_UNKNOWN, "kept", "kept_after_reopen")],
         "controls": [],
         "steps": seed() + [rem("memory:d1", DIGEST("theta"), evidence_refs=["q1", TICKET], label="d1", require_committed=True),
                            rem("memory:d2", DIGEST("iota"), evidence_refs=["d1"], label="d2", require_committed=True),
                            rem("memory:ctl", DIGEST("kappa"), evidence_refs=[TICKET], label="ctl", require_committed=True),
                            forget_q()],
         "probes": {"withheld": {"probe": "recall_mentions", "query": DQ, "historical": True, "tokens": ["d1", "d2"]},
                    "kept": {"probe": "recall_admitted", "query": DIGEST("kappa"), "logical_refs": ["memory:ctl"]},
                    "withheld_after_reopen": {"probe": "recall_mentions", "query": DQ, "historical": True, "tokens": ["d1", "d2"]},
                    "kept_after_reopen": {"probe": "recall_admitted", "query": DIGEST("kappa"), "logical_refs": ["memory:ctl"]}},
         "expect": {"withheld": EQ([]), "kept": EQ(["ctl"]), "withheld_after_reopen": EQ([]), "kept_after_reopen": EQ(["ctl"])}},
        {"id": "E5b-own-scope-derivations-withheld-after-permanent-deletion", "invariants": ["E5"],
         "clauses": [C(D44, Q_OWN, "withheld", "withheld_after_reopen"), C(D786, Q_786_OWN, "withheld"),
                     C(D44, Q_UNKNOWN, "kept"), C(D28, Q_28_PURGE, "q1_exists")],
         "steps": seed() + [rem("memory:d1", DIGEST("theta"), evidence_refs=["q1", TICKET], label="d1", require_committed=True),
                            rem("memory:d2", DIGEST("iota"), evidence_refs=["d1"], label="d2", require_committed=True),
                            rem("memory:ctl", DIGEST("kappa"), evidence_refs=[TICKET], label="ctl", require_committed=True),
                            forget_q(permanent=True), {"op": "reopen"}],
         "probes": {"q1_exists": {"probe": "fact_exists", "fact": "q1"},
                    "withheld": {"probe": "recall_mentions", "query": DQ, "historical": True, "tokens": ["d1", "d2"]},
                    "kept": {"probe": "recall_admitted", "query": DIGEST("kappa"), "logical_refs": ["memory:ctl"]},
                    "withheld_after_reopen": {"probe": "recall_mentions", "query": DQ, "historical": True, "tokens": ["d1", "d2"]}},
         "expect": {"q1_exists": EQ(False), "withheld": EQ([]), "kept": EQ(["ctl"]), "withheld_after_reopen": EQ([])}},
        {"id": "E5c-purged-source-cited-afterwards", "invariants": ["E5"],
         "clauses": [C(D44, Q_OWN, "late_withheld"), C(D786, Q_786_OWN, "late_withheld"), C(D44, Q_UNKNOWN, "bp_admitted"),
                     C(D44, Q_SAME, "bp_admitted", "bp_history"), C(D28, Q_28_PURGE, "q1_exists")],
         "steps": seed() + [forget_q(permanent=True),
                            rem("memory:late", DIGEST("lambda"), evidence_refs=["q1"], label="late", require_committed=True),
                            rem("memory:bp", DIGEST("mu"), evidence_refs=["q1"], **{"as": B}, label="bp", require_committed=True)],
         "probes": {"q1_exists": {"probe": "fact_exists", "fact": "q1"},
                    "late_withheld": {"probe": "recall_mentions", "query": DIGEST("lambda"), "historical": True, "tokens": ["late"]},
                    "bp_admitted": {"probe": "recall_admitted", "query": DIGEST("mu"), "logical_refs": ["memory:bp"], "as": B},
                    "bp_history": {"probe": "history", "ref": "memory:bp", "as": B}},
         "expect": {"q1_exists": EQ(False), "late_withheld": EQ([]), "bp_admitted": EQ(["bp"]), "bp_history": EQ(LIVE("bp"))}},
        {"id": "E6-re-creation-by-the-citing-scope", "invariants": ["E6"],
         "clauses": [C(D44, Q_OPEN, "recreated"), C(D44, Q_GEN, "recreated"), C(D44, Q_SAME, "bf_before", "bf_after", "bf_after_reopen"),
                     C(D44, Q_OWN, "bo_after", "bo_after_reopen"), C(D44, Q_BIND, "bo_before", "bo_after")],
         "steps": seed() + [forget_q(),
                            rem("memory:bf", DIGEST("nu"), evidence_refs=["q1"], **{"as": B}, label="bf", require_committed=True),
                            rem("memory:q", QT("east"), P(Q, QA, "east"), **{"as": B}, label="q-b", name="recreate", require_committed=True),
                            rem("memory:bo", DIGEST("xi"), evidence_refs=["q-b"], **{"as": B}, label="bo", name="bo", require_committed=True)],
         "probes": {"recreated": {"probe": "op_result", "name": "recreate", "field": "after_state"},
                    "bf_before": {"probe": "recall_admitted", "query": DIGEST("nu"), "logical_refs": ["memory:bf"], "as": B},
                    "bo_before": {"probe": "recall_admitted", "query": DIGEST("xi"), "logical_refs": ["memory:bo"], "as": B},
                    "bf_after": {"probe": "recall_admitted", "query": DIGEST("nu"), "logical_refs": ["memory:bf"], "as": B},
                    "bo_after": {"probe": "recall_admitted", "query": DIGEST("xi"), "logical_refs": ["memory:bo"], "as": B},
                    "bf_after_reopen": {"probe": "recall_admitted", "query": DIGEST("nu"), "logical_refs": ["memory:bf"], "as": B},
                    "bo_after_reopen": {"probe": "recall_admitted", "query": DIGEST("xi"), "logical_refs": ["memory:bo"], "as": B}},
         "expect": {"recreated": EQ("v1"), "bf_before": EQ(["bf"]), "bo_before": EQ(["bo"]),
                    "bf_after": EQ(["bf"]), "bo_after": EQ([]), "bf_after_reopen": EQ(["bf"]), "bo_after_reopen": EQ([])}},
        {"id": "E6b-chain-rooted-in-the-foreign-deleted-fact", "invariants": ["E6"],
         "clauses": [C(D44, Q_UNKNOWN, "first", "second", "third"), C(D44, Q_SAME, "first", "second", "third")],
         "steps": seed() + [forget_q(permanent=True),
                            rem("memory:c1", DIGEST("omicron"), evidence_refs=["q1"], **{"as": B}, label="c1", require_committed=True),
                            rem("memory:c2", DIGEST("pi"), evidence_refs=["c1"], **{"as": B}, label="c2", require_committed=True),
                            rem("memory:c3", DIGEST("rho"), evidence_refs=["c2"], **{"as": B}, label="c3", require_committed=True)],
         "probes": {"first": {"probe": "recall_admitted", "query": DIGEST("omicron"), "logical_refs": ["memory:c1"], "as": B},
                    "second": {"probe": "recall_admitted", "query": DIGEST("pi"), "logical_refs": ["memory:c2"], "as": B},
                    "third": {"probe": "recall_admitted", "query": DIGEST("rho"), "logical_refs": ["memory:c3"], "as": B}},
         "expect": {"first": EQ(["c1"]), "second": EQ(["c2"]), "third": EQ(["c3"])}},
    ],
}

# E6 needs the probes evaluated in two phases (before and after B's own deletion): the DSL runs
# every probe after every step, so the "after" observables are produced by a second case.
E6 = FIXTURE["cases"][-2]
assert E6["id"] == "E6-re-creation-by-the-citing-scope"
before = {k: v for k, v in E6["probes"].items() if k in ("recreated", "bf_before", "bo_before")}
E6_before = {**E6, "id": "E6-re-creation-by-the-citing-scope", "invariants": ["E6"],
             "clauses": [C(D44, Q_OPEN, "recreated"), C(D44, Q_GEN, "recreated"), C(D44, Q_SAME, "bf_before"), C(D44, Q_BIND, "bo_before")],
             "probes": before, "expect": {k: E6["expect"][k] for k in before}}
after_probes = {k: v for k, v in E6["probes"].items() if k in ("bf_after", "bo_after")}
reopen_probes = {k: v for k, v in E6["probes"].items() if k in ("bf_after_reopen", "bo_after_reopen")}
E6_after = {"id": "E6a-after-the-citing-scopes-own-deletion", "invariants": ["E6"],
            "clauses": [C(D44, Q_SAME, "bf_after"), C(D44, Q_OWN, "bo_after"), C(D44, Q_BIND, "bo_after")],
            "steps": E6["steps"] + [forget_q(**{"as": B})],
            "probes": after_probes, "expect": {k: E6["expect"][k] for k in after_probes}}
E6_reopen = {"id": "E6r-after-the-citing-scopes-own-deletion-and-reopen", "invariants": ["E6"],
             "clauses": [C(D44, Q_SAME, "bf_after_reopen"), C(D44, Q_OWN, "bo_after_reopen"), C(D44, Q_BIND, "bo_after_reopen")],
             "steps": E6["steps"] + [forget_q(**{"as": B}), {"op": "reopen"}],
             "probes": reopen_probes, "expect": {k: E6["expect"][k] for k in reopen_probes}}
FIXTURE["cases"][-2:-1] = [E6_before, E6_after, E6_reopen]

# ---- coverage assertions: every expectation traced; sources listed; controls and evidence disjoint
sources = {s["path"] for s in FIXTURE["contract_sources"]}
for case in FIXTURE["cases"]:
    traced = {o for c in case["clauses"] for o in c["observables"]}
    controls = set(case.get("controls", ()))
    assert controls <= set(case["expect"]) and not (controls & traced), case["id"]
    missing = set(case["expect"]) - traced - controls
    assert not missing, (case["id"], missing)
    assert {c["source"] for c in case["clauses"]} <= sources, case["id"]
    evidence = set(case.get("implementation_evidence", ()))
    assert not (evidence & set(case["expect"])) and evidence <= set(case.get("record", ())), case["id"]
ids = [c["id"] for c in FIXTURE["cases"]]
assert len(ids) == len(set(ids))
assert {i for c in FIXTURE["cases"] for i in c["invariants"]} == {i["id"] for i in FIXTURE["invariants"]}

text = json.dumps(FIXTURE, indent=1, sort_keys=True) + "\n"
for word in ("Orrin", "Halyard", "Vireo", "theatre", "vineyard", "Oslo", "Bergen", "Turku", "Marrow", "lighthouse"):
    assert word not in text, word
(OUT / "evidence-reference-authorization-v1.json").write_text(text, encoding="utf-8")
print("evidence-reference-authorization-v1", len(FIXTURE["cases"]), "cases",
      sum(len(c["expect"]) for c in FIXTURE["cases"]), "expectations")
