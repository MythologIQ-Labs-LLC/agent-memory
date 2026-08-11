# Repository Governance

Agent Memory is a public reference architecture with one canonical doctrine tree, not a collection of equally authoritative implementation opinions.

## Stewardship and maintainer

The repository is stewarded by **MythologIQ Labs LLC** through `MythologIQ-Labs-LLC/agent-memory`.

The current repository maintainer and doctrine owner is **Kevin R. Knapp** (`@Knapp-Kevin`). Organization stewardship does not rewrite individual authorship provenance.

PAMA is native Agent Memory doctrine authored by Kevin R. Knapp. External implementations may conform to, challenge, or extend the doctrine through the contribution process, but they do not acquire doctrine ownership by implementing it.

## MythologIQ Labs contribution standard

Agent Memory adopts [`docs/policies/AI_ASSISTED_CONTRIBUTIONS.md`](docs/policies/AI_ASSISTED_CONTRIBUTIONS.md) as both a repository rule and the default MythologIQ Labs standard for AI-assisted contribution workflows.

The standard deliberately separates **implementation method** from **contributor accountability**:

- coding agents and AI-assisted development are allowed;
- contributors are not required to hand-write implementation code;
- a responsible human must direct and review the specific contribution and be able to explain and defend its meaningful behavior;
- ordinary repository submissions and maintainer-review interactions remain human-accountable unless a bot or agent has explicit repository authorization;
- autonomous contribution is not accepted by default;
- external repositories may impose stricter rules, which control when contributing upstream.

Repository-specific policy may narrow automation privileges but must not silently weaken this human-accountability baseline.

## Decision classes

Changes are reviewed according to their consequence.

### Editorial

Examples:

- grammar and formatting;
- clearer examples;
- corrected links;
- non-semantic navigation improvements.

These should not change doctrine meaning.

### Evidence

Examples:

- new research;
- benchmark results;
- source-rights records;
- implementation mappings;
- adversarial fixtures;
- runtime evidence.

Evidence may support, challenge, or narrow existing doctrine. Adding evidence does not automatically change an ADR.

### Contract

Examples:

- schema changes;
- fixture-semantic changes;
- conformance-level changes;
- adapter contracts;
- telemetry/interchange contracts;
- PAMA machine-readable interfaces.

Contract changes require compatibility analysis and validation updates.

### Doctrine / ADR

Examples:

- changing an architectural invariant;
- changing the meaning of PAMA authority classes;
- changing lifecycle semantics;
- accepting, superseding, or rejecting an ADR.

Doctrine changes require explicit rationale, affected-surface analysis, evidence, and a preserved decision trail.

## Evidence rule

A merged statement should make its epistemic status clear.

Where material, distinguish:

```text
native doctrine
external evidence
implementation observation
conformance evidence
runtime proof
hypothesis
analogy
```

A validator passing is evidence about the validator's declared contract. It is not automatic proof of production behavior.

## Public-source and reuse-rights rule

Contributors must follow `docs/SOURCE_RIGHTS_POLICY.md`.

Public availability does not imply permission to copy expressive material. External sources should normally be linked and independently synthesized unless a stronger reuse basis is both necessary and documented.

## Merge expectations

A change is merge-ready when:

1. the intended consequence is explicit;
2. affected doctrine and contracts are internally consistent;
3. source provenance and reuse rights are resolved;
4. tests/validators relevant to the change pass;
5. the responsible human has reviewed the specific contribution and can explain its meaningful behavior;
6. required contribution provenance is satisfied;
7. the PR distinguishes what it proves from what remains unproven;
8. material disagreement is either resolved or recorded rather than silently erased.

## Implementation neutrality

Named products and repositories appear in Agent Memory only when they add a concrete implementation, comparison, interoperability, or conformance value.

Conceptual adjacency does not create architectural ownership.

## Security-sensitive changes

Security-sensitive findings should follow `SECURITY.md`. Do not force public disclosure merely to satisfy normal issue-tracking ceremony.

AI assistance does not reduce the review bar for cryptography, authentication, authorization, policy enforcement, isolation boundaries, provenance, destructive lifecycle actions, or other security-sensitive surfaces. Independent validation is required when self-referential tests could mask an implementation error.

## Forks and derivative works

The Apache-2.0 license permits forks and derivative works under its terms. A derivative project may change its own doctrine, but it should not present modified doctrine as an unchanged canonical decision of this repository.

The canonical upstream doctrine is the state merged into `MythologIQ-Labs-LLC/agent-memory` unless an explicit release or version reference says otherwise.
