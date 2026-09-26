# Repository Governance

Agent Memory is the canonical repository for a governed memory product/runtime, its architecture and doctrine, and its evaluation/benchmark laboratory.

It is not a collection of equally authoritative implementation opinions, and it is no longer accurately described as only a reference architecture.

The repository operating model is defined in [`docs/REPOSITORY_OPERATING_MODEL.md`](docs/REPOSITORY_OPERATING_MODEL.md).

## Stewardship and maintainer

The repository is stewarded by **MythologIQ Labs LLC** through `MythologIQ-Labs-LLC/agent-memory`.

The current repository maintainer and doctrine owner is **Kevin R. Knapp** (`@Knapp-Kevin`). Organization stewardship does not rewrite individual authorship provenance.

PAMA is native Agent Memory doctrine authored by Kevin R. Knapp. External implementations may conform to, challenge, or extend the doctrine through the contribution process, but they do not acquire doctrine ownership by implementing it.

## Repository roles

Agent Memory currently operates in three first-class roles:

```text
product/runtime
architecture/governance laboratory
evaluation/benchmark laboratory
```

Each role may produce evidence that affects the others, but no role grants itself authority automatically.

### Product/runtime

The repository contains an installed developer-facing runtime and qualified bounded execution profiles. Runtime behavior can falsify architecture assumptions and may require doctrine clarification, but an implementation shortcut does not become canonical doctrine merely because it shipped.

### Architecture/governance laboratory

The repository remains the canonical home for Agent Memory architecture, ADRs, PAMA, lifecycle/currentness semantics, and authority boundaries. Canonical means decision-owning, not immune from challenge.

### Evaluation/benchmark laboratory

The repository contains benchmark adapters, frozen evidence, evaluator-integrity probes, common evidence contracts, normalized manifests, comparisons, and scorecards. Benchmark results are evidence about measured behavior, never memory authority and never automatic doctrine changes.

## AI-assisted contribution authority

Agent Memory adopts [`docs/policies/AI_ASSISTED_CONTRIBUTIONS.md`](docs/policies/AI_ASSISTED_CONTRIBUTIONS.md) as its repository policy for AI-assisted development and human-directed agent execution.

The policy separates implementation method from repository authority:

- coding agents and AI-assisted development are allowed;
- contributors and maintainers are not required to hand-write code or manually perform every repository API action;
- a responsible human remains accountable for the objective, material risk, and delegated authority;
- authenticated agents may perform repository actions when directly delegated in a bounded working session or authorized by standing repository policy;
- unbounded autonomous contribution is not accepted by default;
- direct delegation inside Agent Memory does not create authority to act in external repositories;
- upstream contribution rules control when they are stricter.

Agent Memory's policy is authoritative only for this repository. Organization-wide contribution-policy inheritance is governed outside this repository and is not implied by local adoption.

DCO is not an active Agent Memory gate until explicit activation and enforcement are merged and discoverable.

## Decision classes

Changes are reviewed according to their consequence.

### Editorial

Examples:

- grammar and formatting;
- clearer examples;
- corrected links;
- non-semantic navigation improvements.

These should not change doctrine, product contract, benchmark denominator, or evidence meaning.

### Evidence / evaluation

Examples:

- new research;
- benchmark results;
- source-rights records;
- implementation mappings;
- adversarial fixtures;
- runtime evidence;
- evaluator-integrity probes;
- normalized benchmark manifests and scorecards.

Evidence may support, challenge, or narrow existing doctrine or product assumptions. Adding evidence does not automatically change an ADR or runtime contract.

### Product / runtime

Examples:

- developer-facing behavior;
- recall/ranking changes;
- lifecycle execution;
- persistence and recovery behavior;
- substrate implementation;
- runtime concurrency or scaling changes.

Product changes require tests and contract compatibility analysis where applicable. When the change remediates a benchmark-discovered defect, the relevant frozen benchmark should be replayed when valid and practical.

### Contract

Examples:

- schema changes;
- fixture-semantic changes;
- conformance-level changes;
- adapter contracts;
- telemetry/interchange contracts;
- PAMA machine-readable interfaces;
- benchmark-run evidence contracts.

Contract changes require compatibility analysis and validation updates.

### Doctrine / ADR

Examples:

- changing an architectural invariant;
- changing the meaning of PAMA authority classes;
- changing lifecycle or currentness semantics;
- changing the relationship between ranking, admission, and authority;
- accepting, superseding, or rejecting an ADR.

Doctrine changes require explicit rationale, affected-surface analysis, evidence, and a preserved decision trail.

## Evidence rule

Agent Memory adopts [`docs/policies/EVIDENCE_PROMOTION.md`](docs/policies/EVIDENCE_PROMOTION.md) as the source-neutral evidence and doctrine-promotion policy.

> **Origin establishes provenance, not evidentiary privilege.**

This applies to every material input, including native doctrine, maintainer or contributor statements, AI-generated analysis, practitioner feedback, external research, standards, implementations, benchmarks, production observations, and external corpora.

A merged statement should make its epistemic status clear.

Where material, distinguish:

```text
native doctrine
product contract
implementation
external evidence
conformance evidence
benchmark evidence
field evidence
runtime proof
hypothesis
analogy
```

Native authorship establishes provenance and repository ownership of a decision. It does not prove the decision correct. External publication or popularity does not prove a claim correct either. Accepted ADRs remain challengeable and may be narrowed, superseded, or rejected when stronger evidence justifies a change.

A validator passing is evidence about the validator's declared contract. It is not automatic proof of production behavior.

## Benchmark and evaluation governance

Evaluation is governed by the same evidence discipline as the rest of the repository.

Required invariants include:

```text
benchmark score != truth
benchmark score != recall admission
benchmark score != mutation authority
benchmark result != doctrine automatically
benchmark improvement != production readiness
implementation evidence != doctrine acceptance
```

An ADR proposal may be merged as **Proposed** so that it can be reviewed, tested, and challenged in-tree. Merging a proposal does not accept it. Acceptance (`Proposed -> Accepted`) is a separate maintainer ruling on the recorded evidence, and it is never implied by an implementation landing or a benchmark improving. For example, ADR-039 is Proposed while its reference profile is implemented behind policy 3.0.0.

Benchmark adapters and reports must preserve exact revision/input/configuration identity where comparability depends on them.

Missing or blocked evidence must remain visibly missing or blocked. `not_run`, `not_measured`, `not_applicable`, and `blocked` must not be silently converted to zero.

A benchmark harness change must not silently alter product behavior. A product remediation must not silently alter the benchmark denominator, frozen input, or evaluator semantics used to prove the before/after result.

### Benchmark-discovered defects

When an external or internal benchmark exposes a material defect, the preferred learning loop is:

```text
observation
  -> classify the failure
  -> open a bounded product/architecture/evaluation issue
  -> remediate
  -> replay the same frozen workload where valid
  -> record improvement, regression, and remaining limitations
```

A benchmark-discovered defect should not be closed only because focused unit tests pass when the originating workload can directly exercise the repaired path.

One benchmark finding may be a hypothesis. Convergence across independent benchmark families is stronger evidence of a general product or architecture weakness.

No benchmark-specific special case may enter runtime behavior solely to improve a score.

## Architecture-learning governance

The repository is allowed to evolve its architecture in response to evidence. It is not allowed to rewrite architecture reflexively whenever a metric is red.

Before promoting a benchmark or field observation into doctrine, identify whether the evidence indicates:

```text
architecture validated
implementation defect
architecture gap
runtime/product contract gap
evaluation defect or gap
benchmark mismatch / non-applicable assumption
inconclusive result
```

The smallest defensible remediation is preferred over broad architecture replacement unless evidence demonstrates the existing boundary itself is wrong.

## Public-source and reuse-rights rule

Contributors must follow `docs/SOURCE_RIGHTS_POLICY.md`.

Public availability does not imply permission to copy expressive material. External sources should normally be linked and independently synthesized unless a stronger reuse basis is both necessary and documented.

Benchmark datasets and reference implementations retain their own licenses and attribution requirements. Frozen input identity does not imply redistribution permission.

## Merge expectations

A change is merge-ready when:

1. the intended consequence and principal change class are explicit;
2. affected doctrine, product behavior, benchmark semantics, and contracts are internally consistent;
3. source provenance and reuse rights are resolved;
4. tests/validators relevant to the change pass;
5. repository authority for any agent-executed action is bounded and accountable;
6. any explicitly active contribution-provenance requirement is satisfied;
7. the PR distinguishes what it proves from what remains unproven;
8. material disagreement is either resolved or recorded rather than silently erased;
9. benchmark-discovered defect remediations include before/after replay evidence when that workload can validly exercise the fix;
10. documentation surfaces that would otherwise become misleading are updated in the same change or explicitly tracked.

Where a task specifies exact-head validation, that validated head is the merge boundary. A later head must be revalidated rather than inheriting trust from an earlier result.

## Implementation neutrality

Named products and repositories appear in Agent Memory only when they add a concrete implementation, comparison, interoperability, ancestry, or conformance value.

Conceptual adjacency does not create architectural ownership.

EvolveAI, CodeGenome, COREFORGE, UOR-derived mechanisms, Jev/Jev-Mem, and other peers may contribute mechanisms or evidence without becoming mandatory runtime dependencies. Generic memory behavior implemented natively here remains owned by Agent Memory unless an explicit architectural decision states otherwise.

## Security-sensitive changes

Security-sensitive findings should follow `SECURITY.md`. Do not force public disclosure merely to satisfy normal issue-tracking ceremony.

AI assistance does not reduce the review bar for cryptography, authentication, authorization, policy enforcement, isolation boundaries, provenance, destructive lifecycle actions, or other security-sensitive surfaces. Independent validation is required when self-referential tests could mask an implementation error.

Benchmark pressure is never justification for weakening a security or governance boundary without an explicit architecture/governance decision.

## Forks and derivative works

The Apache-2.0 license permits forks and derivative works under its terms. A derivative project may change its own doctrine, but it should not present modified doctrine as an unchanged canonical decision of this repository.

The canonical upstream doctrine is the state merged into `MythologIQ-Labs-LLC/agent-memory` unless an explicit release or version reference says otherwise.
