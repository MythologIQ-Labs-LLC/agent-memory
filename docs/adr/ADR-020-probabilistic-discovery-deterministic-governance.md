# ADR-020: Probabilistic Discovery, Deterministic Governance

## Status

Proposed

## Context

Agentic memory operates under uncertainty.

Candidate extraction, semantic retrieval, contradiction detection, source trust, salience, relevance, abstraction, causal inference, and risk estimation may all depend on learned or probabilistic mechanisms.

However, memory also contains transitions whose consequences are too important to delegate directly to uncertain inference:

- canonical promotion
- mutation of durable state
- cross-tenant or cross-user disclosure
- deletion and erasure
- policy mutation
- certification
- inherited memory propagation
- authority changes
- preservation or destruction of evidence

A binary architectural choice between "deterministic memory" and "probabilistic memory" is therefore insufficient.

Research also challenges both extremes. Human memory and decision research supports explicit representation of uncertainty and stochastic retrieval. Current agent-memory work shows value in adaptive learned memory control. At the same time, memory-poisoning research shows that aggressively writing and retrieving memory can create persistent attack surfaces, and runtime-assurance research provides precedent for allowing learned behavior only inside separately enforced safety boundaries.

## Decision candidate

Adopt a **governed uncertainty** architecture with the following separation:

```text
probabilistic / learned epistemics
        |
        v
policy-defined governance envelope
        |
        v
optional stochastic selection among permitted actions
        |
        v
defined state transition + audit receipt
```

### Rule 1: probabilistic outputs are not authority

Learned or probabilistic components MAY produce:

- beliefs
- confidence estimates
- relevance scores
- risk estimates
- contradiction likelihoods
- rankings
- memory candidates
- proposed mutations
- proposed retrieval sets
- proposed consolidation targets

They MUST NOT acquire mutation, promotion, deletion, sharing, or certification authority merely from their scores.

### Rule 2: governance defines the permitted action set

For every consequential transition, a versioned governance function MUST determine the set of permitted outcomes using applicable:

- identity
- scope
- tenant
- authority
- sensitivity
- provenance
- lifecycle state
- risk class
- certification state
- policy

A learned component MUST NOT expand that set.

### Rule 3: stochastic behavior may remain inside the envelope

The architecture MAY permit stochastic or learned selection among actions already authorized by policy.

Examples include:

- retrieval ordering
- query exploration
- low-risk hypothesis testing
- non-destructive consolidation analysis

The invariant is:

```text
selected_action ∈ permitted_action_set
```

### Rule 4: irreversible and authority-changing transitions receive the strongest boundary

Transitions involving canonical truth, erasure, permission expansion, evidence destruction, cross-scope disclosure, policy mutation, or inherited canonical state MUST require explicit prerequisites beyond model confidence.

Depending on risk, these MAY include:

- deterministic policy checks
- external verification
- human approval
- cryptographic authorization
- certification
- quorum
- formal safety constraints

### Rule 5: uncertainty remains visible

The system MUST NOT silently collapse uncertain inference into authoritative fact.

Where material, audit evidence SHOULD preserve:

- estimator/model version
- relevant probabilities or scores
- threshold or rule version
- candidate set
- policy version
- authority scope
- committed result

### Rule 6: deterministic does not mean static

Deterministic governance rules MAY consume probabilistic inputs and MAY evolve through explicit versioned policy changes.

Fixed thresholds MUST NOT be assumed safe merely because they are reproducible.

Thresholds and classifiers that influence consequential transitions SHOULD be calibrated and adversarially evaluated.

### Rule 7: read-path governance is required

A memory that was safe to store MAY become unsafe when combined with other memories or retrieved into a different scope.

Therefore, deterministic or formally bounded policy enforcement MUST exist on both:

```text
write path
read path
```

### Rule 8: formal probabilistic guarantees are allowed when absolute guarantees are impossible

Some systems cannot provide absolute deterministic safety because environment models, hidden parameters, or learned estimators remain uncertain.

Formally bounded probabilistic guarantees MAY be used when:

- the guarantee type is explicit
- the residual risk is measured
- the policy accepts that risk
- stronger deterministic constraints remain enforced where possible

## Consequences

### Positive

- preserves adaptive and learned memory behavior
- prevents model confidence from becoming authority
- makes governance auditable
- separates epistemic uncertainty from permission
- supports stronger security boundaries
- permits safe experimentation inside bounded action spaces
- improves failure analysis by recording policy and estimator versions separately
- provides a conceptual bridge to runtime assurance and shielding architectures

### Negative

- adds architectural complexity
- requires explicit policy and transition semantics
- requires calibration of probabilistic components
- can add latency to high-consequence operations
- may require additional audit storage
- poorly designed deterministic gates can become brittle bottlenecks
- formal guarantees may be difficult for complex memory composition

### Risks

- teams may label a rule "deterministic" and stop evaluating whether it is correct
- fixed thresholds may create false confidence
- stochastic components may influence governance indirectly through poorly bounded inputs
- read-path composition can create risks not visible at write time
- policy version drift may mimic model drift unless both are recorded
- excessive fail-closed behavior can destroy memory utility

## Rejected alternatives

### Fully deterministic memory control

Rejected as a universal doctrine.

Reason:

Memory relevance, ambiguity, contradiction, abstraction, source trust, retrieval, and risk frequently involve uncertainty. Fixed deterministic heuristics can be brittle and may underperform adaptive methods.

### End-to-end model-directed memory

Rejected for consequential state transitions.

Reason:

A model that can decide what to believe and independently grant itself authority to persist, expose, mutate, or delete that belief collapses epistemics and governance into one failure domain.

### Deterministic thresholds as the primary governance mechanism

Rejected as insufficient.

Reason:

Thresholds require calibration, vary by risk and domain, can be attacked, and can fail under memory composition or distribution shift.

### Human approval for every mutation

Rejected as a default.

Reason:

It creates an unnecessary human bottleneck and prevents useful autonomous low-risk adaptation. Human authority should be reserved for policy-defined consequence classes where it adds material assurance.

## Research basis

The doctrine is informed by freely inspectable research rather than citation collection for its own sake.

Relevant sources include:

- stochastic selective memory retrieval and decision noise: https://pmc.ncbi.nlm.nih.gov/articles/PMC3651451/
- working-memory uncertainty in decisions: https://pmc.ncbi.nlm.nih.gov/articles/PMC7165478/
- distinctions among forms of uncertainty: https://pmc.ncbi.nlm.nih.gov/articles/PMC3461114/
- adaptive memory control for LLM agents: https://arxiv.org/abs/2607.13591
- adaptive probabilistic memory-structure gating: https://arxiv.org/abs/2602.14038
- governed evolving agent memory: https://arxiv.org/abs/2603.11768
- memory-poisoning write-channel vulnerabilities: https://arxiv.org/abs/2606.04329
- compositional and context-triggered memory poisoning: https://arxiv.org/abs/2607.14651
- threshold calibration tradeoffs in memory defenses: https://arxiv.org/abs/2601.05504
- Simplex-style runtime assurance: https://arxiv.org/abs/2109.13446
- black-box Simplex runtime assurance: https://arxiv.org/abs/2102.12981
- adaptive shielding under uncertainty: https://arxiv.org/abs/2506.11033

## Validation required before acceptance

Before moving this ADR from Proposed to Accepted, the repository SHOULD add conformance fixtures proving at least:

1. a high-confidence false memory cannot self-promote
2. a semantically perfect cross-tenant memory cannot be recalled across scope
3. probabilistic contradiction detection cannot silently overwrite certified state
4. stochastic retrieval cannot bypass policy filters
5. uncertain sensitivity classification fails safely for high-risk storage
6. model-predicted low utility cannot independently authorize irreversible deletion
7. read-time composition defenses can catch unsafe combinations of individually acceptable memories
8. policy-version changes are distinguishable from estimator/model drift
9. concurrent conflicting mutations resolve through explicit conflict semantics
10. stochastic action selection cannot escape its permitted action set

## Open questions

- Which governance checks require strict computational determinism?
- Which only require deterministic policy semantics?
- When are probabilistic safety guarantees sufficient?
- How should uncertainty propagate into derived and consolidated memory?
- Can learned governance components themselves be certified inside constrained scopes?
- What formal model best represents an allowed action envelope for agent memory?
- How should policy adapt under distribution shift without becoming hidden self-mutation?

## Related doctrine

See:

- `../24-determinism-probability-and-governed-uncertainty.md`
- `../03-scoring-and-decay.md`
- `../04-governance-and-pama.md`
- `../06-conformance-test-plan.md`
- `ADR-002-saturation-is-routing-not-truth.md`
- `ADR-004-pama-controls-mutation-authority.md`
- `ADR-008-memory-threat-model-is-required.md`
- `ADR-013-governed-recall-planner-is-required.md`
