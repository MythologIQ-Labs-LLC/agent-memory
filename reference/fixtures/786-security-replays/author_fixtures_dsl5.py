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
FIB = {"source": DOC44, "clause": "Proposal `overrides` and the scope keywords of `recall` may restate or narrow that identity, never change it: re-declaring another project's scope through one handle is multi-project access, which a `single_project_v1` or restricted legacy store does not admit and a `scope_distinct_v1` store answers with per-project keys. An internally inconsistent override keeps its `1.8.0` refusal (`required isolation domains must also be bound isolation domains`, replay W4) and is checked first."}
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
        "probes": {"other_history_unknown": None, "other_history": {"probe": "history", "ref": "memory:k", "as": "project:b"}},
        "tokens": {"b1_mentions": ["memory:k", "project:a", "dawn"]},
        "expect": {"b1_committed": {"eq": True}, "b1_refusal": {"eq": None}, "b1_before": {"eq": "v0"}, "b1_after": {"eq": "v1"},
                   "b1_snapshot": {"eq": "v0"}, "other_recall": {"eq": ["project:b|memory:k"]},
                   "other_history_unknown": None, "other_history": {"eq": history("project:b|memory:k", 1)}},
        "clauses": [(SD, ["b1_committed", "b1_refusal", "other_recall", "other_history", "head", "owner_history", "owner_recall"]),
                    (OPEN, ["b1_committed"]), (VERSIONS, ["b1_before", "b1_after", "b1_snapshot"])],
        "note": "B's key is B's own never-written memory: creation, not a write onto A's head (SD). A's side is byte-identical, as in -v3.",
    },
    "W3-refusal-survives-restart": {
        "tokens": {"b1_mentions": ["memory:k", "memory:k@2", "dawn", "noon", "project:a"]},
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
                   "sup_rem_raised": {"eq": "ValueError"}, "sup_cor_committed": {"eq": False}, "sup_cor_raised": {"eq": "ValueError"}},
        "record": ["sup_rem_message", "sup_cor_message"],
        "clauses": [(FIB, ["bad_target", "bad_unknown", "bad_target_message", "bad_unknown_message", "sup_rem_committed",
                           "sup_rem_raised", "sup_cor_committed", "sup_cor_raised", "head", "valid", "owner_recall", "tombstones"])],
        "note": "Facade W4 is the one behaviour the integration changes (docs/44): the superset declaration naming A's project changes the handle's identity and is refused with ValueError instead of reaching the canonical gate. The malformed declaration keeps its 1.8.0 message, checked first. The identity refusal's message is recorded, not expected; no clause fixes its wording.",
    },
    "W4b-documented-dispositions-of-complete-and-superset-declarations": {
        "probes": {"sup_disp_raised": raised("sup_disp"), "sup_forget_raised": raised("sup_forget"), "complete_raised": raised("complete"),
                   "sup_disp_message": message("sup_disp"), "sup_forget_message": message("sup_forget"), "complete_message": message("complete")},
        "expect": {"sup_disp": {"eq": False}, "sup_forget": {"eq": False}, "tombstones": {"eq": []}, "complete": {"eq": False},
                   "k2_head": {"eq": "memory:k2"}, "sup_disp_raised": {"eq": "ValueError"}, "sup_forget_raised": {"eq": "ValueError"},
                   "complete_raised": {"eq": "ValueError"}},
        "record": ["sup_disp_message", "sup_forget_message", "complete_message"],
        "clauses": [(FIB, ["sup_disp", "sup_forget", "tombstones", "complete", "k2_head", "sup_disp_raised", "sup_forget_raised", "complete_raised"])],
        "note": "The -v3 dispositions (a superset declaration may dispute or delete; a complete re-declaration commits as the owner) followed from 'Scope is privileged host input' at the facade. Under store-open 1.0.0 the facade binds identity, so each is refused with ValueError and nothing is deleted or written. Host re-declaration remains available only through the module-level envelope surface.",
    },
    "W6-denied-proposals-persist-no-episode": {
        "steps": {1: {"ref_scope": "project:a"}},
        "clauses": [(GATE_W1, ["denied_committed", "denied_refusal", "denied_before", "episode_denied"])],
        "note": "H1: the denied proposal is host-built by B and names A's canonical memory (ref_scope), the host-layer route to the canonical write gate on a scope-distinct store. Expectations unchanged.",
    },
    "W7-refused-attempt-leaves-no-public-trace": {
        "probes": {"other_history_unknown": None, "other_history": {"probe": "history", "ref": "memory:k", "as": "project:b"}},
        "expect": {"b1": {"eq": True}, "other_history_unknown": None, "other_history": {"eq": history("project:b|memory:k", 1)}},
        "clauses": [(SD, ["b1", "other_history", "owner_history", "owner_history_mentions", "canonical_version"])],
        "note": "B's remember creates B's own memory (SD); A's history still carries nothing of it.",
    },
    "W7c-former-owner-attempts-leave-no-trace-in-the-new-generation": {
        "tokens": {"a_disp_mentions": ["gen-b", "dusk"]},
        "expect": {"a_rem": {"eq": True}, "a_rem_refusal": {"eq": None}, "a_forget": {"eq": True}, "a_forget_refusal": {"eq": None}},
        "clauses": [(SD, ["a_rem", "a_forget", "other_history", "other_history_mentions", "other_recall"]),
                    (OPEN, ["a_rem", "a_rem_refusal"]), (FORMER, ["a_disp", "a_disp_refusal", "a_del", "a_del_refusal"])],
        "note": "B's generation lives in B's namespace, so A's own deleted id stays open to A: a_rem re-creates it and a_forget deletes that re-creation. The fact-level answers on A's deleted generation stay already_deleted. M1 drops version tokens from A's own receipt scan.",
    },
    "W8b-refused-and-parked-proposals-on-a-tombstoned-id-report-v0": {
        "tokens": {"parked_b_states": ["v2", "v3", "memory:k", "memory:k@2"]},
        "expect": {"other_history": None, "other_history_unknown": None},
        "record": ["other_history", "other_history_unknown"],
        "clauses": [(SD, ["parked_b_states", "parked_b_after", "parked_b2_after"])],
        "note": "B's parked proposal is on B's own new id. Its own-namespace history is not decided by a clause (R1); A's tombstoned view and the v0 receipts are unchanged.",
    },
    "W8-recreated-generation-starts-its-own-counter": {
        "tokens": {"b1_mentions": ["memory:k", "memory:k@2", "dawn", "noon"]},
        "expect": {"a_back": {"eq": True}, "a_back_refusal": {"eq": None}, "owner_history": {"eq": history("memory:k@3", 1)},
                   "head": {"eq": "memory:k@3"}},
        "clauses": [(SD, ["b1_snapshot", "b1_before", "b1_after", "a_back", "other_history", "other_history_mentions"]),
                    (OPEN, ["a_back", "a_back_refusal"]), (VERSIONS, ["owner_history", "head", "b2_before", "b2_after"])],
        "note": "B's first write is B's own generation (v0 -> v1, unchanged); A's own deleted id stays open to A, whose re-creation starts its own counter (history version 1).",
    },
    # ------------------------------------------------------------------ L family
    "L3-other-project-recreation-is-isolated": {
        "tokens": {"a_mentions": ["gen-b", "dusk"]},
        "expect": {"a_rem": {"eq": True}, "a_rem_refusal": {"eq": None}, "a_rem_after": {"eq": "v1"}, "a_cor": None, "a_cor_refusal": None,
                   "a_del": {"eq": True}, "a_del_refusal": {"eq": None}, "head": {"eq": None}, "owner_history": None},
        "record": ["a_cor", "a_cor_refusal", "owner_history"],
        "clauses": [(SD, ["a_rem", "a_del", "head", "owner_mentions", "other_mentions", "other_history", "other_history_mentions"]),
                    (OPEN, ["a_rem", "a_rem_refusal"]), (VERSIONS, ["a_rem_after"]),
                    (FORMER, ["a_disp", "a_disp_refusal", "a_disp_fact", "a_disp_fact_refusal"])],
        "note": "B's use of the same public key is a separate memory, so A re-creates and deletes its own id as on a store without B. a_cor corrects to the value a_rem just wrote (R1), so A's resulting version count is recorded, not expected.",
    },
    "L4-three-generations-as-of-barriers": {
        "expect": {"b_back": {"eq": True}, "other_history": {"eq": history("project:b|memory:f", 1)}},
        "clauses": [(SD, ["b_back", "other_history"]), (OPEN, ["b_back"]), (VERSIONS, ["other_history"])],
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
    "R5-recreated-history-only-own-events": {
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
            "clauses": [{**GATE_W1, "observables": ["h_committed", "h_refusal", "h_before", "h_after", "episode", "head", "owner_history", "owner_recall"]}],
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
            },
            "expect": {"h_committed": {"eq": False}, "h_refusal": {"eq": "target_unavailable"}, "h_before": {"eq": "v0"},
                       "h_after": {"eq": "v0"}, "h_mentions": {"eq": []}, "episode": {"eq": False}, "head": {"eq": "memory:k"},
                       "owner_history": {"eq": history("memory:k", 1)}, "owner_recall": {"eq": ["memory:k"]}},
            "dsl5_disposition": "H1: the -v3 W1 assertion, made through the host layer because the facade can no longer name A's memory on a scope-distinct store.",
        },
        {
            "id": "W2h-host-built-pruning-naming-the-owners-canonical-memory",
            "invariants": ["W2"],
            "clauses": [{**GATE_W2, "observables": ["h_committed", "h_refusal", "tombstones", "head", "valid", "owner_recall"]}],
            "steps": [
                {"op": "remember", "ref": "memory:k", "text": "Marrow lighthouse keeper shift is dawn", "require_committed": True},
                {"op": "delete_version", "ref": "memory:k", "ref_scope": "project:a", "fact": "memory:k", "as": "project:b", "name": "h"},
            ],
            "probes": {
                "h_committed": {"probe": "op_result", "name": "h", "field": "committed"},
                "h_refusal": {"probe": "op_result", "name": "h", "field": "refusal"},
                "tombstones": {"probe": "tombstoned_ids"},
                "head": {"probe": "canonical_head", "ref": "memory:k"},
                "valid": {"probe": "fact_valid", "fact": "memory:k"},
                "owner_recall": {"probe": "recall_admitted", "query": "Marrow lighthouse keeper shift"},
            },
            "expect": {"h_committed": {"eq": False}, "h_refusal": {"eq": "fact_not_found"}, "tombstones": {"eq": []},
                       "head": {"eq": "memory:k"}, "valid": {"eq": True}, "owner_recall": {"eq": ["memory:k"]}},
            "dsl5_disposition": "H1: the -v3 W2 deletion assertion through the host layer.",
        },
    ],
}

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
        }
        if not any(s["path"] == DOC44 for s in out["contract_sources"]):
            out["contract_sources"].append({"path": DOC44, "sha256_at_base": sha256_at(base_commit, DOC44)})
        ids = [c["id"] for c in out["cases"]]
        assert len(ids) == len(set(ids)), target
        (HERE / f"{target}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        changed = sum(1 for c in out["cases"] if not c.get("dsl5_disposition", "").startswith("carried forward"))
        print(f"{target}: {len(out['cases'])} cases, {changed} changed or new")


if __name__ == "__main__":
    main()
