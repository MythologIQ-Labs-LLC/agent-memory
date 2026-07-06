# Lifecycle State Machine

## Purpose

The lifecycle state machine defines how agentic memory moves from raw experience to durable memory, correction, or pruning.

The state machine does not assume every memory should become permanent. Most memory should remain operational, decay naturally, or be pruned.

## Canonical states

```text
Transient
  -> Observed
  -> Linked
  -> Reinforced
  -> Candidate
  -> Pending Verification
  -> Crystallized
  -> Operationally Reused
  -> Stale
  -> Disputed
  -> Corrected
  -> Reconciled
  -> Pruned
```

## State definitions

### Transient

Short-lived memory used for immediate context. Usually lives in a fast cache or session context.

Entry conditions:

- user message
- tool response
- runtime trace
- temporary reasoning artifact
- unverified observation

Exit conditions:

- ignored and allowed to expire
- promoted to Observed
- attached to an existing memory unit

### Observed

A memory unit exists because some observer recorded an artifact or relation.

Required metadata:

- observer
- timestamp
- source
- method
- raw reference or content hash

### Linked

The memory has graph relations to other memory units.

Example links:

- supports
- contradicts
- depends_on
- refines
- replaces
- derived_from
- implements
- mentions

### Reinforced

The memory has additional support through use, corroboration, cross-reference, verification, or repeated relevance.

Reinforcement must distinguish between meaningful recurrence and access-spam.

### Candidate

The memory has sufficient saturation or governance relevance to be considered for durable treatment.

Candidate status is not approval.

### Pending Verification

The memory is waiting on certification, approval, external confirmation, policy review, or test evidence.

Pending verification is the default state for high-impact memories that appear useful but are not yet trusted.

### Crystallized

The memory has passed identity, provenance, saturation, PAMA authority, and certification gates within a defined scope.

Crystallized does not mean eternal. It means durable under current evidence and policy.

### Operationally Reused

The memory is used by agents or workflows after crystallization or high-confidence routing.

Reuse must preserve references to provenance and certification.

### Stale

The memory remains available but its relevance or correctness may be degrading.

Staleness triggers may include:

- time decay
- changed project state
- changed user preference
- new contradictory evidence
- stale dependencies
- expired certification

### Disputed

The memory has been challenged by contradiction, failed verification, conflict, user correction, or policy change.

Disputed memories must not be silently used as canonical truth.

### Corrected

A dispute has produced a replacement or amendment.

Correction must preserve the old record and its dispute path.

### Reconciled

The corrected memory has been incorporated into the active graph or runtime state.

Reconciliation may result in:

- restored durable state
- downgraded operational state
- split scope
- pruned obsolete version

### Pruned

The memory has been removed from active recall or durable lifecycle consideration.

Pruned does not always mean deleted. Depending on policy, it may mean archived, tombstoned, summarized, or made inaccessible to normal retrieval.

## Required transition metadata

Every state transition should record:

```text
from_state
to_state
trigger
authority
actor
timestamp
evidence_refs
policy_refs
confidence_before
confidence_after
saturation_before
saturation_after
ledger_ref
```

## Promotion gates

A memory can move from Candidate to Pending Verification only if:

```text
identity_resolved == true
provenance_present == true
saturation >= candidate_threshold
trap_class_check != fail
pama_authority in [allow, require_review]
```

A memory can move from Pending Verification to Crystallized only if:

```text
certification_gate == pass
pama_authority == allow
scope_defined == true
dispute_status == clear
```

## Demotion gates

A crystallized memory should be demoted when:

- certification expires
- contradiction is introduced
- policy scope changes
- source is invalidated
- user correction overrides previous state
- implementation dependency changes

Demotion should move to Stale, Disputed, or Corrected, not directly to deletion.

## Trap-class handling

### Access-spam junk

A low-value memory repeatedly accessed must not automatically become durable.

Required behavior:

- access alone has low pinning weight
- cross-reference and corroboration matter more than raw reads
- repeated access without external support should plateau below crystallization

### Confidently-wrong memory

A memory strongly reinforced but later proven wrong must not remain durable.

Required behavior:

- contradiction injects entropy
- saturation decreases
- dispute state blocks canonical use
- correction path preserves previous false claim for audit

## Lifecycle goal

The lifecycle exists to make agent memory accountable.

A memory system is not mature because it remembers more. It is mature when it can explain why something was remembered, why it was trusted, why it changed, and why it was forgotten.
