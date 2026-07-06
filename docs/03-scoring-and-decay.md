# Scoring and Decay

## Purpose

This document consolidates the scoring logic from UOR saturation, EvolveAI memory tier routing, CodeGenome confidence fusion, and PAMA authority into one coherent model.

The scoring model exists to support lifecycle decisions. It must not be mistaken for truth.

## Signal taxonomy

| Signal | Purpose | Typical owner |
|---|---|---|
| Identity | Exact object reference | UOR, content addressing |
| Confidence | Evidence quality or relation probability | CodeGenome, observers |
| Saturation | Lifecycle persistence pressure | PRISM, EvolveAI, memory runtime |
| Authority | Permission to mutate or promote | PAMA, Arbiter, policy layer |
| Certification | Confirmation of durable transition | Verification or approval gate |
| Risk | Potential harm from wrong mutation or permanence | PAMA, governance layer |

## Canonical scoring shape

A memory candidate should be evaluated using a composite model:

```text
memory_lifecycle_score = f(
  identity_resolved,
  evidence_confidence,
  saturation,
  corroboration,
  cross_reference_weight,
  contradiction_pressure,
  access_quality,
  temporal_pressure,
  pama_authority,
  certification_status,
  risk_class
)
```

This is not a single universal equation yet. It is the required signal family.

## Saturation

Saturation is a calibrated lifecycle score.

```text
sigma = pinned_fiber_weight / total_available_fiber_weight
```

Where pinned fibers may include:

- corroboration
- verification
- meaningful re-access
- cross-reference
- dependency strength
- user approval
- policy relevance
- runtime reuse
- successful recall history

Raw access should never dominate saturation.

## Effective decay

A UOR-aligned decay model may use:

```text
lambda_eff = lambda_base * T_ctx
```

Where:

```text
T_ctx = free_fiber_count * ln(2) / n
```

Interpretation:

- higher saturation lowers effective decay
- unresolved or weakly pinned memory decays faster
- fully crystallized memory may enter a non-decaying regime inside its certified scope

## EvolveAI memory tier routing

EvolveAI uses a memory tier score shape:

```text
MTS = (S * Ws) + (A * Wa) + (P * Wp) - (C * Wc)
```

Where:

- S = sensitivity
- A = accuracy requirement
- P = privilege level
- C = compute constraint

Canonical interpretation:

MTS is a routing heuristic. It should be integrated with saturation, confidence, and authority rather than treated as a complete promotion rule.

## CodeGenome confidence fusion

CodeGenome contributes confidence fusion for code-reality observations.

Confidence describes support for graph relations, not lifecycle durability.

Example distinction:

```text
high confidence relation != crystallized memory
high saturation != correct relation
certified relation == confirmed within scope
```

## PAMA authority weighting

PAMA should evaluate whether a memory transition is permitted.

Inputs may include:

- risk class
- scope of change
- source authority
- user approval state
- confidence spread
- contradiction pressure
- reversibility
- blast radius
- implementation maturity

Suggested authority outcomes:

```text
allow
allow_with_ledger
require_review
require_external_verification
block
```

## Crystallization threshold

A crystallization threshold must be calibrated.

Do not choose `sigma >= 0.95` by intuition. Calibrate using labeled examples:

- PERSIST objects that should become durable
- EVAPORATE objects that should decay
- trap-class objects that are designed to fool the scoring system

## Required trap classes

### Access-spam junk

A low-value object hammered with reads to inflate saturation.

Expected result:

```text
candidate == false
crystallized == false
```

### Confidently-wrong memory

An object strongly reinforced but incorrect.

Expected result:

```text
candidate may be true
certification must fail
crystallized == false
state == disputed or pending_verification
```

### Overfit single-source fact

A fact repeated from one uncorroborated source.

Expected result:

```text
saturation plateau below durable threshold unless corroborated or approved
```

## Calibration report

Every scoring implementation should be able to report:

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

## Operating-point selection

The threshold should be chosen according to cost:

| Preference | Threshold behavior |
|---|---|
| Avoid false permanence | higher threshold, require certification |
| Avoid losing valuable memories | lower candidate threshold, stronger review queue |
| Balance both costs | calibrated threshold using explicit tradeoff |

## Hard rule

No score should grant permanence alone.

Only a governed transition can do that.
