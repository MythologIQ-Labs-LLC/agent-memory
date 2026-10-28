"""Author the v7-integration successor generation of the #786/#809 security replays (``786-security-replay-dsl/5``).

The frozen -v3 fixtures (``786-security-replay-dsl/2``) and ``evidence-reference-authorization-v1``
(``786-security-replay-dsl/3``) open several projects in one root, which the integrated v7
candidate's default ``single_project_v1`` store profile refuses (store-open contract 1.0.0). Their
committed evidence binds the #836 tree and is STALE on the integrated tree; it is not edited. This
script writes the successors: ``*-v4.json`` for the three -v3 families and
``evidence-reference-authorization-v2.json``. They run on the supported multi-project profile,
``scope_distinct_v1``, through ``reference/run_786_security_replays_dsl5.py``.

Every step and probe is carried forward. Expectations change only where the store-open contract
changes what the case observes, and each such change cites the clause it follows from:

* ``SD``: a ``scope_distinct_v1`` store binds every public key to (tenant, scope, key), so another
  project's operation on the same public key acts on that project's own memory;
* ``FIB``: facade identity binding, under which an override that changes the handle's project or
  domains is refused with ``ValueError``, after the 1.8.0 malformed-scope refusal;
* the 1.8.0 clauses already cited by the -v3 fixtures for re-creation, generation-relative
  versions and the former owner's answers.

Rules applied uniformly:

* **M1.** On an operation that commits in the caller's own namespace, version tokens are not a
  disclosure signal, because the caller's own receipt carries its own versions. Mention scans keep
  only the other project's fact labels and distinguishing text.
* **R1.** An outcome no cited clause decides is recorded, not expected. Examples are a correction to
  the value already current (W3 ``b2``, L3 ``a_cor``), a parked proposal's own-namespace history
  (W8b), and a re-creation whose value equals a deleted value (R6b).
* **H1.** The canonical write gate stays exercised below the facade. W1h and W2h are new: a
  host-built proposal from another project names the owner's canonical memory (``ref_scope``), the
  host-layer equivalent of what W1/W2 asserted through the facade on a tenant-wide store.

The expectations are written before this generation is first executed. A separate reviewer
compares them to the clauses before that execution (``PREEXECUTION_REVIEW.md`` beside the
evidence). After first execution a fixture is never edited; a corrected expectation requires a
superseding generation with a recorded reason.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DSL = "786-security-replay-dsl/5"
PROFILE = "scope_distinct_v1"
EVENTS1 = ["memory.propose", "memory.authorize", "memory.commit", "memory.receipt"]
DOC44 = "docs/44-public-api-contract.md"

SD = {"source": DOC44, "clause": "| A `scope_distinct_v1` store binds every public key to (tenant, scope, key) | the only multi-project profile |"}
FIB = {"source": DOC44, "clause": "Proposal `overrides` may only restate that identity exactly, and the scope keywords of `recall` may restate it or narrow its isolation domains; neither may change it: [...] An internally inconsistent override keeps its `1.8.0` refusal (`required isolation domains must also be bound isolation domains`, replay W4) and is checked first. Any other override that changes the handle's tenant, project or isolation domains raises `ValueError` (`facade proposal may not override host-bound scope identity`) at the operation's entry, before any target is resolved, for every operation (`remember`, `correct`, `forget`, `dispute`), so nothing is written, deleted or disputed"}
ADAPTER = {"source": DOC44, "clause": "The decision is the adapter's (`write_target_refusal`, `_delete_refusal`, `_dispute_refusal`); the facade only keeps the result shape non-disclosing"}
IDENTITY_MESSAGE = "facade proposal may not override host-bound scope identity"
OPEN = {"source": DOC44, "clause": "An id with no live head (never written or governed-deleted) is open to any writer in the tenant: creation and the #776 re-creation of a deleted id as a fresh generation are unchanged."}
VERSIONS = {"source": DOC44, "clause": "Versions are generation-relative: `state_version`, `state_snapshot`, `before_state` and `after_state` count within the live generation of a logical id. After a governed deletion of the head the id reports `0` to any writer, a re-creation's receipt reads `v0 -> v1`, and the former generation's count never reaches the new one"}
FORMER = {"source": DOC44, "clause": "At the fact level (`dispute` of a tombstoned fact by its uuid, a governed pruning of one of its versions, the adapter's delete of a member of a deleted lineage) the answer is `already_deleted`; at the facade's logical-reference level (`forget`, permanent `forget`, `correct`, `dispute` by `target_reference`) the former owner reads the bare `fact_not_found` result, because the reference has no visible head."}
GATE_W1 = {"source": DOC44, "clause": "`remember` onto a live head outside the writer's scope: `committed: false`, `refusal: \"target_unavailable\"`, receipt `before_state`/`after_state` `v0`, `state_snapshot` `v0`. Nothing is written, no episode is retained, no version moves."}
GATE_W2 = {"source": DOC44, "clause": "`correct`, `forget`, `dispute` on such a memory: the bare `fact_not_found` result, byte-identical to the result for an id nobody wrote."}

SOURCES = {
    "cross-scope-write-authority-denial-v3": "cross-scope-write-authority-denial-v4",
    "deleted-lineage-generations-and-restart-v3": "deleted-lineage-generations-and-restart-v4",
    "public-tombstone-redaction-and-observer-separation-v3": "public-tombstone-redaction-and-observer-separation-v4",
    "evidence-reference-authorization-v1": "evidence-reference-authorization-v2",
}


def history(current, version, tombstoned=False, events=EVENTS1):
    return {"current": current, "state_version": version, "tombstoned": tombstoned, "events": list(events)}


def raised(name):
    return {"probe": "op_result", "name": name, "field": "raised"}


def message(name):
    return {"probe": "op_raised_message", "name": name}


# per case: expect (None deletes), probes (None deletes), record (added), tokens (mention-probe token
# replacement), steps (index -> keys merged), clauses (added, with observables), note
CHANGES: dict[str, dict] = {
    # ------------------------------------------------------------------ W family
    "W1-remember-over-live-head": {
        "probes": {"other_history_unknown": None, "other_history": {"probe": "history", "ref": "memory:k", "as": "project:b"},
                   "other_history_mentions": {"probe": "history_mentions", "ref": "memory:k", "as": "project:b",
                                              "tokens": ["memory:k", "dawn", "project:a"]}},
        "tokens": {"b1_mentions": ["memory:k", "project:a", "dawn"]},
        "expect": {"b1_committed": {"eq": True}, "b1_refusal": {"eq": None}, "b1_before": {"eq": "v0"}, "b1_after": {"eq": "v1"},
                   "b1_snapshot": {"eq": "v0"}, "other_recall": {"eq": ["project:b|memory:k"]},
                   "other_history_unknown": None, "other_history": {"eq": history("project:b|memory:k", 1)},
                   "other_history_mentions": {"eq": []}},
        "clauses": [(SD, ["b1_committed", "b1_refusal", "other_recall", "other_history", "other_history_mentions", "head",
                          "owner_history", "owner_recall", "b1_mentions"]),
                    (OPEN, ["b1_committed"]), (VERSIONS, ["b1_before", "b1_after", "b1_snapshot"])],
        "note": "B's key is B's own never-written memory: creation, not a write onto A's head (SD). A's side is byte-identical, as in -v3.",
    },
    "W3-refusal-survives-restart": {
        "tokens": {"b1_mentions": ["memory:k", "memory:k@2", "v2", "dawn", "noon", "project:a"]},
        "expect": {"b1": {"eq": True}, "b1_refusal": {"eq": None}, "b1_after": {"eq": "v1"},
                   "b2": None, "b2_refusal": None, "b3": {"eq": True}, "b3_refusal": {"eq": None},
                   "b4": {"eq": False}, "b4_refusal": {"eq": "fact_not_found"}},
        "record": ["b2", "b2_refusal"],
        "clauses": [(SD, ["b1", "b1_refusal", "b3", "b3_refusal", "head", "owner_history", "owner_recall"]),
                    (VERSIONS, ["b1_after"]), (FORMER, ["b4", "b4_refusal"])],
        "note": "Across both restarts B acts only on its own memory (b1 creates, b3 deletes it, b4 reads its own deleted id as fact_not_found); A never moves. b2 corrects to the value already current, which no clause decides (R1).",
    },
    "W4-overrides": {
        "probes": {"sup_rem_raised": raised("sup_rem"), "sup_cor_raised": raised("sup_cor"),
                   "sup_rem_message": message("sup_rem"), "sup_cor_message": message("sup_cor")},
        "expect": {"sup_rem_committed": {"eq": False}, "sup_rem_refusal": None, "sup_rem_before": None,
                   "sup_rem_raised": {"eq": "ValueError"}, "sup_cor_committed": {"eq": False}, "sup_cor_raised": {"eq": "ValueError"},
                   "sup_rem_message": {"eq": IDENTITY_MESSAGE}, "sup_cor_message": {"eq": IDENTITY_MESSAGE}},
        "record": ["sup_rem_refusal", "sup_rem_before"],
        "clauses": [(FIB, ["bad_target", "bad_unknown", "bad_target_message", "bad_unknown_message", "sup_rem_committed",
                           "sup_rem_raised", "sup_rem_message", "sup_cor_committed", "sup_cor_raised", "sup_cor_message",
                           "head", "valid", "owner_recall", "tombstones"])],
        "note": "Facade W4 is the one behaviour the integration changes (docs/44): the superset declaration naming A's project changes the handle's identity and is refused with ValueError instead of reaching the canonical gate. The malformed declaration keeps its 1.8.0 message, checked first. Both the refusal and its message are stated in docs/44 (pre-execution review F-1).",
    },
    "W4b-documented-dispositions-of-complete-and-superset-declarations": {
        "probes": {"sup_disp_raised": raised("sup_disp"), "sup_forget_raised": raised("sup_forget"), "complete_raised": raised("complete"),
                   "sup_disp_message": message("sup_disp"), "sup_forget_message": message("sup_forget"), "complete_message": message("complete")},
        "expect": {"sup_disp": {"eq": False}, "sup_forget": {"eq": False}, "tombstones": {"eq": []}, "complete": {"eq": False},
                   "k2_head": {"eq": "memory:k2"}, "sup_disp_raised": {"eq": "ValueError"}, "sup_forget_raised": {"eq": "ValueError"},
                   "complete_raised": {"eq": "ValueError"}, "sup_disp_message": {"eq": IDENTITY_MESSAGE},
                   "sup_forget_message": {"eq": IDENTITY_MESSAGE}, "complete_message": {"eq": IDENTITY_MESSAGE}},
        "clauses": [(FIB, ["sup_disp", "sup_forget", "tombstones", "complete", "k2_head", "sup_disp_raised", "sup_forget_raised",
                           "complete_raised", "sup_disp_message", "sup_forget_message", "complete_message"])],
        "note": "The -v3 dispositions (a superset declaration may dispute or delete; a complete re-declaration commits as the owner) followed from 'Scope is privileged host input' at the facade. Under store-open 1.0.0 the facade binds identity, so each is refused with ValueError and nothing is deleted or written. Host re-declaration remains available only through the module-level envelope surface.",
    },
    "W6-denied-proposals-persist-no-episode": {
        "steps": {1: {"ref_scope": "project:a"}},
        "clauses": [(GATE_W1, ["denied_committed", "denied_refusal", "denied_before", "episode_denied"])],
        "note": "H1: the denied proposal is host-built by B and names A's canonical memory (ref_scope), the host-layer route to the canonical write gate on a scope-distinct store. Expectations unchanged.",
    },
    "W7-refused-attempt-leaves-no-public-trace": {
        "probes": {"other_history_unknown": None, "other_history": {"probe": "history", "ref": "memory:k", "as": "project:b"},
                   "other_history_mentions": {"probe": "history_mentions", "ref": "memory:k", "as": "project:b",
                                              "tokens": ["memory:k", "memory:k@2", "dawn", "noon", "project:a"]}},
        "expect": {"b1": {"eq": True}, "other_history_unknown": None, "other_history": {"eq": history("project:b|memory:k", 1)},
                   "other_history_mentions": {"eq": []}},
        "clauses": [(SD, ["b1", "other_history", "other_history_mentions", "owner_history", "owner_history_mentions",
                          "canonical_version"])],
        "note": "B's remember creates B's own memory (SD); A's history still carries nothing of it.",
    },
    "W7c-former-owner-attempts-leave-no-trace-in-the-new-generation": {
        "tokens": {"a_disp_mentions": ["gen-b", "dusk", "v2"]},
        "tokens_add": {"other_history_mentions": ["memory:k@2"]},
        "expect": {"a_rem": {"eq": True}, "a_rem_refusal": {"eq": None}, "a_forget": {"eq": True}, "a_forget_refusal": {"eq": None}},
        "clauses": [(SD, ["a_rem", "a_forget", "other_history", "other_history_mentions", "other_recall"]),
                    (OPEN, ["a_rem", "a_rem_refusal"]), (FORMER, ["a_disp", "a_disp_refusal", "a_del", "a_del_refusal"])],
        "note": "B's generation lives in B's namespace, so A's own deleted id stays open to A: a_rem re-creates it and a_forget deletes that re-creation. The fact-level answers on A's deleted generation stay already_deleted. M1 drops version tokens from A's own receipt scan.",
    },
    "W8b-refused-and-parked-proposals-on-a-tombstoned-id-report-v0": {
        "tokens": {"parked_b_states": ["v1", "v2", "v3", "memory:k", "memory:k@2"]},
        "probes": {"other_summary": {"probe": "history_summary", "ref": "memory:k", "as": "project:b"},
                   "other_history_mentions": {"probe": "history_mentions", "ref": "memory:k", "as": "project:b",
                                              "tokens": ["memory:k", "memory:k@2", "dawn", "noon", "v2", "v3", "project:a"]}},
        "expect": {"other_history": None, "other_history_unknown": None,
                   "other_summary": {"eq": {"current": None, "state_version": 0, "tombstoned": False}},
                   "other_history_mentions": {"eq": []}},
        "record": ["other_history", "other_history_unknown"],
        "clauses": [(SD, ["parked_b_states", "parked_b_after", "parked_b2_after", "other_summary", "other_history_mentions"]),
                    (VERSIONS, ["other_summary"])],
        "note": "B's parked proposal is on B's own new id. Its own-namespace history is not decided by a clause (R1); A's tombstoned view and the v0 receipts are unchanged.",
    },
    "W8-recreated-generation-starts-its-own-counter": {
        "tokens": {"b1_mentions": ["v3", "memory:k", "memory:k@2", "dawn", "noon"]},
        "tokens_add": {"other_history_mentions": ["memory:k@3"]},
        "expect": {"a_back": {"eq": True}, "a_back_refusal": {"eq": None}, "owner_history": {"eq": history("memory:k@3", 1)},
                   "head": {"eq": "memory:k@3"}},
        "clauses": [(SD, ["b1_snapshot", "b1_before", "b1_after", "a_back", "other_history", "other_history_mentions"]),
                    (OPEN, ["a_back", "a_back_refusal"]), (VERSIONS, ["owner_history", "head", "b2_before", "b2_after"])],
        "note": "B's first write is B's own generation (v0 -> v1, unchanged); A's own deleted id stays open to A, whose re-creation starts its own counter (history version 1).",
    },
    "W2-correct-forget-dispute-by-other": {
        "note": "On a scope-distinct store these facade probes compare B's own never-written key with an unknown id, so they test key binding (SD), not the canonical gate (pre-execution review F-6). The canonical gate is exercised by W2h; correct, permanent deletion and dispute by reference at the host layer are a recorded residual.",
    },
    # ------------------------------------------------------------------ L family
    "L3-other-project-recreation-is-isolated": {
        "tokens": {"a_mentions": ["gen-b", "dusk"]},
        "tokens_add": {"other_mentions": ["memory:f@3", "midnight"], "other_history_mentions": ["memory:f@3"]},
        "expect": {"a_rem": {"eq": True}, "a_rem_refusal": {"eq": None}, "a_rem_after": {"eq": "v1"}, "a_cor": None, "a_cor_refusal": None,
                   "a_del": {"eq": True}, "a_del_refusal": {"eq": None}, "head": {"eq": None}, "owner_history": None},
        "record": ["a_cor", "a_cor_refusal", "owner_history"],
        "clauses": [(SD, ["a_rem", "a_del", "head", "owner_mentions", "other_mentions", "other_history", "other_history_mentions"]),
                    (OPEN, ["a_rem", "a_rem_refusal"]), (VERSIONS, ["a_rem_after"]),
                    (FORMER, ["a_disp", "a_disp_refusal", "a_disp_fact", "a_disp_fact_refusal"])],
        "note": "B's use of the same public key is a separate memory, so A re-creates and deletes its own id as on a store without B. a_cor corrects to the value a_rem just wrote (R1), so A's resulting version count is recorded, not expected.",
    },
    "L4-three-generations-as-of-barriers": {
        "probes": {"other_at_gen3_canonical": {"probe": "version_in_effect", "ref": "memory:f", "at": "gen3", "as": "project:b",
                                               "ref_scope": "project:a"}},
        "expect": {"b_back": {"eq": True}, "other_history": {"eq": history("project:b|memory:f", 1)},
                   "other_at_gen3_canonical": {"eq": None}},
        "clauses": [(SD, ["b_back", "other_history"]), (OPEN, ["b_back"]), (VERSIONS, ["other_history"]),
                    ({"source": DOC44, "clause": "the former generation's count never reaches the new one"}, ["other_at_gen3_canonical"])],
        "note": "B re-creates its own deleted id (SD, OPEN). Every as-of barrier is unchanged.",
    },
    # ------------------------------------------------------------------ R family
    "R6b-refused-proposals-on-the-tombstoned-id-carry-no-former-count": {
        "probes": {"a_back_committed": {"probe": "op_result", "name": "a_back", "field": "committed"}},
        "tokens": {"a_back_mentions": ["gen-b", "mid"], "a_disp_mentions": ["gen-b", "mid"]},
        "record": ["a_back_committed"],
        "clauses": [(SD, ["parked_mentions", "a_back_mentions", "a_disp_mentions", "other_view", "other_history_mentions"])],
        "note": "A's re-creation writes the value of its own deleted version; no cited clause decides readmission of that value (R1). M1 drops version tokens from A's own receipts.",
    },
    "R3-owner-view-stable-under-other-scope-with-distinct-generation-lengths": {
        "note": "On a scope-distinct store B's re-creation is B's own memory, so this case tests that A's deleted view is stable under namespacing. Cross-scope re-creation of A's canonical id is exercised by the host-layer variants W7c-h, W8-h, L3-h and E6-h (pre-execution review F-5). Expectations unchanged.",
    },
    "E6-re-creation-by-the-citing-scope": {
        "note": "Through the facade, B's memory:q is B's own memory. B's re-creation of A's deleted canonical id is E6-h (pre-execution review F-5). Expectations unchanged.",
    },
    "E6a-after-the-citing-scopes-own-deletion": {
        "note": "Through the facade, B's memory:q is B's own memory; the canonical-layer variant is E6a-h. Expectations unchanged.",
    },
    "E6r-after-the-citing-scopes-own-deletion-and-reopen": {
        "note": "Through the facade, B's memory:q is B's own memory; the canonical-layer variant is E6r-h. Expectations unchanged.",
    },
    "R5-recreated-history-only-own-events": {
        "tokens_add": {"other_history_mentions": ["memory:t@2"]},
        "expect": {"a_back": {"eq": True}},
        "clauses": [(SD, ["a_back", "other_history", "other_history_mentions"]), (OPEN, ["a_back"])],
        "note": "A's own deleted id stays open to A (SD, OPEN). B's history still carries only its own events.",
    },
}

NEW_CASES = {
    "cross-scope-write-authority-denial-v4": [
        {
            "id": "W1h-host-built-promotion-naming-the-owners-canonical-memory",
            "invariants": ["W1"],
            "clauses": [{**GATE_W1, "observables": ["h_committed", "h_refusal", "h_before", "h_after", "h_mentions", "episode", "head",
                                                    "owner_history", "owner_recall"]},
                        {**SD, "observables": ["other_recall"]}],
            "steps": [
                {"op": "remember", "ref": "memory:k", "text": "Marrow lighthouse keeper shift is dawn", "name": "a1", "require_committed": True},
                {"op": "commit_with_episode", "ref": "memory:k", "ref_scope": "project:a", "episode": "episode:host-b",
                 "text": "Marrow lighthouse keeper shift is dusk", "as": "project:b", "name": "h"},
            ],
            "probes": {
                "h_committed": {"probe": "op_result", "name": "h", "field": "committed"},
                "h_refusal": {"probe": "op_result", "name": "h", "field": "refusal"},
                "h_before": {"probe": "op_result", "name": "h", "field": "before_state"},
                "h_after": {"probe": "op_result", "name": "h", "field": "after_state"},
                "h_mentions": {"probe": "op_mentions", "name": "h", "tokens": ["memory:k", "dawn", "v1"]},
                "episode": {"probe": "episode_present", "episode": "episode:host-b"},
                "head": {"probe": "canonical_head", "ref": "memory:k"},
                "owner_history": {"probe": "history", "ref": "memory:k"},
                "owner_recall": {"probe": "recall_admitted", "query": "Marrow lighthouse keeper shift"},
                "other_recall": {"probe": "recall_admitted", "query": "Marrow lighthouse keeper shift", "as": "project:b"},
            },
            "expect": {"other_recall": {"eq": []}, "h_committed": {"eq": False}, "h_refusal": {"eq": "target_unavailable"}, "h_before": {"eq": "v0"},
                       "h_after": {"eq": "v0"}, "h_mentions": {"eq": []}, "episode": {"eq": False}, "head": {"eq": "memory:k"},
                       "owner_history": {"eq": history("memory:k", 1)}, "owner_recall": {"eq": ["memory:k"]}},
            "dsl5_disposition": "H1: the -v3 W1 assertion, made through the host layer because the facade can no longer name A's memory on a scope-distinct store. The runner's host commit records before/after only, so state_snapshot is not captured.",
        },
        {
            "id": "W2h-host-built-pruning-naming-the-owners-canonical-memory",
            "invariants": ["W2"],
            "clauses": [{**GATE_W2, "observables": ["h_committed", "h_refusal", "h_never_committed", "h_never_refusal", "tombstones",
                                                    "head", "valid", "owner_recall"]},
                        {**ADAPTER, "observables": ["h_refusal", "h_never_refusal"]}],
            "steps": [
                {"op": "remember", "ref": "memory:k", "text": "Marrow lighthouse keeper shift is dawn", "require_committed": True},
                {"op": "delete_version", "ref": "memory:k", "ref_scope": "project:a", "fact": "memory:k", "as": "project:b", "name": "h"},
                {"op": "delete_version", "ref": "memory:never", "ref_scope": "project:a", "fact": "@literal:ref-999999",
                 "as": "project:b", "name": "h_never"},
            ],
            "probes": {
                "h_committed": {"probe": "op_result", "name": "h", "field": "committed"},
                "h_refusal": {"probe": "op_result", "name": "h", "field": "refusal"},
                "h_never_committed": {"probe": "op_result", "name": "h_never", "field": "committed"},
                "h_never_refusal": {"probe": "op_result", "name": "h_never", "field": "refusal"},
                "tombstones": {"probe": "tombstoned_ids"},
                "head": {"probe": "canonical_head", "ref": "memory:k"},
                "valid": {"probe": "fact_valid", "fact": "memory:k"},
                "owner_recall": {"probe": "recall_admitted", "query": "Marrow lighthouse keeper shift"},
            },
            "expect": {"h_committed": {"eq": False}, "h_refusal": {"eq": "fact_not_found"}, "h_never_committed": {"eq": False},
                       "h_never_refusal": {"eq": "fact_not_found"}, "tombstones": {"eq": []},
                       "head": {"eq": "memory:k"}, "valid": {"eq": True}, "owner_recall": {"eq": ["memory:k"]}},
            "dsl5_disposition": "H1: the -v3 W2 deletion assertion through the host layer. The same host step naming an id nobody wrote is the control, and both must read fact_not_found.",
        },
    ],
}

def _host_recreation(text, ref, label, name=None, require=True):
    step = {"op": "commit_with_episode", "ref": ref, "ref_scope": "project:a", "episode": f"episode:{label}", "text": text,
            "as": "project:b", "label": label}
    if name:
        step["name"] = name
    if require:
        step["require_committed"] = True
    return step


# (target fixture, source case, new id, {step index: replacement or None}, dropped probes, probe additions,
#  expect overrides, note)
HOST_VARIANTS = [
    ("cross-scope-write-authority-denial-v4", "W7c-former-owner-attempts-leave-no-trace-in-the-new-generation",
     "W7c-h-former-owner-answers-after-a-host-built-cross-scope-re-creation",
     {2: lambda st: _host_recreation(st["text"], st["ref"], "gen-b")},
     ["other_history", "other_history_mentions", "other_recall"],
     {"head": {"probe": "canonical_head", "ref": "memory:k"}}, {"head": {"eq": "gen-b"}},
     "B re-creates A's deleted canonical id through the host layer (OPEN). A's answers are the -v3 ones (FORMER: the same whether or not another scope has since re-created the id). B's facade cannot name that memory, so the B-side probes are replaced by the canonical head."),
    ("cross-scope-write-authority-denial-v4", "W8-recreated-generation-starts-its-own-counter",
     "W8-h-host-built-cross-scope-re-creation-starts-its-own-counter",
     {3: lambda st: _host_recreation(st["text"], st["ref"], "gen-b", name="b1", require=False), 6: None},
     ["b1_snapshot", "b2_before", "b2_after", "other_history", "other_history_mentions"],
     {}, {"head": {"eq": "gen-b"}},
     "B's host-built re-creation of A's deleted canonical id starts its own counter (v0 -> v1). A's re-creation attempt then reads target_unavailable, and A keeps the version its deletion recorded. B's facade correction (-v3 b2) cannot name that memory and is dropped. The host commit records no state_snapshot."),
]
HOST_VARIANTS += [
    ("deleted-lineage-generations-and-restart-v4", "L3-other-project-recreation-is-isolated",
     "L3-h-host-built-cross-scope-re-creation-is-isolated",
     {3: lambda st: _host_recreation(st["text"], st["ref"], "gen-b")},
     ["other_mentions", "other_history", "other_history_mentions"], {}, {},
     "B re-creates A's deleted canonical id through the host layer. Every A-side expectation is the -v3 one: target_unavailable on remember, fact_not_found on correct, forget and dispute, already_deleted at the fact level, and a head that is B's generation."),
]
for _source, _new in (("E6-re-creation-by-the-citing-scope", "E6-h-host-built-re-creation-by-the-citing-scope"),
                      ("E6a-after-the-citing-scopes-own-deletion", "E6a-h-after-the-citing-scopes-own-host-built-deletion"),
                      ("E6r-after-the-citing-scopes-own-deletion-and-reopen",
                       "E6r-h-after-the-citing-scopes-own-host-built-deletion-and-reopen")):
    HOST_VARIANTS.append((
        "evidence-reference-authorization-v2", _source, _new,
        {4: lambda st: _host_recreation(st["text"], st["ref"], "q-b", name="recreate"),
         6: lambda st: {"op": "delete_version", "ref": "memory:q", "ref_scope": "project:a", "fact": "q-b", "as": "project:b",
                        "require_committed": True}},
        [], {}, {},
        "B re-creates A's deleted canonical id through the host layer and, where the -v3 case does, deletes its own generation there. Expectations are the -v1 ones."))

INVARIANTS = {
    "W1": "Another project's promotion of the same public key creates that project's own memory (receipt v0 -> v1, snapshot v0) and leaves the owner's head, version, recall and history byte-identical; a host-built promotion from another project that names the owner's canonical memory is refused with target_unavailable, v0/v0, retains no episode and discloses nothing (W1h).",
    "W2": "correct, forget, permanent forget and dispute from another project of a public key it never wrote read byte-identically (ids and timestamps folded) to the same call on an id nobody wrote, and change nothing; a host-built governed pruning from another project naming the owner's canonical memory reads fact_not_found and changes nothing (W2h).",
    "W3": "Across restarts, another project's writes to the same public key act only on its own memory, which it may correct and delete like any owner; the owner's head, version, history and recall never move.",
    "W4": "An override leaving required isolation domains outside the bound domains is malformed (ValueError with one fixed message, checked first); every other override that changes the handle's project or isolation domains -- a superset naming the owner's project, or a complete re-declaration of the owner's scope -- is refused with ValueError for any target and operation, so nothing is written, deleted or disputed (facade identity binding, store-open 1.0.0).",
    "W6": "A host-built proposal from another project naming the owner's canonical memory, and one parked by policy review, persist no episode, live and after restart; a committed proposal keeps its episode.",
    "W7": "Another project's operations on the same public key, and its attempts on the owner's fact by uuid, leave no event, identifier or text in the owner's history; a former owner may re-create its own deleted id whatever another project does with the same public key, and its fact-level answers on the deleted generation stay already_deleted; the other project's history names only its own memory.",
    "W8": "Generations are counted per (project, key): another project's first write is its own generation (v0 -> v1); the owner's re-creation of its deleted id starts its own counter; a refused or policy-parked proposal on a tombstoned or new id reports v0; the owner's deleted view keeps the version its deletion recorded until it re-creates.",
    "L3": "Another project's use of the same public key is a separate memory: the former owner reads nothing of it and re-creates and deletes its own id as on a store without that project (fact-level answers on its deleted generation stay already_deleted); the other project's memory reads nothing of the former owner's.",
    "L4": "Every deleted version is an as-of barrier for every reader, a live generation resolves only for its owner and only from its own start, and each project's re-creation after its own deletion is its own generation.",
    "E6": "B's citation of A's deleted fact stays admitted throughout. When B re-creates A's deleted id at the canonical layer (host-built: E6-h, E6a-h, E6r-h), B's derivation of that generation follows B's own deletion of it, live and after reopen; through the facade B's same public key is B's own memory (E6, E6a, E6r). A chain of B's memories rooted in A's deleted fact is admitted end to end.",
    "R5": "A re-created generation's public history carries only its own events and nothing of another project's memory of the same public key or of a former generation; the owner may re-create its own deleted id independently.",
}

TITLES = {
    "cross-scope-write-authority-denial-v4": "On a scope-distinct store a public key names one memory per project; no project's operation moves, discloses or depends on another's, and the canonical write gate refuses host-built proposals naming another project's memory",
    "deleted-lineage-generations-and-restart-v4": None,
    "public-tombstone-redaction-and-observer-separation-v4": None,
    "evidence-reference-authorization-v2": None,
}

MENTION_PROBES = ("op_mentions", "history_mentions", "recall_mentions")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def sha256_at(commit, path):
    return hashlib.sha256(subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout).hexdigest()


def successor_case(case: dict) -> dict:
    case = copy.deepcopy(case)
    change = CHANGES.get(case["id"])
    if change is None:
        case["dsl5_disposition"] = "carried forward unchanged: its observables do not depend on the store profile"
        return case
    for index, patch in change.get("steps", {}).items():
        case["steps"][index].update(patch)
    for name, spec in change.get("probes", {}).items():
        if spec is None:
            case["probes"].pop(name)
        else:
            case["probes"][name] = spec
    for name, tokens in change.get("tokens", {}).items():
        assert case["probes"][name]["probe"] in MENTION_PROBES, name
        case["probes"][name]["tokens"] = tokens
    for name, tokens in change.get("tokens_add", {}).items():
        assert case["probes"][name]["probe"] in MENTION_PROBES, name
        case["probes"][name]["tokens"] = list(dict.fromkeys([*case["probes"][name]["tokens"], *tokens]))
    for name, matcher in change.get("expect", {}).items():
        if matcher is None:
            case["expect"].pop(name, None)
        else:
            case["expect"][name] = matcher
    case["record"] = sorted(set(case.get("record", [])) | set(change.get("record", [])))
    for clause, observables in change.get("clauses", []):
        case.setdefault("clauses", []).append({**clause, "observables": observables})
    case["dsl5_disposition"] = change["note"]
    missing = (set(case["expect"]) | set(case["record"])) - set(case["probes"])
    assert not missing, (case["id"], missing)
    return case


def host_variant(source_case: dict, new_id: str, steps: dict, drop: list, probes: dict, expect: dict, note: str) -> dict:
    case = copy.deepcopy(source_case)
    case["id"] = new_id
    new_steps = []
    for index, step in enumerate(case["steps"]):
        if index in steps:
            if steps[index] is not None:
                new_steps.append(steps[index](step))
        else:
            new_steps.append(step)
    case["steps"] = new_steps
    for name in drop:
        case["probes"].pop(name)
        case["expect"].pop(name, None)
    case["record"] = [r for r in case.get("record", []) if r not in drop]
    case["probes"].update(probes)
    case["expect"].update(expect)
    clauses = [{**c, "observables": [o for o in c.get("observables", []) if o not in drop]} for c in case.get("clauses", [])]
    clauses.append({**OPEN, "observables": [k for k in case["expect"] if k in ("recreated", "b1_before", "b1_after")]})
    clauses.append({**FORMER, "observables": sorted(case["expect"])})
    case["clauses"] = clauses
    case["dsl5_disposition"] = "host-layer variant (pre-execution review F-5): " + note
    return case


def assert_traced(case: dict) -> None:
    """Every expected observable follows from a cited clause or is a labelled positive control (review F-7)."""
    traced = {o for c in case.get("clauses", []) for o in c.get("observables", [])} | set(case.get("controls", []))
    untraced = set(case["expect"]) - traced
    assert not untraced, (case["id"], sorted(untraced))


def main() -> None:
    base_commit = git("rev-parse", "HEAD")
    for source, target in SOURCES.items():
        fixture = json.loads((HERE / f"{source}.json").read_text(encoding="utf-8"))
        out = {
            "replay_id": target,
            "fixture_version": fixture["fixture_version"] + 1,
            "dsl_version": DSL,
            "store_profile": PROFILE,
            "owning_issue": fixture["owning_issue"],
            "frozen_on": "2026-10-28",
            "status": f"supersedes_{source.rsplit('-', 1)[1]}_on_the_integrated_v7_tree",
            "supersession_reason": (
                f"{source} ({fixture['dsl_version']}) opens several projects in one root; the integrated v7 candidate "
                "(#836 x #786, store-open contract 1.0.0) refuses that on its default single_project_v1 profile, so its "
                "evidence (674-cumulative-candidate/security-replays-2ad4cf23...) cannot be re-recorded and is STALE. "
                "This generation runs every case on the supported multi-project profile, scope_distinct_v1; expectations "
                "change only where the store-open contract changes what the case observes (author_fixtures_dsl5.py)."),
            "superseded_fixture": {"path": f"reference/fixtures/786-security-replays/{source}.json",
                                   "sha256": hashlib.sha256((HERE / f"{source}.json").read_bytes()).hexdigest()},
            "base_commit": base_commit,
            "independence": fixture["independence"],
            "stop_lines": fixture["stop_lines"],
            "title": TITLES[target] or fixture["title"],
            "contract_sources": [{"path": s["path"], "sha256_at_base": sha256_at(base_commit, s["path"])}
                                 for s in fixture["contract_sources"]],
            "invariants": [{**inv, "statement": INVARIANTS.get(inv["id"], inv["statement"])} for inv in fixture["invariants"]],
            "cases": [successor_case(c) for c in fixture["cases"]] + copy.deepcopy(NEW_CASES.get(target, [])),
            "residuals": [
                "Host-layer correct, permanent deletion and dispute by logical reference naming another project's canonical "
                "memory are not replayed by DSL/5, which has host steps for promotion (commit_with_episode) and governed pruning "
                "(delete_version) only. That canonical gate is covered by reference/tests/test_786_cross_scope_write_authority.py "
                "and test_786_cross_scope_write_guard.py on the tenant-wide test fixture (pre-execution review F-6).",
            ],
        }
        by_id = {c["id"]: c for c in fixture["cases"]}
        for variant_target, source_id, new_id, steps, drop, probes, expect, note in HOST_VARIANTS:
            if variant_target == target:
                out["cases"].append(host_variant(by_id[source_id], new_id, steps, drop, probes, expect, note))
        for case in out["cases"]:
            assert_traced(case)
        if not any(s["path"] == DOC44 for s in out["contract_sources"]):
            out["contract_sources"].append({"path": DOC44, "sha256_at_base": sha256_at(base_commit, DOC44)})
        ids = [c["id"] for c in out["cases"]]
        assert len(ids) == len(set(ids)), target
        (HERE / f"{target}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        changed = sum(1 for c in out["cases"] if not c.get("dsl5_disposition", "").startswith("carried forward"))
        print(f"{target}: {len(out['cases'])} cases, {changed} changed or new")


if __name__ == "__main__":
    main()
