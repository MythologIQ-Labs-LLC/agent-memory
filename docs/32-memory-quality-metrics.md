# Memory Quality Metrics

## Purpose

A memory system can pass fixtures and still degrade in production.

Ongoing quality metrics should measure whether memory continues to improve agent behavior without accumulating stale, unsafe, over-authoritative, or incompletely deleted state.

No single quality score is sufficient.

## Metric families

### Retention quality

- valuable-memory retention rate
- false permanence rate
- false evaporation / valuable-memory loss rate
- stale durable-memory rate
- unsupported durable-memory rate

### Retrieval quality

- relevant recall rate
- stale recall rate
- wrong-scope candidate rate
- wrong-scope admission rate
- disputed canonical-use rate
- recall explanation coverage
- composition-risk catch rate

### Calibration and uncertainty

- calibration error where scores are probabilistic
- boundary instability rate
- abstention rate
- abstention precision/utility
- estimator disagreement rate
- out-of-calibration-scope rate
- drift detection latency

### Governance quality

- unauthorized mutation rate
- blocked-action escape rate
- stochastic action-set violation rate
- stale-authorization rejection rate
- policy-version reconstruction rate
- decision-receipt completeness

### Correction and conflict

- correction latency
- correction propagation completeness
- silent overwrite rate
- conflict-resolution latency
- unresolved high-risk dispute age

### Forgetting and deletion

- pruning precision
- deletion completion rate
- derived-memory deletion residue rate
- tombstone correctness
- mistaken deletion recovery rate
- retention-policy violation rate

### Provenance and trust

- provenance retention rate
- independent-corroboration accuracy
- recursive self-citation detection rate
- source-trust calibration
- source-scope mismatch rate

### Privacy and security

- cross-tenant leakage rate
- sensitive-context violation rate
- extraction success under approved test harness
- poisoning persistence rate
- sleeper-poison activation rate
- authority-laundering detection rate

### Recovery

- successful recovery/compensation rate
- recovery time
- blast-radius identification completeness
- certification revocation correctness
- replay/reconstruction success rate

### Agent outcome

- task-success delta with memory
- repeated-failure avoidance
- redundant exploration reduction
- tool-call quality
- policy-compliant completion rate
- token/latency cost per successful memory-assisted task

## Segmentation

Metrics should be segmented by relevant dimensions:

```text
memory_type
risk_class
consequence_class
tenant/scope
sensitivity
retrieval_method
estimator_version
policy_version
```

Aggregate metrics can hide critical failures.

A 0.01% leakage rate is not comforting if every leak is a credential.

## Denominators

Every rate needs a defined denominator.

Wrong:

```text
unsafe_recall_rate = 0.02
```

Better:

```text
unsafe_recall_rate = unsafe_admitted_memories / all_admitted_memories
scope = cross-tenant test workload
sample_size = 50,000
```

## Confidence and sample size

Small samples should not masquerade as stable performance.

Reports should include sample size and, where statistically appropriate, confidence intervals or uncertainty estimates.

## Leading versus lagging metrics

### Leading

- calibration drift
- rising disagreement
- increasing abstention
- boundary instability
- source-trust degradation

### Lagging

- actual leakage
- false permanence
- failed deletion
- task failure
- recovery incident

Both matter.

## Guardrail metrics versus optimization metrics

Some metrics are constraints:

```text
cross_tenant_admission_rate should be zero in defined conformance cases
blocked_action_escape_rate should be zero
```

Others are optimization tradeoffs:

```text
abstention rate
retrieval precision
latency
storage cost
```

Do not optimize convenience by weakening a hard invariant.

## Metric gaming

Potential gaming includes:

- never storing memory to reduce false permanence
- never recalling memory to reduce unsafe recall
- rejecting everything to improve leakage metrics
- avoiding disputes by silently overwriting them
- declaring deletion complete without inspecting derived state

Pair metrics with outcome measures and adversarial fixtures.

## Quality report shape

```text
implementation
version
doctrine_version
policy_version
estimator_versions
measurement_window
workload_description
sample_sizes
metrics
segment_breakdowns
known_exemptions
known_failures
evidence_refs
```

## Drift

Quality reports should distinguish:

- estimator/model drift
- policy change
- workload change
- source distribution change
- product behavior change
- schema migration

A quality regression cannot be diagnosed if every changing variable is labeled `memory got worse`.

## Release and monitoring use

Implementations may define quality gates such as:

- no critical invariant failures
- bounded false permanence
- bounded stale recall
- deletion residue below policy target
- acceptable task-success improvement

The doctrine should define metric meaning; products define acceptable operating points according to consequence.

## Conformance mapping

The canonical conformance report schema should support the major governed-uncertainty metrics, while implementation-specific metrics may live under an extension field.

## Doctrine

Memory quality is not how much the system remembers.

It is how reliably memory improves future behavior while preserving truth boundaries, uncertainty, privacy, authority, correction, and forgetting.
