# Future Subsystem: Multi-Agent Shared Memory Protocol

**Status: future subsystem. Not a core component.** This note exists because the prerequisite guardrails now exist — actor scope, consent, and tenancy ([`../29-actor-scope-consent-and-tenancy.md`](../29-actor-scope-consent-and-tenancy.md)), privacy and sensitivity ([`../19-privacy-and-sensitivity-classifier.md`](../19-privacy-and-sensitivity-classifier.md)), and interoperability profiles ([`../35-interoperability-profiles.md`](../35-interoperability-profiles.md)). Promotion into the component architecture requires its own ADR, protocol specification, and conformance surface.

## Concept

Shared memory across agents, teams, or organizations multiplies memory's value and its blast radius by the same factor. Every single-system failure mode in the threat model acquires a propagation vector: one poisoned memory becomes every subscriber's poisoned memory, one over-broad scope becomes an organization-wide leak, one agent's bad correction becomes everyone's regression.

## Ownership model

- Every shared memory has exactly one **owner principal** (doc 29) — the authority for correction, scope change, and deletion. Sharing distributes *access*, never ownership.
- Shared spaces (team pools, organizational memory) are themselves owned: a space has an owning principal, a scope record, and admission policy. "Commons" without an owner is how contamination becomes permanent.
- Ownership transfer is a governed mutation with receipts, not a side effect of copying.

## Agent identity and delegation

- Every participating agent has a resolvable identity and acts under a delegation chain terminating at an accountable principal — scoped, purpose-bound, time-bounded, non-transitive by default, per doc 29.
- An agent's writes into shared memory carry its identity and delegation ref; anonymous shared writes are unattributable sources and classed accordingly ([`../16-source-trust-and-reputation.md`](../16-source-trust-and-reputation.md)).
- Agent-to-agent assertion is a distinct source class: agent B's claim received by agent A is evidence *that B asserted it*, never direct evidence of the claim — trust composes across the chain, and it attenuates; it does not launder.

## Tenant and role-based recall

- Cross-tenant boundaries are absolute per doc 29: shared spaces exist *within* a tenancy scope, and the cross-tenant relevance trap ([`../../fixtures/cross-tenant-relevance-trap.json`](../../fixtures/cross-tenant-relevance-trap.json)) applies with shared-pool stakes.
- Recall from a shared space evaluates the *recalling* agent's scope, role, purpose, and delegation — membership in a space is candidacy, not admission; the governed recall planner ([`../26-governed-recall-planner.md`](../26-governed-recall-planner.md)) runs on the receiving side.
- Sensitivity handling composes: a memory admissible to agent A working purpose P is not thereby admissible to A working purpose Q, and export from shared space to private context is a scope decision, not a copy.

## Shared correction and dispute

- Corrections route to the owner principal; consumers may dispute. A dispute in shared memory propagates to all subscribers *as dispute state* — blocked from canonical use everywhere at once, which is the point.
- Divergent local corrections of a shared memory are a conflict class for [`../17-conflict-resolution-engine.md`](../17-conflict-resolution-engine.md): resolution is governed, receipted, and propagated; last-writer-wins across agents is the concurrent-mutation failure with more writers.
- The human contract ([`../38-human-correction-ux-contract.md`](../38-human-correction-ux-contract.md)) survives sharing: a user correcting memory about themselves reaches every space that memory was shared into, with propagation receipts.

## Contamination and poisoning mitigations

- **Admission control**: writes into shared spaces pass source trust and sensitivity checks at the space boundary, not just the writer's local policy.
- **Provenance quarantine**: memory derived from one agent's uncertified inference stays marked through every hop; subscribers can quarantine by lineage — see [`../../fixtures/sleeper-memory-poisoning.json`](../../fixtures/sleeper-memory-poisoning.json).
- **Blast-radius accounting**: shared-space mutations carry higher effective risk class per the proportionality dimensions of `04-governance-and-pama.md` (scope and fan-out are inputs, and sharing maximizes both).
- **Revocation propagation**: deletion, correction, and certification-revocation propagate to subscribers with receipts per [`../28-retention-deletion-and-tombstones.md`](../28-retention-deletion-and-tombstones.md); a shared space that cannot demonstrate propagation cannot claim Profile 6.

## Promotion criteria into core

The protocol becomes core only when: an ADR proposes it; the six conformance cases sketched in `14-expanded-scope-recommendations.md` exist as fixtures (plus poisoning-propagation and correction-propagation cases); the protocol is expressed as adapter contracts over [`../34-adapter-contracts.md`](../34-adapter-contracts.md); and two implementations demonstrate governed exchange under Profile 6 evidence.
