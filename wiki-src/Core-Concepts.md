# Core Concepts

Agent Memory is easiest to understand as a set of boundaries. Most failures happen when two useful concepts are collapsed into one convenient but misleading field.

## Core definition

> **Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

That includes facts, episodes, preferences, procedures, corrections, decisions, policies, evidence, and inherited state.

## Persistence horizons

A horizon answers **how far state survives**, not what kind of state it is.

`Immediate → Working → Session → Episodic → Long-term → Remote → Inherited`

A procedural memory can be session-local or inherited. A decision record can be short-lived or permanent evidence. “Long-term memory” is therefore a horizon, not one universal storage bucket.

## Memory content types

Common types include:

- observation
- episodic memory
- semantic memory
- procedural memory
- prospective memory
- preference
- relationship state
- policy
- failure
- correction
- decision
- evidence
- compact environment/model state
- inherited memory

## Signals are not interchangeable

| Signal | Means | Does **not** mean |
|---|---|---|
| Identity | Exact object/reference | Truth or usefulness |
| Confidence | Support for an estimate | Authority |
| Probability | Uncertainty with defined semantics | Generic score |
| Similarity | Representational closeness | Correctness |
| Source trust | Expected reliability in a scope | Permission |
| Relevance | Usefulness to the current task | Recall authorization |
| Saturation | Lifecycle persistence pressure | Truth |
| Sensitivity | Handling/privacy risk | Low utility |
| Scope | Where memory is valid/visible | Global truth |
| Authority | Permission for a consequence | Evidence quality |
| Certification | Required confirmation passed | Immutability |
| Contradiction | Retained states conflict | Automatic winner selection |

## High-value invariants

```text
identity != memory
retrieval != memory
confidence != authority
trust != authority
relevance != permission
saturation != truth
utility != deletion authority
proposal != commit
historical truth != current truth
chronology != causality
uncertain sensitivity != non-sensitive
adaptation != authority
memory != procedure
procedure != permission
permission != governance
```

## Historical truth versus current truth

A memory can remain historically valid while no longer describing the present.

```text
historically true != currently true
stale != false
superseded != corrected
```

Agent Memory keeps those distinctions because silently overwriting history destroys evidence.

## Canonical sources

- Glossary: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/00-glossary.md
- Layer model: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/01-layer-model.md
- Memory theory: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/22-agentic-memory-theory-and-development.md

## Next

- **[PAMA](PAMA)** for adaptive authority
- **[Lifecycle and Forgetting](Lifecycle-and-Forgetting)** for persistence and deletion
- **[Governed Uncertainty](Governed-Uncertainty)** for probabilistic inference under bounded authority
