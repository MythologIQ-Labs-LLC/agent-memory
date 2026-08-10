# Integration Roadmap

## Purpose

This roadmap turns the doctrine into implementation work across the related repos.

The priority is consolidation before expansion. The system already has enough ideas. What it needs now is shared vocabulary, conformance boundaries, implementation hooks, and evidence that uncertain inference cannot silently become memory authority.

## Phase 1: Canonical doctrine stabilization

### Goal

Make this repository the shared reference point.

### Tasks

- finalize glossary
- finalize layer model
- finalize lifecycle state machine
- finalize scoring and decay doctrine
- finalize PAMA governance boundaries
- finalize governed-uncertainty doctrine and disposition ADR-020 only after evidence supports acceptance
- finalize ADR set
- add source backlinks to related repos

### Exit criteria

```text
README points to canonical docs
ADRs accepted, revised, or explicitly proposed
each related repo has an implementation-map entry
open questions are tracked as issues
governed-uncertainty audit has no unresolved critical contradiction
```

## Phase 2: Cross-repo backlinks

### Goal

Every implementation repo references the doctrine.

### Target repos

- UOR Framework
- EvolveAI
- CodeGenome
- COREFORGE
- FailSafe or governance repos as applicable
- Bicameral decision-memory surfaces as applicable

### Recommended backlink text

```text
This implementation follows the Agent Memory doctrine maintained in Knapp-Kevin/agent-memory. See the layer model, lifecycle state machine, PAMA governance model, governed-uncertainty doctrine, and conformance test plan for canonical terminology.
```

## Phase 3: Implementation alignment issues

### Goal

Create repo-specific issues that map existing implementation behavior to doctrine.

### Suggested issues

1. Map UOR identity boundaries to ADR-001 and deterministic-substrate requirements.
2. Map EvolveAI lifecycle states to `docs/02-lifecycle-state-machine.md`, including proposal versus commit.
3. Map EvolveAI CMHL and MTS logic to `docs/03-scoring-and-decay.md`, including estimator version, calibration scope, uncertainty, hysteresis, and drift.
4. Map CodeGenome confidence and provenance to the evidence layer, including inferred-edge estimator provenance and disagreement.
5. Map COREFORGE Vault writes to PAMA enforcement points.
6. Map Neurospace runtime memory to operational versus canonical memory states and recall-time scope enforcement.
7. Map FailSafe / Arbiter approval gates to crystallization and mutation transitions, including policy-version and permitted-action receipts.
8. Map Bicameral drift detection to probabilistic proposal versus governed durable decision change.

## Phase 4: Governed-uncertainty boundary inventory

### Goal

Identify every place an estimate can influence a consequential memory action.

### Required inventory fields

```text
component
estimator_or_rule
input_scope
output_type
estimator_version
calibration_scope
consequence_candidate
governance_boundary
policy_owner
permitted_action_set
commit_boundary
audit_receipt
```

### Exit criteria

- every probabilistic or learned estimator with memory consequences is listed
- every listed estimator points to a policy boundary
- every policy boundary points to a commit/enforcement point
- no estimator is documented as self-authorizing mutation, promotion, deletion, sharing, or certification

## Phase 5: Conformance fixture design

### Goal

Create executable fixtures for testing doctrine alignment.

### Core fixture set

- valuable persistent memory
- ephemeral memory
- access-spam junk
- confidently-wrong memory
- contradicted memory
- certified durable memory
- unauthorized mutation attempt
- pruning with audit preservation

### Governed-uncertainty fixture set

- high-confidence false promotion
- threshold jitter
- estimator disagreement
- cross-tenant relevance trap
- stochastic retrieval inside policy envelope
- unsafe multi-memory composition
- uncertain sensitivity classification
- irreversible deletion under uncertain utility
- policy-versus-estimator version drift
- concurrent conflicting mutation

### Deliverables

```text
fixtures/*.json
schemas/memory-unit.schema.json
schemas/conformance-report.schema.json
scripts/validate-fixtures.*
```

## Phase 6: Runtime enforcement hooks

### Goal

Make doctrine enforceable in product and agent runtimes.

### Target enforcement points

- Vault write boundary
- graph mutation boundary
- crystallization gate
- context assembly pipeline
- correction workflow
- pruning workflow
- deletion workflow
- scope-sharing / tenancy boundary
- agent action planner

### Required behavior

At each enforcement point, identify:

```text
what may be probabilistic
what must remain invariant
what policy version applies
what action set is permitted
what happens on missing authority
what receipt is emitted
```

## Phase 7: Calibration and uncertainty harness

### Goal

Calibrate lifecycle estimators and expose false-permanence, boundary-instability, and drift risk.

### Required metrics where applicable

```text
threshold
sample_size
persist_retention_rate
false_permanence_rate
evaporation_rate_for_true_ephemeral
trap_class_failure_rate
durability_dimensions_tested
scope_of_validity
calibration_error
boundary_instability_rate
abstention_rate
estimator_disagreement_rate
out_of_scope_rate
estimator_version
calibration_version
```

### Required studies

- threshold sensitivity
- perturbation stability
- repeated-seed behavior for stochastic components
- calibration by memory class and consequence class
- out-of-distribution behavior
- policy-version versus estimator-version change
- hysteresis or equivalent anti-oscillation behavior

## Phase 8: Decision receipts and replay

### Goal

Make consequential memory decisions reconstructable without requiring exact replay of stochastic cognition.

### Minimum receipt

```text
actor
memory_id
requested_action
estimator_refs
estimator_versions
uncertainty_summary
policy_refs
policy_version
permitted_action_set
selected_action
selection_mode
before_state
after_state
rollback_path
evidence_refs
timestamp
```

### Exit criteria

An auditor can reconstruct what was estimated, what was allowed, what was prohibited, what was selected, and what changed.

## Phase 9: Research challenge loop

### Goal

Continuously test doctrine assumptions against accessible research and empirical failures.

### Practice

- prefer freely inspectable research where practical
- record findings that support the doctrine
- record findings that challenge it
- classify biological/cognitive transfers as mechanism, functional analogy, engineering prescription, or open hypothesis
- create conformance fixtures when research exposes a falsifiable failure mode
- do not promote a research-inspired idea to doctrine solely because the analogy is appealing

## Phase 10: Doctrine versioning

### Goal

Make doctrine changes traceable.

### Proposed versioning

```text
v0.1: initial doctrine spine
v0.2: schema and fixture definitions
v0.3: executable conformance harness
v0.4: cross-repo implementation mappings
v0.5: governed-uncertainty receipts and runtime boundary inventory
v1.0: stable doctrine with tests, research challenge history, and adoption notes
```

## Immediate next issues

Create issues for:

1. Add schemas for memory units and conformance reports.
2. Add fixture examples for all required conformance cases.
3. Expand the calibration harness to measure uncertainty, drift, and decision-boundary stability.
4. Add cross-repo backlink and governed-uncertainty mapping issues for EvolveAI, CodeGenome, COREFORGE, FailSafe / Arbiter, and Bicameral.
5. Add PAMA decision-table tests for finite authority outcomes and bounded stochastic action.
6. Add a decision-receipt schema that separates estimator outputs from governance outcomes.
7. Build the cross-repo boundary inventory before accepting ADR-020.

## Acceptance dependency for ADR-020

ADR-020 should remain Proposed until at least the following are demonstrated:

```text
core conformance fixtures exist
governed-uncertainty fixtures exist
at least one implementation boundary is mapped end to end
high-confidence false promotion is blocked
cross-scope relevance is blocked at read time
stochastic choice cannot select prohibited actions
irreversible deletion is not authorized by utility score alone
policy and estimator version drift remain distinguishable
```

## Roadmap principle

Do not add another concept until the existing concepts have a stable place to live.

Do not call governed uncertainty complete until it survives implementation and adversarial testing. Documentation agreeing with itself is useful. It is also an exceptionally low bar for reality.
