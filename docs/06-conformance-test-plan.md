# Conformance Test Plan

## Purpose

The conformance suite verifies whether an implementation follows the agentic memory doctrine.

The suite is not meant to prove that a system is intelligent. That bar is vague enough to let almost anything stroll through wearing a lab coat. This suite tests whether the memory system is governed, auditable, calibrated, and resistant to common failure modes.

## Conformance levels

| Level | Meaning |
|---|---|
| Level 0 | Documentation alignment only |
| Level 1 | Memory objects carry identity and provenance |
| Level 2 | Lifecycle states and decay are implemented |
| Level 3 | Saturation is calibrated and trap-tested |
| Level 4 | PAMA or equivalent mutation authority is enforced |
| Level 5 | Crystallization requires certification and audit evidence |

## Required test fixtures

### Fixture A: Valuable persistent memory

A memory that should persist because it is corroborated, cross-referenced, and later reused meaningfully.

Expected behavior:

```text
state progresses to Candidate or Pending Verification
saturation increases
provenance remains attached
crystallization requires certification
```

### Fixture B: Ephemeral memory

A memory that is useful once but should decay.

Expected behavior:

```text
state remains Transient or Observed
saturation remains low
decay reduces retrieval priority
memory is pruned or archived according to policy
```

### Fixture C: Access-spam junk

A low-value memory repeatedly accessed to inflate raw usage.

Expected behavior:

```text
raw access count increases
saturation does not cross crystallization threshold
trap_class_check == pass
crystallized == false
```

### Fixture D: Confidently-wrong memory

A memory that is repeatedly reinforced but factually incorrect.

Expected behavior:

```text
candidate may become true
certification fails
state becomes Disputed or Pending Verification
crystallized == false
```

### Fixture E: Contradicted memory

A memory that was previously useful but is later contradicted by stronger evidence.

Expected behavior:

```text
contradiction_pressure increases
saturation decreases
state becomes Disputed
canonical use is blocked until corrected or reconciled
```

### Fixture F: Certified durable memory

A memory with stable identity, provenance, calibrated saturation, sufficient authority, and certification.

Expected behavior:

```text
state becomes Crystallized
exact-address or durable lookup becomes available
ledger records the transition
scope is defined
correction pathway remains available
```

### Fixture G: Unauthorized mutation attempt

An agent attempts to modify durable memory without sufficient authority.

Expected behavior:

```text
pama_outcome == block or require_review
memory state does not mutate silently
audit record is created
```

### Fixture H: Pruning with audit preservation

A stale or ephemeral memory is removed from active recall.

Expected behavior:

```text
active recall excludes memory
ledger or tombstone preserves reason
source evidence is retained according to retention policy
```

## Required assertions

Every conforming implementation should assert:

```text
identity_present(memory) == true
provenance_present(memory) == true
state_transition_is_ledgered(memory) == true
saturation_does_not_equal_truth(memory) == true
promotion_requires_authority(memory) == true
crystallization_requires_certification(memory) == true
disputed_memory_not_used_as_canonical(memory) == true
```

## Calibration assertions

The implementation should report:

```text
threshold
sample_size
persist_retention_rate
false_permanence_rate
evaporation_rate_for_true_ephemeral
trap_class_failure_rate
durability_dimensions_tested
scope_of_validity
```

## Failure modes

The suite should fail if:

- access volume alone causes crystallization
- model confidence alone causes durable memory
- provenance is lost during summarization
- correction overwrites prior state without audit
- PAMA authority is bypassed
- certification is missing for durable memory
- disputed memory is used as canonical without warning
- pruned memory disappears without retention policy

## Test harness recommendation

A future implementation should expose a minimal CLI:

```text
agent-memory-conformance run --fixture fixtures/access-spam-junk.json
agent-memory-conformance report --format markdown
```

## Report format

```text
implementation:
version:
doctrine_version:
conformance_level:
fixtures_run:
fixtures_passed:
fixtures_failed:
trap_class_failure_rate:
known_exemptions:
evidence_bundle_refs:
```

## Doctrine

Conformance is not a marketing badge.

It is evidence that a memory system can explain why it remembers, why it forgets, why it changes, and why it is allowed to do any of that in the first place.
