# Schema Registry and Type Evolution

> Canonical requirement: [ADR-014](adr/ADR-014-schema-registry-and-type-evolution-are-needed.md)

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
decision_ref
decision_outcome
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

The decision and receipt remain distinct artifacts. The receipt carries enough authority context to identify the decision and reconstruct its outcome class, while the referenced decision remains authoritative for the full PAMA evaluation record.

Decision-receipt version compatibility currently follows this boundary:

```text
1.0.0
  historical receipt shape
  decision_ref / decision_outcome absent or optional
  remains valid historical evidence

1.1.0
  decision_ref required
  decision_outcome required
  receipt <-> decision binding can be verified bidirectionally
```

This is intentionally versioned rather than retroactively making new fields required on all stored receipts. Optional-to-required evolution is breaking unless historical objects are migrated, and signed or content-addressed evidence must not be silently rewritten merely to satisfy a newer convenience contract.

For 1.1.0 receipts, consumers that possess the referenced decision should verify at least:

- `decision_ref` resolves to the intended PAMA/authority decision;
- `decision_outcome` matches that decision;
- policy version and permitted/prohibited action sets match;
- selected action matches the decision and belongs to the permitted set;
- the decision points back to the same receipt;
- the outcome and action envelope are internally consistent.

A receipt proves what was recorded about the authority decision and selected consequence. It does not, by itself, prove downstream execution occurred.

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

The repository schema registry includes machine-readable contracts for memory units, conformance results, audit events, decision receipts, PAMA decisions, calibration evidence, source records, portable/interchange evidence, isolation boundaries, governance projections, and other bounded profiles introduced by validated architecture slices.

The canonical inventory is the [`../schemas/`](../schemas/) directory. Do not rely on a hand-maintained schema count in prose as a maturity signal.

Core examples include:

- [`../schemas/memory-unit.schema.json`](../schemas/memory-unit.schema.json) — the memory unit, including uncertainty, scope, tombstone, and action-envelope fields
- [`../schemas/conformance-report.schema.json`](../schemas/conformance-report.schema.json) — conformance results with estimator/policy versioning and the standardized metric family
- [`../schemas/memory-audit-event.schema.json`](../schemas/memory-audit-event.schema.json) — structured audit events with correlation/causation identifiers
- [`../schemas/decision-receipt.schema.json`](../schemas/decision-receipt.schema.json) — reconstruction receipts for consequential decisions, including the versioned authority-decision backlink
- [`../schemas/pama-decision.schema.json`](../schemas/pama-decision.schema.json) — PAMA authority decision records
- [`../schemas/calibration-results.schema.json`](../schemas/calibration-results.schema.json) — labeled calibration case input for the calibration report generator
- [`../schemas/source-record.schema.json`](../schemas/source-record.schema.json) — source-registry records with rights and reuse gating

## Fixture versioning

Conformance fixtures are versioned artifacts with their own evolution rules, distinct from the schemas of the objects they contain:

```text
"fixture_version": "MAJOR.MINOR.PATCH"
```

- The fixture version describes the **scenario contract**: expected behavior, required invariants, trap semantics, and material scenario inputs, not the memory-unit schema version.
- Prose or metadata changes that leave expected behavior untouched may remain patch-compatible.
- Changing expected behavior, required invariants, trap semantics, or material scenario inputs requires a version change; breaking scenario-semantic changes require a major version change.
- Runtime evidence must record `fixture_id` plus `fixture_version`, so results remain comparable after fixtures evolve.
- `scripts/validate_fixtures.py` requires and validates the field on every fixture.

## Conformance cases

- old consumer receives new optional field
- old consumer receives unknown enum member
- historical 1.0 decision receipt remains valid under the compatibility schema
- 1.1 decision receipt omits required decision backlink/outcome
- decision receipt references the wrong authority decision
- decision receipt outcome does not match the referenced decision
- decision and receipt point at different counterparts
- outcome class contradicts the permitted/prohibited action envelope
- decision receipt references mismatched policy version
- estimator score changes semantics without type change
- migrated object loses provenance
- schema adapter strips tenant scope
- unknown schema attempts durable mutation

## Doctrine

Schemas govern meaning, not merely syntax.

Interoperability is unsafe when two components agree on JSON while disagreeing on what the JSON means.
