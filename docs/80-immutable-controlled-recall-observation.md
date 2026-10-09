# #644 — Immutable controlled-recall observation receipt (parallel implementation)

**Status:** staged runtime candidate on unopened quiet branch; **not qualified for merge or Runtime Baseline v7**. This module is intentionally separate from Claude's `implementation/644-safety-reconciliation-v7-review-no-ci` validation. The active published Runtime Baseline remains v6.

## Problem

`ControlledRecallResult` exposes mutable `recall.candidates`, `recall.admitted`, `recall.ranked_admitted`, `route_candidate_counts` and route results. A caller can clear a competitor, change a route count or reorder a result before asking whether enough memory was retrieved. A follow-on sufficiency observer that trusts these values would be vulnerable to the exact mutable-evidence and hidden-candidate defects exposed by Claude's independent #644 evaluation.

Being able to freeze what the planner actually produced is **necessary but insufficient** for authorizing retrieval to stop. A content hash over caller-controlled data is not a signature, a canonical state revision, or proof that the search evaluated the entire eligible slot.

## Implementation

`reference/agentmem_ref/runtime/recall_observation_receipt.py` defines:

- `RouteObservation`, a slotted frozen typed record of a selected route's limit, anchor budget, observed work and planned execution.
- `RecallObservationReceipt`, a slotted frozen record of the exact candidate, governed-admitted and ranked reference sequences, full available-route count map, selected route budgets, query and reader-context fingerprints, actual admission policy/mode and evaluated-at time.
- `capture_recall_observation(...)`, a deterministic, defensive-copy constructor with domain-separated SHA-256 over canonical JSON.
- `matches_mutable_result(...)`, which detects later modifications to membership, ranking, route execution or **any** route count, including an available route with zero planned work.

The existing `ControlledRecallPlanner.recall()` now creates the receipt **before** exposing `ControlledRecallResult`, and the result carries `observation_receipt` plus `observation_unchanged()`. The earlier candidate generation, admission, ranking, `evidence_sufficiency_met` and `stop_reason` calculations remain unchanged. The public `AgentMemory.recall` contract is not modified.

Receipt capture uses only in-memory data already produced by the normal planner. It does not search, tick clocks, create identifiers, call external providers, perform separate admissions, write to the database, or change PAMA. It can still add bounded CPU/hash/memory overhead, which must be measured independently before integration.

## Security and authority boundaries

- `snapshot_attested=false`, `slot_closure_attested=false`, `can_stop=false`, `authority_effect=none` and `state_revision=null` are **constructor-enforced**. A caller cannot set them to true or invent an accepted revision using the dataclass API.
- Frozen, slotted data plus tuple membership protect against *ordinary* Python list/dict mutation after capture. The SHA-256 detects corruption of a captured object, but **does not authenticate its producer**. A malicious in-process caller can construct a different self-consistent receipt; object-level immutability is not a trust boundary against arbitrary Python execution.
- The digest includes raw *internal* fact identity sequences in its canonical input; `to_dict()` deliberately exposes admitted references and candidate counts, not refused or hidden candidate identities. `query_digest` and `reader_digest` are **deterministic fingerprints, not confidentiality protections**, especially for low-entropy queries or scope names.
- Reader fingerprints include domain set, principal, project, purpose and task. Domain ordering is canonicalized because the recall context states that order does not encode hierarchy.
- The receipt contains no durable substrate generation, SQLite transaction snapshot, source-independence attestation, complete same-slot scan or trusted untyped-competitor classification. It cannot establish that the observation is current after a concurrent write.
- No code in this candidate may consume `observation_receipt` as permission to execute or even propose a completeness stop. The safe #644 observer's continuation-only hold remains controlling.

## Code and local validation gates

Changed protected paths are `runtime/recall_observation_receipt.py`, `runtime/recall_control.py`, and the flat compatibility alias `agentmem_ref/recall_observation_receipt.py`; `scripts/restructure_package.py` registers the new runtime module to prevent the package-layout regression that Claude found in the earlier v7 work.

Added `reference/tests/test_recall_observation_receipt.py` (11 focused cases) and an end-to-end result-mutation test in `reference/tests/test_recall_control.py`. These tests are **committed but not yet executed on a complete repository checkout**; the connected desktop remains offline. The branch is based on published `main` independently of Claude's work. No v7 declaration/register edit was made here to avoid creating a competing or invalid successor claim.

Before merging anything:

1. Locally run the 11 receipt tests, controlled recall tests, package-layout checker and full reference suite. Reproduce tests against the exact branch SHA; run no GitHub Actions for iterative debugging.
2. Test empty queries, context permutations, blank task/project, historical intent, route hit caps, large candidate lists, SQLite governed-read restart behavior, mutated route budgets and admission/ranking order, plus cross-tenant candidate privacy.
3. Verify byte-identical default public `AgentMemory.recall` and PAMA/audit output on normal and recovery scenarios versus published v6. Measure receipt capture overhead at realistic scale, including memory allocation.
4. When Claude's #644 safety reconciliation reports return, reconcile this receipt with the exact surviving v7 candidate, perform the sanctioned declaration generator and `TRANSITION` checker on **one** combined protected-file set. Do not merge or publish until the gauntlet and independent AMB/LongMemEval requirements pass.
5. Only a separately designed, authenticated read-revision and slot-closure capability may consider moving `snapshot_attested` or `slot_closure_attested` away from false. That would be a new explicit, independently qualified policy version, not a caller flag.
