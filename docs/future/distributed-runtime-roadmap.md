# Future Subsystem: Distributed Memory Runtime Roadmap

**Status: proposed roadmap. Not implemented. Not qualified. Authority effect: none.**

This note exists so the single-host boundary reads as a milestone rather than a ceiling, and so nobody mistakes the roadmap for a capability. It is grounded in the substrate inventory ([`../43-substrate-inventory-and-maturity.md`](../43-substrate-inventory-and-maturity.md)), the production qualification rule in its section 10, and the project boundary for a future distinct runtime product ([`../AGENT_MEMORY_PROJECT_MODEL.md`](../AGENT_MEMORY_PROJECT_MODEL.md), issue [#556](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/556)). It creates no new implementation issue; opening one is an owner decision.

## What is true today

| Claim | State | Evidence |
|---|---|---|
| One production-credible canonical substrate is RC-qualified for a single host | **qualified** | `SQLiteTemporalGraph` under `sqlite_single_host_v1`, issue #427 closed through PR #452 |
| Reference checkpoint/restart correctness is proven | **proven (reference profile)** | `InMemoryTemporalGraph` under the #363 remediation program, [`../46-state-checkpoint-contract.md`](../46-state-checkpoint-contract.md) |
| A Graphiti adapter exists | **experimental** | `GraphitiSubstrate`; deprecated upstream driver path; no canonical restart profile |
| Rust kernel | **shadow only** | deterministic-primitive parity under #602; Python remains the qualified runtime ([`../66-rust-runtime-qualification-current-state.md`](../66-rust-runtime-qualification-current-state.md)) |
| Postgres, graph databases, Markdown/files, object stores | **storage technologies, not substrates** | [`../43-substrate-inventory-and-maturity.md`](../43-substrate-inventory-and-maturity.md) section 8 |
| Distributed / multi-host persistence, consensus, partition tolerance, horizontal scale | **not claimed** | `SQLiteTemporalGraph` explicitly disclaims leader election, partition handling, and distributed scale |

```text
qualified single-host SQLite != distributed runtime support
substrate adapter exists     != substrate qualified
storage technology           != Agent Memory substrate
```

## Why the direction is still right

The architecture already separates canonical state (the temporal/canonical substrate behind `TemporalGraphPort`), governed admission and mutation authority (PAMA), and derived state (projections, candidate routes, representation caches). That separation is what makes a multi-substrate runtime possible without changing memory semantics: a substrate earns a profile by satisfying the same correctness obligations, not by being a popular database. "No single shape of memory is best for everything" is therefore a design direction the current code can honour, not a feature it has shipped. The composition program that would prove it, representation by representation, is issue [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636); this roadmap covers only the persistence-topology axis of that program.

## Proposed stages

Each stage is gated by the qualification rule in [`../43-substrate-inventory-and-maturity.md`](../43-substrate-inventory-and-maturity.md) section 10. No stage promotes the next by association, and none changes doctrine.

| Stage | Outcome | Gate before it can be claimed |
|---|---|---|
| 0. Single-host SQLite (current) | one qualified canonical substrate | complete (#427 / PR #452) |
| 1. Substrate contract hardening | the canonical-substrate behavioural surface, transaction/generation semantics, and restart/deletion/scope obligations are stated as a testable contract that a second implementation can target | contract and conformance fixtures accepted; `SQLiteTemporalGraph` passes them unchanged |
| 2. Second native single-host substrate | a relational or graph substrate (candidate classes: Postgres; a modern Graphiti backend; another durable temporal provider) implements the contract on one host | restart, stale-writer, torn-write, deletion-residue, tenancy, and no-authority-from-storage evidence on the exact backend version; operational characterization published |
| 3. Multi-process, single authority | several processes share one canonical substrate with runtime-owned serialization and compare-and-commit generations | the existing single-handle threading contract ([`../47-developer-facade-and-local-open-path.md`](../47-developer-facade-and-local-open-path.md)) is extended with executable multi-writer evidence; no change to PAMA or admission |
| 4. Replicated canonical state | canonical state survives host loss through replication with an explicit consistency profile | consensus or leader-election mechanism named, versioned, and qualified; partition behaviour fails closed; derived state remains rebuildable; deletion completeness holds across replicas |
| 5. Federated / multi-tenant topologies | isolation domains map onto deployment boundaries | ADR-022 governed-crossing semantics proven across hosts; see [`multi-agent-shared-memory-protocol.md`](multi-agent-shared-memory-protocol.md) |

Markdown, files, and object stores remain candidates for bounded artifacts, backup, evidence, or derived state at every stage. They are not on this ladder as canonical substrates unless a profile earns it through the same rule.

## Non-claims

- Nothing above is scheduled, funded, or assigned. Sequencing is a proposal.
- Finishing a stage does not make Agent Memory "distributed-ready"; only the explicit profile that was qualified is supported.
- A future hardened runtime product may carry some of this work under a different identity and licensing boundary ([#556](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/556)). That boundary is undecided.
- Benchmark results on a distributed profile would be a new evidence identity, never comparable to single-host rows by default.

## Promotion criteria into core

Any stage enters canonical documentation only when: an ADR or accepted profile names it; the substrate inventory is updated to the maturity actually earned in the same change (inventory section 12); executable evidence exists at the exact backend version; and the README runtime entry point is updated to match. Until then this page is the only place the roadmap should be described, and it should keep saying "proposed".
