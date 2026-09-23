# ADR-006: Neurospace Is Product Runtime Ancestry, Not Agent Memory Ownership

## Status

Accepted; refined by [ADR-036](ADR-036-same-owner-components-are-first-party-modules.md)

## Context

COREFORGE Vault and Neurospace provide a product/runtime model where agents assemble, traverse, retrieve, and use memory. Direct inspection established that this is real implementation ancestry: Vault/Neurospace contains memory domains, source references, context broker/engine/packets, graph recall, decay-ranked retrieval, lineage, mutation boundaries, and product-facing memory workflows.

The original version of this ADR called Neurospace the canonical operational runtime-memory role in the current implementation map. That described a useful transition state while Agent Memory itself lacked a comparable native runtime surface.

It is **not** the destination architecture.

Agent Memory now owns the generic runtime-memory and context-assembly contracts. COREFORGE/Neurospace may donate proven mechanisms and product lessons, then consume Agent Memory as those capabilities become native.

## Decision

**Agent Memory owns generic runtime memory, governed recall, context assembly semantics, lifecycle/currentness, provenance, correction, forgetting, and memory-domain behavior.**

COREFORGE Vault / Neurospace is classified as:

- first-party product/runtime implementation ancestry;
- a source of mechanisms and behavioral evidence worth harvesting;
- a future downstream consumer of Agent Memory's canonical memory subsystem.

The intended direction is:

```text
historical/current transition state
COREFORGE contains/emulates memory machinery
        |
        v
harvest proven generic mechanisms into Agent Memory
        |
        v
Agent Memory owns generic memory runtime semantics
        |
        v
COREFORGE consumes Agent Memory
```

COREFORGE may continue to own product-specific responsibilities such as local packaging, encryption, UX, offline orchestration, inference integration, caching, or product policy. Those product responsibilities do not make Vault/Neurospace the owner of generic Agent Memory semantics.

Candidate generation and ranking may remain probabilistic. Recall admission must still enforce currentness, policy, tenant/isolation, sensitivity, dispute, and scope constraints before memory influences active cognition.

## Consequences

### Positive

- reverses the dependency in the intended direction: products consume Agent Memory rather than Agent Memory stitching product runtimes together;
- preserves useful COREFORGE runtime lessons without making COREFORGE mandatory for Agent Memory;
- gives Cortera, TARA, agents, and other products one canonical memory subsystem to consume;
- permits product-specific Vault/Neurospace UX and privacy behavior to remain specialized;
- allows Agent Memory to test generic memory behavior independently of a COREFORGE deployment.

### Negative

- overlapping generic memory machinery in COREFORGE must eventually be thinned, delegated, or clearly classified as product-local adaptation;
- migration needs explicit compatibility for memory identity, lineage, context packets, local encryption boundaries, and offline behavior;
- temporary duplication may exist while native Agent Memory functionality catches up to proven COREFORGE mechanisms.

## Runtime rule

```text
operationally_useful != canonical
highly_relevant != authorized_for_context
product_implementation != canonical_memory_owner
```

A memory may be useful in a context window without being crystallized, and a relevant memory may still be prohibited from recall.

A COREFORGE product feature may also be excellent without becoming the canonical implementation boundary for every Agent Memory consumer.

## Acceptance scope

Accepted establishes Neurospace and Vault as first-party runtime ancestry and a downstream product relationship.

It does **not** claim:

- that the current COREFORGE/Neurospace implementation satisfies every Agent Memory doctrine or conformance requirement;
- that COREFORGE is required for Agent Memory runtime operation;
- that Vault owns generic Agent Memory persistence or lifecycle semantics; or
- that context broker/packet behavior may bypass Agent Memory governed recall admission.

## Doctrine

Agent Memory is where generic memory semantics are owned.

Neurospace is one place those semantics can be productized and used.
