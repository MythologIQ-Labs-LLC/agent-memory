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
  -> failure-memory ownership/currentness narrowing
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

## Correction, dispute, retraction, and typed recall

A correction extends the current revision. It cannot silently change governed scope or action-class identity.

A disputed failure memory stays retained and historically visible, but the runtime removes it from active failure guidance after ordinary recall admission.

Retraction uses the existing governed delete/tombstone path. History remains reconstructable in the revision owner while current recall influence is removed.

Specialized failure-memory recall is deliberately narrower than the generic Cognitive Mesh recall helper:

```text
shared candidate generation
  -> governed adapter admission
  -> failure-memory ownership/type filter
  -> current failure revision check
  -> disputed/retracted check
  -> contextual policy
  -> active failure refs only
```

An unrelated semantic or epistemic fact may be a valid adapter-level admitted fact for the same text query. That does not make it failure memory. The failure-memory surface fails closed with a type mismatch and never broadens the adapter's admitted set.

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

There is no `allow`, `deny`, or `block` field. That omission is load-bearing.

## Restart posture

The generic standalone `FailureMemory` revision owner remains process-local.

`CheckpointedFailureMemory` provides a bounded restart-safe specialization when explicitly composed through `ComposedRestartSafeRuntime`. Its owner checkpoint preserves append-only failure lineage, revision-to-fact ownership, and the Cognitive Mesh object map. Restore validates those mappings against the durable substrate and fails closed when an owner record points to a fact that is absent.

Restart tests prove, for that bounded composition:

- recurrence count/currentness survives recovery;
- retracted/tombstoned state does not regain current influence;
- corrupt missing-fact owner mappings fail recovery.

This does not promote the generic capability profile to a universal checkpoint/replay claim. The profile continues to report the standalone owner as process-local and cites the checkpointed specialization as bounded evidence.

## Evaluation evidence

`reference/run_failure_memory_benchmark.py` is revision-bound to an exact Agent Memory commit and fixture SHA. It reports quality, performance, and governance separately.

The benchmark measures:

- deterministic identity equivalence/separation;
- false recurrence matches;
- repeated-failure retrieval;
- recurrence identification;
- correction/retraction currentness;
- wrong-scope admission violations;
- repeated-recall recurrence mutation;
- similarity authority/bypass violations;
- retracted resurfacing;
- owner checkpoint size.

It deliberately reports downstream avoided-failure action outcomes as `not_measured`: remembering a failure produces governed evidence, not automatic action authority.

## Acceptance evidence

Focused tests cover:

- deterministic stable identity;
- initial governed commit and recall;
- high similarity/high impact cannot bypass correction review;
- explicit recurrence stays under one logical identity;
- repeated recall cannot manufacture recurrence;
- duplicate recurrence evidence is rejected;
- high-severity perfect-similarity match evidence still has no authority effect;
- disputed causal memory is retained but not active guidance;
- retraction tombstones current influence while preserving revision history;
- stale lineage and silent scope movement fail before mutation;
- restart preserves current admissible failure state and recurrence;
- retracted state does not resurrect on restart;
- corrupted owner checkpoint mappings fail closed;
- unrelated admitted memory forms cannot become active failure guidance;
- current failure revision remains active after supersession/correction.

## Closeout boundary

No EvolveAI runtime dependency is required or desired.

#471 may close only after the exact final PR head is green and #470's harvest matrix/canonical ownership language is reconciled from `partially_absorbed` / `further native implementation planned` to the evidence-supported native disposition. #470 itself remains open for the other ancestry/peer rows.
