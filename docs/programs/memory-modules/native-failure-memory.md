# Native Governed Negative/Failure Memory

Issue: #471  
Parent harvest closeout: #470

## Purpose

Agent Memory needs a native way to retain what went wrong without turning remembered failure into standing authority.

EvolveAI Shadow Genome is useful implementation ancestry for typed failure state, stable identity, repeat detection, persistence pressure, bounded capacity, and similarity-based recurrence evidence. Its direct similarity-to-block behavior is not adopted.

The Agent Memory boundary is:

```text
failure observation
  -> stable logical failure identity
  -> typed failure revision and evidence
  -> Cognitive Mesh proposal
  -> existing PAMA-governed commit / review / refusal
  -> ordinary governed recall
  -> non-authoritative failure evidence
  -> downstream action or mutation remains separately governed
```

## Non-authority doctrine

These are useful signals:

```text
similarity
severity
impact estimate
repeat count
recurrence evidence
root-cause hypothesis
mitigation history
```

None of them means:

```text
PASS
BLOCK
truth
certification
permanence
mutation permission
action permission
```

A critical remembered failure at similarity `1.0` is still evidence. It may be stale, disputed, superseded, out of scope, based on a bad causal explanation, or irrelevant to the current environment.

## Identity

`derive_failure_ref()` hashes caller-declared stable identity inputs:

```text
scope
action_class
category
identity_basis
```

The explicit `identity_basis` exists so mutable exception prose, generated explanation text, or a transient stack trace does not silently become logical identity.

Repeated observations of the same logical failure extend one append-only revision history. Similar but materially different failures should use distinct identity bases.

## Revision model

Each `FailureRevision` preserves:

- logical failure and revision identity;
- action class;
- summary;
- category;
- causal status: `observed`, `inferred`, or `hypothesis`;
- governed scope/isolation/project/task/purpose;
- expected and actual outcomes;
- open severity label and optional bounded impact estimate;
- root-cause candidates;
- mitigation;
- verification evidence;
- applicability conditions;
- source evidence;
- explicit recurrence evidence;
- optional similarity estimator output;
- current/disputed/retracted state;
- estimator identity/version when similarity is present.

Failure categories and severity labels remain open domain vocabulary. This implementation does not establish a universal failure ontology.

## Recurrence semantics

The initial observed failure counts as one occurrence. Further recurrence requires an explicit recurrence evidence reference and a governed revision.

```text
same logical failure observed again
    -> may add recurrence evidence

similar failure candidate
    -> similarity evidence only

independent evidence about cause
    -> may strengthen a causal explanation under its own evidence semantics

same memory recalled five times
    -> no new recurrence
    -> no new corroboration
```

Duplicate recurrence evidence is rejected before substrate mutation.

## Correction, dispute, and retraction

A correction extends the current revision. It cannot silently change governed scope or action-class identity.

A disputed failure memory stays retained and historically visible, but the reference runtime removes it from active failure guidance after ordinary recall admission.

Retraction uses the existing governed delete/tombstone path. History remains reconstructable in the revision owner while current recall influence is removed.

## Similarity evidence

`FailureMatchEvidence` is deliberately weak:

```text
failure_ref
similarity_score
occurrence_count
severity_label
memory_status
authority_effect = none
```

There is no `allow`, `deny`, or `block` field.

That omission is load-bearing.

## Current implementation posture

The first implementation slice is runtime-wired but its revision and recurrence indexes are process-local.

The underlying facts are written through the configured governed Agent Memory substrate, but #471 must remain open until restart-safe owner checkpoint/recovery evidence proves that the failure-memory lineage itself survives restart without resurrection of retracted state or loss of recurrence/currentness semantics.

Therefore the current capability profile truthfully declares:

```text
maturity: runtime_wired
restart_recovery: process_local_only
reconciliation: process_local_only
authority_effect: none
```

## Acceptance evidence in this slice

`reference/tests/test_failure_memory.py` pressures:

- deterministic stable identity;
- initial governed commit and recall;
- high similarity/high impact cannot bypass correction review;
- explicit recurrence stays under one logical identity;
- repeated recall cannot manufacture recurrence;
- duplicate recurrence evidence is rejected;
- high-severity perfect-similarity match evidence still has no authority effect;
- disputed causal memory is retained but not active guidance;
- retraction tombstones current influence while preserving revision history;
- stale lineage and silent scope movement fail before mutation.

## Remaining #471 work

Before closeout:

1. add restart-safe owner checkpoint/recovery for failure revision and fact mappings;
2. prove tombstoned/retracted failure state does not regain influence after restart;
3. prove restart preserves recurrence count and current/disputed state;
4. add bounded evaluation evidence for failure retrieval quality, false recurrence matches, performance, and governance separately;
5. update #470 harvest disposition from partial to absorbed only after that evidence exists.

No EvolveAI runtime dependency is required or desired.