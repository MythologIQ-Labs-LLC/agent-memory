# Governed Uncertainty

Agent Memory does not require deterministic cognition. It requires uncertain inference to remain separate from permission to create consequences.

> **Probabilistic epistemics. Governed consequences.**  
> **Uncertainty may propose. Authority constrains.**

## The control pipeline

```text
experience / request
      ↓
estimate / proposal
      ↓
governance envelope
      ↓
permitted action set
      ↓
selection
      ↓
committed consequence
      ↓
receipt + state transition
```

A selector may be deterministic or stochastic. The invariant is that it cannot choose outside the permitted set.

```text
selected_action ∈ permitted_action_set
```

## Where determinism belongs

Deterministic or formally bounded controls are especially valuable for:

- exact identity and references
- schema validity
- tenant and scope binding
- capability/authorization checks
- provenance requirements
- lifecycle transition legality
- policy-version binding
- state/version matching
- cryptographic verification

These are the substrate constraints that should not depend on a model “feeling confident.”

## Where probability belongs

Probabilistic, learned, or heuristic components are useful for:

- relevance
- confidence
- contradiction detection
- source trust
- sensitivity inference
- staleness
- utility
- clustering
- summarization
- causal hypotheses
- poisoning likelihood

The estimates can influence the decision. They do not define their own authority.

## Governance envelope

The governance layer maps uncertain evidence plus hard constraints into a finite set of allowed consequences.

Examples:

- permit ephemeral use but prohibit durable mutation
- permit recall but redact sensitive fields
- permit a reversible correction but prohibit destructive deletion
- allow stochastic ranking only among tenant-authorized candidates
- require verification before promotion
- block an action when delegation has expired

## Consequence classes

A useful mental model is to increase governance strength with permanence and blast radius:

| Class | Typical consequence |
|---|---|
| 0 | observation or ephemeral analysis |
| 1 | reversible runtime influence |
| 2 | durable mutation |
| 3 | shared, canonical, or sensitive effects |
| 4 | irreversible, security, or privilege-critical effects |

## Determinism is not automatically safety

A deterministic rule can be reproducibly wrong. A threshold can be exact while encoding bad assumptions. A formally bounded action set can still be unsafe if the policy is wrong.

The architecture therefore requires challenge tests for:

- brittle policies
- estimator-policy coupling
- state races
- hidden stochasticity
- false formalism
- over-conservative blocking
- human-review laundering

## ADR-020 status

The doctrine and structural contracts exist, but **ADR-020 remains Proposed** because the repository still needs real end-to-end runtime evidence showing uncertainty is contained within a governed action envelope.

## Canonical sources

- Governed uncertainty: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/24-determinism-probability-and-governed-uncertainty.md
- ADR-020: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/adr/ADR-020-probabilistic-discovery-deterministic-governance.md
- Decision receipt schema: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/schemas/decision-receipt.schema.json

## Next

- **[PAMA](PAMA)** for proportional mutation authority
- **[Conformance and Evidence](Conformance-and-Evidence)** for the runtime proof bar
