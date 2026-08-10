# Schema Registry and Type Evolution

## Purpose

Agent Memory needs stable semantic contracts without freezing implementation experimentation.

The schema registry defines which fields and meanings belong to doctrine-level interoperability, how those types evolve, and how implementations extend them without silently changing semantics.

## Core rule

```text
schema compatibility != field-name compatibility only
```

If two systems both emit `confidence: 0.8` but one means semantic similarity and the other means calibrated factual probability, the schemas are semantically incompatible even if JSON validation passes with enthusiasm.

## Registry layers

### Doctrine core

Stable cross-implementation concepts such as:

- memory identity
- lifecycle state
- acquisition mode
- provenance
- scope/tenant
- sensitivity labels
- authority references
- policy version
- certification state
- dispute/supersession state
- estimator provenance
- uncertainty representation
- deletion/tombstone state
- decision receipt

### Extension layer

Implementation-specific fields may be added under explicit namespacing or extension objects.

Example:

```json
{
  "extensions": {
    "codegenome": {...},
    "evolveai": {...}
  }
}
```

Extensions must not redefine core-field meaning.

## Required versioning

Each doctrine-level serialized object should identify a schema version.

Recommended:

```text
schema_name
schema_version
```

Version semantics should distinguish:

- backward-compatible additive change
- compatible semantic clarification
- breaking field/type change
- breaking semantic change

A semantic change can be breaking even when the JSON type does not change.

## Type evolution rules

### Additive field

May be backward compatible when optional and existing semantics remain valid.

### New enum member

Potentially breaking for closed consumers. Consumers should define unknown-value behavior.

### Changed field meaning

Breaking. Requires a new schema version or explicit migration.

### Optional to required

Breaking unless all stored objects are migrated.

### Scalar to structured uncertainty

Breaking unless the old scalar remains interpretable through an explicit compatibility adapter.

## Semantic types that must not collapse

Keep separate:

```text
confidence
probability
similarity
trust
saturation
relevance
sensitivity
authority
certification
```

Likewise:

```text
proposal
permitted_action_set
selected_action
committed_transition
```

## Estimator provenance type

A consequential estimate should be representable as:

```json
{
  "signal_type": "semantic_relevance",
  "value": 0.91,
  "value_semantics": "cosine-derived ranking score, not calibrated probability",
  "estimator_id": "retriever-x",
  "estimator_version": "3.2",
  "calibration_ref": null,
  "uncertainty": null,
  "scope": "project-A"
}
```

## Uncertainty type

Support multiple representations rather than forcing one universal confidence scalar.

Possible forms:

- categorical: low / medium / high
- interval
- probability distribution summary
- ensemble disagreement
- conformal set
- unknown / unavailable

Every representation should declare its semantics.

## Authority type

Authority records should identify:

```text
actor
principal
scope
capability / permission
policy_ref
policy_version
expiry / revocation
source of delegation
```

Authority must not be inferred from estimator fields.

## Decision-receipt type

A common receipt should support:

```text
requested_action
state_snapshot
estimate_refs
policy_version
authority_refs
permitted_actions
prohibited_actions
selected_action
selection_mode
before_state
after_state
evidence_refs
rollback_or_recovery_ref
timestamp
```

## Migration

A migration should record:

```text
migration_id
from_schema_version
to_schema_version
transformation
lossy_fields
semantic_changes
validation_result
rollback_or_backup_ref
```

Lossy migration requires explicit handling. "The old field didn't fit" is not provenance.

## Unknown fields and versions

For low-risk read-only consumers, preserving unknown extension fields may be sufficient.

For consequential mutation, a consumer should not silently process an unknown core schema version if it cannot establish the semantics required for authority.

Possible outcome:

```text
unsupported_schema -> abstain / quarantine / require_adapter
```

## Registry governance

Schema changes should be reviewed for:

- backward compatibility
- semantic compatibility
- privacy impact
- deletion/migration impact
- conformance impact
- implementation adoption cost

## Current repository schemas

The repository currently contains:

- `schemas/memory-unit.schema.json`
- `schemas/conformance-report.schema.json`

These predate the full governed-uncertainty model and should be reconciled in a subsequent schema/fixture slice.

## Conformance cases

- old consumer receives new optional field
- old consumer receives unknown enum member
- estimator score changes semantics without type change
- migrated object loses provenance
- schema adapter strips tenant scope
- unknown schema attempts durable mutation
- decision receipt references mismatched policy version

## Doctrine

Schemas govern meaning, not merely syntax.

Interoperability is unsafe when two components agree on JSON while disagreeing on what the JSON means.
