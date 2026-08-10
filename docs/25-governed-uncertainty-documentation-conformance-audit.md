# Governed Uncertainty Documentation Conformance Audit

## Purpose

This document measures the repository's existing documentation against the governed-uncertainty doctrine introduced in `docs/24-determinism-probability-and-governed-uncertainty.md` and proposed in `docs/adr/ADR-020-probabilistic-discovery-deterministic-governance.md`.

The goal is not to reward documents for repeating the same terminology. The goal is to determine whether each relevant document preserves the architectural boundary between uncertain inference and governed consequence.

This audit is intentionally incremental. Each slice records:

1. the baseline document state
2. applicable criteria
3. gaps and contradictions
4. remediation applied
5. post-remediation score
6. verification evidence
7. merge state

A documentation score is **not** evidence that an implementation is safe or conforming. It measures doctrine coverage only.

## Audit anchor

Baseline for the first audit pass:

```text
repository: Knapp-Kevin/agent-memory
baseline_main_commit: 2bf1f6bca18820b55e754913b606900d5cbe872d
baseline_source: merged PR #32
```

## Working doctrine under test

The current doctrine candidate is:

> Probabilistic discovery may produce beliefs, rankings, hypotheses, candidates, confidence estimates, and proposed actions. Consequential memory transitions must occur inside an explicit governance envelope whose permissions, prohibitions, state transitions, and audit consequences are deterministic or formally bounded.

Equivalent shorter form:

> The system may be uncertain about what is true while remaining certain about what it is allowed to do with that uncertainty.

This doctrine remains subject to challenge. Deterministic behavior is not assumed to be safer merely because it is deterministic, and probabilistic behavior is not assumed to be unsafe merely because it is uncertain.

## Scoring scale

Each applicable criterion is scored from 0 through 4.

| Score | Meaning |
|---|---|
| 0 | absent, contradicted, or unsafe assumption |
| 1 | implicit or incidental coverage |
| 2 | partially explicit but materially incomplete |
| 3 | explicit and mostly correct, but not fully bounded or testable |
| 4 | explicit, bounded, auditable, and testable within the document's purpose |
| N/A | criterion is not materially applicable to that document |

Coverage percentage is calculated only across applicable criteria.

## Canonical audit criteria

### GU-1 Deterministic substrate

Does the document identify operations that require stable, reproducible behavior, such as identity, schema validation, authorization, state-transition validity, exact references, ledger semantics, or deletion scope?

### GU-2 Probabilistic epistemics

Does the document explicitly permit and correctly scope probabilistic or learned behavior for uncertain interpretation, ranking, inference, confidence, contradiction detection, relevance, trust estimation, abstraction, or discovery?

### GU-3 Authority separation

Does the document clearly state that confidence, relevance, saturation, probability, model output, or learned policy does not itself grant mutation, promotion, deletion, sharing, certification, or policy authority?

### GU-4 Uncertainty representation and provenance

Does the document preserve where an estimate came from, what it measures, how calibrated it is, its scope, model/method version when relevant, and whether uncertainty itself is represented rather than collapsed into a point estimate?

### GU-5 Governed consequence

Does uncertain input resolve into a finite, policy-defined set of permitted outcomes or state transitions whose effects are explicit?

### GU-6 Consequence proportionality

Does governance become stronger as actions become less reversible, more durable, more sensitive, broader in scope, higher in authority, or larger in blast radius?

### GU-7 Auditability and replay

Can a consequential decision be reconstructed from actor, inputs, evidence, estimator outputs, policy version, outcome, before/after state, and rollback or recovery information where applicable?

### GU-8 Bounded stochastic action

If stochastic behavior is permitted after governance, does the document make clear that randomness or learned choice may select only among actions already permitted by the governance envelope?

### GU-9 Calibration, abstention, and drift

Does the document address uncertainty calibration, threshold sensitivity, hysteresis where needed, estimator disagreement, abstention/escalation, distribution shift, model drift, and the difference between policy-version change and estimator-version change?

### GU-10 Adversarial and conformance validation

Does the document define tests or failure cases that can falsify its assumptions, including high-confidence error, threshold jitter, unsafe composition, stochastic retrieval, cross-scope relevance, uncertainty in sensitivity, concurrent mutation, or irreversible action under uncertain utility?

## Interpretation bands

These bands are reporting aids, not certification levels.

| Coverage | Interpretation |
|---|---|
| 90-100% | doctrine-explicit |
| 75-89% | substantially aligned |
| 60-74% | partial alignment; important gaps remain |
| 40-59% | implicit or structurally incomplete |
| below 40% | materially under-specified for governed uncertainty |

A high score cannot compensate for a critical contradiction. Any document that grants durable authority directly from confidence, probability, saturation, similarity, or model output fails GU-3 regardless of aggregate score.

---

# Slice 1: Core architecture documents 01-04

## Baseline assessment

Baseline was measured against `main` at `2bf1f6b` before remediation.

| Document | GU-1 | GU-2 | GU-3 | GU-4 | GU-5 | GU-6 | GU-7 | GU-8 | GU-9 | GU-10 | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `01-layer-model.md` | 4 | 1 | 4 | 1 | 3 | 2 | 3 | 0 | 1 | 1 | 50% |
| `02-lifecycle-state-machine.md` | 4 | 1 | 4 | 2 | 4 | 2 | 4 | 0 | 1 | 2 | 60% |
| `03-scoring-and-decay.md` | 3 | 3 | 4 | 2 | 3 | 3 | 2 | 0 | 3 | 3 | 65% |
| `04-governance-and-pama.md` | 3 | 2 | 4 | 2 | 4 | 4 | 4 | 0 | 2 | 2 | 68% |

### `01-layer-model.md`

Strengths:

- deterministic identity is already explicit
- saturation, certification, and authority are separated
- mutation capability is explicitly separated from mutation authority

Gaps:

- no named probabilistic epistemic responsibility
- no rule for carrying estimator uncertainty into governance
- no bounded-stochastic-action rule
- no explicit distinction between estimator output and policy outcome

Remediation target:

- classify layers by control character
- add an explicit epistemic/governance boundary
- require estimator provenance where probabilistic outputs affect memory
- state that stochastic choice may occur only after policy filtering

### `02-lifecycle-state-machine.md`

Strengths:

- state machine is naturally deterministic and auditable
- transition metadata already records authority, evidence, confidence, saturation, and ledger references
- promotion and crystallization are distinct transitions

Gaps:

- threshold outputs can appear to directly drive transitions without an explicit proposal/commit split
- no behavior for uncertain or conflicting estimators
- no hysteresis or threshold-jitter treatment
- no estimator/method version in transition evidence

Remediation target:

- separate transition proposal from transition commit
- make estimator outputs inputs to governance, not state mutation instructions
- define escalation/abstention for uncertainty near consequential boundaries
- record estimator and policy versions

### `03-scoring-and-decay.md`

Strengths:

- strongest pre-existing separation of confidence, saturation, authority, certification, and risk
- explicitly states that no score grants permanence
- already requires calibration and trap classes

Gaps:

- calibration is centered on threshold selection rather than uncertainty quality
- no confidence intervals or calibration-error concept
- no estimator disagreement, drift, abstention, or hysteresis handling
- point estimates may appear more precise than their evidence warrants

Remediation target:

- define score uncertainty as first-class metadata
- add calibration error, drift, and decision-boundary stability checks
- require abstention/escalation zones where false irreversible transitions are costly

### `04-governance-and-pama.md`

Strengths:

- authority is already separate from confidence and saturation
- risk and reversibility are already first-class PAMA inputs
- finite authority outcomes already exist
- enforcement is located at mutation boundaries

Gaps:

- PAMA inputs do not explicitly include uncertainty quality, estimator provenance, or estimator disagreement
- no rule that PAMA outcome mapping must be deterministic or formally bounded for a fixed input/policy snapshot
- no explicit allowance for stochastic choice among already-permitted actions
- no fail-safe behavior when policy or estimator state cannot be reconstructed

Remediation target:

- add governed-uncertainty inputs and decision receipt fields
- define deterministic/formally bounded authority resolution
- permit bounded stochastic choice only after authorization
- fail closed or escalate when authority cannot be reconstructed for high-consequence actions

## Slice 1 completion criteria

Slice 1 may be merged when:

- [ ] all four documents are remediated against their stated targets
- [ ] no existing invariant is weakened
- [ ] no document grants authority directly from a probabilistic estimate
- [ ] changed files remain documentation-only
- [ ] post-remediation scores are recorded here
- [ ] branch diff is reviewed against `main`
- [ ] merge uses the verified head SHA

## Remaining audit queue

Next slices should evaluate, in order:

1. `05-repo-implementation-map.md` through `10-memory-unit-examples.md`
2. `11-component-architecture.md` through `14-expanded-scope-recommendations.md`
3. planned/implemented `15` through `19` documents, where present
4. `20-memory-foundations-across-scales.md` through `24-determinism-probability-and-governed-uncertainty.md`
5. all ADRs, with special attention to authority, lifecycle, retention/deletion, observability, recovery, and quality metrics
6. schemas and fixtures
7. README and cross-document consistency

Each slice should preserve baseline and post-remediation measurements so doctrine evolution remains inspectable rather than anecdotal.
