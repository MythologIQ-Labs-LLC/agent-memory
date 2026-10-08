# Failure memory into recall: shadow qualification (#690)

**Status:** Evaluation-only implementation, not a product/runtime integration. Parent: [#690](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/690), [#668](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/668). Independent of currentness #732 and adaptive controller #731.

## Why this is a real memory capability

Agent Memory retains a first-party, governed negative/failure memory with revisions, recurrence evidence, dispute, retraction, and specialized contextual recall. Yet the public facade does not compose its output. A downstream agent consequently cannot rely on ordinary recall as proof that it has received **usable, scope-authorized, current failure-specific evidence**.

The gap is not a benchmark score or an English phrase classification. It is an integration and meaning problem:

~~~text
ordinary adapter recall
  -> generic candidates
  -> ordinary governed admission
  -> [not equivalent to] failure-specific usable evidence

FailureMemory.recall_active
  -> same adapter's governed admission
  -> validate failure owner/fact linkage
  -> contextual applicability
  -> current active failure revision
  -> usable negative experience evidence

usable evidence != authority to block/deny an action
recurrence != proof of causation
impact/severity != approval
generic admission != specialized failure admission
~~~

## Implemented qualification slice

`reference/agentmem_ref/evaluation/failure_recall_shadow.py` uses the **existing** `FailureMemory.recall_active` method, so it does not copy admission or contextual gate logic. It produces a diagnostic `ShadowFailureRecall` with:
- generic candidate/admitted fact IDs for comparison;
- usable active failure revisions **only after** the actual specialized gate;
- typed contextual/refusal reasons, sorted for deterministic inspection;
- occurrence count, causal posture, severity, action class and revision identity as **descriptive evidence**;
- explicit `authority_effect=none`, `mutates_memory=false`, and `integration_state=evaluation_only`.

It performs one existing specialized recall call and does not modify failure history, action approvals, recurrence, PAMA, canonical state, or facade output. It never invents a similarity score from lexical overlap. The module lives in the baseline-declared **evaluation exclusion** and is not imported by production runtime.

### Repeatable local checks

~~~sh
PYTHONPATH=reference python -m unittest tests.test_failure_recall_shadow -v
python scripts/check_runtime_baseline_equivalence.py
~~~

Tests use the real in-memory governed substrate, real failure revision lifecycle and actual `FailureMemory.recall_active` gate for successful reads, scope isolation, disputed/retracted revisions and read-only properties. A small number of deliberate mocked outcomes check whether a future facade could accidentally mistake generic admission for failure usability even if a malformed upstream reply claimed it was active.

These tests are **behavioral conformance/qualification**, not an external benchmark. They do not assert superiority, optimize on benchmark examples, or import scorer golden labels. Do not promote this qualification into a same-harness competitor row.

## Future runtime tranche, explicitly NOT implemented here

A real public-facade capability must have a versioned, owner-controlled failure-memory binding. The future contract will need to answer:

1. How does the facade obtain a qualified, restart-safe `FailureMemory` owner for the same tenant, scope, actor, and substrate rather than constructing a new process-local owner?
2. How are failure-revision provenance and identity bound across restarts and corrections, and what happens if an owner snapshot is missing or stale?
3. Can one governed recall admission result be reused safely, rather than calling the underlying admission engine twice with inconsistent state? Shadow qualification uses one specialized call today.
4. Should returned failure metadata be a separate typed evidence field, never a ranking feature or permission gate? What is the minimal disclosure surface for each scope?
5. How will a consumer distinguish a recalled failure, a disputed/retracted record, absence of evidence, and an actual authority decision? A failure recollection cannot veto actions on its own.
6. How can opt-in be demonstrated byte-equal to the current default on existing accepted benchmark lanes?

Any production implementation must declare the next Runtime Baseline successor, retain the accepted -v2 (and current -v6) exact replay floors, test permissions and negative controls, and pass the governed lane gate. **Do not open a competing v7 declaration while #732's R6 extraction acceptance remains under local qualification.**

## Independent broad tests to run before acceptance

- Real incidents that are related but have distinct canonical identities; do not conflate them based on similarity alone.
- Repeated failures with explicit evidence, and false recurrences that must not increase count.
- Disputed source facts, legal hold/retraction and stale cached revision owners.
- Cross-tenant/project/actor and purpose mismatch.
- Memory with a known prior failure where lexical retrieval misses the query: candidate discovery is a separate capability defect; the shadow layer must not claim success.
- Failure that was legitimately admitted in generic memory but whose failure-specific applicability is denied.
- An agent attempting to use a recalled critical failure to override an approved host action: blocked without separate authority.

**Decision:** this slice is useful non-overlapping progress while Claude runs currentness benchmarks. Runtime semantics are intentionally unchanged. A stronger facade integration waits for a governed successor, independently frozen memory-specific conformance, and exact external replay.
