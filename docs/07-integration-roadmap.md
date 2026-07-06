# Integration Roadmap

## Purpose

This roadmap turns the doctrine into implementation work across the related repos.

The priority is consolidation before expansion. The system already has enough ideas. What it needs now is shared vocabulary, conformance boundaries, and implementation hooks.

## Phase 1: Canonical doctrine stabilization

### Goal

Make this repository the shared reference point.

### Tasks

- finalize glossary
- finalize layer model
- finalize lifecycle state machine
- finalize scoring and decay doctrine
- finalize PAMA governance boundaries
- finalize ADR set
- add source backlinks to related repos

### Exit criteria

```text
README points to canonical docs
ADRs accepted or revised
each related repo has an implementation-map entry
open questions are tracked as issues
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
This implementation follows the Agent Memory doctrine maintained in Knapp-Kevin/agent-memory. See the layer model, lifecycle state machine, PAMA governance model, and conformance test plan for canonical terminology.
```

## Phase 3: Implementation alignment issues

### Goal

Create repo-specific issues that map existing implementation behavior to doctrine.

### Suggested issues

1. Map UOR identity boundaries to ADR-001.
2. Map EvolveAI lifecycle states to `docs/02-lifecycle-state-machine.md`.
3. Map EvolveAI CMHL and MTS logic to `docs/03-scoring-and-decay.md`.
4. Map CodeGenome confidence and provenance to the evidence layer.
5. Map COREFORGE Vault writes to PAMA enforcement points.
6. Map Neurospace runtime memory to operational vs canonical memory states.
7. Map FailSafe / Arbiter approval gates to crystallization and mutation transitions.

## Phase 4: Conformance fixture design

### Goal

Create executable fixtures for testing doctrine alignment.

### Fixture set

- valuable persistent memory
- ephemeral memory
- access-spam junk
- confidently-wrong memory
- contradicted memory
- certified durable memory
- unauthorized mutation attempt
- pruning with audit preservation

### Deliverables

```text
fixtures/*.json
schemas/memory-unit.schema.json
schemas/conformance-report.schema.json
scripts/validate-fixtures.*
```

## Phase 5: Runtime enforcement hooks

### Goal

Make doctrine enforceable in product and agent runtimes.

### Target enforcement points

- Vault write boundary
- graph mutation boundary
- crystallization gate
- context assembly pipeline
- correction workflow
- pruning workflow
- agent action planner

## Phase 6: Calibration harness

### Goal

Calibrate saturation thresholds and expose false-permanence risk.

### Required metrics

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

## Phase 7: Doctrine versioning

### Goal

Make doctrine changes traceable.

### Proposed versioning

```text
v0.1: initial doctrine spine
v0.2: schema and fixture definitions
v0.3: executable conformance harness
v0.4: cross-repo implementation mappings
v1.0: stable doctrine with tests and adoption notes
```

## Immediate next issues

Create issues for:

1. Add schemas for memory units and conformance reports.
2. Add fixture examples for all required conformance cases.
3. Add a calibration protocol document based on saturation threshold testing.
4. Add cross-repo backlink issues for EvolveAI, CodeGenome, and COREFORGE.
5. Add PAMA decision table for mutation authority outcomes.

## Roadmap principle

Do not add another concept until the existing concepts have a stable place to live.
