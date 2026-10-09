# #644 — Read-only committed transition witness

**State:** staged on unopened quiet branch, outside Claude's independent #644 validation branch. Not merged, benchmark-qualified, authorized for stopping, or published as a runtime baseline. Immutable Runtime Baseline v6 remains active.

## Precise problem

A proposition with `assertion=change` is **only an assertion**. Even an existing write-time `state_change_candidate` proposal is not an applied replacement. Conversely, a recorded correction must distinguish a past **state change** (old value may have been historically valid) from an **error correction** (old value was rejected as false). Neither is evidence that a particular retrieved candidate is the *immediate* successor of that correction, because pre-existing replacement records do not store a direct successor fact UUID.

This slice implements a conservative, read-only observer of existing governed correction records, without inventing a direct successor edge.

## Executable path

```text
ControlledRecallResult.admitted (candidate IDs; caller-mutable, not attested)
    -> ControlledRecallPlanner.observe_governed_transition_witnesses
    -> GovernedMemoryAdapter.governed_applied_transition_witnesses
         source fact currently admitted and still the logical memory's current head
         source has eligible persisted caller-declared typed change assertion
         recheck tenant, domains, required domains, project, task, tombstone, dispute
         inspect persisted source-side state_change_candidate relation
         historical prior fact visible inside same reader and semantic scope
         prior is actually event-invalid; never return its raw text or values
         current target fact in the supplied admitted set and currently reauthorized
         target logical memory and strict scope match source/prior/current
         prior's durable replacement record has same logical memory and
         explicit semantic proposal ID in the correcting proposal's evidence_refs
    -> governed_transition_witness.inspect_committed_replacement
         applied_state_change_observed OR applied_error_correction_observed
         scoped proposal/current/prior/source IDs, no raw fact text
         immediate_successor_verified=false
         answer_quality_verified=false, can_stop=false, can_mutate=false
         authority_effect=none
```

The source relation must additionally carry the accepted typed basis (`typed_slot` or `typed_link`), and its recorded target memory must match the replacement record. The replacement record must include a committed replacement time. The record's `proposal_id` is the *governed correction proposal*, while the original write-time semantic `proposal_id` must appear in `evidence_refs`. Their difference matters: merely writing a source statement, proposing a change, or committing an unrelated correction must never count as applying that semantic proposal.

This is **not cryptographic attestation**: the result is derived from the committed adapter's durable record and the read-time scope, not from a third-party proof of identity or evidence independence. A caller could mutate the internal result's admitted list, so query membership and the original retrieval revision are **not immutable**, even though every exposed current fact is independently reauthorized. These witnesses must never be used as executable stopping authority.

## Guaranteed non-behaviors

- No writes, replacements, replays, pruning, correction application, PAMA bypass, audit emission or changes to normal `recall()`.
- No inference from observed text that an applied correction occurred.
- No assumption that the current head is the correction's immediate successor. It may be several governed changes later; `immediate_successor_verified` always remains false.
- No inference that state change and error correction mean the same thing. For error corrections the previous value cannot be presented as historically true.
- No automatic reinterpretation of #644 `value_coherence_unresolved` as resolved. That is a future scoped relation-and-temporal policy with independent qualification.
- No raw value payloads in the witness report. Only guarded fact and proposal references are returned.
- No cross-domain access to invalid historical text; prior scope/tenant/tombstone/dispute and current target admission checks happen before looking up the replacement record.

## Verification

**Executed locally on exact committed source and unit-test blobs:** `python -m unittest discover -s /mnt/data/am644/reference/tests -p 'test_governed_transition_witness.py' -v` passed **7/7** (Python 3.13). The exact Git blobs are `governed_transition_witness.py: 3928708751da8544c86eb5e15f59c7af194e4557`, `test_governed_transition_witness.py: bf55d608c632d1319147059432239d3884faf80c`. These tests cover missing citations, unrelated correction, wrong proposal identity/slot, differing committed correction types, no inferred immediate successor and authority-forgery refusal.

**Written but NOT run in full repository checkout:** `reference/tests/test_governed_transition_integration.py`, five cases exercising `AgentMemory.apply_semantic_proposal`, uncited correction, error correction, mismatched scope and duplicate admitted IDs. The complete adapter and planner integration, state restart durability and multi-stage correction chain must be run and reviewed locally before this can be qualified.

## Baseline candidate and independent QA

`reports/runtime/baseline-v7-declaration.json` now pins four protected runtime blobs (adapter, sufficiency observer, transition witness and recall controller) and adds `committed-governed-transition-witness-v1` as a replay gate. `reports/runtime/baseline-register.json` still declares `declared_successor=null`; Runtime Baseline **v6** controls. Reconcile all four exact blobs and the full v6 noninterference corpus before any PR or acceptance.

Once Claude completes its ongoing independent value-coherence evaluation, extend it with the five integration cases and adversarial alternatives: forged semantic `proposal_id` in correction evidence, duplicate prior/current identity, changed context, post-application removal of source/current target, error-correction refusal of historical validity, later corrections of the same target, and restart-loaded extension state. Never modify frozen benchmark cases, add a GitHub Actions workflow or optimize for the evaluator's wording.

**Not yet implemented:** signed query-membership receipts, immediate successor link persistence, decision policy for `value_coherence` resolution, or adaptive stopping. Those are separate explicitly governed evolution slices, not implicit behavior of this read-only witness.
