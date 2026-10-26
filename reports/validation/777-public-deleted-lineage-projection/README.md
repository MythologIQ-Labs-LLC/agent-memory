# #777 public deleted-lineage read projection

| | |
|---|---|
| Contract branch | `evaluation/777-public-deleted-identifier-contract-no-ci` @ `0a9f69459ac1745c1e19643eb27f6b600ede6f44` (verified; base `5d90965`) |
| Implementation | `implementation/777-public-deleted-identifier-redaction-no-ci`: independent tests `1d8d8a4` (fail) → `27c2626` → **`541c09f`** |
| Protected blobs at `541c09f` | `api/surface.py` `eb95340f…`, `runtime/adapter.py` `50120369…`, `runtime/recall_control.py` `c049d23f…`, `schemas/api-result-envelope.schema.json` `251dd11b…` |
| Environment | Claude Code cloud, evaluator `9961067`. No Actions, no PR, no merge, no v7 change. |
| Verdict | **Implemented; CHANGES REQUIRED before promotion.** Two governance items are needed: a successor declaration that bumps the public contract to 1.7.0, and an owner decision on an authorized audit interface. All functional gates pass. |

## Preregistered tests at `0a9f694`
- 3 of 4 fail as intended: deleted IDs appear in recall `admissions`/`candidates`, also after restart, and in a survivor's `write_semantics` relations.
- The live-provenance control passes.

## Counterexample beyond the issue (recorded before code)
`AgentMemory.history()` had **no reader scope**. A `project:b` handle saw that `project:a`'s `memory:a` existed and was deleted (`tombstoned: true`, 9 events including `memory.delete` with timestamps), which is distinguishable from a nonexistent memory (`logs/probe_history_cross_project.py`). This is pre-existing on v7.

## What the projection does (after canonical governance; admission unchanged)
| Surface | Ordinary handle sees |
|---|---|
| `AgentMemory.recall` and stage `recall` | Deleted-generation fact IDs and refusal reasons in the deletion family (`tombstoned`, `logical_memory_deleted`, `derived_from_*`) are removed from `candidates` and `admissions`. Any withheld ID inside visible decisions (route provenance, ranking evidence) is dropped. The response carries `public_projection: {policy_id: public-deleted-lineage-redaction, policy_version: 1.0.0, deleted_lineage: withheld}`. |
| Shadow recall control | Route counts, candidate count and **stop reason** are computed over public candidates only. Before: `frontier_exhausted` vs `no_evidence` revealed that a deleted memory matched. |
| `write_semantics` (surviving fact) | Relations naming a withheld fact or memory are dropped from the read; `relation_count` is reduced by exactly that number (count-only relations are kept). **Stored semantics are unchanged.** There is no marker here, to keep the extractor-off byte identity. |
| `history` | A memory whose current fact is out of scope or deleted reads exactly as unknown: `{current_fact_uuid: null, state_version: 0, tombstoned: false, events: []}`, and `rejected_values: []`. For a live or re-created memory, only the live generation's events are shown, and every deletion correlation is omitted. A disputed memory remains visible: the privacy boundary is deletion plus scope, not admission. |
| `ControlledRecallPlanner` graph hits | Reported paths come from a second traversal that neither reports nor passes through deleted generations. **Canonical candidates and refusals are unchanged** (the #776 graph test still sees the residue refused). |
| Internal audit | `tombstones`, adapter `events`, stored semantics and canonical recall are retained. `AgentMemory._canonical_recall` / `_canonical_history` are **in-process evaluation only** and not part of the public contract. Governance evaluators (temporal-currentness gauntlet, AgentMemBench runner, RC scenario) and tests that assert refusals now read the canonical record. Their outputs are byte-identical to before. |

**Indistinguishability.** For the same query, a store where the matching memory was deleted and a store where it never existed give byte-identical public recall, with and without shadow control. The only exception is the controller's wall-clock `usage.elapsed_ms`, which is computed from the query and normalized in the test.

## Tests
- `test_777_public_projection_review.py` (15 tests) covers:
  - exact-identity named deleted memory vs unknown;
  - indistinguishability, with and without shadow control;
  - derived (2 hops) withheld vs live derivations kept;
  - partial (superseded-version) deletion;
  - re-created memory id;
  - restart;
  - cross-project, same-project-deleted and re-created `history`;
  - graph paths;
  - stage-level recall;
  - survivor relations dropped while stored semantics are unchanged;
  - live relation preserved;
  - versioned marker.
- Results: 19/19 #777 tests pass (`logs/777_tests_at_541c09f.log`).
- **Migrated old-contract tests** (each now asserts the canonical record keeps the refusal or tombstone **and** the public projection withholds it): `test_historical_evidence_admission`, `test_bm25_hash_seed_determinism`, `test_candidate_materialization`, `test_developer_facade`.

## Regression
- **Full suite at `541c09f`:** 2755 run, 5 failures = 4 protected-runtime freeze guards (now also naming the new protected files) plus the pre-existing durability failure.
- **First cut `27c2626`:** 16 failures, all triaged and fixed in `541c09f`:
  - package-layout rule;
  - `write_semantics` byte identity;
  - `relation_count` for count-only relations;
  - disputed memory hidden from `history`;
  - evaluators and tests reading public output for governance.
- **Served quality:** byte-identical to `5d90965` on Halcyon, Cedarline, Brightwater, Fenmoor and the blind theatre corpus. The projection never changes admission (`runs/`).

## Versioning and remaining decisions
1. **Public contract version.** `contract_version` stays **1.6.0** because it is pinned by the frozen v7 baseline identity (`test_runtime_baseline_succession`). The change is versioned as an additive, independently versioned `public_projection` policy field. The *candidate* semantics of contract 1.3.0 (refused residue listed) change for deleted lineage, so a successor declaration should publish this as **contract 1.7.0** with a migration note.
2. **Authorized audit interface.** None was added. Detailed records are internal only (not reachable through the scoped handle), per issue item 6. A governed, separately authorized audit reader is a separate slice; **no debug flag grants it**.
3. **Residual linkable fields:**
   - `history.state_version` of a re-created memory counts writes from the deleted generation.
   - Event and fact id sequence numbers are global counters, so gaps can suggest that writes happened.
4. **Base:** this branch is based on `5d90965`, not on the #776 memo fix `bd16a7e`. They are independent slices and are not combined.
