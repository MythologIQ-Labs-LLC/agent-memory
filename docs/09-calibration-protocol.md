# Saturation Calibration Protocol

## Purpose

This protocol defines how to calibrate saturation before using it to route, retain, evict, or propose crystallization for memory units.

Saturation is useful only when it separates objects that should persist from objects that should evaporate. Until calibrated, saturation is just a number with confidence issues. So, naturally, we must supervise it.

## Calibration question

The calibration question is:

```text
Does sigma separate persist-worthy memory from evaporate-worthy memory across the durability dimensions this implementation claims to support?
```

It is not:

```text
Does sigma look intuitively reasonable?
```

Human intuition is how we got password reuse and meetings that could have been emails. Do not use it as a thresholding method.

## Required labeled classes

### PERSIST

Objects that should remain durable or enter a non-decaying regime within a defined scope.

Examples:

- corroborated project decision
- verified code artifact relationship
- user-approved preference
- policy rule with provenance
- recurring, meaningful, cross-referenced memory

### EVAPORATE

Objects that should decay, expire, or remain outside durable memory.

Examples:

- one-time transient context
- uncorroborated single-source assertion
- stale runtime trace
- temporary task note
- contradicted observation

### TRAP

Objects designed to fool naive saturation logic.

Required traps:

- access-spam junk
- confidently-wrong memory
- overfit single-source fact
- stale-but-frequently-recalled memory

## Calibration process

1. Build a labeled fixture set.
2. Drive each fixture through realistic interaction history.
3. Record sigma at the decision point.
4. Plot or compare PERSIST, EVAPORATE, and TRAP distributions.
5. Measure overlap.
6. Choose the threshold based on operational cost.
7. Report the scope of validity.

## Required measurements

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

## Threshold selection

| Goal | Threshold behavior |
|---|---|
| Avoid false permanence | raise threshold and require certification |
| Avoid losing valuable memory | lower candidate threshold but require review |
| Balance costs | choose threshold from explicit tradeoff curve |

## Overlap rule

Distribution overlap matters more than mean score.

A persist mean of 0.92 and evaporate mean of 0.33 is not enough if trap objects still cross the crystallization threshold.

## Trap-class rule

If a trap class crystallizes, the calibration failed.

That does not mean the trap object was secretly valuable. It means the scoring model is measuring the wrong thing.

## Scope of validity

A calibration is valid only for the durability dimensions tested.

For example, a calibration that tests only cryptographic verification says nothing about social corroboration, repeated meaningful use, or decision continuity.

## Example calibration report

```yaml
implementation: EvolveAI-reference
version: v0.0.0-example
doctrine_version: v0.2
threshold: 0.95
sample_size: 80
persist_retention_rate: 0.92
false_permanence_rate: 0.01
evaporation_rate_for_true_ephemeral: 0.88
trap_class_failure_rate: 0.00
durability_dimensions_tested:
  - corroboration
  - cross_reference
  - verification
  - meaningful_reuse
scope_of_validity: synthetic doctrine fixtures plus implementation-specific memory traces
known_exemptions:
  - human preference memories require explicit approval regardless of sigma
```

## Certification interaction

Calibration may identify crystallization candidates.

Certification decides whether crystallization is allowed.

```text
sigma >= threshold -> candidate
candidate + certification + PAMA allow -> crystallized
```

## Doctrine

Calibrated saturation is a lifecycle signal.

It is not identity, not truth, and not permission.
